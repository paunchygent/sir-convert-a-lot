"""Named artifact resolution for transcript-bundle jobs.

Purpose:
    Resolve the canonical transcript JSON artifact for audio transcript jobs
    and product-neutral formatter artifacts for audio and replay
    transcript-bundle jobs.

Relationships:
    - Used by `interfaces.http_routes_job_artifacts_v2`.
    - Reads transcript artifacts produced by audio transcript execution and
      formatter replay execution.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs_v2 import SourceFormatV2
from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
    CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT,
    TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS,
    TRANSCRIPT_FORMATTER_DEFINITIONS_BY_KEY,
    TranscriptFormatterArtifactDefinition,
    render_transcript_formatter_outputs,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    TRANSCRIPT_JSON_ARTIFACT_KEY,
    TRANSCRIPT_JSON_FILENAME,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class ResolvedAudioTranscriptArtifact:
    """Filesystem and response metadata for one audio transcript artifact."""

    path: Path
    content_type: str
    filename: str


def build_audio_transcript_artifact_manifest(*, job: StoredJobV2) -> dict[str, object]:
    """Build a public named-artifact manifest for a transcript-bundle job."""

    artifacts: list[dict[str, object]] = []
    if job.source_format != SourceFormatV2.TRANSCRIPT_JSON:
        artifacts.append(
            {
                "artifact_key": TRANSCRIPT_JSON_ARTIFACT_KEY,
                "availability": "available",
                "filename": TRANSCRIPT_JSON_FILENAME,
                "content_type": "application/json",
                "size_bytes": job.artifact_size_bytes,
                "sha256": job.artifact_sha256,
                "retrieval_path": _retrieval_path(
                    job=job,
                    artifact_key=TRANSCRIPT_JSON_ARTIFACT_KEY,
                ),
            }
        )
    artifacts.extend(
        _formatter_manifest_entry(job=job, definition=definition)
        for definition in TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS
    )
    return {
        "api_version": "v2",
        "job_id": job.job_id,
        "output_format": job.output_format.value,
        "artifacts": artifacts,
    }


def write_requested_transcript_formatter_artifacts(
    *,
    job: StoredJobV2,
    canonical_json_bytes: bytes,
) -> None:
    """Write requested formatter artifacts beside canonical transcript JSON."""

    requested = _requested_output_artifacts(job)
    requested_formatters = requested.difference({CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT})
    if not requested_formatters:
        return
    try:
        payload = json.loads(canonical_json_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _formatter_precondition_error() from exc
    if not isinstance(payload, Mapping):
        raise _formatter_precondition_error()
    try:
        rendered = render_transcript_formatter_outputs(canonical_payload=payload)
    except ValidationError as exc:
        raise _formatter_precondition_error() from exc
    for definition in TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS:
        if definition.output_artifact not in requested_formatters:
            continue
        artifact_bytes = rendered[definition.artifact_key]
        _artifact_path(job=job, filename=definition.filename).write_bytes(artifact_bytes)


def resolve_audio_transcript_artifact(
    *,
    job: StoredJobV2,
    artifact_key: str,
) -> ResolvedAudioTranscriptArtifact:
    """Resolve an available transcript artifact or fail with a governed error."""

    if artifact_key == TRANSCRIPT_JSON_ARTIFACT_KEY:
        if job.source_format == SourceFormatV2.TRANSCRIPT_JSON:
            raise ServiceError(
                status_code=404,
                code="transcript_replay_artifact_unavailable",
                message="Transcript formatter replay does not emit canonical JSON artifacts.",
                retryable=False,
                details={"artifact_key": artifact_key},
            )
        if (
            not job.artifact_path.exists()
            and TRANSCRIPT_JSON_ARTIFACT_KEY not in job.terminal_artifact_object_refs
        ):
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
    definition = TRANSCRIPT_FORMATTER_DEFINITIONS_BY_KEY.get(artifact_key)
    if definition is not None:
        requested = _requested_output_artifacts(job)
        if definition.output_artifact not in requested:
            raise ServiceError(
                status_code=409,
                code=_unavailable_code(job),
                message="Requested transcript formatter artifact was not requested for this job.",
                retryable=False,
                details={"artifact_key": artifact_key, "availability": "unrequested"},
            )
        path = _artifact_path(job=job, filename=definition.filename)
        if not path.exists() and artifact_key not in job.terminal_artifact_object_refs:
            raise ServiceError(
                status_code=409,
                code=_unavailable_code(job),
                message="Requested transcript formatter artifact is unavailable.",
                retryable=False,
                details={"artifact_key": artifact_key, "availability": "unavailable"},
            )
        return ResolvedAudioTranscriptArtifact(
            path=path,
            content_type=definition.content_type,
            filename=definition.filename,
        )
    raise ServiceError(
        status_code=404,
        code=_unavailable_code(job),
        message="Named transcript artifact key is not recognized.",
        retryable=False,
        details={"artifact_key": artifact_key},
    )


def _formatter_manifest_entry(
    *,
    job: StoredJobV2,
    definition: TranscriptFormatterArtifactDefinition,
) -> dict[str, object]:
    artifact_key = definition.artifact_key
    output_artifact = definition.output_artifact
    filename = definition.filename
    content_type = definition.content_type
    requested = _requested_output_artifacts(job)
    base = {
        "artifact_key": artifact_key,
        "content_type": content_type,
        "filename": filename,
    }
    if output_artifact not in requested:
        return {
            **base,
            "availability": "unrequested",
            "unavailable_code": _unavailable_code(job),
        }
    path = _artifact_path(job=job, filename=filename)
    if not path.exists():
        ref = job.terminal_artifact_object_refs.get(artifact_key)
        if ref is None:
            return {
                **base,
                "availability": "unavailable",
                "unavailable_code": _unavailable_code(job),
            }
        return {
            **base,
            "availability": "available",
            "size_bytes": ref.size_bytes,
            "sha256": ref.sha256,
            "retrieval_path": _retrieval_path(job=job, artifact_key=artifact_key),
        }
    artifact_bytes = path.read_bytes()
    return {
        **base,
        "availability": "available",
        "size_bytes": len(artifact_bytes),
        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "retrieval_path": _retrieval_path(job=job, artifact_key=artifact_key),
    }


def _requested_output_artifacts(job: StoredJobV2) -> frozenset[str]:
    if job.source_format == SourceFormatV2.TRANSCRIPT_JSON:
        replay_options = job.spec.transcript_formatter_options
        if replay_options is None:
            return frozenset()
        return frozenset(artifact.value for artifact in replay_options.requested_artifacts)
    audio_options = job.spec.audio_transcription_options
    if audio_options is None:
        return frozenset({CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT})
    return frozenset(audio_options.output_artifacts)


def _artifact_path(*, job: StoredJobV2, filename: str) -> Path:
    return job.artifact_path.parent / filename


def _retrieval_path(*, job: StoredJobV2, artifact_key: str) -> str:
    return f"/v2/convert/jobs/{job.job_id}/artifacts/{artifact_key}"


def _formatter_precondition_error() -> ServiceError:
    return ServiceError(
        status_code=500,
        code="audio_transcript_artifact_unavailable",
        message="Canonical transcript JSON is invalid for formatter artifact generation.",
        retryable=False,
    )


def _unavailable_code(job: StoredJobV2) -> str:
    if job.source_format == SourceFormatV2.TRANSCRIPT_JSON:
        return "transcript_replay_artifact_unavailable"
    return "audio_transcript_artifact_unavailable"
