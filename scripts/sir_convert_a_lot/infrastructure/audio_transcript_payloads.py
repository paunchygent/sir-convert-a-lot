"""Audio transcript canonical JSON payload builder.

Purpose:
    Validate merged chunk transcript responses and build the canonical
    `transcript_json` artifact while preserving fail-closed diarization and
    sanitized runtime metadata.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime` after all
      chunks have accepted checkpoints.
    - Shares runtime constants from `audio_transcript_runtime_types` with the
      public artifact routing layer.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    STT_SIDECAR_CONTRACT_VERSION,
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    TRANSCRIPT_JSON_ARTIFACT_KEY,
    TRANSCRIPT_JSON_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2

PLACEHOLDER_SPEAKER_LABELS = frozenset(
    {
        "",
        "diarization_unavailable",
        "speaker",
        "speaker_unknown",
        "unknown",
    }
)
ALLOWED_RUNTIME_METADATA_KEYS = frozenset(
    {
        "acceleration_used",
        "normalization_profile",
    }
)


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """Validated transcript segment for canonical JSON output."""

    segment_id: str
    start_seconds: float
    end_seconds: float
    speaker_label: str
    text: str
    language: str | None
    confidence: float | None


def build_transcript_payload(
    *,
    job: StoredJobV2,
    response: Mapping[str, object],
    readiness_profiles: Mapping[str, str],
) -> dict[str, object]:
    """Build the canonical transcript JSON payload for one completed job."""

    status = required_string(response, "status")
    if status != "succeeded":
        error_code = sidecar_error_code(response)
        raise ServiceError(
            status_code=502,
            code=error_code.value,
            message="Audio transcription sidecar failed the job.",
            retryable=error_code == AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE,
            details={"sidecar_status": status},
        )
    segments = parse_segments(required_sequence(response, "segments"))
    if not segments:
        raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    language = required_mapping(response, "language")
    diarization = required_mapping(response, "diarization")
    media = required_mapping(response, "media")
    diarization_status = required_string(diarization, "status")
    if diarization_status != "succeeded":
        raise invalid_sidecar_response(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
    requested_options = job.spec.audio_transcription_options
    if requested_options is None:
        raise invalid_sidecar_response(AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED)
    duration_seconds = required_float(media, "duration_seconds")
    chunks = parse_chunks(required_sequence(media, "chunks"))
    source_sha256 = hashlib.sha256(job.upload_path.read_bytes()).hexdigest()
    normalized_audio_sha256 = optional_string(media, "normalized_audio_sha256")
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
            "text": required_string(response, "transcript_text"),
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
            "detected": required_string(language, "detected"),
            "confidence": optional_float(language, "confidence"),
        },
        "diarization": {
            "requested_mode": requested_options.diarization.mode.value,
            "used_mode": optional_string(diarization, "mode_used")
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
            "runtime": sanitized_runtime_metadata(
                response=response,
                readiness_profiles=readiness_profiles,
            ),
        },
        "warnings": string_list(response.get("warnings")),
    }


def sanitized_runtime_metadata(
    *,
    response: Mapping[str, object],
    readiness_profiles: Mapping[str, str],
) -> dict[str, object]:
    """Return public-safe runtime metadata for the artifact."""

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
            if key in ALLOWED_RUNTIME_METADATA_KEYS and isinstance(value, str):
                sanitized[key] = value
    return sanitized


def parse_segments(entries: Sequence[object]) -> list[TranscriptSegment]:
    """Parse and validate canonical transcript segments."""

    segments: list[TranscriptSegment] = []
    previous_end = 0.0
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        segment = TranscriptSegment(
            segment_id=required_string(entry, "segment_id"),
            start_seconds=required_float(entry, "start_seconds"),
            end_seconds=required_float(entry, "end_seconds"),
            speaker_label=required_string(entry, "speaker_label"),
            text=required_string(entry, "text"),
            language=optional_string(entry, "language"),
            confidence=optional_float(entry, "confidence"),
        )
        if segment.start_seconds < previous_end or segment.end_seconds <= segment.start_seconds:
            raise invalid_sidecar_response(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)
        normalized_speaker = segment.speaker_label.strip().lower()
        if normalized_speaker in PLACEHOLDER_SPEAKER_LABELS:
            raise invalid_sidecar_response(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
        previous_end = segment.end_seconds
        segments.append(segment)
    return segments


def parse_chunks(entries: Sequence[object]) -> list[dict[str, object]]:
    """Parse media chunk metadata for the canonical artifact."""

    chunks: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        chunks.append(
            {
                "chunk_index": required_int(entry, "chunk_index"),
                "start_seconds": required_float(entry, "start_seconds"),
                "end_seconds": required_float(entry, "end_seconds"),
                "overlap_seconds": optional_float(entry, "overlap_seconds") or 0.0,
            }
        )
    if not chunks:
        raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return chunks


def sidecar_error_code(response: Mapping[str, object]) -> AudioTranscriptionErrorCode:
    """Return a governed error code from a sidecar failure response."""

    value = response.get("error_code")
    if isinstance(value, str):
        try:
            return AudioTranscriptionErrorCode(value)
        except ValueError:
            return AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED
    return AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED


def required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    """Return a required nested mapping from a sidecar response."""

    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return {str(nested_key): nested_value for nested_key, nested_value in value.items()}


def required_sequence(payload: Mapping[str, object], key: str) -> Sequence[object]:
    """Return a required sequence from a sidecar response."""

    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return value


def required_string(payload: Mapping[str, object], key: str) -> str:
    """Return a required non-empty string from a sidecar response."""

    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)


def optional_string(payload: Mapping[str, object], key: str) -> str | None:
    """Return an optional non-empty string from a sidecar response."""

    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def required_float(payload: Mapping[str, object], key: str) -> float:
    """Return a required number from a sidecar response."""

    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)


def optional_float(payload: Mapping[str, object], key: str) -> float | None:
    """Return an optional number from a sidecar response."""

    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def required_int(payload: Mapping[str, object], key: str) -> int:
    """Return a required integer from a sidecar response."""

    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)


def string_list(value: object) -> list[str]:
    """Return only string entries from a sidecar warnings list."""

    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    return [item for item in value if isinstance(item, str)]


def invalid_sidecar_response(error_code: AudioTranscriptionErrorCode) -> ServiceError:
    """Build the standard invalid-sidecar response error."""

    return ServiceError(
        status_code=502,
        code=error_code.value,
        message="Audio transcription sidecar returned an invalid transcript payload.",
        retryable=False,
    )
