"""Typed payloads for PDF throughput lane throughput benchmarking.

Purpose:
    Centralize the benchmark payload schema shared by the PDF throughput benchmark harness and
    markdown report renderer.

Relationships:
    - Imported by `pdf_throughput_benchmark_report`.
    - Imported by `benchmarking.pdf_throughput_report`.
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
    ocr_enabled: bool | None
    ocr_engine_used: str | None
    ocr_languages_used: list[str] | None
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
    total_latency_seconds: float
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
    """Hemma deploy verification parity summary embedded into the PDF throughput benchmark evidence
    bundle.
    """

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


class DeployParityReportChecks(TypedDict):
    """Typed subset of the Hemma deploy verification verification checks used by PDF throughput
    benchmark.
    """

    expected_revision_matches_remote: bool | None
    service_revision_matches_remote: bool | None
    live_smoke_passed: bool | None
    metrics_scan_passed: bool | None


class DeployParityReportPayload(TypedDict):
    """Typed subset of the Hemma deploy verification verification payload consumed by PDF throughput
    benchmark.
    """

    status: str | None
    lane: str | None
    expected_revision: str | None
    remote_revision: str | None
    service_revision: str | None
    checks: DeployParityReportChecks


class ComparisonSummary(TypedDict):
    """Cross-profile comparison summary."""

    baseline_profile: str
    tuned_profile: str
    p50_improvement_percent: float
    meets_target: bool
    recommended_profile: str
    recommended_defaults: ProfileConfig
    rollback_conditions: list[str]


class DirtyCorpusManifestEntry(TypedDict):
    """One metadata-only dirty OCR corpus entry."""

    source_id: str
    source_sha256: str
    page_count: int
    dirty_data_classes: list[str]
    expected_ocr_languages: list[str]
    privacy_state: str
    safe_excerpts_may_be_reported: bool


class DirtyCorpusManifestSummary(TypedDict):
    """Sanitized summary of the dirty OCR corpus manifest."""

    schema_version: str
    corpus_id: str
    entry_count: int
    executed_entry_count: int
    total_pages: int
    dirty_data_class_counts: dict[str, int]
    required_dirty_data_classes_present: list[str]
    missing_required_dirty_data_classes: list[str]
    expected_ocr_languages: list[str]
    privacy_state_counts: dict[str, int]
    safe_excerpt_entry_count: int
    synthetic_fixture_entry_count: int
    contains_real_dirty_inputs: bool
    source_hashes_verified: bool
    real_data_gate_satisfied: bool
    entries: list[DirtyCorpusManifestEntry]


class ProfileSafetySummary(TypedDict):
    """PDF throughput benchmark safe-profile classification for one benchmark profile."""

    profile_name: str
    max_chunk_workers: int
    gpu_stage_max_concurrency: int
    safe_profile: bool
    unsafe_reason: str | None


class DirtyCorpusFailureTaxonomy(TypedDict):
    """Failure and warning buckets required by the dirty-corpus report."""

    failed_job_count: int
    warning_count: int
    input_quality_warning_count: int
    engine_runtime_failure_count: int
    timeout_failure_count: int
    gpu_resource_failure_count: int
    conversion_bug_failure_count: int


class DirtyCorpusOcrMetadataSummary(TypedDict):
    """Observed OCR/backend metadata summary for dirty-corpus reports."""

    ocr_enabled_job_count: int
    ocr_engine_used_values: list[str]
    ocr_languages_used_values: list[str]
    backend_used_values: list[str]
    acceleration_used_values: list[str]
    warning_count: int


class DirtyPdfBenchmarkProofSummary(TypedDict):
    """Final dirty-corpus proof target fields required by dirty PDF OCR final proof."""

    runtime_mode: str
    production_service_runtime: bool
    target_executed_pages: int
    target_wall_clock_seconds: int
    tuned_profile: str
    tuned_total_pages: int
    tuned_wall_clock_seconds: float
    tuned_success_rate: float
    source_hashes_verified: bool
    real_data_gate_satisfied: bool
    deploy_parity_proven: bool
    all_profiles_safe: bool
    meets_150_page_target: bool


class DirtyCorpusReportExtension(TypedDict):
    """dirty PDF OCR corpus dirty-corpus extension embedded in PDF throughput benchmark reports."""

    schema_version: str
    manifest: DirtyCorpusManifestSummary
    profile_safety: list[ProfileSafetySummary]
    all_profiles_safe: bool
    deploy_parity_required: bool
    deploy_parity_proven: bool
    failure_taxonomy: DirtyCorpusFailureTaxonomy
    ocr_metadata_summary: DirtyCorpusOcrMetadataSummary
    dirty_pdf_ocr_proof: DirtyPdfBenchmarkProofSummary


class BenchmarkPayload(TypedDict):
    """Canonical PDF throughput benchmark payload shape."""

    benchmark_id: str
    generated_at: str
    mode: str
    corpus: CorpusSummary
    job_defaults: JobDefaults
    runtime_surface: RuntimeSurface
    runtime_parity: RuntimeParitySummary
    profiles: list[ProfilePayload]
    comparison: ComparisonSummary
    dirty_corpus: DirtyCorpusReportExtension | None
