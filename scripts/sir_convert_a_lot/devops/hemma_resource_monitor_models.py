"""Typed contracts for the detached Hemma resource monitor.

Purpose:
    Centralize the Hemma resource monitor monitor launch, sample, summary, and status models
    so the CLI and runtime stay under the repo's module-size boundary.

Relationships:
    - Imported by `run_hemma_resource_monitor.py` for operator I/O.
    - Imported by `hemma_resource_monitor_runtime.py` for worker state and
      artifact serialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RuntimeKind = Literal["rocm", "cuda", "none"]


@dataclass(frozen=True)
class HemmaResourceMonitorLaunch:
    """Deterministic launch metadata for one detached resource monitor."""

    generated_at: str
    launch_id: str
    repo_root: str
    pid: int
    runtime_kind: RuntimeKind
    interval_seconds: float
    duration_seconds: float | None
    command: list[str]


@dataclass(frozen=True)
class HemmaResourceMonitorRunState:
    """Persisted worker state for one detached resource monitor."""

    launch_id: str
    started_at: str
    finished_at: str | None
    exit_reason: str | None
    sample_count: int
    latest_sample_at: str | None
    latest_gpu_busy_percent: int | None
    latest_gpu_memory_used_percent: int | None
    latest_host_cpu_busy_percent: int | None
    latest_host_memory_used_percent: int | None
    error: str | None


@dataclass(frozen=True)
class HemmaResourceSample:
    """One timestamped host resource sample."""

    captured_at: str
    runtime_kind: RuntimeKind
    gpu_busy_percent: int | None
    gpu_memory_used_percent: int | None
    host_cpu_busy_percent: int | None
    host_memory_used_percent: int | None


@dataclass(frozen=True)
class HemmaResourceMonitorSummary:
    """Aggregate summary derived from one monitor's recorded samples."""

    launch_id: str
    sample_count: int
    first_sample_at: str | None
    last_sample_at: str | None
    gpu_busy_percent_min: int | None
    gpu_busy_percent_median: float | None
    gpu_busy_percent_max: int | None
    gpu_memory_used_percent_min: int | None
    gpu_memory_used_percent_median: float | None
    gpu_memory_used_percent_max: int | None
    host_cpu_busy_percent_min: int | None
    host_cpu_busy_percent_median: float | None
    host_cpu_busy_percent_max: int | None
    host_memory_used_percent_min: int | None
    host_memory_used_percent_median: float | None
    host_memory_used_percent_max: int | None


@dataclass(frozen=True)
class HemmaResourceMonitorStatus:
    """Operator-facing status view for one detached resource monitor."""

    checked_at: str
    launch_id: str
    pid: int
    running: bool
    runtime_kind: RuntimeKind
    interval_seconds: float
    duration_seconds: float | None
    stop_requested: bool
    worker_state_found: bool
    worker_state: dict[str, object] | None
    summary: dict[str, object]
