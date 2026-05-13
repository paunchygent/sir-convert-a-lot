"""Named artifact resolution for DigiExam migration bundles.

Purpose:
    Resolve product-facing artifact keys from the terminal
    `digiexam_migration_bundle_v1` manifest without exposing private job
    directories or synthesizing empty files.

Relationships:
    - Used by `interfaces.http_routes_job_artifacts_v2`.
    - Reads bundle manifests produced by
      `infrastructure.digiexam_migration_bundle_builder`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class ResolvedDigiExamMigrationArtifact:
    """Filesystem and response metadata for one available named artifact."""

    path: Path
    content_type: str
    filename: str


@dataclass(frozen=True)
class DigiExamMigrationResultMetadataFields:
    """Route-specific result metadata derived from a persisted bundle manifest."""

    bundle_status: Literal["complete", "partial", "blocked"]
    source_sha256: str
    target_availability: dict[str, str]
    manual_follow_up_required: bool
    warning_count: int
    artifact_count: int


def resolve_digiexam_migration_artifact(
    *,
    job: StoredJobV2,
    artifact_key: str,
) -> ResolvedDigiExamMigrationArtifact:
    """Resolve one available named artifact from the terminal bundle manifest."""

    normalized_key = _normalize_artifact_key(artifact_key)
    if normalized_key == DigiExamMigrationArtifactKey.BUNDLE_MANIFEST:
        return ResolvedDigiExamMigrationArtifact(
            path=job.artifact_path,
            content_type="application/json",
            filename=job.artifact_path.name,
        )

    manifest = _load_manifest(job.artifact_path)
    entries = manifest.get("artifacts")
    if not isinstance(entries, list):
        raise _invalid_manifest_error()

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("artifact_key") != normalized_key.value:
            continue
        return _resolve_entry(job=job, entry={str(key): value for key, value in entry.items()})

    raise ServiceError(
        status_code=404,
        code="digiexam_artifact_not_found",
        message="Named DigiExam migration artifact does not exist in the bundle.",
        retryable=False,
        details={"artifact_key": normalized_key.value},
    )


def load_digiexam_migration_result_metadata(
    *,
    job: StoredJobV2,
) -> DigiExamMigrationResultMetadataFields:
    """Load route-specific result metadata from the persisted bundle manifest."""

    manifest = _load_manifest(job.artifact_path)
    source = _required_object(manifest, "source")
    manual_follow_up = _required_object(manifest, "manual_follow_up")
    warnings = _required_object(manifest, "warnings")
    entries = _required_artifact_entries(manifest)
    source_sha256 = _required_string(source, "sha256")
    return DigiExamMigrationResultMetadataFields(
        bundle_status=_required_bundle_status(manifest),
        source_sha256=source_sha256,
        target_availability=_target_availability(entries),
        manual_follow_up_required=_required_bool(manual_follow_up, "required"),
        warning_count=_required_int(warnings, "count"),
        artifact_count=len(entries),
    )


def _normalize_artifact_key(value: str) -> DigiExamMigrationArtifactKey:
    try:
        return DigiExamMigrationArtifactKey(value)
    except ValueError as exc:
        raise ServiceError(
            status_code=404,
            code="digiexam_artifact_not_found",
            message="Named DigiExam migration artifact key is not recognized.",
            retryable=False,
            details={"artifact_key": value},
        ) from exc


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _invalid_manifest_error() from exc
    if not isinstance(payload, dict):
        raise _invalid_manifest_error()
    schema_version = payload.get("schema_version")
    if schema_version != DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION:
        raise _invalid_manifest_error()
    return {str(key): value for key, value in payload.items()}


def _resolve_entry(
    *,
    job: StoredJobV2,
    entry: dict[str, object],
) -> ResolvedDigiExamMigrationArtifact:
    availability = entry.get("availability")
    if availability != DigiExamMigrationArtifactAvailability.AVAILABLE.value:
        blocker_code = entry.get("blocker_code")
        error_code = _unavailable_artifact_error_code(availability, blocker_code)
        raise ServiceError(
            status_code=409,
            code=error_code,
            message="Named DigiExam migration artifact is not available.",
            retryable=False,
            details={
                "artifact_key": str(entry.get("artifact_key")),
                "availability": str(availability),
            },
        )
    filename = entry.get("filename")
    content_type = entry.get("content_type")
    if not isinstance(filename, str) or not isinstance(content_type, str):
        raise _invalid_manifest_error()
    artifact_path = job.artifact_path.parent / filename
    if not artifact_path.exists():
        raise ServiceError(
            status_code=500,
            code="digiexam_target_artifact_missing",
            message="Bundle manifest references an available artifact that is missing.",
            retryable=True,
            details={"artifact_key": str(entry.get("artifact_key"))},
        )
    return ResolvedDigiExamMigrationArtifact(
        path=artifact_path,
        content_type=content_type,
        filename=filename,
    )


def _unavailable_artifact_error_code(availability: object, blocker_code: object) -> str:
    if isinstance(blocker_code, str):
        return blocker_code
    if availability == DigiExamMigrationArtifactAvailability.NOT_REQUESTED.value:
        return "digiexam_artifact_not_requested"
    if availability == DigiExamMigrationArtifactAvailability.NOT_IMPLEMENTED.value:
        return "digiexam_artifact_not_implemented"
    if availability == DigiExamMigrationArtifactAvailability.NOT_SUPPORTED_BY_EXAMNET.value:
        return "digiexam_artifact_not_supported_by_examnet"
    if availability == DigiExamMigrationArtifactAvailability.FAILED.value:
        return "digiexam_artifact_failed"
    return "digiexam_artifact_blocked"


def _required_artifact_entries(manifest: dict[str, object]) -> tuple[dict[str, object], ...]:
    entries = manifest.get("artifacts")
    if not isinstance(entries, list):
        raise _invalid_manifest_error()
    normalized_entries: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise _invalid_manifest_error()
        normalized_entries.append({str(key): value for key, value in entry.items()})
    return tuple(normalized_entries)


def _target_availability(entries: tuple[dict[str, object], ...]) -> dict[str, str]:
    target_keys = {
        DigiExamMigrationArtifactKey.EXAMNET_PDF.value,
        DigiExamMigrationArtifactKey.QTI_PACKAGE.value,
    }
    availability_by_key: dict[str, str] = {}
    for entry in entries:
        artifact_key = entry.get("artifact_key")
        if artifact_key not in target_keys:
            continue
        availability = entry.get("availability")
        if not isinstance(artifact_key, str) or not isinstance(availability, str):
            raise _invalid_manifest_error()
        availability_by_key[artifact_key] = availability
    if set(availability_by_key) != target_keys:
        raise _invalid_manifest_error()
    return availability_by_key


def _required_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise _invalid_manifest_error()
    return {str(child_key): child_value for child_key, child_value in value.items()}


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise _invalid_manifest_error()
    return value


def _required_bundle_status(
    payload: dict[str, object],
) -> Literal["complete", "partial", "blocked"]:
    value = _required_string(payload, "bundle_status")
    if value == "complete":
        return "complete"
    if value == "partial":
        return "partial"
    if value == "blocked":
        return "blocked"
    raise _invalid_manifest_error()


def _required_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise _invalid_manifest_error()
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _invalid_manifest_error()
    return value


def _invalid_manifest_error() -> ServiceError:
    return ServiceError(
        status_code=500,
        code="digiexam_bundle_manifest_invalid",
        message="DigiExam migration bundle manifest is invalid.",
        retryable=True,
    )
