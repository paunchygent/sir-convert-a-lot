"""Runtime telemetry sink for Sir Convert-a-Lot service API v2.

Purpose:
    Provide a typed, app-owned telemetry sink that runtime components can use to
    emit bounded-cardinality Prometheus metrics without owning collector setup.

Relationships:
    - Constructed by `interfaces.http_api` and stored in app state.
    - Injected into `infrastructure.runtime_engine_v2.ServiceRuntimeV2`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import normalize_phase_timings_map

_KNOWN_BACKEND_LABELS: frozenset[str] = frozenset(
    {"docling", "pymupdf", "pandoc", "weasyprint", "pandoc+weasyprint"}
)
_KNOWN_ACCELERATION_POLICY_LABELS: frozenset[str] = frozenset(
    {"gpu_required", "gpu_prefer", "cpu_only"}
)
_KNOWN_ACCELERATION_USED_LABELS: frozenset[str] = frozenset({"cpu", "cuda"})
_KNOWN_RETRY_KINDS: frozenset[str] = frozenset({"ocr_auto", "ordering", "other"})
_KNOWN_GPU_RUNTIME_KINDS: frozenset[str] = frozenset({"rocm", "cuda"})


def _normalize_backend_label(value: str | None) -> str:
    if value is None:
        return "none"
    normalized = value.strip().lower()
    if normalized in _KNOWN_BACKEND_LABELS:
        return normalized
    return "other"


def _normalize_acceleration_used_label(value: str | None) -> str:
    if value is None:
        return "none"
    normalized = value.strip().lower()
    if normalized in _KNOWN_ACCELERATION_USED_LABELS:
        return normalized
    return "other"


def _normalize_acceleration_policy_label(value: AccelerationPolicy | None) -> str:
    if value is None:
        return "none"
    normalized = value.value.strip().lower()
    if normalized in _KNOWN_ACCELERATION_POLICY_LABELS:
        return normalized
    return "other"


def _retry_kind_from_warning(warning: str) -> str | None:
    normalized = warning.strip().lower()
    if normalized == "":
        return None
    if normalized == "docling_auto_ocr_retry_applied":
        return "ocr_auto"
    if "ordering_retry" in normalized:
        return "ordering"
    if "retry" in normalized:
        return "other"
    return None


def _normalize_gpu_runtime_kind(value: str | None) -> str:
    if value is None:
        return "none"
    normalized = value.strip().lower()
    if normalized in _KNOWN_GPU_RUNTIME_KINDS:
        return normalized
    return "other"


class RuntimeTelemetrySinkV2:
    """Prometheus-backed runtime telemetry sink with bounded label sets."""

    def __init__(self, *, registry: CollectorRegistry) -> None:
        self.jobs_active = Gauge(
            "sir_convert_a_lot_v2_jobs_active",
            "Number of currently active v2 conversion jobs.",
            registry=registry,
        )
        self.jobs_queued = Gauge(
            "sir_convert_a_lot_v2_jobs_queued",
            "Number of queued v2 conversion jobs.",
            registry=registry,
        )
        self.workers_max = Gauge(
            "sir_convert_a_lot_v2_workers_max",
            "Configured maximum concurrent v2 conversion workers.",
            registry=registry,
        )
        self.worker_saturation_ratio = Gauge(
            "sir_convert_a_lot_v2_worker_saturation_ratio",
            "Active workers divided by configured maximum workers for v2 runtime.",
            registry=registry,
        )
        self.gpu_concurrency_cap = Gauge(
            "sir_convert_a_lot_v2_gpu_concurrency_cap",
            "Configured concurrency cap for GPU-backed conversion work.",
            registry=registry,
        )
        self.chunk_workers_active = Gauge(
            "sir_convert_a_lot_v2_chunk_workers_active",
            "Current active PDF chunk conversion workers across running jobs.",
            registry=registry,
        )
        self.chunk_workers_per_job_max = Gauge(
            "sir_convert_a_lot_v2_chunk_workers_per_job_max",
            "Configured maximum PDF chunk workers per job.",
            registry=registry,
        )
        self.chunk_workers_global_cap = Gauge(
            "sir_convert_a_lot_v2_chunk_workers_global_cap",
            "Global cap for concurrent PDF chunk workers across the runtime.",
            registry=registry,
        )
        self.chunk_worker_saturation_ratio = Gauge(
            "sir_convert_a_lot_v2_chunk_worker_saturation_ratio",
            "Active chunk workers divided by configured global chunk worker cap.",
            registry=registry,
        )
        self.job_terminal_total = Counter(
            "sir_convert_a_lot_v2_jobs_terminal_total",
            "Terminal v2 jobs by status and bounded route/runtime dimensions.",
            [
                "status",
                "source_format",
                "output_format",
                "backend",
                "acceleration_policy",
                "acceleration_used",
            ],
            registry=registry,
        )
        self.retry_total = Counter(
            "sir_convert_a_lot_v2_job_retries_total",
            "Retry-like conversion fallback counts inferred from warnings.",
            ["retry_kind", "source_format"],
            registry=registry,
        )
        self.stage_duration_seconds = Histogram(
            "sir_convert_a_lot_v2_stage_duration_seconds",
            "Canonical v2 conversion stage timings in seconds.",
            ["stage", "source_format"],
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
                30.0,
                60.0,
                120.0,
                300.0,
            ),
            registry=registry,
        )
        self.gpu_device_count = Gauge(
            "sir_convert_a_lot_v2_gpu_device_count",
            "Observed GPU device count by runtime kind.",
            ["runtime_kind"],
            registry=registry,
        )
        self.gpu_busy_percent = Gauge(
            "sir_convert_a_lot_v2_gpu_busy_percent",
            "Best-effort observed GPU busy percent by runtime kind.",
            ["runtime_kind"],
            registry=registry,
        )
        self.gpu_memory_used_percent = Gauge(
            "sir_convert_a_lot_v2_gpu_memory_used_percent",
            "Best-effort observed GPU memory used percent by runtime kind.",
            ["runtime_kind"],
            registry=registry,
        )

    def observe_runtime_capacity(
        self,
        *,
        active_jobs: int,
        queued_jobs: int,
        max_workers: int,
        gpu_available: bool,
        gpu_stage_global_cap: int | None = None,
    ) -> None:
        """Record queue/worker capacity gauges for runtime scheduling visibility."""
        capped_max_workers = max(1, int(max_workers))
        capped_active_jobs = max(0, int(active_jobs))
        capped_queued_jobs = max(0, int(queued_jobs))
        self.jobs_active.set(capped_active_jobs)
        self.jobs_queued.set(capped_queued_jobs)
        self.workers_max.set(capped_max_workers)
        saturation = min(1.0, float(capped_active_jobs) / float(capped_max_workers))
        self.worker_saturation_ratio.set(saturation)
        resolved_gpu_cap = (
            max(1, int(gpu_stage_global_cap))
            if gpu_stage_global_cap is not None
            else capped_max_workers
        )
        self.gpu_concurrency_cap.set(resolved_gpu_cap if gpu_available else 0)

    def observe_chunk_capacity(
        self,
        *,
        active_chunk_workers: int,
        max_chunk_workers_per_job: int,
        global_chunk_worker_cap: int,
    ) -> None:
        """Record bounded PDF chunk worker capacity and saturation gauges."""
        capped_active = max(0, int(active_chunk_workers))
        capped_per_job = max(1, int(max_chunk_workers_per_job))
        capped_global = max(1, int(global_chunk_worker_cap))
        self.chunk_workers_active.set(capped_active)
        self.chunk_workers_per_job_max.set(capped_per_job)
        self.chunk_workers_global_cap.set(capped_global)
        saturation = min(1.0, float(capped_active) / float(capped_global))
        self.chunk_worker_saturation_ratio.set(saturation)

    def observe_phase_timings(
        self,
        *,
        source_format: SourceFormatV2,
        phase_timings_ms: Mapping[str, object],
    ) -> None:
        """Observe canonicalized per-stage durations for one conversion attempt."""
        normalized_timings = normalize_phase_timings_map(phase_timings_ms)
        source_label = source_format.value
        for stage_key, duration_ms in normalized_timings.items():
            self.stage_duration_seconds.labels(stage_key, source_label).observe(
                max(0.0, float(duration_ms) / 1000.0)
            )

    def observe_terminal_job(
        self,
        *,
        status: JobStatus,
        source_format: SourceFormatV2,
        output_format: OutputFormatV2,
        backend_used: str | None,
        acceleration_policy: AccelerationPolicy | None,
        acceleration_used: str | None,
    ) -> None:
        """Increment bounded terminal counter for one completed/canceled job."""
        self.job_terminal_total.labels(
            status.value,
            source_format.value,
            output_format.value,
            _normalize_backend_label(backend_used),
            _normalize_acceleration_policy_label(acceleration_policy),
            _normalize_acceleration_used_label(acceleration_used),
        ).inc()

    def observe_gpu_snapshot(
        self,
        *,
        runtime_kind: str | None,
        gpu_device_count: int | None,
        gpu_busy_percent: int | None,
        gpu_memory_used_percent: int | None,
    ) -> None:
        """Observe best-effort GPU snapshot gauges from terminal conversion metadata."""
        runtime_label = _normalize_gpu_runtime_kind(runtime_kind)
        if gpu_device_count is not None:
            self.gpu_device_count.labels(runtime_label).set(max(0, int(gpu_device_count)))
        if gpu_busy_percent is not None:
            self.gpu_busy_percent.labels(runtime_label).set(max(0, min(100, gpu_busy_percent)))
        if gpu_memory_used_percent is not None:
            self.gpu_memory_used_percent.labels(runtime_label).set(
                max(0, min(100, gpu_memory_used_percent))
            )

    def observe_retry_warnings(
        self,
        *,
        source_format: SourceFormatV2,
        warnings: Sequence[str],
    ) -> None:
        """Increment retry counters from warning categories without high-card labels."""
        for warning in warnings:
            retry_kind = _retry_kind_from_warning(warning)
            if retry_kind is None or retry_kind not in _KNOWN_RETRY_KINDS:
                continue
            self.retry_total.labels(retry_kind, source_format.value).inc()


class NoopRuntimeTelemetrySinkV2:
    """No-op telemetry sink used when runtime is created outside HTTP app context."""

    def observe_runtime_capacity(
        self,
        *,
        active_jobs: int,
        queued_jobs: int,
        max_workers: int,
        gpu_available: bool,
        gpu_stage_global_cap: int | None = None,
    ) -> None:
        del active_jobs, queued_jobs, max_workers, gpu_available, gpu_stage_global_cap

    def observe_chunk_capacity(
        self,
        *,
        active_chunk_workers: int,
        max_chunk_workers_per_job: int,
        global_chunk_worker_cap: int,
    ) -> None:
        del active_chunk_workers, max_chunk_workers_per_job, global_chunk_worker_cap

    def observe_phase_timings(
        self,
        *,
        source_format: SourceFormatV2,
        phase_timings_ms: Mapping[str, object],
    ) -> None:
        del source_format, phase_timings_ms

    def observe_terminal_job(
        self,
        *,
        status: JobStatus,
        source_format: SourceFormatV2,
        output_format: OutputFormatV2,
        backend_used: str | None,
        acceleration_policy: AccelerationPolicy | None,
        acceleration_used: str | None,
    ) -> None:
        del (
            status,
            source_format,
            output_format,
            backend_used,
            acceleration_policy,
            acceleration_used,
        )

    def observe_gpu_snapshot(
        self,
        *,
        runtime_kind: str | None,
        gpu_device_count: int | None,
        gpu_busy_percent: int | None,
        gpu_memory_used_percent: int | None,
    ) -> None:
        del runtime_kind, gpu_device_count, gpu_busy_percent, gpu_memory_used_percent

    def observe_retry_warnings(
        self,
        *,
        source_format: SourceFormatV2,
        warnings: Sequence[str],
    ) -> None:
        del source_format, warnings
