"""Worker supervision loop for service API v2 runtime jobs.

Purpose:
    Own the background queue scanner that recovers interrupted jobs and starts
    eligible queued work while respecting the configured worker cap.

Relationships:
    - Used by `infrastructure.runtime_engine_v2.ServiceRuntimeV2`.
    - Reads durable state through `infrastructure.job_store_v2.JobStoreV2`.
    - Delegates actual job execution back to the runtime engine through a
      typed callback.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from types import TracebackType
from typing import Protocol

from scripts.sir_convert_a_lot.domain.service_routes_v2 import route_dispatches_runtime_jobs_v2
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    StoredJobRecordV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig


class RuntimeSupervisorLockV2(Protocol):
    """Context-manager lock used by the runtime supervisor."""

    def __enter__(self) -> object:
        """Acquire the lock."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Release the lock."""


class RuntimeSupervisorJobStoreV2(Protocol):
    """Job-store operations needed by the runtime supervisor."""

    def sweep_expired(self) -> None:
        """Remove expired job visibility surfaces."""

    def recover_running_jobs_to_queued(self, *, active_job_ids: set[str]) -> list[str]:
        """Recover abandoned running jobs not present in the active worker set."""

    def list_job_ids(self) -> list[str]:
        """Return visible job ids in store order."""

    def get_job(self, job_id: str) -> StoredJobRecordV2:
        """Return a durable job record or raise a visibility exception."""


class RuntimeSupervisorV2:
    """Background supervisor for queued and recovered v2 jobs."""

    def __init__(
        self,
        *,
        config: ServiceConfig,
        job_store: RuntimeSupervisorJobStoreV2,
        active_job_ids: set[str],
        lock: RuntimeSupervisorLockV2,
        shutdown_event: threading.Event,
        run_job_async: Callable[[str], None],
        emit_capacity: Callable[[], None],
    ) -> None:
        self._config = config
        self._job_store = job_store
        self._active_job_ids = active_job_ids
        self._lock = lock
        self._shutdown_event = shutdown_event
        self._run_job_async = run_job_async
        self._emit_capacity = emit_capacity

    def start_if_enabled(self) -> threading.Thread | None:
        """Start the supervisor loop when runtime config enables it."""
        if not self._config.enable_supervisor:
            return None
        thread = threading.Thread(target=self.run_loop, daemon=True)
        thread.start()
        return thread

    def run_loop(self) -> None:
        """Run queued jobs and recover interrupted jobs until shutdown."""
        while not self._shutdown_event.is_set():
            try:
                self._job_store.sweep_expired()
                self._job_store.recover_running_jobs_to_queued(active_job_ids=self._active_job_ids)
                max_workers = max(1, self._config.max_workers)
                with self._lock:
                    active_count = len(self._active_job_ids)
                if active_count < max_workers:
                    self._start_queued_jobs_until_capacity(max_workers=max_workers)
            except Exception:
                pass
            self._emit_capacity()
            self._shutdown_event.wait(timeout=max(0.05, self._config.supervisor_poll_seconds))

    def _start_queued_jobs_until_capacity(self, *, max_workers: int) -> None:
        for job_id in self._job_store.list_job_ids():
            with self._lock:
                if len(self._active_job_ids) >= max_workers:
                    break
                if job_id in self._active_job_ids:
                    continue
            try:
                record = self._job_store.get_job(job_id)
            except (JobMissingV2, JobExpiredV2):
                continue
            if record.status != JobStatus.QUEUED:
                continue
            if not route_dispatches_runtime_jobs_v2(
                source_format=record.source_format,
                output_format=record.output_format,
            ):
                continue
            self._run_job_async(job_id)


def join_supervisor_thread_v2(
    *,
    thread: threading.Thread | None,
    supervisor_poll_seconds: float,
) -> None:
    """Join a supervisor thread with the runtime's bounded shutdown timeout."""
    if thread is None:
        return
    if not thread.is_alive():
        return
    join_timeout_seconds = max(1.0, supervisor_poll_seconds * 4)
    thread.join(timeout=join_timeout_seconds)
