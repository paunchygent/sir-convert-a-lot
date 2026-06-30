"""Request-scoped correction replay artifact-set storage.

Purpose:
    Persist immutable correction replay artifact sets and verify nested
    artifact downloads against the exact correction request identity that
    produced them.

Relationships:
    - Used by `infrastructure.correction_replay_artifact_writer` after accepted
      correction apply batches render target bytes.
    - Used by the v2 nested correction replay artifact route to resolve
      artifact-set references without falling back to source-job latest bytes.
    - Publishes typed reference DTOs from
      `application.exam_authoring_corrections_apply_models`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from scripts.sir_convert_a_lot.application.exam_authoring_correction_replay_artifacts import (
    ExamAuthoringCorrectionReplayArtifactDefinition,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionReplayArtifactReferenceV1,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionTargetV1,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2

CORRECTION_REPLAY_ARTIFACT_SET_SCHEMA_VERSION: Final[
    Literal["correction_replay_artifact_set_manifest_v1"]
] = "correction_replay_artifact_set_manifest_v1"
CORRECTION_REPLAY_ARTIFACT_REFERENCE_SCHEMA_VERSION: Final[
    Literal["correction_replay_artifact_reference_v1"]
] = "correction_replay_artifact_reference_v1"
CORRECTION_REPLAY_PROFILE_VERSION = "digiexam_correction_replay_v1"


@dataclass(frozen=True)
class CorrectionReplayArtifactSetIdentity:
    """Normalized request identity for one correction replay artifact set."""

    job_id: str
    request_id: str
    source_binding_digest: str
    source_state_sha256: str
    correction_payload_digest: str
    target_set_digest: str
    replay_profile_version: str
    request_identity_digest: str
    artifact_set_id: str


@dataclass(frozen=True)
class CorrectionReplayRenderedArtifact:
    """Rendered target artifact ready to be recorded in a replay set."""

    definition: ExamAuthoringCorrectionReplayArtifactDefinition
    path: Path


@dataclass(frozen=True)
class CorrectionReplayArtifactResolution:
    """Filesystem and response metadata for one verified replay artifact."""

    content_type: str
    filename: str
    path: Path


class CorrectionReplayArtifactSetEntryV1(BaseModel):
    """Manifest entry for one available replay artifact."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target: ExamAuthoringCorrectionTargetV1
    artifact_key: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    content_sha256: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)


