"""Audio transcript sidecar request builders.

Purpose:
    Build provider-neutral request payloads for media probe, global
    diarization, and deterministic chunk transcription without leaking
    backend-native STT or diarization settings into the main service.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime`.
    - References chunk windows from `infrastructure.audio_transcript_chunking`
      and public audio options from stored Service API v2 jobs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_chunking import AudioChunkWindow
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    TRANSCRIPT_JSON_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def build_sidecar_request(*, job: StoredJobV2) -> dict[str, object]:
    """Build the base internal sidecar request for an audio job."""

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


def build_diarization_request(
    *,
    base_request: Mapping[str, object],
    normalized_audio_handle: str | None,
    normalized_audio_sha256: str,
) -> dict[str, object]:
    """Build a global diarization request for normalized audio."""

    request = dict(base_request)
    request["normalized_audio"] = {
        "handle": normalized_audio_handle,
        "sha256": normalized_audio_sha256,
    }
    return request


def build_chunk_request(
    *,
    base_request: Mapping[str, object],
    chunk: AudioChunkWindow,
    normalized_audio_handle: str | None,
    normalized_audio_sha256: str,
) -> dict[str, object]:
    """Build a deterministic chunk transcription request."""

    request = build_diarization_request(
        base_request=base_request,
        normalized_audio_handle=normalized_audio_handle,
        normalized_audio_sha256=normalized_audio_sha256,
    )
    request["chunk"] = chunk.to_payload()
    return request


def source_media_sha256(job: StoredJobV2) -> str:
    """Return the source upload hash used to validate checkpoints."""

    return f"sha256:{hashlib.sha256(job.upload_path.read_bytes()).hexdigest()}"
