"""Transcript formatter replay runtime for Service API v2.

Purpose:
    Execute stateless formatter replay from uploaded canonical transcript JSON
    plus typed speaker display-name overlays, producing product-neutral TXT,
    Markdown, WebVTT, and SRT artifacts without source audio or STT access.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for
      `transcript_json -> transcript_bundle`.
    - Reuses `domain.transcript_formatter_artifacts` rendering strategies from
      the accepted Task 358 formatter implementation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.audio_transcription_options_v2 import (
    TranscriptFormatterReplayOptionsV2,
)
from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
    TRANSCRIPT_FORMATTER_DEFINITIONS_BY_OUTPUT,
    CanonicalTranscriptPayload,
    TranscriptFormatterArtifactDefinition,
    TranscriptSegmentPayload,
    render_validated_transcript_formatter_outputs,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    TRANSCRIPT_JSON_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2

TRANSCRIPT_FORMATTER_REPLAY_RESULT_SCHEMA_VERSION = "transcript_formatter_replay_result_v1"
TRANSCRIPT_FORMATTER_REPLAY_PIPELINE = "transcript_json_to_transcript_bundle_replay_v2"


@dataclass(frozen=True, slots=True)
class TranscriptFormatterReplayExecutionResult:
    """Successful replay execution result for v2 conversion wrapping."""

    artifact_bytes: bytes
    warnings: list[str]
    phase_timings_ms: dict[str, int] = field(default_factory=dict)


def execute_transcript_formatter_replay_job(
    *,
    job: StoredJobV2,
) -> TranscriptFormatterReplayExecutionResult:
    """Execute one transcript formatter replay job."""

    options = job.spec.transcript_formatter_options
    if options is None:
        raise _invalid_replay_request(reason="missing_options")
    transcript = _load_canonical_transcript(job.upload_path)
    _validate_replay_transcript(transcript)
    _validate_override_inventory(transcript=transcript, options=options)
    projected = _project_display_labels(transcript=transcript, options=options)
    rendered = render_validated_transcript_formatter_outputs(transcript=projected)
    definitions = _requested_definitions(options)
    for definition in definitions:
        artifact_bytes = rendered[definition.artifact_key]
        _artifact_path(job=job, filename=definition.filename).write_bytes(artifact_bytes)
    primary_payload = _build_replay_result_manifest(job=job, definitions=definitions)
    primary_bytes = json.dumps(
        primary_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return TranscriptFormatterReplayExecutionResult(
        artifact_bytes=primary_bytes,
        warnings=[],
    )


def _load_canonical_transcript(upload_path: Path) -> CanonicalTranscriptPayload:
    try:
        payload = json.loads(upload_path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _invalid_replay_request(reason="malformed_json") from exc
    if not isinstance(payload, Mapping):
        raise _invalid_replay_request(reason="non_object_json")
    try:
        return CanonicalTranscriptPayload.model_validate(payload)
    except ValidationError as exc:
        raise _invalid_replay_request(reason="non_canonical_transcript") from exc


def _validate_replay_transcript(transcript: CanonicalTranscriptPayload) -> None:
    if transcript.diarization.status != "succeeded":
        raise _invalid_replay_request(reason="partial_transcript")


def _validate_override_inventory(
    *,
    transcript: CanonicalTranscriptPayload,
    options: TranscriptFormatterReplayOptionsV2,
) -> None:
    inventory = frozenset(segment.speaker_label for segment in transcript.segments)
    for override in options.speaker_label_overrides:
        if override.canonical_speaker_label not in inventory:
            raise _invalid_replay_request(reason="unknown_speaker_label")


def _project_display_labels(
    *,
    transcript: CanonicalTranscriptPayload,
    options: TranscriptFormatterReplayOptionsV2,
) -> CanonicalTranscriptPayload:
    override_map = {
        override.canonical_speaker_label: override.display_name
        for override in options.speaker_label_overrides
    }
    projected_segments: list[TranscriptSegmentPayload] = []
    for segment in transcript.segments:
        display_label = override_map.get(segment.speaker_label, segment.speaker_label)
        projected_segments.append(segment.model_copy(update={"speaker_label": display_label}))
    return transcript.model_copy(update={"segments": projected_segments})


def _requested_definitions(
    options: TranscriptFormatterReplayOptionsV2,
) -> tuple[TranscriptFormatterArtifactDefinition, ...]:
    return tuple(
        TRANSCRIPT_FORMATTER_DEFINITIONS_BY_OUTPUT[artifact.value]
        for artifact in options.requested_artifacts
    )


def _build_replay_result_manifest(
    *,
    job: StoredJobV2,
    definitions: tuple[TranscriptFormatterArtifactDefinition, ...],
) -> dict[str, object]:
    return {
        "schema_version": TRANSCRIPT_FORMATTER_REPLAY_RESULT_SCHEMA_VERSION,
        "api_version": "v2",
        "job_id": job.job_id,
        "source_schema_version": TRANSCRIPT_JSON_SCHEMA_VERSION,
        "output_format": job.output_format.value,
        "artifacts": [
            _available_manifest_entry(job=job, definition=definition) for definition in definitions
        ],
    }


def _available_manifest_entry(
    *,
    job: StoredJobV2,
    definition: TranscriptFormatterArtifactDefinition,
) -> dict[str, object]:
    path = _artifact_path(job=job, filename=definition.filename)
    artifact_bytes = path.read_bytes()
    return {
        "artifact_key": definition.artifact_key,
        "availability": "available",
        "content_type": definition.content_type,
        "filename": definition.filename,
        "size_bytes": len(artifact_bytes),
        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "retrieval_path": f"/v2/convert/jobs/{job.job_id}/artifacts/{definition.artifact_key}",
    }


def _artifact_path(*, job: StoredJobV2, filename: str) -> Path:
    return job.artifact_path.parent / filename


def _invalid_replay_request(*, reason: str) -> ServiceError:
    return ServiceError(
        status_code=422,
        code="transcript_formatter_replay_invalid",
        message="Transcript formatter replay request is invalid.",
        retryable=False,
        details={"reason": reason},
    )
