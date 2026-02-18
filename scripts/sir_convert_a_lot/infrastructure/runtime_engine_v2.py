"""Sir Convert-a-Lot infrastructure runtime engine for service API v2.

Purpose:
    Provide filesystem-backed v2 job persistence, idempotency tracking, and
    asynchronous conversion execution for multi-format conversion workflows
    executed on Hemma (dockerized runtime).

Relationships:
    - Consumed by v2 HTTP routes for service API v2 job lifecycle operations.
    - Coexists with the locked v1 runtime engine in `infrastructure.runtime_engine`.
    - Uses v1 PDF backends (Docling/PyMuPDF) for the PDF->Markdown stage where needed.
    - Uses Pandoc/WeasyPrint converter utilities for HTML/Markdown outputs.
"""

from __future__ import annotations

import threading
import time
from typing import Literal
from uuid import uuid4

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.docling_backend import DoclingConversionBackend
from scripts.sir_convert_a_lot.infrastructure.idempotency_store import IdempotencyStore
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    JobStateConflictV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.pymupdf_backend import PyMuPdfConversionBackend
from scripts.sir_convert_a_lot.infrastructure.runtime_heartbeat_v2 import (
    start_conversion_heartbeat_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    V2ExecutionResult,
    execute_v2_job_conversion,
)

__all__ = ["JobStoreV2", "ServiceRuntimeV2", "StoredJobV2"]