class CorrectionReplayArtifactSetManifestV1(BaseModel):
    """Immutable manifest for one correction replay artifact set."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["correction_replay_artifact_set_manifest_v1"] = (
        CORRECTION_REPLAY_ARTIFACT_SET_SCHEMA_VERSION
    )
    job_id: str = Field(min_length=1)
    artifact_set_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    source_binding_digest: str = Field(min_length=1)
    source_state_sha256: str = Field(min_length=1)
    correction_payload_digest: str = Field(min_length=1)
    target_set_digest: str = Field(min_length=1)
    replay_profile_version: str = Field(min_length=1)
    request_identity_digest: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    artifacts: tuple[CorrectionReplayArtifactSetEntryV1, ...]


def build_correction_replay_artifact_set_identity(
    *,
    job: StoredJobV2,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
) -> CorrectionReplayArtifactSetIdentity:
    """Build the content-safe request identity used for replay-set binding."""

    source_binding_digest = _sha256_json(request_body.source_binding.model_dump(mode="json"))
    correction_payload_digest = _sha256_json(
        [entry.model_dump(mode="json") for entry in request_body.corrections]
    )
    target_set_digest = _sha256_json(sorted(set(targets)))
    identity_payload = {
        "job_id": job.job_id,
        "request_id": request_body.request_id,
        "source_binding_digest": source_binding_digest,
        "source_state_sha256": request_body.source_binding.source_state_sha256,
        "correction_payload_digest": correction_payload_digest,
        "target_set_digest": target_set_digest,
        "replay_profile_version": CORRECTION_REPLAY_PROFILE_VERSION,
    }
    request_identity_digest = _sha256_json(identity_payload)
    artifact_set_id = f"crset_{request_identity_digest.removeprefix('sha256:')[:32]}"
    return CorrectionReplayArtifactSetIdentity(
        job_id=job.job_id,
        request_id=request_body.request_id,
        source_binding_digest=source_binding_digest,
        source_state_sha256=request_body.source_binding.source_state_sha256,
        correction_payload_digest=correction_payload_digest,
        target_set_digest=target_set_digest,
        replay_profile_version=CORRECTION_REPLAY_PROFILE_VERSION,
        request_identity_digest=request_identity_digest,
        artifact_set_id=artifact_set_id,
    )


def find_verified_duplicate_artifact_set(
    *,
    job: StoredJobV2,
    identity: CorrectionReplayArtifactSetIdentity,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
) -> CorrectionReplayArtifactSetManifestV1 | None:
    """Return an existing verified duplicate set or reject request-id conflicts."""

    for manifest_path in sorted(_correction_replay_sets_dir(job).glob("*/manifest.json")):
        manifest = _load_manifest_or_none(manifest_path)
        if manifest is None or manifest.request_id != identity.request_id:
            continue
        if manifest.request_identity_digest != identity.request_identity_digest:
            raise ServiceError(
                status_code=409,
                code="exam_authoring_correction_replay_request_conflict",
                message="Correction replay request_id was reused with different content.",
                retryable=False,
                details={"request_id": identity.request_id},
            )
        if _manifest_matches_identity(manifest=manifest, identity=identity) and _has_targets(
            manifest=manifest,
            targets=targets,
        ):
            _verify_manifest_files(job=job, manifest=manifest)
            return manifest
    return None


def artifact_set_dir(*, job: StoredJobV2, artifact_set_id: str) -> Path:
    """Return the directory for one replay artifact set."""

    return _correction_replay_sets_dir(job) / artifact_set_id


def write_correction_replay_artifact_set_manifest(
    *,
    job: StoredJobV2,
    identity: CorrectionReplayArtifactSetIdentity,
    rendered_artifacts: tuple[CorrectionReplayRenderedArtifact, ...],
) -> CorrectionReplayArtifactSetManifestV1:
    """Write the artifact-set manifest after target files are finalized."""

    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entries = tuple(_entry_for_rendered_artifact(artifact) for artifact in rendered_artifacts)
    manifest = CorrectionReplayArtifactSetManifestV1(
        job_id=job.job_id,
        artifact_set_id=identity.artifact_set_id,
        request_id=identity.request_id,
        source_binding_digest=identity.source_binding_digest,
        source_state_sha256=identity.source_state_sha256,
        correction_payload_digest=identity.correction_payload_digest,
        target_set_digest=identity.target_set_digest,
        replay_profile_version=identity.replay_profile_version,
        request_identity_digest=identity.request_identity_digest,
        created_at=created_at,
        artifacts=entries,
    )
    manifest_path = artifact_set_dir(job=job, artifact_set_id=identity.artifact_set_id)
    manifest_path.mkdir(parents=True, exist_ok=True)
    (manifest_path / "manifest.json").write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return manifest


def references_by_target_from_manifest(
    manifest: CorrectionReplayArtifactSetManifestV1,
) -> dict[ExamAuthoringCorrectionTargetV1, ExamAuthoringCorrectionReplayArtifactReferenceV1]:
    """Build public typed artifact references from a verified manifest."""

    return {
        entry.target: ExamAuthoringCorrectionReplayArtifactReferenceV1(
            schema_version=CORRECTION_REPLAY_ARTIFACT_REFERENCE_SCHEMA_VERSION,
            job_id=manifest.job_id,
            artifact_set_id=manifest.artifact_set_id,
            artifact_key=entry.artifact_key,
            target=entry.target,
            content_sha256=entry.content_sha256,
            request_id=manifest.request_id,
            source_binding_digest=manifest.source_binding_digest,
            source_state_sha256=manifest.source_state_sha256,
            correction_payload_digest=manifest.correction_payload_digest,
            target_set_digest=manifest.target_set_digest,
            replay_profile_version=manifest.replay_profile_version,
            created_at=manifest.created_at,
        )
        for entry in manifest.artifacts
    }


def resolve_correction_replay_artifact(
    *,
    job: StoredJobV2,
    artifact_set_id: str,
    artifact_key: str,
    content_sha256: str,
) -> CorrectionReplayArtifactResolution:
    """Resolve one nested replay artifact with strict reference validation."""

    manifest_path = artifact_set_dir(job=job, artifact_set_id=artifact_set_id) / "manifest.json"
    if not manifest_path.exists():
        raise ServiceError(
            status_code=404,
            code="correction_replay_artifact_set_not_found",
            message="Correction replay artifact set was not found.",
            retryable=False,
            details={"artifact_set_id": artifact_set_id},
        )
    manifest = _load_manifest_or_mismatch(manifest_path)
    if manifest.job_id != job.job_id or manifest.artifact_set_id != artifact_set_id:
        raise _reference_mismatch(artifact_set_id=artifact_set_id, artifact_key=artifact_key)
    for entry in manifest.artifacts:
        if entry.artifact_key != artifact_key:
            continue
        if entry.content_sha256 != content_sha256:
            raise _reference_mismatch(
                artifact_set_id=artifact_set_id,
                artifact_key=artifact_key,
            )
        artifact_path = artifact_set_dir(job=job, artifact_set_id=artifact_set_id) / entry.filename
        if not artifact_path.exists() or _sha256_file(artifact_path) != content_sha256:
            raise _reference_mismatch(
                artifact_set_id=artifact_set_id,
                artifact_key=artifact_key,
            )
        return CorrectionReplayArtifactResolution(
            content_type=entry.content_type,
            filename=entry.filename,
            path=artifact_path,
        )
    raise _reference_mismatch(artifact_set_id=artifact_set_id, artifact_key=artifact_key)


def _correction_replay_sets_dir(job: StoredJobV2) -> Path:
    return job.artifact_path.parent / "correction-replays"


def _entry_for_rendered_artifact(
    artifact: CorrectionReplayRenderedArtifact,
) -> CorrectionReplayArtifactSetEntryV1:
    return CorrectionReplayArtifactSetEntryV1(
        target=artifact.definition.target,
        artifact_key=artifact.definition.artifact_key,
        filename=artifact.definition.filename,
        content_type=artifact.definition.content_type,
        content_sha256=_sha256_file(artifact.path),
        size_bytes=artifact.path.stat().st_size,
    )


def _has_targets(
    *,
    manifest: CorrectionReplayArtifactSetManifestV1,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
) -> bool:
    available_targets = {entry.target for entry in manifest.artifacts}
    return set(targets).issubset(available_targets)


def _manifest_matches_identity(
    *,
    manifest: CorrectionReplayArtifactSetManifestV1,
    identity: CorrectionReplayArtifactSetIdentity,
) -> bool:
    return (
        manifest.job_id == identity.job_id
        and manifest.artifact_set_id == identity.artifact_set_id
        and manifest.source_binding_digest == identity.source_binding_digest
        and manifest.source_state_sha256 == identity.source_state_sha256
        and manifest.correction_payload_digest == identity.correction_payload_digest
        and manifest.target_set_digest == identity.target_set_digest
        and manifest.replay_profile_version == identity.replay_profile_version
    )


def _verify_manifest_files(
    *,
    job: StoredJobV2,
    manifest: CorrectionReplayArtifactSetManifestV1,
) -> None:
    set_dir = artifact_set_dir(job=job, artifact_set_id=manifest.artifact_set_id)
    for entry in manifest.artifacts:
        artifact_path = set_dir / entry.filename
        if not artifact_path.exists() or _sha256_file(artifact_path) != entry.content_sha256:
            raise _reference_mismatch(
                artifact_set_id=manifest.artifact_set_id,
                artifact_key=entry.artifact_key,
            )


def _load_manifest_or_none(path: Path) -> CorrectionReplayArtifactSetManifestV1 | None:
    try:
        return _load_manifest(path)
    except (OSError, ValidationError, json.JSONDecodeError):
        return None


def _load_manifest_or_mismatch(path: Path) -> CorrectionReplayArtifactSetManifestV1:
    try:
        return _load_manifest(path)
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise _reference_mismatch(
            artifact_set_id=path.parent.name,
            artifact_key="unknown",
        ) from exc


def _load_manifest(path: Path) -> CorrectionReplayArtifactSetManifestV1:
    return CorrectionReplayArtifactSetManifestV1.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def _reference_mismatch(*, artifact_set_id: str, artifact_key: str) -> ServiceError:
    return ServiceError(
        status_code=409,
        code="correction_replay_artifact_reference_mismatch",
        message="Correction replay artifact reference does not match the stored artifact set.",
        retryable=False,
        details={"artifact_set_id": artifact_set_id, "artifact_key": artifact_key},
    )


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
