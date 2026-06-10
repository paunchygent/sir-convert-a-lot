"""Transcript-bundle execution and canonical JSON packaging.

Purpose:
    Execute admitted audio transcript-bundle jobs through the internal STT
    sidecar boundary, validate diarized segment output, and package the first
    canonical transcript JSON artifact without exposing sidecar secrets or
    backend-native model details.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for
      `audio -> transcript_bundle` jobs.
    - Uses `domain.audio_transcription_policy` for sidecar readiness decisions.
    - Emits progress updates consumed by `infrastructure.runtime_job_runner_v2`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    STT_SIDECAR_CONTRACT_VERSION,
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    evaluate_stt_sidecar_readiness,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    AudioTranscriptionSidecarClient,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfConversionCanceledV2,
)

TRANSCRIPT_JSON_SCHEMA_VERSION = "transcript_json_v1"
TRANSCRIPT_JSON_ARTIFACT_KEY = "transcript_json"
TRANSCRIPT_JSON_FILENAME = "transcript_json.json"

_PLACEHOLDER_SPEAKER_LABELS = frozenset(
    {
        "",
        "diarization_unavailable",
        "speaker",
        "speaker_unknown",
        "unknown",
    }
)
_ALLOWED_RUNTIME_METADATA_KEYS = frozenset(
    {
        "acceleration_used",
        "normalization_profile",
    }
)


@dataclass(frozen=True, slots=True)
class AudioProgressUpdateV2:
    """Route-specific progress update for audio transcript jobs."""

    stage: str
    audio_total_media_seconds: float | None = None
    audio_processed_media_seconds: float | None = None
    audio_percent_complete: float | None = None
    audio_current_chunk_index: int | None = None
    audio_total_chunks: int | None = None


@dataclass(frozen=True, slots=True)
class AudioTranscriptBundleExecutionResult:
    """Successful audio transcript execution result for v2 conversion wrapping."""

    artifact_bytes: bytes
    backend_used: str
    acceleration_used: str
    warnings: list[str]
    phase_timings_ms: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _TranscriptSegment:
    segment_id: str
    start_seconds: float
    end_seconds: float
    speaker_label: str
    text: str
    language: str | None
    confidence: float | None


def execute_audio_transcript_bundle_job(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    sidecar: AudioTranscriptionSidecarClient,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    is_cancel_requested: Callable[[], bool] | None,
) -> AudioTranscriptBundleExecutionResult:
    """Execute one admitted audio job and persist canonical transcript JSON."""

    del config
    _emit_progress(progress_callback, AudioProgressUpdateV2(stage="probing_media"))
    health = sidecar.health()
    capabilities = sidecar.capabilities()
    readiness = evaluate_stt_sidecar_readiness(
        health_payload=health,
        capability_payload=capabilities,
    )
    if not readiness.ready:
        error_code = readiness.error_code or AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE
        raise ServiceError(
            status_code=503,
            code=error_code.value,
            message="Audio transcription sidecar is not ready.",
            retryable=True,
            details=dict(readiness.details),
        )

    _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)
    _emit_progress(progress_callback, AudioProgressUpdateV2(stage="transcribing"))
    sidecar_request = _build_sidecar_request(job=job)
    response = sidecar.transcribe(sidecar_request)
    _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)
    _emit_progress(progress_callback, AudioProgressUpdateV2(stage="aligning_segments"))
    artifact_payload = _build_transcript_payload(
        job=job,
        response=response,
        readiness_profiles=readiness.profile_labels,
    )
    artifact_bytes = json.dumps(
        artifact_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    job.artifact_path.write_bytes(artifact_bytes)
    media = _required_mapping(response, "media")
    duration_seconds = _required_float(media, "duration_seconds")
    chunks = _required_sequence(media, "chunks")
    _emit_progress(
        progress_callback,
        AudioProgressUpdateV2(
            stage="packaging",
            audio_total_media_seconds=duration_seconds,
            audio_processed_media_seconds=duration_seconds,
            audio_percent_complete=100.0,
            audio_current_chunk_index=max(0, len(chunks) - 1),
            audio_total_chunks=len(chunks),
        ),
    )
    runtime_metadata = artifact_payload["metadata"]
    if not isinstance(runtime_metadata, Mapping):
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    runtime_obj = runtime_metadata.get("runtime")
    acceleration_used = "rocm"
    if isinstance(runtime_obj, Mapping):
        acceleration_obj = runtime_obj.get("acceleration_used")
        if isinstance(acceleration_obj, str) and acceleration_obj.strip() != "":
            acceleration_used = acceleration_obj
    warnings = _string_list(response.get("warnings"))
    return AudioTranscriptBundleExecutionResult(
        artifact_bytes=artifact_bytes,
        backend_used="stt_sidecar",
        acceleration_used=acceleration_used,
        warnings=warnings,
    )


def _build_sidecar_request(*, job: StoredJobV2) -> dict[str, object]:
    options = job.spec.audio_transcription_options
    if options is None:
        raise ServiceError(
            status_code=422,
            code=AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED.value,
            message="Audio transcription options are required for transcript execution.",
            retryable=False,
        )
    diarization = options.diarization
    return {
        "request_handle": job.job_id,
        "source": {
            "kind": "local_upload",
            "path": job.upload_path.as_posix(),
            "filename": job.source_filename,
        },
        "options": {
            "language": options.language,
            "max_duration_seconds": options.max_duration_seconds,
            "output_schema_version": TRANSCRIPT_JSON_SCHEMA_VERSION,
            "diarization": {
                "mode": diarization.mode.value,
                "num_speakers": diarization.num_speakers,
                "min_speakers": diarization.min_speakers,
                "max_speakers": diarization.max_speakers,
            },
        },
    }


def _build_transcript_payload(
    *,
    job: StoredJobV2,
    response: Mapping[str, object],
    readiness_profiles: Mapping[str, str],
) -> dict[str, object]:
    status = _required_string(response, "status")
    if status != "succeeded":
        error_code = _sidecar_error_code(response)
        raise ServiceError(
            status_code=502,
            code=error_code.value,
            message="Audio transcription sidecar failed the job.",
            retryable=error_code == AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE,
            details={"sidecar_status": status},
        )
    segments = _parse_segments(_required_sequence(response, "segments"))
    if not segments:
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    language = _required_mapping(response, "language")
    diarization = _required_mapping(response, "diarization")
    media = _required_mapping(response, "media")
    diarization_status = _required_string(diarization, "status")
    if diarization_status != "succeeded":
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
    requested_options = job.spec.audio_transcription_options
    if requested_options is None:
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED)
    duration_seconds = _required_float(media, "duration_seconds")
    chunks = _parse_chunks(_required_sequence(media, "chunks"))
    source_sha256 = hashlib.sha256(job.upload_path.read_bytes()).hexdigest()
    normalized_audio_sha256 = _optional_string(media, "normalized_audio_sha256")
    if normalized_audio_sha256 is None:
        normalized_audio_sha256 = "sha256:unreported"
    return {
        "schema_version": TRANSCRIPT_JSON_SCHEMA_VERSION,
        "artifact_key": TRANSCRIPT_JSON_ARTIFACT_KEY,
        "source": {
            "filename": job.source_filename,
            "format": job.source_format.value,
        },
        "transcript": {
            "text": _required_string(response, "transcript_text"),
        },
        "segments": [
            {
                "segment_id": segment.segment_id,
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "speaker_label": segment.speaker_label,
                "text": segment.text,
                "language": segment.language,
                "confidence": segment.confidence,
            }
            for segment in segments
        ],
        "language": {
            "requested": requested_options.language,
            "detected": _required_string(language, "detected"),
            "confidence": _optional_float(language, "confidence"),
        },
        "diarization": {
            "requested_mode": requested_options.diarization.mode.value,
            "used_mode": _optional_string(diarization, "mode_used")
            or requested_options.diarization.mode.value,
            "status": diarization_status,
        },
        "media": {
            "duration_seconds": duration_seconds,
            "chunk_count": len(chunks),
            "chunks": chunks,
        },
        "metadata": {
            "source": {
                "sha256": f"sha256:{source_sha256}",
            },
            "normalized_audio_sha256": normalized_audio_sha256,
            "runtime": _sanitized_runtime_metadata(
                response=response,
                readiness_profiles=readiness_profiles,
            ),
        },
        "warnings": _string_list(response.get("warnings")),
    }


def _sanitized_runtime_metadata(
    *,
    response: Mapping[str, object],
    readiness_profiles: Mapping[str, str],
) -> dict[str, object]:
    runtime_metadata = response.get("runtime_metadata")
    sanitized: dict[str, object] = {
        "sidecar_contract_version": STT_SIDECAR_CONTRACT_VERSION,
    }
    stt_profile = readiness_profiles.get("stt_profile")
    diarization_profile = readiness_profiles.get("diarization_profile")
    if stt_profile is not None:
        sanitized["stt_profile"] = stt_profile
    if diarization_profile is not None:
        sanitized["diarization_profile"] = diarization_profile
    if isinstance(runtime_metadata, Mapping):
        for key, value in runtime_metadata.items():
            if key in _ALLOWED_RUNTIME_METADATA_KEYS and isinstance(value, str):
                sanitized[key] = value
    return sanitized


def _parse_segments(entries: Sequence[object]) -> list[_TranscriptSegment]:
    segments: list[_TranscriptSegment] = []
    previous_end = 0.0
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        segment = _TranscriptSegment(
            segment_id=_required_string(entry, "segment_id"),
            start_seconds=_required_float(entry, "start_seconds"),
            end_seconds=_required_float(entry, "end_seconds"),
            speaker_label=_required_string(entry, "speaker_label"),
            text=_required_string(entry, "text"),
            language=_optional_string(entry, "language"),
            confidence=_optional_float(entry, "confidence"),
        )
        if segment.start_seconds < previous_end or segment.end_seconds <= segment.start_seconds:
            raise _invalid_sidecar_response(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)
        normalized_speaker = segment.speaker_label.strip().lower()
        if normalized_speaker in _PLACEHOLDER_SPEAKER_LABELS:
            raise _invalid_sidecar_response(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
        previous_end = segment.end_seconds
        segments.append(segment)
    return segments


def _parse_chunks(entries: Sequence[object]) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        chunks.append(
            {
                "chunk_index": _required_int(entry, "chunk_index"),
                "start_seconds": _required_float(entry, "start_seconds"),
                "end_seconds": _required_float(entry, "end_seconds"),
                "overlap_seconds": _optional_float(entry, "overlap_seconds") or 0.0,
            }
        )
    if not chunks:
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return chunks


def _sidecar_error_code(response: Mapping[str, object]) -> AudioTranscriptionErrorCode:
    value = response.get("error_code")
    if isinstance(value, str):
        try:
            return AudioTranscriptionErrorCode(value)
        except ValueError:
            return AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED
    return AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED


def _raise_if_canceled(
    is_cancel_requested: Callable[[], bool] | None,
    *,
    sidecar: AudioTranscriptionSidecarClient,
    request_handle: str,
) -> None:
    if is_cancel_requested is None or not is_cancel_requested():
        return
    sidecar.cancel(request_handle)
    raise PdfConversionCanceledV2(job_id=request_handle)


def _emit_progress(
    callback: Callable[[AudioProgressUpdateV2], None] | None,
    update: AudioProgressUpdateV2,
) -> None:
    if callback is not None:
        callback(update)


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return {str(nested_key): nested_value for nested_key, nested_value in value.items()}


def _required_sequence(payload: Mapping[str, object], key: str) -> Sequence[object]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return value


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _required_float(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)


def _optional_float(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise _invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    return [item for item in value if isinstance(item, str)]


def _invalid_sidecar_response(error_code: AudioTranscriptionErrorCode) -> ServiceError:
    return ServiceError(
        status_code=502,
        code=error_code.value,
        message="Audio transcription sidecar returned an invalid transcript payload.",
        retryable=False,
    )
