"""Contracts for recurring Hemma scratch maintenance.

Purpose:
    Define the constants and immutable data contracts used by the recurring
    scratch-maintenance policy for high-churn Qwen workloads on Hemma.

Relationships:
    - Used by `hemma_scratch_maintenance_runtime.py` as the runtime
      orchestration contract.
    - Used by `hemma_scratch_maintenance_selection.py` for candidate
      selection policy.
    - Used by `hemma_scratch_timer_runtime.py` for systemd timer
      installation and status reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.hemma_scratch_policy_runtime import (
    ArchivedScratchPath,
)

DEFAULT_TIMER_OUTPUT_ROOT = Path(
    "build/verification/hemma-scratch-maintenance-hemma-scratch-maintenance"
)
DEFAULT_RUNS_ROOT = Path("/srv/scratch/sir-convert-a-lot/build/runs")
DEFAULT_VERIFICATION_ROOT = Path("/srv/scratch/sir-convert-a-lot/build/verification")
DEFAULT_MAINTENANCE_BLOCK_FILE = Path("/srv/scratch/sir-convert-a-lot/.scratch-maintenance.block")
DEFAULT_TARGET_FREE_BYTES = 96 * 1024**3
DEFAULT_CANDIDATE_MIN_AGE_HOURS = 12.0
DEFAULT_KEEP_MOST_RECENT = 2
DEFAULT_TIMER_NAME = "sir-convert-a-lot-qwen-scratch-maintenance.timer"
DEFAULT_SERVICE_NAME = "sir-convert-a-lot-qwen-scratch-maintenance.service"
DEFAULT_TIMER_ON_BOOT_SEC = "15min"
DEFAULT_TIMER_ON_UNIT_ACTIVE_SEC = "1h"
PROTECTED_QWEN_PILOT_RUN_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/qwen-finetune-20260313t102144z"
)
PROTECTED_QWEN_FALLBACK_RCA_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/qwen-scratch-rca-20260316t-1405-a1"
)


@dataclass(frozen=True)
class CandidateParent:
    """One parent root whose immediate child directories may be archived."""

    root: Path
    category: str
    keep_most_recent: int
    excluded_child_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaintenanceCandidate:
    """One cold scratch artifact tree selected for potential archival."""

    category: str
    source_path: str
    archive_path: str
    size_bytes: int
    age_hours: float


@dataclass(frozen=True)
class ScratchMaintenanceReport:
    """Deterministic report for one scratch maintenance pass."""

    checked_at: str
    scratch_root: str
    storage_archive_root: str
    required_free_bytes: int
    target_free_bytes: int
    candidate_min_age_hours: float
    keep_most_recent: int
    block_file_path: str
    block_file_present: bool
    active_container_names: list[str]
    status: str
    blocked_reason: str | None
    scratch_free_bytes_before: int
    scratch_free_bytes_after: int
    selected_candidates: list[MaintenanceCandidate]
    archived_paths: list[ArchivedScratchPath]
    pruned_docker_state: bool
    meets_target_after: bool


@dataclass(frozen=True)
class ScratchTimerInstallReport:
    """Deterministic report for one timer install or refresh action."""

    installed_at: str
    service_name: str
    timer_name: str
    unit_dir: str
    service_path: str
    timer_path: str
    lingering_enabled_before: bool
    lingering_enabled_after: bool
    timer_enabled: bool
    timer_active: bool


@dataclass(frozen=True)
class ScratchTimerStatusReport:
    """Deterministic status snapshot for the recurring scratch timer."""

    checked_at: str
    service_name: str
    timer_name: str
    unit_dir: str
    timer_enabled: bool
    timer_active: bool
    lingering_enabled: bool
    timer_list_output: str


@dataclass(frozen=True)
class ScratchTimerSettings:
    """Normalized settings for the recurring user-level systemd timer."""

    repo_root: Path
    output_root: Path
    unit_dir: Path
    service_name: str
    timer_name: str
    scratch_root: Path
    storage_archive_root: Path
    runs_root: Path
    verification_root: Path
    block_file_path: Path
    required_free_bytes: int
    target_free_bytes: int
    candidate_min_age_hours: float
    keep_most_recent: int
    prune_docker_state: bool
    timer_on_boot_sec: str
    timer_on_unit_active_sec: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
