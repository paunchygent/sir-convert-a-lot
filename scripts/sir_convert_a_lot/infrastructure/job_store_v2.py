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

from datetime import timedelta

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2_core import JobStoreV2Core


class JobStoreV2(JobStoreV2Core):
    """Filesystem-backed store for v2 conversion jobs."""

    def list_job_ids(self) -> list[str]:
        return sorted(path.name for path in self.jobs_dir.iterdir() if path.is_dir())

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


__all__ = ["JobStoreV2"]
