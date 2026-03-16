"""Selection policy for recurring Hemma scratch maintenance.

Purpose:
    Select cold scratch artifact trees that are safe to archive when Hemma is
    idle, while protecting the latest and explicitly pinned Qwen evidence.

Relationships:
    - Used by `task205_hemma_scratch_maintenance_runtime.py` to decide which
      paths can be archived during one maintenance pass.
    - Reuses Task 204 archive-path and directory-size helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task204_hemma_scratch_policy_runtime import (
    DEFAULT_SCRATCH_ROOT,
    DEFAULT_STORAGE_ARCHIVE_ROOT,
    archive_destination_for_source,
    directory_size_bytes,
)
from scripts.sir_convert_a_lot.devops.task205_hemma_scratch_maintenance_contracts import (
    DEFAULT_KEEP_MOST_RECENT,
    DEFAULT_RUNS_ROOT,
    DEFAULT_VERIFICATION_ROOT,
    PROTECTED_STORY29_RCA_ROOT,
    PROTECTED_TASK101_RUN_ROOT,
    CandidateParent,
    MaintenanceCandidate,
)


def default_candidate_parents(
    *,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    verification_root: Path = DEFAULT_VERIFICATION_ROOT,
    keep_most_recent: int = DEFAULT_KEEP_MOST_RECENT,
) -> list[CandidateParent]:
    """Return the default parent roots governed by the maintenance policy."""
    return [
        CandidateParent(
            root=runs_root,
            category="runs-top-level",
            keep_most_recent=keep_most_recent,
            excluded_child_names=(
                "qwen3-tts-swedish-finetune",
                "qwen3-tts-swedish-preprocessing",
            ),
        ),
        CandidateParent(
            root=runs_root / "qwen3-tts-swedish-finetune",
            category="runs-finetune",
            keep_most_recent=keep_most_recent,
        ),
        CandidateParent(
            root=runs_root / "qwen3-tts-swedish-preprocessing",
            category="runs-preprocessing",
            keep_most_recent=keep_most_recent,
        ),
        CandidateParent(
            root=verification_root,
            category="verification-top-level",
            keep_most_recent=keep_most_recent,
            excluded_child_names=("qwen3-tts-swedish-hemma-training",),
        ),
        CandidateParent(
            root=verification_root / "qwen3-tts-swedish-hemma-training",
            category="verification-training",
            keep_most_recent=max(keep_most_recent, 4),
        ),
    ]


def default_protected_paths() -> tuple[Path, ...]:
    """Return the roots that must stay on scratch for the active RCA lane."""
    return (
        PROTECTED_TASK101_RUN_ROOT,
        PROTECTED_STORY29_RCA_ROOT,
    )


def _child_directory_age_hours(path: Path, *, now: datetime) -> float:
    """Return one directory age in hours based on its mtime."""
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    age_seconds = max(0.0, (now - modified_at).total_seconds())
    return age_seconds / 3600.0


def _iter_candidate_children(parent: CandidateParent) -> list[Path]:
    """Return archiveable immediate child directories under one parent."""
    if not parent.root.exists():
        return []
    children: list[Path] = []
    for child in sorted(parent.root.iterdir()):
        if child.name in parent.excluded_child_names:
            continue
        if child.is_symlink() or not child.is_dir():
            continue
        children.append(child)
    return children


def _keep_names(children: list[Path], *, keep_count: int) -> set[str]:
    """Return the newest child names that the maintenance policy must retain."""
    newest_first = sorted(children, key=lambda path: path.stat().st_mtime, reverse=True)
    return {path.name for path in newest_first[:keep_count]}


def _is_protected_path(path: Path, *, protected_paths: tuple[Path, ...]) -> bool:
    """Return whether one path is explicitly excluded from archival."""
    return path in protected_paths


def _looks_active_against_containers(path: Path, *, active_container_names: list[str]) -> bool:
    """Return whether one path name appears tied to an active Qwen container."""
    return any(
        path.name in container_name or container_name in path.name
        for container_name in active_container_names
    )


def _select_parent_candidates(
    *,
    parent: CandidateParent,
    scratch_root: Path,
    storage_archive_root: Path,
    protected_paths: tuple[Path, ...],
    active_container_names: list[str],
    candidate_min_age_hours: float,
    now: datetime,
) -> list[MaintenanceCandidate]:
    """Return selected maintenance candidates for one governed parent root."""
    children = _iter_candidate_children(parent)
    keep_names = _keep_names(children, keep_count=parent.keep_most_recent)
    candidates: list[MaintenanceCandidate] = []
    for child in children:
        if child.name in keep_names:
            continue
        if _is_protected_path(child, protected_paths=protected_paths):
            continue
        if _looks_active_against_containers(child, active_container_names=active_container_names):
            continue
        age_hours = _child_directory_age_hours(child, now=now)
        if age_hours < candidate_min_age_hours:
            continue
        archive_path = archive_destination_for_source(
            child,
            scratch_root=scratch_root,
            storage_archive_root=storage_archive_root,
        )
        candidates.append(
            MaintenanceCandidate(
                category=parent.category,
                source_path=child.as_posix(),
                archive_path=archive_path.as_posix(),
                size_bytes=directory_size_bytes(child),
                age_hours=age_hours,
            )
        )
    return candidates


def select_maintenance_candidates(
    *,
    scratch_root: Path = DEFAULT_SCRATCH_ROOT,
    storage_archive_root: Path = DEFAULT_STORAGE_ARCHIVE_ROOT,
    candidate_parents: list[CandidateParent],
    protected_paths: tuple[Path, ...],
    active_container_names: list[str],
    candidate_min_age_hours: float,
) -> list[MaintenanceCandidate]:
    """Select cold artifact roots eligible for archival during maintenance."""
    now = datetime.now(UTC)
    selected: list[MaintenanceCandidate] = []
    for parent in candidate_parents:
        selected.extend(
            _select_parent_candidates(
                parent=parent,
                scratch_root=scratch_root,
                storage_archive_root=storage_archive_root,
                protected_paths=protected_paths,
                active_container_names=active_container_names,
                candidate_min_age_hours=candidate_min_age_hours,
                now=now,
            )
        )
    return sorted(selected, key=lambda item: item.size_bytes, reverse=True)
