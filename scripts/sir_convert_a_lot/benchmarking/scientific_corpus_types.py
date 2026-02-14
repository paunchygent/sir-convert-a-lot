"""Typed contracts for the Task 12 scientific-corpus harness.

Purpose:
    Centralize TypedDict, protocol, and profile types for deterministic
    scientific-corpus benchmark execution and reporting.

Relationships:
    - Used by `scientific_corpus_execution.py` for lane/profile execution.
    - Used by `scientific_corpus_quality.py` for rubric/decision logic.
    - Used by `scripts.sir_convert_a_lot.benchmark_scientific_corpus`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, TypedDict

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client import SubmittedJob

RUBRIC_WEIGHTS: dict[str, float] = {
    "layout_fidelity": 0.45,
    "information_retention": 0.35,
    "legibility": 0.20,
}


class CorpusFileInfo(TypedDict):
    """Per-document corpus metadata."""

    source_file: str
    source_size_bytes: int
    document_slug: str


class CorpusSummary(TypedDict):
    """Corpus summary included in output payload."""

    path: str
    count: int
    files: list[CorpusFileInfo]


class BenchmarkLatencySummary(TypedDict):
    """Latency distribution summary."""

    min: float
    mean: float
    p50: float
    p90: float
    p99: float
    max: float


class LaneSummary(TypedDict):
    """Summary for one profile or lane."""

    total_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    canceled_jobs: int
    running_jobs: int
    success_rate: float
    throughput_jobs_per_minute: float
    latency_seconds: BenchmarkLatencySummary
    warnings_total: int
    retry_warnings_total: int
    backend_usage: dict[str, int]
    acceleration_usage: dict[str, int]


class LaneJobRecord(TypedDict):
    """Per-job execution record for Task 12 evidence."""

    source_file: str
    source_size_bytes: int
    document_slug: str
    backend_profile: str
    job_id: str | None
    status: str
    error_code: str | None
    latency_seconds: float
    backend_used: str | None
    acceleration_used: str | None
    warnings: list[str]
    retry_warnings_count: int
    output_markdown_path: str | None
    output_metadata_path: str | None


class JobSpecProfile(TypedDict):
    """Echo of deterministic job-spec profile used for a run."""

    backend_strategy: str
    ocr_mode: str
    table_mode: str
    normalize: str
    acceleration_policy: str


class LaneProfileResult(TypedDict):
    """One profile result under a lane."""

    profile_name: str
    job_spec_profile: JobSpecProfile
    summary: LaneSummary
    jobs: list[LaneJobRecord]


class LaneResult(TypedDict):
    """One lane output shape."""

    lane: str
    service_url: str
    profiles: list[LaneProfileResult]
    summary: LaneSummary
    gate_passed: bool


class RubricEntry(TypedDict):
    """Manual quality rubric entry for one document/backend."""

    source_file: str
    document_slug: str
    backend: str
    layout_fidelity: int
    information_retention: int
    legibility: int
    notes: str


class RubricPayload(TypedDict):
    """Rubric file shape."""

    generated_at: str
    auto_generated: bool
    weights: dict[str, float]
    entries: list[RubricEntry]


class RankingEntry(TypedDict):
    """Ranked backend entry from decision logic."""

    backend: str
    median_weighted_score: float
    severe_quality_failures: int
    success_rate: float
    latency_p50: float


class DecisionSummary(TypedDict):
    """Task 12 quality-first decision payload."""

    algorithm: str
    ranking: list[RankingEntry]
    quality_winner: str
    recommended_production_backend: str
    follow_up_required: bool
    follow_up_note: str | None


class GovernanceSummary(TypedDict):
    """Governance compatibility assessment payload."""

    production_profile: JobSpecProfile
    quality_winner: str
    quality_winner_compatible_for_production: bool
    recommended_production_backend: str
    notes: list[str]


class ServiceRevision(TypedDict):
    """Service revision metadata."""

    local_sha: str
    hemma_sha: str


class BenchmarkPayload(TypedDict):
    """Final Task 12 machine-readable artifact."""

    benchmark_id: str
    generated_at: str
    service_revision: ServiceRevision
    corpus: CorpusSummary
    acceptance_lane: LaneResult
    evaluation_lane: LaneResult
    quality_rubric: RubricPayload
    decision: DecisionSummary
    governance_compatibility: GovernanceSummary
    artifacts_root: str


class BenchmarkClient(Protocol):
    """Protocol subset used by the scientific-corpus harness."""

    def __enter__(self) -> "BenchmarkClient":
        """Enter context manager and return self."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit context manager."""
        ...

    def submit_pdf_job(
        self,
        *,
        pdf_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        correlation_id: str | None = None,
    ) -> SubmittedJob:
        """Submit one PDF conversion job."""
        ...

    def wait_for_terminal_status(
        self,
        job_id: str,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float = 0.2,
        correlation_id: str | None = None,
    ) -> JobStatus:
        """Poll until job reaches terminal status."""
        ...

    def fetch_result_payload(
        self,
        job_id: str,
        *,
        correlation_id: str | None = None,
        inline: bool = True,
    ) -> dict[str, object]:
        """Fetch raw job result payload."""
        ...


class BenchmarkClientFactory(Protocol):
    """Factory protocol for constructing benchmark client instances."""

    def __call__(self, *, base_url: str, api_key: str) -> BenchmarkClient:
        """Create a context-managed benchmark client."""
        ...


@dataclass(frozen=True)
class BackendProfile:
    """Deterministic profile for one backend lane run."""

    profile_name: str
    backend_strategy: str
    ocr_mode: str
    table_mode: str
    normalize: str
    acceleration_policy: str

    def to_job_spec_profile(self) -> JobSpecProfile:
        """Return profile in API-job-spec echo format."""
        return {
            "backend_strategy": self.backend_strategy,
            "ocr_mode": self.ocr_mode,
            "table_mode": self.table_mode,
            "normalize": self.normalize,
            "acceleration_policy": self.acceleration_policy,
        }
