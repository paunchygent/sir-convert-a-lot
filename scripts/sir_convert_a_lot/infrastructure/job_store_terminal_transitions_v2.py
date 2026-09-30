"""Terminal state transitions for v2 jobs.

Purpose:
    Persist the successful and failed terminal transitions of a running v2 job:
    terminal artifact write, result or error metadata, final progress fields,
    diagnostics phase timings, and the terminal lifecycle event.

Relationships:
    - Called by `job_store_v2.JobStoreV2.mark_succeeded` and
      `job_store_v2.JobStoreV2.mark_failed`.
    - Uses `job_store_v2_core.JobStoreV2Core` locking and manifest primitives.
    - Delegates object-store persistence to `job_store_terminal_artifacts_v2`.
"""

from __future__ import annotations

import hashlib
import time

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_to_rfc3339,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import append_lifecycle_event
from scripts.sir_convert_a_lot.infrastructure.job_store_manifest_v2 import (
    ensure_diagnostics,
    merge_phase_timings,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import StoredJobRecordV2
from scripts.sir_convert_a_lot.infrastructure.job_store_terminal_artifacts_v2 import (
    persist_terminal_artifact_objects_v2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2_core import JobStoreV2Core
from scripts.sir_convert_a_lot.infrastructure.object_store_models import TerminalArtifactStore
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CONVERSION_TOTAL_MS,
    TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS,
)
from scripts.sir_convert_a_lot.infrastructure.progress_fields_v2 import (
    parse_optional_nonneg_float,
    parse_optional_nonneg_int,
)


def _artifact_content_type(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.MD:
        return "text/markdown"
    if output_format == OutputFormatV2.PDF:
        return "application/pdf"
    if output_format == OutputFormatV2.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if output_format == OutputFormatV2.TRANSCRIPT_BUNDLE:
        return "application/json"
    raise AssertionError(f"Unsupported output_format: {output_format}")


def mark_job_succeeded_v2(
    store: JobStoreV2Core,
    job_id: str,
    *,
    object_store: TerminalArtifactStore,
    artifact_bytes: bytes,
    pipeline_used: str,
    backend_used: str | None,
    acceleration_used: str | None,
    ocr_enabled: bool | None,
    ocr_engine_used: str | None,
    ocr_languages_used: list[str] | None,
    options_fingerprint: str,
    acceleration_policy_requested: str | None,
    gpu_runtime_kind: str | None,
    gpu_device_count: int | None,
    gpu_busy_percent: int | None,
    gpu_memory_used_percent: int | None,
    template_id: str | None,
    template_version: str | None,
    template_artifact_sha256: str | None,
    parallel_enabled: bool | None,
    max_chunk_workers: int | None,
    chunk_size_pages: int | None,
    effective_gpu_stage_limit: int | None,
    scheduling_mode: str | None,
    formula_authority: dict[str, object] | None,
    warnings: list[str],
    phase_timings_ms: dict[str, int] | None,
) -> StoredJobRecordV2:
    """Persist successful terminal state and result metadata for a v2 job."""
    persist_started = utc_now()
    persist_started_monotonic = time.perf_counter()

    manifest_path = store._manifest_path(job_id)
    with store._job_manifest_lock(job_id):
        payload = store._read_manifest_locked(job_id)
        store._require_status(
            payload=payload,
            job_id=job_id,
            expected_statuses=(JobStatus.RUNNING,),
        )

        output_format_obj = payload.get("output_format")
        if not isinstance(output_format_obj, str):
            raise ValueError(f"manifest missing output_format for job_id={job_id}")
        output_format = OutputFormatV2(output_format_obj)

        artifact_path = store._artifact_path(job_id, output_format)
        artifact_path.write_bytes(artifact_bytes)
        sha = hashlib.sha256(artifact_bytes).hexdigest()
        content_type = _artifact_content_type(output_format)
        owner_obj = payload.get("owner")
        owner_api_key_scope = "service-api-key"
        if isinstance(owner_obj, dict):
            scope_obj = owner_obj.get("api_key_scope")
            if isinstance(scope_obj, str) and scope_obj.strip() != "":
                owner_api_key_scope = scope_obj
        source_format_obj = payload.get("source_format")
        source_format_value = source_format_obj if isinstance(source_format_obj, str) else "unknown"
        object_refs = persist_terminal_artifact_objects_v2(
            object_store=object_store,
            job_id=job_id,
            owner_api_key_scope=owner_api_key_scope,
            source_format_value=source_format_value,
            output_format=output_format,
            artifact_path=artifact_path,
            primary_content_type=content_type,
            primary_payload=artifact_bytes,
        )

        now = utc_now()
        payload["status"] = JobStatus.SUCCEEDED.value
        timestamps = payload.get("timestamps")
        if not isinstance(timestamps, dict):
            timestamps = {}
            payload["timestamps"] = timestamps
        timestamps["updated_at"] = dt_to_rfc3339(now)
        timestamps["completed_at"] = dt_to_rfc3339(now)

        progress_obj = payload.get("progress")
        progress = progress_obj if isinstance(progress_obj, dict) else {}
        payload["progress"] = progress
        progress["stage"] = "succeeded"
        source_format_obj = payload.get("source_format")
        if isinstance(source_format_obj, str) and source_format_obj == "pdf":
            total_pages = parse_optional_nonneg_int(progress.get("total_pages"))
            if total_pages is not None and total_pages > 0:
                progress["processed_pages"] = total_pages
                if progress.get("failed_pages") is None:
                    progress["failed_pages"] = 0
            progress["percent_complete"] = 100.0
            progress["eta_seconds"] = 0
            if phase_timings_ms is not None and total_pages is not None and total_pages > 0:
                attempt_ms_obj = phase_timings_ms.get(TIMING_KEY_CONVERSION_TOTAL_MS)
                attempt_ms = (
                    attempt_ms_obj
                    if isinstance(attempt_ms_obj, int) and not isinstance(attempt_ms_obj, bool)
                    else None
                )
                if attempt_ms is not None and attempt_ms > 0:
                    minutes = attempt_ms / 60_000.0
                    progress["pages_per_minute"] = float(total_pages) / minutes
        if isinstance(source_format_obj, str) and source_format_obj == "audio":
            audio_total = parse_optional_nonneg_float(progress.get("audio_total_media_seconds"))
            if audio_total is not None:
                progress["audio_processed_media_seconds"] = audio_total
            progress["audio_percent_complete"] = 100.0
            progress["audio_pipeline_percent_complete"] = 100.0
            progress["audio_pipeline_eta_seconds"] = 0

        payload["error"] = None
        payload["result_metadata"] = {
            "artifact": {
                "filename": artifact_path.name,
                "format": output_format.value,
                "content_type": content_type,
                "size_bytes": len(artifact_bytes),
                "sha256": sha,
                "object_ref": object_refs["primary"].to_json(),
            },
            "terminal_artifact_object_refs": {
                artifact_key: ref.to_json() for artifact_key, ref in object_refs.items()
            },
            "conversion_metadata": {
                "pipeline_used": pipeline_used,
                "backend_used": backend_used,
                "acceleration_used": acceleration_used,
                "ocr_enabled": ocr_enabled,
                "ocr_engine_used": ocr_engine_used,
                "ocr_languages_used": (
                    list(ocr_languages_used) if ocr_languages_used is not None else None
                ),
                "acceleration_policy_requested": acceleration_policy_requested,
                "gpu_runtime_kind": gpu_runtime_kind,
                "gpu_device_count": gpu_device_count,
                "gpu_busy_percent": gpu_busy_percent,
                "gpu_memory_used_percent": gpu_memory_used_percent,
                "options_fingerprint": options_fingerprint,
                "template_id": template_id,
                "template_version": template_version,
                "template_artifact_sha256": template_artifact_sha256,
                "parallel_enabled": parallel_enabled,
                "max_chunk_workers": max_chunk_workers,
                "chunk_size_pages": chunk_size_pages,
                "effective_gpu_stage_limit": effective_gpu_stage_limit,
                "scheduling_mode": scheduling_mode,
                "formula_authority": dict(formula_authority or {}),
            },
            "warnings": list(warnings),
        }

        diagnostics = ensure_diagnostics(payload)
        diagnostics["last_heartbeat_at"] = dt_to_rfc3339(now)
        if phase_timings_ms is not None:
            merge_phase_timings(
                diagnostics=diagnostics,
                additional_phase_timings_ms=phase_timings_ms,
            )
        diagnostics["current_phase_started_at"] = dt_to_rfc3339(persist_started)
        append_lifecycle_event(
            payload=payload,
            status=JobStatus.SUCCEEDED,
            stage="succeeded",
            occurred_at=now,
        )

        atomic_write_json(manifest_path, payload)
        persist_elapsed_ms = max(0, int((time.perf_counter() - persist_started_monotonic) * 1000))
        merge_phase_timings(
            diagnostics=diagnostics,
            additional_phase_timings_ms={TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS: persist_elapsed_ms},
        )
        atomic_write_json(manifest_path, payload)
    return store.get_job(job_id)


def mark_job_failed_v2(
    store: JobStoreV2Core,
    job_id: str,
    *,
    code: str,
    message: str,
    retryable: bool,
    details: dict[str, object] | None,
    phase_timings_ms: dict[str, int] | None,
) -> StoredJobRecordV2:
    """Persist failed terminal state and failure metadata for a v2 job."""
    persist_started = utc_now()
    persist_started_monotonic = time.perf_counter()

    manifest_path = store._manifest_path(job_id)
    with store._job_manifest_lock(job_id):
        payload = store._read_manifest_locked(job_id)
        store._require_status(
            payload=payload,
            job_id=job_id,
            expected_statuses=(JobStatus.RUNNING,),
        )
        now = utc_now()

        payload["status"] = JobStatus.FAILED.value
        timestamps = payload.get("timestamps")
        if not isinstance(timestamps, dict):
            timestamps = {}
            payload["timestamps"] = timestamps
        timestamps["updated_at"] = dt_to_rfc3339(now)
        timestamps["completed_at"] = dt_to_rfc3339(now)

        progress_obj = payload.get("progress")
        progress = progress_obj if isinstance(progress_obj, dict) else {}
        payload["progress"] = progress
        progress["stage"] = "failed"

        payload["result_metadata"] = None
        payload["error"] = {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details,
        }
        diagnostics = ensure_diagnostics(payload)
        diagnostics["last_heartbeat_at"] = dt_to_rfc3339(now)
        if phase_timings_ms is not None:
            merge_phase_timings(
                diagnostics=diagnostics,
                additional_phase_timings_ms=phase_timings_ms,
            )
        diagnostics["current_phase_started_at"] = dt_to_rfc3339(persist_started)
        append_lifecycle_event(
            payload=payload,
            status=JobStatus.FAILED,
            stage="failed",
            occurred_at=now,
        )

        atomic_write_json(manifest_path, payload)
        persist_elapsed_ms = max(0, int((time.perf_counter() - persist_started_monotonic) * 1000))
        merge_phase_timings(
            diagnostics=diagnostics,
            additional_phase_timings_ms={TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS: persist_elapsed_ms},
        )
        atomic_write_json(manifest_path, payload)
    return store.get_job(job_id)


__all__ = ["mark_job_failed_v2", "mark_job_succeeded_v2"]
