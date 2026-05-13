"""Runtime capacity and terminal telemetry helpers for service API v2.

Purpose:
    Keep worker-capacity gauges, PDF chunk-capacity gauges, GPU snapshot
    enrichment, and terminal-job observations out of the v2 runtime engine so
    orchestration code can focus on job lifecycle transitions.

Relationships:
    - Used by `infrastructure.runtime_engine_v2.ServiceRuntimeV2`.
    - Emits through `infrastructure.runtime_telemetry_v2` sinks.
    - Reads durable job state through the v2 job-store contract.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy, JobStatus
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import (
    GpuRuntimeProbeResult,
    probe_torch_gpu_runtime,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_utilization_snapshot import (
    sample_gpu_utilization_snapshot,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    StoredJobRecordV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.runtime_telemetry_v2 import (
    NoopRuntimeTelemetrySinkV2,
    RuntimeTelemetrySinkV2,
)


class RuntimeCapacityJobStoreV2(Protocol):
    """Job-store operations needed for runtime capacity telemetry."""

    def list_job_ids(self) -> list[str]:
        """Return all visible v2 job ids."""

    def get_job(self, job_id: str) -> StoredJobRecordV2:
        """Return one durable job record or raise a store visibility error."""


RuntimeTelemetrySinkLikeV2 = RuntimeTelemetrySinkV2 | NoopRuntimeTelemetrySinkV2


@dataclass(frozen=True)
class RuntimeGpuUtilizationFieldsV2:
    """Best-effort GPU utilization fields persisted with terminal jobs."""

    runtime_kind: str | None
    device_count: int | None
    busy_percent: int | None
    memory_used_percent: int | None


class RuntimeCapacityTelemetryEmitterV2:
    """Emit runtime and PDF chunk worker capacity gauges from bounded state."""

    def __init__(
        self,
        *,
        config: ServiceConfig,
        telemetry_sink: RuntimeTelemetrySinkLikeV2,
        job_store: RuntimeCapacityJobStoreV2,
        active_job_count: Callable[[], int],
        active_chunk_worker_count: Callable[[], int],
    ) -> None:
        self._config = config
        self._telemetry_sink = telemetry_sink
        self._job_store = job_store
        self._active_job_count = active_job_count
        self._active_chunk_worker_count = active_chunk_worker_count

    def _queued_job_count(self) -> int:
        queued_jobs = 0
        for job_id in self._job_store.list_job_ids():
            try:
                record = self._job_store.get_job(job_id)
            except (JobMissingV2, JobExpiredV2):
                continue
            if record.status == JobStatus.QUEUED:
                queued_jobs += 1
        return queued_jobs

    def emit_runtime_capacity(self) -> None:
        """Emit active/queued job capacity metrics when telemetry is enabled."""
        if not self._config.enable_runtime_telemetry_calls:
            return
        try:
            active_jobs = max(0, int(self._active_job_count()))
            max_workers = max(1, self._config.max_workers)
            gpu_stage_global_cap = max(1, self._config.gpu_stage_max_concurrency)
            queued_jobs = self._queued_job_count()
            self._telemetry_sink.observe_runtime_capacity(
                active_jobs=active_jobs,
                queued_jobs=queued_jobs,
                max_workers=max_workers,
                gpu_available=self._config.gpu_available,
                gpu_stage_global_cap=gpu_stage_global_cap,
            )
        except Exception:
            return

    def emit_chunk_capacity(self) -> None:
        """Emit active PDF chunk worker capacity metrics when telemetry is enabled."""
        if not self._config.enable_runtime_telemetry_calls:
            return
        try:
            active_chunk_workers = max(0, int(self._active_chunk_worker_count()))
            max_chunk_workers_per_job = (
                max(1, int(self._config.max_chunk_workers))
                if self._config.enable_parallel_pdf_chunks
                else 1
            )
            global_chunk_worker_cap = max(1, int(self._config.gpu_stage_max_concurrency))
            self._telemetry_sink.observe_chunk_capacity(
                active_chunk_workers=active_chunk_workers,
                max_chunk_workers_per_job=max_chunk_workers_per_job,
                global_chunk_worker_cap=global_chunk_worker_cap,
            )
        except Exception:
            return


class RuntimeChunkWorkerLimiterV2:
    """Bound global PDF chunk worker concurrency and emit capacity changes."""

    def __init__(
        self,
        *,
        max_concurrency: int,
        emit_capacity: Callable[[], None],
    ) -> None:
        self._semaphore = threading.BoundedSemaphore(max(1, int(max_concurrency)))
        self._emit_capacity = emit_capacity
        self._lock = threading.Lock()
        self._active_workers = 0

    @property
    def active_workers(self) -> int:
        """Return the current active chunk worker count."""
        with self._lock:
            return max(0, int(self._active_workers))

    def acquire(self) -> None:
        """Acquire one global chunk worker slot and emit capacity metrics."""
        self._semaphore.acquire()
        with self._lock:
            self._active_workers += 1
        self._emit_capacity()

    def release(self) -> None:
        """Release one global chunk worker slot and emit capacity metrics."""
        with self._lock:
            self._active_workers = max(0, self._active_workers - 1)
        try:
            self._semaphore.release()
        finally:
            self._emit_capacity()


def resolve_acceleration_policy_v2(job: StoredJobV2) -> AccelerationPolicy | None:
    """Return the requested acceleration policy from a stored job, when present."""
    execution = job.spec.execution
    if execution is None:
        return None
    return execution.acceleration_policy


def resolve_requested_acceleration_policy_value_v2(job: object) -> str | None:
    """Return the persisted requested acceleration policy value for terminal metadata."""
    spec_obj = getattr(job, "spec", None)
    execution_obj = getattr(spec_obj, "execution", None)
    policy_obj = getattr(execution_obj, "acceleration_policy", None)
    if isinstance(policy_obj, AccelerationPolicy):
        return policy_obj.value
    if isinstance(policy_obj, str) and policy_obj.strip() != "":
        return policy_obj
    return None


def collect_gpu_utilization_fields_v2(
    *,
    acceleration_used: str | None,
) -> RuntimeGpuUtilizationFieldsV2:
    """Collect best-effort GPU utilization fields for CUDA-backed completions."""
    if acceleration_used != "cuda":
        return RuntimeGpuUtilizationFieldsV2(
            runtime_kind=None,
            device_count=None,
            busy_percent=None,
            memory_used_percent=None,
        )
    probe: GpuRuntimeProbeResult = probe_torch_gpu_runtime()
    runtime_kind = probe.runtime_kind if probe.runtime_kind in {"rocm", "cuda"} else "none"
    snapshot = sample_gpu_utilization_snapshot(runtime_kind=runtime_kind)
    busy_percent = snapshot.gpu_busy_percent if snapshot is not None else None
    memory_percent = snapshot.gpu_memory_used_percent if snapshot is not None else None
    return RuntimeGpuUtilizationFieldsV2(
        runtime_kind=runtime_kind if runtime_kind != "none" else None,
        device_count=probe.device_count if probe.device_count >= 0 else None,
        busy_percent=busy_percent,
        memory_used_percent=memory_percent,
    )


def observe_canceled_job_telemetry_v2(
    *,
    enabled: bool,
    telemetry_sink: RuntimeTelemetrySinkLikeV2,
    job: StoredJobV2,
) -> None:
    """Observe terminal cancellation telemetry without surfacing telemetry failures."""
    if not enabled:
        return
    try:
        telemetry_sink.observe_terminal_job(
            status=job.status,
            source_format=job.source_format,
            output_format=job.output_format,
            backend_used=job.backend_used,
            acceleration_policy=resolve_acceleration_policy_v2(job),
            acceleration_used=job.acceleration_used,
        )
    except Exception:
        return


def observe_succeeded_job_telemetry_v2(
    *,
    enabled: bool,
    telemetry_sink: RuntimeTelemetrySinkLikeV2,
    job: StoredJobV2,
) -> None:
    """Observe terminal success telemetry without surfacing telemetry failures."""
    if not enabled:
        return
    try:
        telemetry_sink.observe_phase_timings(
            source_format=job.source_format,
            phase_timings_ms=job.phase_timings_ms,
        )
        telemetry_sink.observe_retry_warnings(
            source_format=job.source_format,
            warnings=job.warnings,
        )
        telemetry_sink.observe_gpu_snapshot(
            runtime_kind=job.gpu_runtime_kind,
            gpu_device_count=job.gpu_device_count,
            gpu_busy_percent=job.gpu_busy_percent,
            gpu_memory_used_percent=job.gpu_memory_used_percent,
        )
        telemetry_sink.observe_terminal_job(
            status=job.status,
            source_format=job.source_format,
            output_format=job.output_format,
            backend_used=job.backend_used,
            acceleration_policy=resolve_acceleration_policy_v2(job),
            acceleration_used=job.acceleration_used,
        )
    except Exception:
        return


def observe_failed_job_telemetry_v2(
    *,
    enabled: bool,
    telemetry_sink: RuntimeTelemetrySinkLikeV2,
    job: StoredJobV2,
) -> None:
    """Observe terminal failure telemetry without surfacing telemetry failures."""
    if not enabled:
        return
    try:
        telemetry_sink.observe_phase_timings(
            source_format=job.source_format,
            phase_timings_ms=job.phase_timings_ms,
        )
        telemetry_sink.observe_terminal_job(
            status=job.status,
            source_format=job.source_format,
            output_format=job.output_format,
            backend_used=job.backend_used,
            acceleration_policy=resolve_acceleration_policy_v2(job),
            acceleration_used=job.acceleration_used,
        )
    except Exception:
        return
