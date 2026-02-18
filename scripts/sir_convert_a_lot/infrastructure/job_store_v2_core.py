"""Filesystem-backed job store core for Sir Convert-a-Lot service API v2.

Purpose:
    Provide durable v2 job persistence + atomic state transitions for runtime
    orchestration, including binary artifacts (PDF/DOCX) and auxiliary uploads
    (resources zip, reference docx).

Relationships:
    - Extended by `infrastructure.job_store_v2.JobStoreV2` (sweeping + recovery).
    - Used by `infrastructure.runtime_engine_v2` for v2 job lifecycle operations.
    - Uses `infrastructure.job_store_manifest_v2` for manifest creation/parsing.
"""

from __future__ import annotations

import fcntl
import hashlib
import time
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


def _artifact_content_type(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.PDF:
        return "application/pdf"
    if output_format == OutputFormatV2.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise AssertionError(f"Unsupported output_format: {output_format}")


class JobStoreV2Core:
    """Filesystem-backed core store for v2 conversion jobs."""

    def __init__(
        self,
        *,
        data_root: Path,
        raw_ttl_seconds: int,
        artifact_ttl_seconds: int,
        tombstone_ttl_seconds: int = 30 * 24 * 3600,
    ) -> None:
        self.data_root = data_root
        self.jobs_dir = data_root / "jobs_v2"
        self.expired_dir = data_root / "expired_v2"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.expired_dir.mkdir(parents=True, exist_ok=True)
        self.raw_ttl_seconds = raw_ttl_seconds
        self.artifact_ttl_seconds = artifact_ttl_seconds
        self.tombstone_ttl_seconds = tombstone_ttl_seconds

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
    ) -> StoredJobRecordV2:
        manifest_path = self._manifest_path(job_id)
        with self._job_manifest_lock(job_id):
            payload = self._read_manifest_locked(job_id)
            now = utc_now()

            payload["status"] = status.value
            progress = payload.get("progress")
            if not isinstance(progress, dict):
                progress = {}
                payload["progress"] = progress
            progress["stage"] = stage

            timestamps = payload.get("timestamps")
            if not isinstance(timestamps, dict):
                timestamps = {}
                payload["timestamps"] = timestamps
            timestamps["updated_at"] = dt_to_rfc3339(now)
            diagnostics = ensure_diagnostics(payload)
            diagnostics["last_heartbeat_at"] = dt_to_rfc3339(now)
            diagnostics["current_phase_started_at"] = dt_to_rfc3339(now)

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

            atomic_write_json(manifest_path, payload)
            return True

    def mark_succeeded(
        self,
        job_id: str,
        *,
        artifact_bytes: bytes,
        pipeline_used: str,
        backend_used: str | None,
        acceleration_used: str | None,
        options_fingerprint: str,
        warnings: list[str],
        phase_timings_ms: dict[str, int] | None = None,
    ) -> StoredJobRecordV2:
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
                    "options_fingerprint": options_fingerprint,
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

            atomic_write_json(manifest_path, payload)
            persist_elapsed_ms = max(
                0, int((time.perf_counter() - persist_started_monotonic) * 1000)
            )
            merge_phase_timings(
                diagnostics=diagnostics,
                additional_phase_timings_ms={"persist_ms": persist_elapsed_ms},
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

            atomic_write_json(manifest_path, payload)
            persist_elapsed_ms = max(
                0, int((time.perf_counter() - persist_started_monotonic) * 1000)
            )
            merge_phase_timings(
                diagnostics=diagnostics,
                additional_phase_timings_ms={"persist_ms": persist_elapsed_ms},
            )
            atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

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

            atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)


__all__ = ["JobStoreV2Core"]
