"""Audio transcript checkpoint merge response builder.

Purpose:
    Merge accepted chunk checkpoints with probe and diarization metadata into
    the canonical sidecar-like response consumed by transcript JSON packaging.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime` after Task 357
      chunk execution completes.
    - Validates final ordering through `audio_transcript_alignment` before any
      terminal artifact is persisted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_alignment import (
    validate_global_segment_order,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_checkpoints import (
    AcceptedAudioChunkCheckpoint,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_chunking import AudioChunkPlan
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_payloads import (
    invalid_sidecar_response,
    optional_string,
    required_mapping,
    required_string,
    string_list,
)


def build_checkpointed_sidecar_response(
    *,
    plan: AudioChunkPlan,
    probe_response: Mapping[str, object],
    diarization_response: Mapping[str, object],
    checkpoints: Mapping[int, AcceptedAudioChunkCheckpoint],
) -> dict[str, object]:
    """Merge accepted chunk checkpoints into a transcript response."""

    segments: list[dict[str, object]] = []
    for chunk in plan.chunks:
        checkpoint = checkpoints.get(chunk.chunk_index)
        if checkpoint is None or not checkpoint.alignment_validated:
            raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        segments.extend(dict(segment) for segment in checkpoint.transcript_segments)
    validate_global_segment_order(segments)
    media = required_mapping(probe_response, "media")
    diarization = required_mapping(diarization_response, "diarization")
    first_language = _first_language(segments)
    return {
        "status": "succeeded",
        "transcript_text": " ".join(required_string(segment, "text") for segment in segments),
        "segments": segments,
        "language": {"detected": first_language, "confidence": None},
        "diarization": {
            "status": required_string(diarization, "status"),
            "mode_used": optional_string(diarization, "mode_used") or "auto",
        },
        "media": {
            "duration_seconds": plan.total_media_seconds,
            "normalized_audio_sha256": required_string(media, "normalized_audio_sha256"),
            "chunks": [chunk.to_payload() for chunk in plan.chunks],
        },
        "runtime_metadata": _runtime_metadata_from_probe(probe_response),
        "warnings": string_list(probe_response.get("warnings"))
        + string_list(diarization_response.get("warnings")),
    }


def _first_language(segments: Sequence[Mapping[str, object]]) -> str:
    for segment in segments:
        language = optional_string(segment, "language")
        if language is not None:
            return language
    return "auto"


def _runtime_metadata_from_probe(probe_response: Mapping[str, object]) -> Mapping[str, object]:
    runtime_metadata = probe_response.get("runtime_metadata")
    if isinstance(runtime_metadata, Mapping):
        return {str(key): value for key, value in runtime_metadata.items()}
    return {}
