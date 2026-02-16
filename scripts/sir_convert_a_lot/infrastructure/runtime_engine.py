"""Sir Convert-a-Lot infrastructure runtime engine.

Purpose:
    Provide filesystem-backed job persistence, idempotency tracking, and
    asynchronous conversion execution for the conversion bounded context.

Relationships:
    - Consumed by `interfaces.http_api` as the service backend.
    - Uses `domain.specs` for domain rules and `application.contracts` metadata.
"""

from __future__ import annotations

import threading
import time
from typing import Literal
from uuid import uuid4

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    JobSpec,
    JobStatus,
)
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    validate_acceleration_policy as validate_acceleration_policy_rule,
)
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    validate_backend_strategy as validate_backend_strategy_rule,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
)
from scripts.sir_convert_a_lot.infrastructure.docling_backend import DoclingConversionBackend
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import (
    GpuRuntimeProbeResult,
    probe_torch_gpu_runtime,
)
from scripts.sir_convert_a_lot.infrastructure.idempotency_store import IdempotencyStore
from scripts.sir_convert_a_lot.infrastructure.job_store import (
    JobExpired,
    JobMissing,
    JobStateConflict,
    JobStore,
)
from scripts.sir_convert_a_lot.infrastructure.pymupdf_backend import PyMuPdfConversionBackend
from scripts.sir_convert_a_lot.infrastructure.runtime_config import (
    fingerprint_for_request,
    service_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_conversion import execute_job_conversion
from scripts.sir_convert_a_lot.infrastructure.runtime_heartbeat import start_conversion_heartbeat
from scripts.sir_convert_a_lot.infrastructure.runtime_models import (
    ServiceConfig,
    ServiceError,
    StoredJob,
    utc_now,
)

__all__ = [
    "ServiceConfig",
    "ServiceError",
    "StoredJob",
    "ServiceRuntime",
    "fingerprint_for_request",
    "service_config_from_env",
    "utc_now",
]


class ServiceRuntime:
    """Thread-safe runtime state and execution for Sir Convert-a-Lot jobs."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.job_store = JobStore(
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
                        except (JobMissing, JobExpired):
                            continue
                        if record.status != JobStatus.QUEUED:
                            continue
                        self.run_job_async(job_id)
            except Exception:
                # Defensive: keep supervisor alive.
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
        return f"job_{uuid4().hex[:26]}"

    def get_job(self, job_id: str) -> StoredJob | None:
        self.job_store.sweep_expired()
        try:
            record = self.job_store.get_job(job_id)
        except JobExpired as exc:
            raise ServiceError(
                status_code=404,
                code="job_expired",
                message="Job has expired and is no longer available.",
                retryable=False,
                details={"job_id": exc.job_id},
            ) from exc
        except JobMissing:
            return None

        return StoredJob(
            job_id=record.job_id,
            spec=record.spec,
            source_filename=record.source_filename,
            upload_path=record.upload_path,
            artifact_path=record.artifact_path,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            expires_at=record.expires_at,
            progress_stage=record.progress_stage,
            pages_total=record.pages_total,
            pages_processed=record.pages_processed,
            last_heartbeat_at=record.last_heartbeat_at,
            current_phase_started_at=record.current_phase_started_at,
            phase_timings_ms=dict(record.phase_timings_ms),
            warnings=list(record.warnings),
            artifact_sha256=record.artifact_sha256,
            artifact_size_bytes=record.artifact_size_bytes,
            backend_used=record.backend_used,
            acceleration_used=record.acceleration_used,
            ocr_enabled=record.ocr_enabled,
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

    def create_job(self, spec: JobSpec, upload_bytes: bytes, source_filename: str) -> StoredJob:
        self.validate_backend_strategy(spec)
        self.validate_acceleration_policy(spec)
        job_id = self._new_job_id()
        record = self.job_store.create_job(
            job_id=job_id,
            spec=spec,
            source_filename=source_filename,
            upload_bytes=upload_bytes,
        )
        stored = self.get_job(record.job_id)
        if stored is None:
            raise RuntimeError("created job must be loadable immediately")
        return stored

    def _set_job_status(
        self,
        job_id: str,
        status: JobStatus,
        stage: str,
        *,
        pages_processed: int | None = None,
        pages_total: int | None = None,
    ) -> StoredJob | None:
        try:
            record = self.job_store.update_progress(
                job_id,
                status=status,
                stage=stage,
                pages_processed=pages_processed,
                pages_total=pages_total,
            )
        except (JobMissing, JobExpired):
            return None
        return self.get_job(record.job_id)

    def cancel_job(
        self, job_id: str
    ) -> Literal["missing", "accepted", "already_canceled", "conflict"]:
        job = self.get_job(job_id)
        if job is None:
            return "missing"
        if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
            try:
                self.job_store.mark_canceled(job_id)
            except (JobMissing, JobExpired):
                return "missing"
            return "accepted"
        if job.status == JobStatus.CANCELED:
            return "already_canceled"
        return "conflict"

    def validate_backend_strategy(self, spec: JobSpec) -> None:
        """Enforce backend compatibility constraints for the active rollout."""
        violation = validate_backend_strategy_rule(spec)
        if violation is None:
            return
        raise ServiceError(
            status_code=violation.status_code,
            code=violation.code,
            message=violation.message,
            retryable=violation.retryable,
            details=violation.details,
        )

    def validate_acceleration_policy(self, spec: JobSpec) -> GpuRuntimeProbeResult | None:
        """Enforce GPU-first rollout policy constraints."""
        violation = validate_acceleration_policy_rule(
            spec,
            gpu_available=self.config.gpu_available,
            allow_cpu_only=self.config.allow_cpu_only,
            allow_cpu_fallback=self.config.allow_cpu_fallback,
        )
        if violation is not None:
            raise ServiceError(
                status_code=violation.status_code,
                code=violation.code,
                message=violation.message,
                retryable=violation.retryable,
                details=violation.details,
            )

        probe: GpuRuntimeProbeResult | None = None
        if (
            self.config.gpu_available
            and spec.execution.acceleration_policy
            in {AccelerationPolicy.GPU_REQUIRED, AccelerationPolicy.GPU_PREFER}
            and spec.conversion.backend_strategy in {BackendStrategy.AUTO, BackendStrategy.DOCLING}
        ):
            probe = probe_torch_gpu_runtime()
            if not (probe.is_available and probe.runtime_kind in {"rocm", "cuda"}):
                raise ServiceError(
                    status_code=503,
                    code="gpu_not_available",
                    message=(
                        "GPU runtime is unavailable for the selected backend "
                        "under GPU-required policy."
                    ),
                    retryable=True,
                    details={
                        "reason": "backend_gpu_runtime_unavailable",
                        "backend": "docling",
                        "runtime_kind": probe.runtime_kind,
                        "hip_version": probe.hip_version,
                        "cuda_version": probe.cuda_version,
                    },
                )
        return probe

    def _execute_conversion(
        self, job: StoredJob
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        self.validate_backend_strategy(job.spec)
        runtime_probe = self.validate_acceleration_policy(job.spec)

        source_bytes = job.upload_path.read_bytes()
        if not source_bytes.startswith(b"%PDF"):
            raise ServiceError(
                status_code=422,
                code="pdf_unreadable",
                message="Uploaded file is not a readable PDF.",
                retryable=False,
            )
        try:
            return execute_job_conversion(
                spec=job.spec,
                source_filename=job.source_filename,
                source_bytes=source_bytes,
                gpu_available=self.config.gpu_available,
                gpu_runtime_probe=runtime_probe,
                docling_backend=self.docling_backend,
                pymupdf_backend=self.pymupdf_backend,
            )
        except BackendGpuUnavailableError as exc:
            raise ServiceError(
                status_code=503,
                code="gpu_not_available",
                message=(
                    "GPU runtime is unavailable for the selected backend under GPU-required policy."
                ),
                retryable=True,
                details={
                    "reason": "backend_gpu_runtime_unavailable",
                    "backend": "docling",
                    "runtime_kind": exc.probe.runtime_kind,
                    "hip_version": exc.probe.hip_version,
                    "cuda_version": exc.probe.cuda_version,
                },
            ) from exc
        except BackendInputError as exc:
            raise ServiceError(
                status_code=422,
                code="pdf_unreadable",
                message=f"Uploaded PDF could not be converted: {exc}",
                retryable=False,
            ) from exc
        except BackendExecutionError as exc:
            raise ServiceError(
                status_code=500,
                code="conversion_internal_error",
                message=f"Unexpected backend conversion failure: {exc}",
                retryable=True,
            ) from exc

    def run_job_async(self, job_id: str) -> None:
        """Run a conversion job asynchronously in a background thread."""
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
            except (JobMissing, JobExpired):
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

            self._set_job_status(
                job_id, JobStatus.RUNNING, "converting", pages_processed=1, pages_total=1
            )
            self.job_store.touch_heartbeat(job_id)
            heartbeat_stop, heartbeat_thread = start_conversion_heartbeat(
                job_store=self.job_store,
                job_id=job_id,
                heartbeat_interval_seconds=self.config.heartbeat_interval_seconds,
            )

            try:
                conversion_started = time.perf_counter()
                markdown_content, metadata, warnings, phase_timings_ms = self._execute_conversion(
                    job
                )
                phase_timings_ms["conversion_attempt_ms"] = max(
                    0, int((time.perf_counter() - conversion_started) * 1000)
                )
                artifact_bytes = markdown_content.encode("utf-8")
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=max(0.5, self.config.heartbeat_interval_seconds))
                self.job_store.mark_succeeded(
                    job_id,
                    markdown_bytes=artifact_bytes,
                    backend_used=metadata.backend_used,
                    acceleration_used=metadata.acceleration_used,
                    ocr_enabled=metadata.ocr_enabled,
                    options_fingerprint=metadata.options_fingerprint,
                    warnings=warnings,
                    phase_timings_ms=phase_timings_ms,
                )
            except JobStateConflict:
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
                except (JobMissing, JobExpired, JobStateConflict):
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
                except (JobMissing, JobExpired, JobStateConflict):
                    return
        finally:
            with self._lock:
                self._active_job_ids.discard(job_id)