class ServiceRuntimeV2:
    """Thread-safe runtime state and execution for Sir Convert-a-Lot v2 jobs."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.job_store = JobStoreV2(
            data_root=config.data_root,
            raw_ttl_seconds=config.upload_ttl_seconds,
            artifact_ttl_seconds=config.result_ttl_seconds,
        )
        self.idempotency_store = IdempotencyStore(
            data_root=config.data_root,
            ttl_seconds=config.idempotency_ttl_seconds,
        )
        self.docling_backend = DoclingConversionBackend()
        self.pymupdf_backend = PyMuPdfConversionBackend()
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._supervisor_thread: threading.Thread | None = None
        self._active_job_ids: set[str] = set()

        self.job_store.sweep_expired()
        self.job_store.recover_running_jobs_to_queued(active_job_ids=self._active_job_ids)

        if self.config.enable_supervisor:
            self._supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
            self._supervisor_thread.start()

    def _supervisor_loop(self) -> None:
        """Background supervisor that runs queued jobs and re-runs recovered jobs."""
        while not self._shutdown_event.is_set():
            try:
                self.job_store.sweep_expired()
                self.job_store.recover_running_jobs_to_queued(active_job_ids=self._active_job_ids)

                with self._lock:
                    active_count = len(self._active_job_ids)
                    max_workers = max(1, self.config.max_workers)
                if active_count < max_workers:
                    for job_id in self.job_store.list_job_ids():
                        with self._lock:
                            if len(self._active_job_ids) >= max_workers:
                                break
                            if job_id in self._active_job_ids:
                                continue
                        try:
                            record = self.job_store.get_job(job_id)
                        except (JobMissingV2, JobExpiredV2):
                            continue
                        if record.status != JobStatus.QUEUED:
                            continue
                        self.run_job_async(job_id)
            except Exception:
                pass

            self._shutdown_event.wait(timeout=max(0.05, self.config.supervisor_poll_seconds))

    def shutdown(self) -> None:
        """Stop background supervisor loops and release runtime resources."""
        self._shutdown_event.set()
        if self._supervisor_thread is None:
            return
        if not self._supervisor_thread.is_alive():
            return
        join_timeout_seconds = max(1.0, self.config.supervisor_poll_seconds * 4)
        self._supervisor_thread.join(timeout=join_timeout_seconds)

    def _new_job_id(self) -> str:
        return f"jobv2_{uuid4().hex[:26]}"

    def get_job(self, job_id: str) -> StoredJobV2 | None:
        self.job_store.sweep_expired()
        try:
            record = self.job_store.get_job(job_id)
        except JobExpiredV2 as exc:
            raise ServiceError(
                status_code=404,
                code="job_expired",
                message="Job has expired and is no longer available.",
                retryable=False,
                details={"job_id": exc.job_id},
            ) from exc
        except JobMissingV2:
            return None

        return StoredJobV2(
            job_id=record.job_id,
            spec=record.spec,
            source_filename=record.source_filename,
            source_format=record.source_format,
            output_format=record.output_format,
            upload_path=record.upload_path,
            resources_zip_path=record.resources_zip_path,
            reference_docx_path=record.reference_docx_path,
            artifact_path=record.artifact_path,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            expires_at=record.expires_at,
            progress_stage=record.progress_stage,
            last_heartbeat_at=record.last_heartbeat_at,
            current_phase_started_at=record.current_phase_started_at,
            phase_timings_ms=dict(record.phase_timings_ms),
            warnings=list(record.warnings),
            artifact_sha256=record.artifact_sha256,
            artifact_size_bytes=record.artifact_size_bytes,
            pipeline_used=record.pipeline_used,
            backend_used=record.backend_used,
            acceleration_used=record.acceleration_used,
            options_fingerprint=record.options_fingerprint,
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            failure_retryable=record.failure_retryable,
            failure_details=record.failure_details,
        )

    def get_idempotency(self, scope_key: str):
        return self.idempotency_store.get(scope_key)

    def put_idempotency(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        self.idempotency_store.put(scope_key, fingerprint, job_id)

    def create_job(
        self,
        *,
        spec: JobSpecV2,
        upload_bytes: bytes,
        resources_zip_bytes: bytes | None,
        reference_docx_bytes: bytes | None,
    ) -> StoredJobV2:
        job_id = self._new_job_id()
        record = self.job_store.create_job(
            job_id=job_id,
            spec=spec,
            upload_bytes=upload_bytes,
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=reference_docx_bytes,
        )
        stored = self.get_job(record.job_id)
        if stored is None:
            raise RuntimeError("created v2 job must be loadable immediately")
        return stored

    def cancel_job(
        self, job_id: str
    ) -> Literal["missing", "accepted", "already_canceled", "conflict"]:
        job = self.get_job(job_id)
        if job is None:
            return "missing"
        if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
            try:
                self.job_store.mark_canceled(job_id)
            except (JobMissingV2, JobExpiredV2):
                return "missing"
            return "accepted"
        if job.status == JobStatus.CANCELED:
            return "already_canceled"
        return "conflict"

    def run_job_async(self, job_id: str) -> None:
        """Run a v2 conversion job asynchronously in a background thread."""
        with self._lock:
            if job_id in self._active_job_ids:
                return
            self._active_job_ids.add(job_id)
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()

    def _run_job(self, job_id: str) -> None:
        try:
            try:
                claimed = self.job_store.claim_queued_job(job_id)
            except (JobMissingV2, JobExpiredV2):
                return
            if not claimed:
                return

            job = self.get_job(job_id)
            if job is None:
                return

            time.sleep(self.config.processing_delay_seconds)

            job = self.get_job(job_id)
            if job is None:
                return
            if job.status == JobStatus.CANCELED:
                return

            self.job_store.update_progress(job_id, status=JobStatus.RUNNING, stage="converting")
            self.job_store.touch_heartbeat(job_id)
            heartbeat_stop, heartbeat_thread = start_conversion_heartbeat_v2(
                job_store=self.job_store,
                job_id=job_id,
                heartbeat_interval_seconds=self.config.heartbeat_interval_seconds,
            )

            try:
                conversion_started = time.perf_counter()
                result: V2ExecutionResult = execute_v2_job_conversion(
                    job=job,
                    config=self.config,
                    docling_backend=self.docling_backend,
                    pymupdf_backend=self.pymupdf_backend,
                )
                phase_timings_ms = dict(result.phase_timings_ms)
                phase_timings_ms["conversion_attempt_ms"] = max(
                    0, int((time.perf_counter() - conversion_started) * 1000)
                )
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=max(0.5, self.config.heartbeat_interval_seconds))
                self.job_store.mark_succeeded(
                    job_id,
                    artifact_bytes=result.artifact_bytes,
                    pipeline_used=result.pipeline_used,
                    backend_used=result.backend_used,
                    acceleration_used=result.acceleration_used,
                    options_fingerprint=f"sha256:{result.options_fingerprint}",
                    warnings=result.warnings,
                    phase_timings_ms=phase_timings_ms,
                )
            except JobStateConflictV2:
                return
            except ServiceError as exc:
                conversion_elapsed_ms = max(
                    0, int((time.perf_counter() - conversion_started) * 1000)
                )
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=max(0.5, self.config.heartbeat_interval_seconds))
                try:
                    self.job_store.mark_failed(
                        job_id,
                        code=exc.code,
                        message=exc.message,
                        retryable=exc.retryable,
                        details=exc.details,
                        phase_timings_ms={"conversion_attempt_ms": conversion_elapsed_ms},
                    )
                except (JobMissingV2, JobExpiredV2, JobStateConflictV2):
                    return
            except Exception as exc:  # pragma: no cover - defensive fallback
                conversion_elapsed_ms = max(
                    0, int((time.perf_counter() - conversion_started) * 1000)
                )
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=max(0.5, self.config.heartbeat_interval_seconds))
                try:
                    self.job_store.mark_failed(
                        job_id,
                        code="conversion_internal_error",
                        message=f"Unexpected conversion error: {exc}",
                        retryable=True,
                        details=None,
                        phase_timings_ms={"conversion_attempt_ms": conversion_elapsed_ms},
                    )
                except (JobMissingV2, JobExpiredV2, JobStateConflictV2):
                    return
        finally:
            with self._lock:
                self._active_job_ids.discard(job_id)
