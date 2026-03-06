"""Typed payloads for Story 20 throughput benchmarking.

Purpose:
    Centralize the benchmark payload schema shared by the Task 74 harness and
    markdown report renderer.

Relationships:
    - Imported by `benchmark_story20_throughput_report`.
    - Imported by `benchmarking.story20_throughput_report`.
"""

from __future__ import annotations

from typing import TypedDict


class CorpusFileRecord(TypedDict):
    """One generated corpus file summary."""

    filename: str
    page_count: int
    size_bytes: int
    sha256: str


class JobRecord(TypedDict):
    """One profile job result entry."""

    source_file: str
    page_count: int
    job_id: str | None
    status: str
    latency_seconds: float
    pages_per_minute: float | None
    backend_used: str | None
    acceleration_used: str | None
    gpu_busy_percent: int | None
    gpu_memory_used_percent: int | None
    warnings: list[str]


class LatencySummary(TypedDict):
    """Latency summary shape."""

    min: float
    mean: float
    p50: float
    p90: float
    max: float


class ProfileSummary(TypedDict):
    """Top-level profile summary."""

    total_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    success_rate: float
    error_rate: float
    latency_seconds: LatencySummary
    pages_per_minute_p50: float


class ResourceEvidence(TypedDict):
    """Resource evidence sampled while jobs are running."""

    peak_jobs_queued: float
    peak_jobs_active: float
    peak_worker_saturation_ratio: float
    peak_chunk_worker_saturation_ratio: float
    peak_gpu_busy_percent: float
    peak_gpu_memory_used_percent: float
    contains_job_id_label: bool


class ProfileConfig(TypedDict):
    """One benchmark profile runtime config summary."""

    parallel_enabled: bool
    max_chunk_workers: int
    chunk_size_pages: int
    gpu_stage_max_concurrency: int
    acceleration_policy: str


class ProfilePayload(TypedDict):
    """One benchmark profile payload."""

    profile_name: str
    config: ProfileConfig
    summary: ProfileSummary
    resource_evidence: ResourceEvidence
    jobs: list[JobRecord]


class CorpusSummary(TypedDict):
    """Generated corpus summary."""

    corpus_root: str
    count: int
    page_counts: list[int]
    files: list[CorpusFileRecord]


class JobDefaults(TypedDict):
    """Shared job defaults recorded in the benchmark payload."""

    acceleration_policy: str
    ocr_mode: str
    ocr_engine: str
    ocr_languages: list[str]


class RuntimeSurface(TypedDict):
    """Benchmark runtime surface declaration."""

    mode: str
    host: str | None
    service_url: str | None
    parity_source: str


class RuntimeParitySummary(TypedDict):
    """Task 76 parity summary embedded into the Task 74 evidence bundle."""

    status: str | None
    lane: str | None
    expected_revision: str | None
    remote_revision: str | None
    service_revision: str | None
    expected_revision_matches_remote: bool | None
    service_revision_matches_remote: bool | None
    live_smoke_passed: bool | None
    metrics_scan_passed: bool | None
    parity_proven: bool
    notes: list[str]


class Task76ReportChecks(TypedDict):
    """Typed subset of the Task 76 verification checks used by Task 74."""

    expected_revision_matches_remote: bool | None
    service_revision_matches_remote: bool | None
    live_smoke_passed: bool | None
    metrics_scan_passed: bool | None


class Task76ReportPayload(TypedDict):
    """Typed subset of the Task 76 verification payload consumed by Task 74."""

    status: str | None
    lane: str | None
    expected_revision: str | None
    remote_revision: str | None
    service_revision: str | None
    checks: Task76ReportChecks


class ComparisonSummary(TypedDict):
    """Cross-profile comparison summary."""

    baseline_profile: str
    tuned_profile: str
    p50_improvement_percent: float
    meets_target: bool
    recommended_profile: str
    recommended_defaults: ProfileConfig
    rollback_conditions: list[str]


class BenchmarkPayload(TypedDict):
    """Canonical Task 74 benchmark payload shape."""

    benchmark_id: str
    generated_at: str
    mode: str
    corpus: CorpusSummary
    job_defaults: JobDefaults
    runtime_surface: RuntimeSurface
    runtime_parity: RuntimeParitySummary
    profiles: list[ProfilePayload]
    comparison: ComparisonSummary
