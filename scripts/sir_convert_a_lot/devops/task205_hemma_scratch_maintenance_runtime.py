"""Idle-safe recurring Hemma scratch maintenance for Qwen artifact churn.

Purpose:
    Orchestrate one recurring maintenance pass that archives cold scratch
    artifacts onto storage only when no active Qwen workload is running and no
    manual maintenance block is present.

Relationships:
    - Used by `run_task204_hemma_scratch_policy.py` for the `maintain`
      subcommand.
    - Delegates candidate policy to
      `task205_hemma_scratch_maintenance_selection.py`.
    - Delegates timer behavior to `task205_hemma_scratch_timer_runtime.py`.
    - Reuses Task 204 audit/archive primitives from
      `task204_hemma_scratch_policy_runtime.py`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.task204_hemma_scratch_policy_runtime import (
    DEFAULT_REQUIRED_FREE_BYTES,
    DEFAULT_SCRATCH_ROOT,
    DEFAULT_STORAGE_ARCHIVE_ROOT,
    DEFAULT_VERIFICATION_ROOT,
    ArchivedScratchPath,
    archive_scratch_paths,
    scratch_free_bytes,
)
from scripts.sir_convert_a_lot.devops.task205_hemma_scratch_maintenance_contracts import (
    DEFAULT_CANDIDATE_MIN_AGE_HOURS,
    DEFAULT_KEEP_MOST_RECENT,
    DEFAULT_MAINTENANCE_BLOCK_FILE,
    DEFAULT_RUNS_ROOT,
    DEFAULT_TARGET_FREE_BYTES,
    MaintenanceCandidate,
    ScratchMaintenanceReport,
    utc_now_iso,
)
from scripts.sir_convert_a_lot.devops.task205_hemma_scratch_maintenance_selection import (
    default_candidate_parents,
    default_protected_paths,
    select_maintenance_candidates,
)
from scripts.sir_convert_a_lot.devops.task205_hemma_scratch_timer_runtime import (
    active_qwen_container_names,
)
from scripts.sir_convert_a_lot.ml.qwen.common.storage import cleanup_non_active_docker_state


def _select_source_paths_to_archive(
    *,
    candidates: list[MaintenanceCandidate],
    free_bytes_before: int,
    target_free_bytes: int,
) -> list[Path]:
    """Return the minimal selected source paths needed to reach target headroom."""
    selected_source_paths: list[Path] = []
    projected_free_bytes = free_bytes_before
    for candidate in candidates:
        if projected_free_bytes >= target_free_bytes:
            break
        selected_source_paths.append(Path(candidate.source_path))
        projected_free_bytes += candidate.size_bytes
    return selected_source_paths


def _archive_selected_candidates(
    *,
    candidates: list[MaintenanceCandidate],
    free_bytes_before: int,
    scratch_root: Path,
    storage_archive_root: Path,
    target_free_bytes: int,
) -> list[ArchivedScratchPath]:
    """Archive the subset of candidates required to recover target headroom."""
    selected_source_paths = _select_source_paths_to_archive(
        candidates=candidates,
        free_bytes_before=free_bytes_before,
        target_free_bytes=target_free_bytes,
    )
    if not selected_source_paths:
        return []
    return archive_scratch_paths(
        selected_source_paths,
        scratch_root=scratch_root,
        storage_archive_root=storage_archive_root,
    )


def _maintenance_status(
    *,
    free_bytes_before: int,
    target_free_bytes: int,
    active_container_names: list[str],
    block_file_present: bool,
    archived_paths: list[ArchivedScratchPath],
    pruned_docker_state: bool,
) -> tuple[str, str | None]:
    """Return the deterministic maintenance status and blocked reason."""
    if free_bytes_before >= target_free_bytes:
        return "already-healthy", None
    if active_container_names:
        return "blocked", "active-qwen-containers"
    if block_file_present:
        return "blocked", "manual-block-file"
    if archived_paths and pruned_docker_state:
        return "archived-and-pruned", None
    if archived_paths:
        return "archived", None
    if pruned_docker_state:
        return "pruned-docker-only", None
    return "no-candidates", None


def run_scratch_maintenance(
    *,
    scratch_root: Path = DEFAULT_SCRATCH_ROOT,
    storage_archive_root: Path = DEFAULT_STORAGE_ARCHIVE_ROOT,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    verification_root: Path = DEFAULT_VERIFICATION_ROOT,
    block_file_path: Path = DEFAULT_MAINTENANCE_BLOCK_FILE,
    required_free_bytes: int = DEFAULT_REQUIRED_FREE_BYTES,
    target_free_bytes: int = DEFAULT_TARGET_FREE_BYTES,
    candidate_min_age_hours: float = DEFAULT_CANDIDATE_MIN_AGE_HOURS,
    keep_most_recent: int = DEFAULT_KEEP_MOST_RECENT,
    prune_docker_state: bool,
) -> ScratchMaintenanceReport:
    """Archive cold artifacts only when Hemma is idle enough for safe cleanup."""
    free_bytes_before = scratch_free_bytes(scratch_root)
    active_container_names = active_qwen_container_names()
    block_file_present = block_file_path.exists()
    selected_candidates: list[MaintenanceCandidate] = []
    archived_paths: list[ArchivedScratchPath] = []
    pruned = False

    if (
        free_bytes_before < target_free_bytes
        and not active_container_names
        and not block_file_present
    ):
        selected_candidates = select_maintenance_candidates(
            scratch_root=scratch_root,
            storage_archive_root=storage_archive_root,
            candidate_parents=default_candidate_parents(
                runs_root=runs_root,
                verification_root=verification_root,
                keep_most_recent=keep_most_recent,
            ),
            protected_paths=default_protected_paths(),
            active_container_names=active_container_names,
            candidate_min_age_hours=candidate_min_age_hours,
        )
        archived_paths = _archive_selected_candidates(
            candidates=selected_candidates,
            free_bytes_before=free_bytes_before,
            scratch_root=scratch_root,
            storage_archive_root=storage_archive_root,
            target_free_bytes=target_free_bytes,
        )
        if prune_docker_state and scratch_free_bytes(scratch_root) < target_free_bytes:
            cleanup_non_active_docker_state()
            pruned = True

    free_bytes_after = scratch_free_bytes(scratch_root)
    status, blocked_reason = _maintenance_status(
        free_bytes_before=free_bytes_before,
        target_free_bytes=target_free_bytes,
        active_container_names=active_container_names,
        block_file_present=block_file_present,
        archived_paths=archived_paths,
        pruned_docker_state=pruned,
    )
    return ScratchMaintenanceReport(
        checked_at=utc_now_iso(),
        scratch_root=scratch_root.as_posix(),
        storage_archive_root=storage_archive_root.as_posix(),
        required_free_bytes=required_free_bytes,
        target_free_bytes=target_free_bytes,
        candidate_min_age_hours=candidate_min_age_hours,
        keep_most_recent=keep_most_recent,
        block_file_path=block_file_path.as_posix(),
        block_file_present=block_file_present,
        active_container_names=active_container_names,
        status=status,
        blocked_reason=blocked_reason,
        scratch_free_bytes_before=free_bytes_before,
        scratch_free_bytes_after=free_bytes_after,
        selected_candidates=selected_candidates,
        archived_paths=archived_paths,
        pruned_docker_state=pruned,
        meets_target_after=(
            free_bytes_after >= target_free_bytes and free_bytes_after >= required_free_bytes
        ),
    )
