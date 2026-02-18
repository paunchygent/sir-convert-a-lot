"""Manifest composition/parsing helpers for the filesystem v2 job store.

Purpose:
    Keep v2 manifest serialization and diagnostics parsing isolated from v2 job
    store state-transition mechanics, so persistence and transition logic stay
    SRP-aligned.

Relationships:
    - Used by `infrastructure.job_store_v2` for manifest creation and loading.
    - Produces `StoredJobRecordV2` defined in `infrastructure.job_store_models_v2`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    dt_from_rfc3339,
    dt_to_rfc3339,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import StoredJobRecordV2


def ensure_diagnostics(payload: dict[str, object]) -> dict[str, object]:
    """Return diagnostics object, creating an empty one when missing."""
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
        payload["diagnostics"] = diagnostics
    return diagnostics


def parse_phase_timings(diagnostics: dict[str, object]) -> dict[str, int]:
    """Parse sanitized phase timing values from diagnostics payload."""
    phase_timings_obj = diagnostics.get("phase_timings_ms")
    if not isinstance(phase_timings_obj, dict):
        return {}
    parsed: dict[str, int] = {}
    for key, value in phase_timings_obj.items():
        if isinstance(key, str) and isinstance(value, int):
            parsed[key] = value
    return parsed


def set_phase_timings(*, diagnostics: dict[str, object], phase_timings_ms: dict[str, int]) -> None:
    """Persist normalized phase timings into diagnostics payload."""
    diagnostics["phase_timings_ms"] = {key: int(value) for key, value in phase_timings_ms.items()}


def merge_phase_timings(
    *,
    diagnostics: dict[str, object],
    additional_phase_timings_ms: dict[str, int],
) -> dict[str, int]:
    """Merge additional phase timings into diagnostics in-place."""
    merged = parse_phase_timings(diagnostics)
    for key, value in additional_phase_timings_ms.items():
        merged[key] = merged.get(key, 0) + int(value)
    set_phase_timings(diagnostics=diagnostics, phase_timings_ms=merged)
    return merged


def build_initial_manifest(
    *,
    job_id: str,
    spec: JobSpecV2,
    now: datetime,
    pinned: bool,
    raw_expires_at: datetime,
    artifact_expires_at: datetime,
) -> dict[str, object]:
    """Build initial on-disk manifest structure for a newly created v2 job."""
    return {
        "job_id": job_id,
        "job_spec": spec.model_dump(mode="json"),
        "status": JobStatus.QUEUED.value,
        "source_filename": spec.source.filename,
        "source_format": spec.source.format.value,
        "output_format": spec.conversion.output_format.value,
        "progress": {"stage": "queued"},
        "timestamps": {
            "created_at": dt_to_rfc3339(now),
            "updated_at": dt_to_rfc3339(now),
            "completed_at": None,
        },
        "retention": {
            "pinned": pinned,
            "raw_expires_at": dt_to_rfc3339(raw_expires_at),
            "artifact_expires_at": dt_to_rfc3339(artifact_expires_at),
        },
        "result_metadata": None,
        "error": None,
        "diagnostics": {
            "last_heartbeat_at": dt_to_rfc3339(now),
            "current_phase_started_at": dt_to_rfc3339(now),
            "phase_timings_ms": {},
        },
    }


def parse_stored_job_record(
    *,
    payload: dict[str, object],
    manifest_path: Path,
    expected_job_id: str,
    upload_path: Path,
    resources_zip_path: Path | None,
    reference_docx_path: Path | None,
    artifact_path: Path,
) -> StoredJobRecordV2:
    """Parse one v2 manifest payload into a typed durable job record."""
    job_id_obj = payload.get("job_id")
    if job_id_obj != expected_job_id:
        raise ValueError(f"manifest job_id mismatch: {manifest_path}")

    spec_payload = payload.get("job_spec")
    if not isinstance(spec_payload, dict):
        raise ValueError(f"manifest missing job_spec object: {manifest_path}")
    spec = JobSpecV2.model_validate(spec_payload)

    status_value = payload.get("status")
    if not isinstance(status_value, str):
        raise ValueError(f"manifest missing status: {manifest_path}")
    status = JobStatus(status_value)

    timestamps = payload.get("timestamps")
    if not isinstance(timestamps, dict):
        raise ValueError(f"manifest missing timestamps: {manifest_path}")
    created_at = dt_from_rfc3339(timestamps.get("created_at"))
    updated_at = dt_from_rfc3339(timestamps.get("updated_at"))
    completed_at = dt_from_rfc3339(timestamps.get("completed_at"))
    if created_at is None or updated_at is None:
        raise ValueError(f"manifest missing required timestamps: {manifest_path}")

    retention = payload.get("retention")
    if not isinstance(retention, dict):
        raise ValueError(f"manifest missing retention object: {manifest_path}")
    pinned_obj = retention.get("pinned")
    pinned = bool(pinned_obj) if isinstance(pinned_obj, bool) else False
    raw_expires_at = dt_from_rfc3339(retention.get("raw_expires_at"))
    artifact_expires_at = dt_from_rfc3339(retention.get("artifact_expires_at"))
    if raw_expires_at is None or artifact_expires_at is None:
        raise ValueError(f"manifest missing retention timestamps: {manifest_path}")

    progress = payload.get("progress")
    if not isinstance(progress, dict):
        raise ValueError(f"manifest missing progress: {manifest_path}")
    stage_obj = progress.get("stage")
    stage = stage_obj if isinstance(stage_obj, str) else "unknown"

    diagnostics = payload.get("diagnostics")
    diagnostics_obj = diagnostics if isinstance(diagnostics, dict) else {}
    last_heartbeat_at = dt_from_rfc3339(diagnostics_obj.get("last_heartbeat_at"))
    current_phase_started_at = dt_from_rfc3339(diagnostics_obj.get("current_phase_started_at"))
    phase_timings_ms = parse_phase_timings(diagnostics_obj)
    if status in {JobStatus.SUCCEEDED, JobStatus.FAILED} and "persist_ms" not in phase_timings_ms:
        phase_timings_ms["persist_ms"] = 0

    result_obj = payload.get("result_metadata")
    error_obj = payload.get("error")

    warnings: list[str] = []
    artifact_sha256: str | None = None
    artifact_size_bytes: int | None = None
    pipeline_used: str | None = None
    backend_used: str | None = None
    acceleration_used: str | None = None
    options_fingerprint: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_retryable = False
    failure_details: dict[str, object] | None = None

    if isinstance(result_obj, dict):
        warnings_obj = result_obj.get("warnings")
        if isinstance(warnings_obj, list):
            warnings = [warning for warning in warnings_obj if isinstance(warning, str)]

        artifact_obj = result_obj.get("artifact")
        if isinstance(artifact_obj, dict):
            sha_obj = artifact_obj.get("sha256")
            size_obj = artifact_obj.get("size_bytes")
            artifact_sha256 = sha_obj if isinstance(sha_obj, str) else None
            artifact_size_bytes = size_obj if isinstance(size_obj, int) else None

        meta_obj = result_obj.get("conversion_metadata")
        if isinstance(meta_obj, dict):
            pipeline_obj = meta_obj.get("pipeline_used")
            backend_obj = meta_obj.get("backend_used")
            accel_obj = meta_obj.get("acceleration_used")
            options_obj = meta_obj.get("options_fingerprint")
            pipeline_used = pipeline_obj if isinstance(pipeline_obj, str) else None
            backend_used = backend_obj if isinstance(backend_obj, str) else None
            acceleration_used = accel_obj if isinstance(accel_obj, str) else None
            options_fingerprint = options_obj if isinstance(options_obj, str) else None

    if isinstance(error_obj, dict):
        code_obj = error_obj.get("code")
        message_obj = error_obj.get("message")
        retryable_obj = error_obj.get("retryable")
        details_obj = error_obj.get("details")
        failure_code = code_obj if isinstance(code_obj, str) else None
        failure_message = message_obj if isinstance(message_obj, str) else None
        failure_retryable = retryable_obj if isinstance(retryable_obj, bool) else False
        failure_details = details_obj if isinstance(details_obj, dict) else None

    return StoredJobRecordV2(
        job_id=expected_job_id,
        spec=spec,
        source_filename=spec.source.filename,
        source_format=spec.source.format,
        output_format=spec.conversion.output_format,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        completed_at=completed_at,
        raw_expires_at=raw_expires_at,
        artifact_expires_at=artifact_expires_at,
        pinned=pinned,
        progress_stage=stage,
        last_heartbeat_at=last_heartbeat_at,
        current_phase_started_at=current_phase_started_at,
        phase_timings_ms=phase_timings_ms,
        warnings=warnings,
        upload_path=upload_path,
        resources_zip_path=resources_zip_path,
        reference_docx_path=reference_docx_path,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        artifact_size_bytes=artifact_size_bytes,
        pipeline_used=pipeline_used,
        backend_used=backend_used,
        acceleration_used=acceleration_used,
        options_fingerprint=options_fingerprint,
        failure_code=failure_code,
        failure_message=failure_message,
        failure_retryable=failure_retryable,
        failure_details=failure_details,
    )
