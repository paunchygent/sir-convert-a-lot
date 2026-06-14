"""Audio transcript runtime types and artifact constants.

Purpose:
    Define the stable runtime data structures shared by audio transcript
    execution, progress projection, and artifact publication.

Relationships:
    - Imported by `infrastructure.audio_transcript_bundle_runtime` for the
      v2 executor boundary.
    - Imported by artifact routing and job-runner code that project audio
      progress and canonical transcript JSON metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TRANSCRIPT_JSON_SCHEMA_VERSION = "transcript_json_v1"
TRANSCRIPT_JSON_ARTIFACT_KEY = "transcript_json"
TRANSCRIPT_JSON_FILENAME = "transcript_json.json"


@dataclass(frozen=True, slots=True)
class AudioProgressUpdateV2:
    """Route-specific progress update for audio transcript jobs."""

    stage: str
    audio_total_media_seconds: float | None = None
    audio_processed_media_seconds: float | None = None
    audio_percent_complete: float | None = None
    audio_current_chunk_index: int | None = None
    audio_total_chunks: int | None = None
    audio_pipeline_percent_complete: float | None = None
    audio_pipeline_eta_seconds: int | None = None
    phase_timings_ms: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AudioTranscriptBundleExecutionResult:
    """Successful audio transcript execution result for v2 conversion wrapping."""

    artifact_bytes: bytes
    backend_used: str
    acceleration_used: str
    warnings: list[str]
    phase_timings_ms: dict[str, int] = field(default_factory=dict)
