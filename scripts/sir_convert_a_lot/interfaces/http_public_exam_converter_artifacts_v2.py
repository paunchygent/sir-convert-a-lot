"""Public Exam Converter artifact response helpers.

Purpose:
    Build public artifact manifest responses with per-artifact read leases
    without adding manifest shaping logic to the v2 artifact route module.

Relationships:
    - Used by `interfaces.http_routes_job_artifacts_v2`.
    - Delegates lease creation to `interfaces.http_public_exam_converter_access_v2`.
"""

from __future__ import annotations

from fastapi import Request

from scripts.sir_convert_a_lot.application.public_exam_converter_access_policy_v2 import (
    VerifiedPublicConversionGrantV2,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    ObjectStoreMissingError,
    ObjectStoreUnavailableError,
    TerminalArtifactStore,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.terminal_artifact_json_loader_v2 import (
    TerminalArtifactJsonInvalidError,
    load_terminal_artifact_json_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_public_exam_converter_access_v2 import (
    issue_public_artifact_read_lease_fragment_v2,
    public_bundle_manifest_artifact_key_v2,
)


def load_public_bundle_manifest_v2(
    *,
    request: Request,
    service_started_at: str,
    job: StoredJobV2,
    verified_grant: VerifiedPublicConversionGrantV2,
    object_store: TerminalArtifactStore,
) -> dict[str, object]:
    """Load a public bundle manifest and attach named-artifact read leases."""

    manifest = _load_manifest_object(job=job, object_store=object_store)
    manifest["artifacts"] = _public_artifact_entries_with_leases(
        request=request,
        service_started_at=service_started_at,
        job=job,
        verified_grant=verified_grant,
        entries=manifest.get("artifacts"),
    )
    return manifest


def _load_manifest_object(
    *,
    job: StoredJobV2,
    object_store: TerminalArtifactStore,
) -> dict[str, object]:
    try:
        manifest_object = load_terminal_artifact_json_v2(
            object_store=object_store,
            job=job,
            artifact_key="bundle_manifest",
            filesystem_path=job.artifact_path,
        )
    except ObjectStoreMissingError as exc:
        raise ServiceError(
            status_code=404,
            code="artifact_not_available",
            message="Artifact object is not available.",
            retryable=True,
        ) from exc
    except ObjectStoreUnavailableError as exc:
        raise ServiceError(
            status_code=503,
            code="artifact_store_unavailable",
            message="Artifact storage is temporarily unavailable.",
            retryable=True,
        ) from exc
    except TerminalArtifactJsonInvalidError as exc:
        raise _invalid_public_manifest("Public artifact manifest could not be loaded.") from exc
    manifest: dict[str, object] = {}
    for key, value in manifest_object.items():
        manifest[key] = value
    return manifest


def _public_artifact_entries_with_leases(
    *,
    request: Request,
    service_started_at: str,
    job: StoredJobV2,
    verified_grant: VerifiedPublicConversionGrantV2,
    entries: object,
) -> list[object]:
    if not isinstance(entries, list):
        raise _invalid_public_manifest("Public artifact manifest entries have an invalid shape.")
    public_entries: list[object] = []
    for entry in entries:
        if not isinstance(entry, dict):
            public_entries.append(entry)
            continue
        public_entry = _string_keyed_entry(entry)
        artifact_key = _artifact_key_for_lease(
            artifact_key=public_entry.get("artifact_key"),
            availability=public_entry.get("availability"),
        )
        if artifact_key is not None:
            public_entry["public_artifact_read_lease"] = (
                issue_public_artifact_read_lease_fragment_v2(
                    request=request,
                    service_started_at=service_started_at,
                    verified_grant=verified_grant,
                    job=job,
                    artifact_key=artifact_key,
                )
            )
        public_entries.append(public_entry)
    return public_entries


def _string_keyed_entry(entry: dict[object, object]) -> dict[str, object]:
    public_entry: dict[str, object] = {}
    for key, value in entry.items():
        if isinstance(key, str):
            public_entry[key] = value
    return public_entry


def _artifact_key_for_lease(*, artifact_key: object, availability: object) -> str | None:
    if (
        isinstance(artifact_key, str)
        and artifact_key != public_bundle_manifest_artifact_key_v2()
        and availability == "available"
    ):
        return artifact_key
    return None


def _invalid_public_manifest(message: str) -> ServiceError:
    return ServiceError(
        status_code=500,
        code="result_missing_artifact",
        message=message,
        retryable=False,
    )
