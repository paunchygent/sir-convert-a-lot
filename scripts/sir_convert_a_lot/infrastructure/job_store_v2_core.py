"""Filesystem-backed v2 job store core.

Purpose: durable v2 persistence + atomic lifecycle transitions for jobs,
including artifacts and auxiliary uploads (resources zip/reference docx).
Relationships: extended by `job_store_v2`, consumed by `runtime_engine_v2`,
and backed by `job_store_manifest_v2`.
"""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Iterator

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import (
    append_lifecycle_event,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_manifest_v2 import (
    build_initial_manifest,
    ensure_diagnostics,
    merge_phase_timings,
    parse_stored_job_record,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    JobStateConflictV2,
    StoredJobRecordV2,
)
from scripts.sir_convert_a_lot.infrastructure.progress_fields_v2 import (
    clamp_monotonic_float,
    clamp_monotonic_int,
    parse_optional_nonneg_float,
    parse_optional_nonneg_int,
    parse_optional_percent,
    parse_progress_page_fields,
)


class JobStoreV2Core:
    """Filesystem-backed core store for v2 conversion jobs."""

    def __init__(
        self,
        *,
        data_root: Path,
        raw_ttl_seconds: int,
        artifact_ttl_seconds: int,
        tombstone_ttl_seconds: int = 30 * 24 * 3600,
        replay_horizon_seconds: int = 24 * 3600,
    ) -> None:
        self.data_root = data_root
        self.jobs_dir = data_root / "jobs_v2"
        self.expired_dir = data_root / "expired_v2"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.expired_dir.mkdir(parents=True, exist_ok=True)
        self.raw_ttl_seconds = raw_ttl_seconds
        self.artifact_ttl_seconds = artifact_ttl_seconds
        self.tombstone_ttl_seconds = tombstone_ttl_seconds
        self.replay_horizon_seconds = max(1, replay_horizon_seconds)

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def _manifest_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "manifest.json"

    def _raw_upload_path(self, job_id: str, source_format: SourceFormatV2) -> Path:
        suffix = source_format.value
        return self._job_dir(job_id) / "raw" / f"input.{suffix}"

    def _resources_zip_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "raw" / "resources.zip"

    def _reference_docx_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "raw" / "reference.docx"

    def _artifact_path(self, job_id: str, output_format: OutputFormatV2) -> Path:
        suffix = output_format.value
        return self._job_dir(job_id) / "artifacts" / f"output.{suffix}"

    def _log_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "logs" / "run.log"

    def _tombstone_path(self, job_id: str) -> Path:
        return self.expired_dir / f"{job_id}.json"

    def _lock_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / ".manifest.lock"

    def _raise_missing_or_expired(self, job_id: str) -> None:
        tombstone = self._tombstone_path(job_id)
        if tombstone.exists():
            raise JobExpiredV2(job_id=job_id)
        raise JobMissingV2(job_id=job_id)

    @contextmanager
    def _job_manifest_lock(self, job_id: str) -> Iterator[None]:
        job_dir = self._job_dir(job_id)
        if not job_dir.exists():
            self._raise_missing_or_expired(job_id)

        lock_path = self._lock_path(job_id)
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_manifest_locked(self, job_id: str) -> dict[str, object]:
        manifest_path = self._manifest_path(job_id)
        if not manifest_path.exists():
            self._raise_missing_or_expired(job_id)
        return read_json(manifest_path)

    def _require_status(
        self,
        *,
        payload: dict[str, object],
        job_id: str,
        expected_statuses: tuple[JobStatus, ...],
    ) -> None:
        status_obj = payload.get("status")
        if not isinstance(status_obj, str):
            raise ValueError(f"manifest missing status for job_id={job_id}")
        actual_status = JobStatus(status_obj)
        if actual_status not in expected_statuses:
            raise JobStateConflictV2(
                job_id=job_id,
                expected_statuses=expected_statuses,
                actual_status=actual_status,
            )

    def create_job(
        self,
        *,
        job_id: str,
        spec: JobSpecV2,
        upload_bytes: bytes,
        resources_zip_bytes: bytes | None,
        reference_docx_bytes: bytes | None,
    ) -> StoredJobRecordV2:
        now = utc_now()

        job_dir = self._job_dir(job_id)
        (job_dir / "raw").mkdir(parents=True, exist_ok=True)
        (job_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_dir / "logs").mkdir(parents=True, exist_ok=True)

        upload_path = self._raw_upload_path(job_id, spec.source.format)
        resources_path: Path | None = None
        reference_docx_path: Path | None = None

        upload_path.write_bytes(upload_bytes)
        if resources_zip_bytes is not None:
            resources_path = self._resources_zip_path(job_id)
            resources_path.write_bytes(resources_zip_bytes)
        if reference_docx_bytes is not None:
            reference_docx_path = self._reference_docx_path(job_id)
            reference_docx_path.write_bytes(reference_docx_bytes)

        log_path = self._log_path(job_id)
        log_path.write_text("", encoding="utf-8")

        pinned = bool(spec.retention.pin)
        raw_expires_at = now + timedelta(seconds=self.raw_ttl_seconds)
        artifact_expires_at = now + timedelta(seconds=self.artifact_ttl_seconds)

        manifest = build_initial_manifest(
            job_id=job_id,
            spec=spec,
            now=now,
            pinned=pinned,
            raw_expires_at=raw_expires_at,
            artifact_expires_at=artifact_expires_at,
        )
        append_lifecycle_event(
            payload=manifest,
            status=JobStatus.QUEUED,
            stage="queued",
            occurred_at=now,
        )
        atomic_write_json(self._manifest_path(job_id), manifest)

        return self.get_job(job_id)

    def get_job(self, job_id: str) -> StoredJobRecordV2:
        manifest_path = self._manifest_path(job_id)
        if not manifest_path.exists():
            tombstone = self._tombstone_path(job_id)
            if tombstone.exists():
                raise JobExpiredV2(job_id=job_id)
            raise JobMissingV2(job_id=job_id)

        payload = read_json(manifest_path)

        source_format_obj = payload.get("source_format")
        output_format_obj = payload.get("output_format")
        if not isinstance(source_format_obj, str) or not isinstance(output_format_obj, str):
            raise ValueError(f"manifest missing source/output formats: {manifest_path}")
        source_format = SourceFormatV2(source_format_obj)
        output_format = OutputFormatV2(output_format_obj)

        resources_path = self._resources_zip_path(job_id)
        resources_zip_path = resources_path if resources_path.exists() else None
        reference_path = self._reference_docx_path(job_id)
        reference_docx_path = reference_path if reference_path.exists() else None

        record = parse_stored_job_record(
            payload=payload,
            manifest_path=manifest_path,
            expected_job_id=job_id,
            upload_path=self._raw_upload_path(job_id, source_format),
            resources_zip_path=resources_zip_path,
            reference_docx_path=reference_docx_path,
            artifact_path=self._artifact_path(job_id, output_format),
        )

        now = utc_now()
        if not record.pinned and now > record.artifact_expires_at:
            raise JobExpiredV2(job_id=job_id)

        return record

    def update_progress(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: str,
        total_pages: int | None = None,
        processed_pages: int | None = None,
        failed_pages: int | None = None,
        percent_complete: float | None = None,
        pages_per_minute: float | None = None,
        eta_seconds: int | None = None,
        phase_timings_ms: dict[str, int] | None = None,
    ) -> StoredJobRecordV2:
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            now = utc_now()
            previous_status_obj = payload.get("status")
            previous_status = (
                JobStatus(previous_status_obj) if isinstance(previous_status_obj, str) else None
            )

            payload["status"] = status.value
            progress = payload.get("progress")
            if not isinstance(progress, dict):
                progress = {}
                payload["progress"] = progress
            previous_stage_obj = progress.get("stage")
            previous_stage = previous_stage_obj if isinstance(previous_stage_obj, str) else None
            existing_page_fields = parse_progress_page_fields(progress)
            progress["stage"] = stage
            progress.setdefault("total_pages", None)
            progress.setdefault("processed_pages", None)
            progress.setdefault("failed_pages", None)
            progress.setdefault("percent_complete", None)
            progress.setdefault("pages_per_minute", None)
            progress.setdefault("eta_seconds", None)

            progress_changed = False
            updated_total_pages = parse_optional_nonneg_int(total_pages)
            if (
                updated_total_pages is not None
                and existing_page_fields.total_pages is None
                and updated_total_pages > 0
            ):
                progress["total_pages"] = updated_total_pages
                progress_changed = True

            resolved_total_pages = parse_optional_nonneg_int(progress.get("total_pages"))

            updated_processed_pages = parse_optional_nonneg_int(processed_pages)
            if resolved_total_pages is not None and updated_processed_pages is not None:
                updated_processed_pages = min(updated_processed_pages, resolved_total_pages)
            resolved_processed_pages = clamp_monotonic_int(
                existing_page_fields.processed_pages,
                updated_processed_pages,
            )
            if resolved_processed_pages != existing_page_fields.processed_pages:
                progress["processed_pages"] = resolved_processed_pages
                progress_changed = True

            updated_failed_pages = parse_optional_nonneg_int(failed_pages)
            if resolved_total_pages is not None and updated_failed_pages is not None:
                updated_failed_pages = min(updated_failed_pages, resolved_total_pages)
            resolved_failed_pages = clamp_monotonic_int(
                existing_page_fields.failed_pages,
                updated_failed_pages,
            )
            if resolved_failed_pages != existing_page_fields.failed_pages:
                progress["failed_pages"] = resolved_failed_pages
                progress_changed = True

            updated_percent = parse_optional_percent(percent_complete)
            resolved_percent = clamp_monotonic_float(
                existing_page_fields.percent_complete,
                updated_percent,
            )
            if resolved_percent != existing_page_fields.percent_complete:
                progress["percent_complete"] = resolved_percent
                progress_changed = True

            updated_ppm = parse_optional_nonneg_float(pages_per_minute)
            if updated_ppm is not None and updated_ppm != existing_page_fields.pages_per_minute:
                progress["pages_per_minute"] = updated_ppm
                progress_changed = True

            updated_eta_seconds = parse_optional_nonneg_int(eta_seconds)
            if (
                updated_eta_seconds is not None
                and updated_eta_seconds != existing_page_fields.eta_seconds
            ):
                progress["eta_seconds"] = updated_eta_seconds
                progress_changed = True

            timestamps = payload.get("timestamps")
            if not isinstance(timestamps, dict):
                timestamps = {}
                payload["timestamps"] = timestamps
            timestamps["updated_at"] = dt_to_rfc3339(now)
            diagnostics = ensure_diagnostics(payload)
            diagnostics["last_heartbeat_at"] = dt_to_rfc3339(now)
            diagnostics["current_phase_started_at"] = dt_to_rfc3339(now)
            if phase_timings_ms is not None:
                merge_phase_timings(
                    diagnostics=diagnostics,
                    additional_phase_timings_ms=phase_timings_ms,
                )
            should_emit_event = (
                previous_status != status
                or previous_stage != stage
                or progress_changed
                or phase_timings_ms is not None
            )
            if should_emit_event:
                append_lifecycle_event(
                    payload=payload,
                    status=status,
                    stage=stage,
                    occurred_at=now,
                )

            atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

    def touch_heartbeat(self, job_id: str) -> bool:
        """Update heartbeat timestamp for running jobs; return False when not running."""
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            status_obj = payload.get("status")
            if not isinstance(status_obj, str):
                raise ValueError(f"manifest missing status for job_id={job_id}")
            if JobStatus(status_obj) != JobStatus.RUNNING:
                return False

            now = utc_now()
            timestamps = payload.get("timestamps")
            if not isinstance(timestamps, dict):
                timestamps = {}
                payload["timestamps"] = timestamps
            timestamps["updated_at"] = dt_to_rfc3339(now)

            diagnostics = ensure_diagnostics(payload)
            new_heartbeat_at = dt_to_rfc3339(now)
            if diagnostics.get("last_heartbeat_at") == new_heartbeat_at:
                return True
            diagnostics["last_heartbeat_at"] = new_heartbeat_at

            atomic_write_json(manifest_path, payload)
            return True

    def claim_queued_job(self, job_id: str) -> bool:
        """Atomically claim a queued job for execution ownership."""
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            status_obj = payload.get("status")
            if not isinstance(status_obj, str):
                raise ValueError(f"manifest missing status for job_id={job_id}")
            if JobStatus(status_obj) != JobStatus.QUEUED:
                return False

            now = utc_now()
            payload["status"] = JobStatus.RUNNING.value
            progress = payload.get("progress")
            if not isinstance(progress, dict):
                progress = {}
                payload["progress"] = progress
            progress["stage"] = "starting"

            timestamps = payload.get("timestamps")
            if not isinstance(timestamps, dict):
                timestamps = {}
                payload["timestamps"] = timestamps
            timestamps["updated_at"] = dt_to_rfc3339(now)
            diagnostics = ensure_diagnostics(payload)
            diagnostics["last_heartbeat_at"] = dt_to_rfc3339(now)
            diagnostics["current_phase_started_at"] = dt_to_rfc3339(now)
            append_lifecycle_event(
                payload=payload,
                status=JobStatus.RUNNING,
                stage="starting",
                occurred_at=now,
            )

            atomic_write_json(manifest_path, payload)
            return True

    def mark_canceled(self, job_id: str) -> StoredJobRecordV2:
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            status_obj = payload.get("status")
            if not isinstance(status_obj, str):
                raise ValueError(f"manifest missing status for job_id={job_id}")
            actual_status = JobStatus(status_obj)
            if actual_status == JobStatus.CANCELED:
                return self.get_job(job_id)

            if actual_status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
                raise JobStateConflictV2(
                    job_id=job_id,
                    expected_statuses=(JobStatus.QUEUED, JobStatus.RUNNING),
                    actual_status=actual_status,
                )

            now = utc_now()
            payload["status"] = JobStatus.CANCELED.value
            progress = payload.get("progress")
            if not isinstance(progress, dict):
                progress = {}
                payload["progress"] = progress
            progress["stage"] = "canceled"

            timestamps = payload.get("timestamps")
            if not isinstance(timestamps, dict):
                timestamps = {}
                payload["timestamps"] = timestamps
            timestamps["updated_at"] = dt_to_rfc3339(now)

            diagnostics = ensure_diagnostics(payload)
            diagnostics["last_heartbeat_at"] = dt_to_rfc3339(now)
            diagnostics["current_phase_started_at"] = dt_to_rfc3339(now)
            append_lifecycle_event(
                payload=payload,
                status=JobStatus.CANCELED,
                stage="canceled",
                occurred_at=now,
            )

            atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)


__all__ = ["JobStoreV2Core"]
