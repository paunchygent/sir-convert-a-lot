"""Filesystem-backed job store for Sir Convert-a-Lot v1.

Provides durable v1 job-state persistence and recovery for runtime orchestration.
"""

from __future__ import annotations

import fcntl
import hashlib
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Iterator

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_manifest import (
    build_initial_manifest,
    ensure_diagnostics,
    merge_phase_timings,
    parse_stored_job_record,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models import (
    JobExpired,
    JobMissing,
    JobStateConflict,
    StoredJobRecord,
)


class JobStore:
    """Filesystem-backed store for v1 conversion jobs."""

    def __init__(
        self,
        *,
        data_root: Path,
        raw_ttl_seconds: int,
        artifact_ttl_seconds: int,
        tombstone_ttl_seconds: int = 30 * 24 * 3600,
    ) -> None:
        self.data_root = data_root
        self.jobs_dir = data_root / "jobs"
        self.expired_dir = data_root / "expired"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.expired_dir.mkdir(parents=True, exist_ok=True)
        self.raw_ttl_seconds = raw_ttl_seconds
        self.artifact_ttl_seconds = artifact_ttl_seconds
        self.tombstone_ttl_seconds = tombstone_ttl_seconds

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def _manifest_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "manifest.json"

    def _raw_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "raw" / "input.pdf"

    def _artifact_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "artifacts" / "output.md"

    def _log_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "logs" / "run.log"

    def _tombstone_path(self, job_id: str) -> Path:
        return self.expired_dir / f"{job_id}.json"

    def _lock_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / ".manifest.lock"

    def _raise_missing_or_expired(self, job_id: str) -> None:
        tombstone = self._tombstone_path(job_id)
        if tombstone.exists():
            raise JobExpired(job_id=job_id)
        raise JobMissing(job_id=job_id)

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
            raise JobStateConflict(
                job_id=job_id,
                expected_statuses=expected_statuses,
                actual_status=actual_status,
            )

    def create_job(
        self,
        *,
        job_id: str,
        spec: JobSpec,
        source_filename: str,
        upload_bytes: bytes,
    ) -> StoredJobRecord:
        now = utc_now()

        job_dir = self._job_dir(job_id)
        (job_dir / "raw").mkdir(parents=True, exist_ok=True)
        (job_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_dir / "logs").mkdir(parents=True, exist_ok=True)

        upload_path = self._raw_path(job_id)
        self._artifact_path(job_id)
        log_path = self._log_path(job_id)

        upload_path.write_bytes(upload_bytes)
        log_path.write_text("", encoding="utf-8")

        pinned = bool(spec.retention.pin)
        raw_expires_at = now + timedelta(seconds=self.raw_ttl_seconds)
        artifact_expires_at = now + timedelta(seconds=self.artifact_ttl_seconds)

        manifest = build_initial_manifest(
            job_id=job_id,
            spec=spec,
            source_filename=source_filename,
            now=now,
            pinned=pinned,
            raw_expires_at=raw_expires_at,
            artifact_expires_at=artifact_expires_at,
        )
        atomic_write_json(self._manifest_path(job_id), manifest)

        return self.get_job(job_id)

    def get_job(self, job_id: str) -> StoredJobRecord:
        manifest_path = self._manifest_path(job_id)
        if not manifest_path.exists():
            tombstone = self._tombstone_path(job_id)
            if tombstone.exists():
                raise JobExpired(job_id=job_id)
            raise JobMissing(job_id=job_id)

        payload = read_json(manifest_path)
        record = parse_stored_job_record(
            payload=payload,
            manifest_path=manifest_path,
            expected_job_id=job_id,
            upload_path=self._raw_path(job_id),
            artifact_path=self._artifact_path(job_id),
        )

        now = utc_now()
        if not record.pinned and now > record.artifact_expires_at:
            # Job exists but is expired.
            raise JobExpired(job_id=job_id)

        return record

    def update_progress(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: str,
        pages_processed: int | None = None,
        pages_total: int | None = None,
    ) -> StoredJobRecord:
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
            if pages_processed is not None:
                progress["pages_processed"] = pages_processed
            if pages_total is not None:
                progress["pages_total"] = pages_total

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
        markdown_bytes: bytes,
        backend_used: str,
        acceleration_used: str,
        ocr_enabled: bool,
        options_fingerprint: str,
        warnings: list[str],
        phase_timings_ms: dict[str, int] | None = None,
    ) -> StoredJobRecord:
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

            artifact_path = self._artifact_path(job_id)
            artifact_path.write_bytes(markdown_bytes)
            sha = hashlib.sha256(markdown_bytes).hexdigest()

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
                    "markdown_filename": artifact_path.name,
                    "size_bytes": len(markdown_bytes),
                    "sha256": sha,
                },
                "conversion_metadata": {
                    "backend_used": backend_used,
                    "acceleration_used": acceleration_used,
                    "ocr_enabled": ocr_enabled,
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
    ) -> StoredJobRecord:
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

    def mark_canceled(self, job_id: str) -> StoredJobRecord:
        return self.update_progress(job_id, status=JobStatus.CANCELED, stage="canceled")

    def list_job_ids(self) -> list[str]:
        return sorted(path.name for path in self.jobs_dir.iterdir() if path.is_dir())

    def recover_running_jobs_to_queued(self, *, active_job_ids: set[str]) -> list[str]:
        """Convert orphaned running jobs to queued.

        This is deterministic and safe on startup because no worker processes are tracked in v1.
        """
        recovered: list[str] = []
        for job_id in self.list_job_ids():
            if job_id in active_job_ids:
                continue
            try:
                record = self.get_job(job_id)
            except (JobMissing, JobExpired):
                continue
            if record.status == JobStatus.RUNNING:
                self.update_progress(job_id, status=JobStatus.QUEUED, stage="queued")
                recovered.append(job_id)
        return recovered

    def sweep_expired(self) -> None:
        """Sweep expired jobs and retain tombstones so the API can return job_expired."""
        now = utc_now()

        # Expire old tombstones.
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
            except JobExpired:
                # Create/refresh tombstone and remove directory contents.
                tombstone_payload: dict[str, object] = {
                    "job_id": job_id,
                    "expired_at": dt_to_rfc3339(now),
                }
                atomic_write_json(self._tombstone_path(job_id), tombstone_payload)
                # Remove job directory (best-effort).
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
            except JobMissing:
                continue

            if record.pinned:
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
