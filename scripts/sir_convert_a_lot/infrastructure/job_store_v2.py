"""Filesystem-backed job store for Sir Convert-a-Lot service API v2.

Purpose:
    Provide the canonical v2 job store surface used by the v2 runtime, including
    housekeeping operations (sweeping and recovery) layered on top of the core
    atomic transition and persistence logic.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` for v2 job lifecycle operations.
    - Extends `infrastructure.job_store_v2_core.JobStoreV2Core`.
"""

from __future__ import annotations

import hashlib
import time
from datetime import timedelta

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import (
    JobLifecycleEventRecordV2,
    append_lifecycle_event,
    list_events_after_sequence,
    prune_replay_events,
    resolve_resume_sequence,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_manifest_v2 import (
    ensure_diagnostics,
    merge_phase_timings,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    StoredJobRecordV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2_core import JobStoreV2Core
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CONVERSION_TOTAL_MS,
    TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS,
)
from scripts.sir_convert_a_lot.infrastructure.progress_fields_v2 import (
    parse_optional_nonneg_int,
)


def _artifact_content_type(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.MD:
        return "text/markdown"
    if output_format == OutputFormatV2.PDF:
        return "application/pdf"
    if output_format == OutputFormatV2.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise AssertionError(f"Unsupported output_format: {output_format}")


class JobStoreV2(JobStoreV2Core):
    """Filesystem-backed store for v2 conversion jobs."""

    def list_job_ids(self) -> list[str]:
        return sorted(path.name for path in self.jobs_dir.iterdir() if path.is_dir())

    def prune_job_events(self, *, job_id: str, replay_horizon_seconds: int | None = None) -> None:
        """Prune replay events for one job id using the configured horizon."""
        resolved_horizon = self.replay_horizon_seconds
        if replay_horizon_seconds is not None:
            resolved_horizon = max(1, replay_horizon_seconds)
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            changed = prune_replay_events(
                payload=payload,
                now=utc_now(),
                replay_horizon_seconds=resolved_horizon,
            )
            if changed:
                atomic_write_json(manifest_path, payload)

    def annotate_resume_metadata(
        self,
        *,
        job_id: str,
        resumed_from_job_id: str,
        checkpoint_sha256: str,
    ) -> None:
        """Persist audit metadata linking a resume job to its source checkpoint."""
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            payload["resume"] = {
                "from_job_id": resumed_from_job_id,
                "checkpoint_sha256": checkpoint_sha256,
            }
            atomic_write_json(manifest_path, payload)

    def resolve_events_resume_sequence(
        self,
        *,
        job_id: str,
        cursor: str | None,
        last_event_id: str | None,
        replay_horizon_seconds: int | None = None,
    ) -> int:
        """Resolve replay pointer to sequence for SSE resume semantics."""
        resolved_horizon = self.replay_horizon_seconds
        if replay_horizon_seconds is not None:
            resolved_horizon = max(1, replay_horizon_seconds)
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            changed = prune_replay_events(
                payload=payload,
                now=utc_now(),
                replay_horizon_seconds=resolved_horizon,
            )
            sequence = resolve_resume_sequence(
                payload=payload,
                cursor=cursor,
                last_event_id=last_event_id,
                replay_horizon_seconds=resolved_horizon,
            )
            if changed:
                atomic_write_json(manifest_path, payload)
            return sequence

    def list_job_events_after_sequence(
        self,
        *,
        job_id: str,
        after_sequence: int,
        replay_horizon_seconds: int | None = None,
    ) -> list[JobLifecycleEventRecordV2]:
        """Return replay events newer than the provided sequence pointer."""
        resolved_horizon = self.replay_horizon_seconds
        if replay_horizon_seconds is not None:
            resolved_horizon = max(1, replay_horizon_seconds)
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            changed = prune_replay_events(
                payload=payload,
                now=utc_now(),
                replay_horizon_seconds=resolved_horizon,
            )
            events = list_events_after_sequence(payload=payload, after_sequence=after_sequence)
            if changed:
                atomic_write_json(manifest_path, payload)
            return events

    def mark_succeeded(
        self,
        job_id: str,
        *,
        artifact_bytes: bytes,
        pipeline_used: str,
        backend_used: str | None,
        acceleration_used: str | None,
        ocr_enabled: bool | None = None,
        ocr_engine_used: str | None = None,
        ocr_languages_used: list[str] | None = None,
        options_fingerprint: str,
        acceleration_policy_requested: str | None = None,
        gpu_runtime_kind: str | None = None,
        gpu_device_count: int | None = None,
        gpu_busy_percent: int | None = None,
        gpu_memory_used_percent: int | None = None,
        template_id: str | None = None,
        template_version: str | None = None,
        template_artifact_sha256: str | None = None,
        parallel_enabled: bool | None = None,
        max_chunk_workers: int | None = None,
        chunk_size_pages: int | None = None,
        effective_gpu_stage_limit: int | None = None,
        scheduling_mode: str | None = None,
        warnings: list[str],
        phase_timings_ms: dict[str, int] | None = None,
    ) -> StoredJobRecordV2:
        """Persist successful terminal state and result metadata for a v2 job."""
        persist_started = utc_now()
        persist_started_monotonic = time.perf_counter()

        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            self._require_status(
                payload=payload,
                job_id=job_id,
                expected_statuses=(JobStatus.RUNNING,),
            )

            output_format_obj = payload.get("output_format")
            if not isinstance(output_format_obj, str):
                raise ValueError(f"manifest missing output_format for job_id={job_id}")
            output_format = OutputFormatV2(output_format_obj)

            artifact_path = self._artifact_path(job_id, output_format)
            artifact_path.write_bytes(artifact_bytes)
            sha = hashlib.sha256(artifact_bytes).hexdigest()
            content_type = _artifact_content_type(output_format)

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

            payload["error"] = None
            payload["result_metadata"] = {
                "artifact": {
                    "filename": artifact_path.name,
                    "format": output_format.value,
                    "content_type": content_type,
                    "size_bytes": len(artifact_bytes),
                    "sha256": sha,
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
            persist_elapsed_ms = max(
                0, int((time.perf_counter() - persist_started_monotonic) * 1000)
            )
            merge_phase_timings(
                diagnostics=diagnostics,
                additional_phase_timings_ms={
                    TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS: persist_elapsed_ms
                },
            )
            atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

    def mark_failed(
        self,
        job_id: str,
        *,
        code: str,
        message: str,
        retryable: bool,
        details: dict[str, object] | None,
        phase_timings_ms: dict[str, int] | None = None,
    ) -> StoredJobRecordV2:
        """Persist failed terminal state and failure metadata for a v2 job."""
        persist_started = utc_now()
        persist_started_monotonic = time.perf_counter()

        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            self._require_status(
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
            persist_elapsed_ms = max(
                0, int((time.perf_counter() - persist_started_monotonic) * 1000)
            )
            merge_phase_timings(
                diagnostics=diagnostics,
                additional_phase_timings_ms={
                    TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS: persist_elapsed_ms
                },
            )
            atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

    def recover_running_jobs_to_queued(self, *, active_job_ids: set[str]) -> list[str]:
        """Convert orphaned running v2 jobs to queued."""
        recovered: list[str] = []
        for job_id in self.list_job_ids():
            if job_id in active_job_ids:
                continue
            try:
                record = self.get_job(job_id)
            except (JobMissingV2, JobExpiredV2):
                continue
            if record.status == JobStatus.RUNNING:
                self.update_progress(job_id, status=JobStatus.QUEUED, stage="queued")
                recovered.append(job_id)
        return recovered

    def sweep_expired(self) -> None:
        """Sweep expired v2 jobs and retain tombstones so the API can return job_expired."""
        now = utc_now()

        tombstone_ttl = timedelta(seconds=self.tombstone_ttl_seconds)
        for tombstone in self.expired_dir.glob("*.json"):
            try:
                payload = read_json(tombstone)
                expired_at = dt_from_rfc3339(payload.get("expired_at"))
            except Exception:
                continue
            if expired_at is not None and now - expired_at > tombstone_ttl:
                tombstone.unlink(missing_ok=True)

        for job_id in self.list_job_ids():
            manifest_path = self._manifest_path(job_id)
            if not manifest_path.exists():
                continue
            try:
                record = self.get_job(job_id)
            except JobExpiredV2:
                tombstone_payload: dict[str, object] = {
                    "job_id": job_id,
                    "expired_at": dt_to_rfc3339(now),
                }
                atomic_write_json(self._tombstone_path(job_id), tombstone_payload)
                for child in self._job_dir(job_id).rglob("*"):
                    if child.is_file():
                        child.unlink(missing_ok=True)
                for child in sorted(self._job_dir(job_id).rglob("*"), reverse=True):
                    if child.is_dir():
                        try:
                            child.rmdir()
                        except OSError:
                            pass
                try:
                    self._job_dir(job_id).rmdir()
                except OSError:
                    pass
                continue
            except JobMissingV2:
                continue

            if record.pinned:
                self.prune_job_events(job_id=job_id)
                continue

            if now > record.raw_expires_at:
                raw_dir = self._job_dir(job_id) / "raw"
                if raw_dir.exists():
                    for child in raw_dir.rglob("*"):
                        if child.is_file():
                            child.unlink(missing_ok=True)
                    for child in sorted(raw_dir.rglob("*"), reverse=True):
                        if child.is_dir():
                            try:
                                child.rmdir()
                            except OSError:
                                pass
                    try:
                        raw_dir.rmdir()
                    except OSError:
                        pass

            self.prune_job_events(job_id=job_id)


__all__ = ["JobStoreV2"]
