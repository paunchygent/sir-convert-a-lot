"""Named artifact resolution for audio transcript bundles.

Purpose:
    Resolve the canonical transcript JSON artifact and explicitly unavailable
    formatter artifacts for successful audio transcript-bundle jobs.

Relationships:
    - Used by `interfaces.http_routes_job_artifacts_v2`.
    - Reads transcript artifacts produced by
      `infrastructure.audio_transcript_bundle_runtime`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    TRANSCRIPT_JSON_ARTIFACT_KEY,
    TRANSCRIPT_JSON_FILENAME,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2

_FORMATTER_ARTIFACT_KEYS = frozenset(
    {
        "transcript_txt",
        "transcript_md",
        "transcript_vtt",
        "transcript_srt",
    }
)


@dataclass(frozen=True)
class ResolvedAudioTranscriptArtifact:
    """Filesystem and response metadata for one audio transcript artifact."""

    path: Path
    content_type: str
    filename: str


def build_audio_transcript_artifact_manifest(*, job: StoredJobV2) -> dict[str, object]:
    """Build a public named-artifact manifest for a transcript-bundle job."""

    return {
        "api_version": "v2",
        "job_id": job.job_id,
        "output_format": job.output_format.value,
        "artifacts": [
            {
                "artifact_key": TRANSCRIPT_JSON_ARTIFACT_KEY,
                "availability": "available",
                "filename": TRANSCRIPT_JSON_FILENAME,
                "content_type": "application/json",
                "size_bytes": job.artifact_size_bytes,
                "sha256": job.artifact_sha256,
            },
            {
                "artifact_key": "transcript_txt",
                "availability": "not_implemented",
                "unavailable_code": "audio_transcript_artifact_unavailable",
            },
            {
                "artifact_key": "transcript_md",
                "availability": "not_implemented",
                "unavailable_code": "audio_transcript_artifact_unavailable",
            },
            {
                "artifact_key": "transcript_vtt",
                "availability": "not_implemented",
                "unavailable_code": "audio_transcript_artifact_unavailable",
            },
            {
                "artifact_key": "transcript_srt",
                "availability": "not_implemented",
                "unavailable_code": "audio_transcript_artifact_unavailable",
            },
        ],
    }


def resolve_audio_transcript_artifact(
    *,
    job: StoredJobV2,
    artifact_key: str,
) -> ResolvedAudioTranscriptArtifact:
    """Resolve an available transcript artifact or fail with a governed error."""

    if artifact_key == TRANSCRIPT_JSON_ARTIFACT_KEY:
        if not job.artifact_path.exists():
            raise ServiceError(
                status_code=500,
                code="audio_transcript_artifact_unavailable",
                message="Transcript JSON artifact is missing from a successful job.",
                retryable=True,
                details={"artifact_key": artifact_key},
            )
        return ResolvedAudioTranscriptArtifact(
            path=job.artifact_path,
            content_type="application/json",
            filename=TRANSCRIPT_JSON_FILENAME,
        )
    if artifact_key in _FORMATTER_ARTIFACT_KEYS:
        raise ServiceError(
            status_code=409,
            code="audio_transcript_artifact_unavailable",
            message="Requested transcript formatter artifact is not implemented yet.",
            retryable=False,
            details={"artifact_key": artifact_key, "availability": "not_implemented"},
        )
    raise ServiceError(
        status_code=404,
        code="audio_transcript_artifact_unavailable",
        message="Named transcript artifact key is not recognized.",
        retryable=False,
        details={"artifact_key": artifact_key},
    )
