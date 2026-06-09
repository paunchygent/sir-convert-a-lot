"""Recurring Hemma scratch-governance helpers for high-churn Qwen workloads.

Purpose:
    Provide one committed audit and remediation runtime for the recurring
    `/srv/scratch` pressure caused by detached Qwen proof lanes, large
    checkpoint trees, and Docker churn on Hemma.

Relationships:
    - Used by `run_hemma_scratch_policy.py`.
    - Reuses generic storage-tier migration helpers from
      `ml.qwen.common.storage`.
    - Supplies the remote scratch-headroom evidence consumed by the Qwen fallback proof lane
      proof wrappers before they launch detached Hemma work.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.storage import (
    cleanup_non_active_docker_state,
    docker_system_df,
    migrate_tree_to_tier,
    replace_with_canonical_symlink,
    run_checked,
)

DEFAULT_SCRATCH_ROOT = Path("/srv/scratch")
DEFAULT_STORAGE_ARCHIVE_ROOT = Path("/srv/storage/sir-convert-a-lot/archive/scratch-mirror")
DEFAULT_REPO_SCRATCH_ROOT = DEFAULT_SCRATCH_ROOT / "sir-convert-a-lot"
DEFAULT_RUNS_ROOT = DEFAULT_REPO_SCRATCH_ROOT / "build/runs"
DEFAULT_VERIFICATION_ROOT = DEFAULT_REPO_SCRATCH_ROOT / "build/verification"
DEFAULT_AUDIT_MIN_BYTES = 5 * 1024**3
DEFAULT_REQUIRED_FREE_BYTES = 64 * 1024**3
DEFAULT_TOP_COUNT = 12


@dataclass(frozen=True)
class ScratchConsumer:
    """One size-ranked scratch consumer in the audit report."""

    path: str
    size_bytes: int


@dataclass(frozen=True)
class ScratchAuditReport:
    """Deterministic audit report for Hemma scratch consumption."""

    checked_at: str
    scratch_root: str
    storage_archive_root: str
    required_free_bytes: int
    scratch_total_bytes: int
    scratch_used_bytes: int
    scratch_free_bytes: int
    meets_required_headroom: bool
    docker_system_df: str
    top_level_consumers: list[ScratchConsumer]
    run_consumers: list[ScratchConsumer]
    verification_consumers: list[ScratchConsumer]


@dataclass(frozen=True)
class ArchivedScratchPath:
    """One archived scratch path with its destination and preserved symlink."""

    source_path: str
    archive_path: str
    size_bytes: int


@dataclass(frozen=True)
class ScratchRemediationReport:
    """Deterministic remediation report for one scratch cleanup pass."""

    checked_at: str
    scratch_root: str
    storage_archive_root: str
    required_free_bytes: int
    scratch_free_bytes_before: int
    scratch_free_bytes_after: int
    meets_required_headroom_after: bool
    archived_paths: list[ArchivedScratchPath]
    pruned_docker_state: bool
    docker_system_df_before: str
    docker_system_df_after: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _du_output(path: Path) -> str:
    """Return `du -sB1` output, retrying with sudo for protected roots."""
    commands = [
        (["du", "-s", "-B1", path.as_posix()], f"du {path.as_posix()}"),
        (["sudo", "-n", "du", "-s", "-B1", path.as_posix()], f"sudo du {path.as_posix()}"),
    ]
    last_error: SystemExit | None = None
    for command, label in commands:
        try:
            return run_checked(command, label=label)
        except SystemExit as exc:
            last_error = exc
    if last_error is None:
        raise SystemExit(f"No du command could be executed for `{path.as_posix()}`.")
    raise last_error


def directory_size_bytes(path: Path) -> int:
    """Return the on-disk size for one directory tree using `du -sB1`."""
    if not path.exists():
        return 0
    output = _du_output(path)
    line = output.strip().splitlines()[0]
    size_field = line.split()[0]
    return int(size_field)


def scratch_free_bytes(scratch_root: Path) -> int:
    """Return the currently available bytes on the scratch filesystem."""
    return int(shutil.disk_usage(scratch_root).free)


def _docker_system_df_or_error() -> str:
    """Return the Docker storage summary or one readable error message."""
    try:
        return docker_system_df()
    except SystemExit as exc:
        return str(exc)


def _iter_size_ranked_directories(
    root: Path,
    *,
    min_bytes: int,
    limit: int,
) -> list[ScratchConsumer]:
    """Return the largest non-symlink child directories under one root."""
    if not root.exists():
        return []
    consumers: list[ScratchConsumer] = []
    for child in sorted(root.iterdir()):
        if child.is_symlink():
            continue
        if not child.is_dir():
            continue
        size_bytes = directory_size_bytes(child)
        if size_bytes < min_bytes:
            continue
        consumers.append(
            ScratchConsumer(
                path=child.as_posix(),
                size_bytes=size_bytes,
            )
        )
    return sorted(consumers, key=lambda item: item.size_bytes, reverse=True)[:limit]


def build_scratch_audit_report(
    *,
    scratch_root: Path = DEFAULT_SCRATCH_ROOT,
    storage_archive_root: Path = DEFAULT_STORAGE_ARCHIVE_ROOT,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    verification_root: Path = DEFAULT_VERIFICATION_ROOT,
    min_bytes: int = DEFAULT_AUDIT_MIN_BYTES,
    required_free_bytes: int = DEFAULT_REQUIRED_FREE_BYTES,
    top_count: int = DEFAULT_TOP_COUNT,
) -> ScratchAuditReport:
    """Build one deterministic audit report for Hemma scratch pressure."""
    usage = shutil.disk_usage(scratch_root)
    free_bytes = int(usage.free)
    return ScratchAuditReport(
        checked_at=utc_now_iso(),
        scratch_root=scratch_root.as_posix(),
        storage_archive_root=storage_archive_root.as_posix(),
        required_free_bytes=required_free_bytes,
        scratch_total_bytes=int(usage.total),
        scratch_used_bytes=int(usage.used),
        scratch_free_bytes=free_bytes,
        meets_required_headroom=free_bytes >= required_free_bytes,
        docker_system_df=_docker_system_df_or_error(),
        top_level_consumers=_iter_size_ranked_directories(
            scratch_root,
            min_bytes=min_bytes,
            limit=top_count,
        ),
        run_consumers=_iter_size_ranked_directories(
            runs_root,
            min_bytes=min_bytes,
            limit=top_count,
        ),
        verification_consumers=_iter_size_ranked_directories(
            verification_root,
            min_bytes=min_bytes,
            limit=top_count,
        ),
    )


def archive_destination_for_source(
    source_path: Path,
    *,
    scratch_root: Path,
    storage_archive_root: Path,
) -> Path:
    """Return the mirrored storage-archive destination for one scratch path."""
    relative_path = source_path.relative_to(scratch_root)
    return storage_archive_root / relative_path


def _validate_source_path(source_path: Path, *, scratch_root: Path) -> None:
    """Require one explicit remediation source path to be safe and scratch-backed."""
    if not source_path.is_absolute():
        raise SystemExit(f"Scratch remediation expects an absolute path, got `{source_path}`.")
    try:
        source_path.relative_to(scratch_root)
    except ValueError as exc:
        raise SystemExit(
            f"Scratch remediation only accepts paths under `{scratch_root}`; got `{source_path}`."
        ) from exc
    if not source_path.exists():
        raise SystemExit(f"Scratch remediation source path does not exist: `{source_path}`.")
    if source_path.is_symlink():
        raise SystemExit(
            f"Scratch remediation source path is already archived via symlink: `{source_path}`."
        )
    if not source_path.is_dir():
        raise SystemExit(f"Scratch remediation source path must be a directory: `{source_path}`.")


def archive_scratch_paths(
    source_paths: list[Path],
    *,
    scratch_root: Path = DEFAULT_SCRATCH_ROOT,
    storage_archive_root: Path = DEFAULT_STORAGE_ARCHIVE_ROOT,
) -> list[ArchivedScratchPath]:
    """Archive explicit scratch directories onto storage and symlink them back."""
    archived_paths: list[ArchivedScratchPath] = []
    for source_path in source_paths:
        _validate_source_path(source_path, scratch_root=scratch_root)
        archive_path = archive_destination_for_source(
            source_path,
            scratch_root=scratch_root,
            storage_archive_root=storage_archive_root,
        )
        size_bytes = directory_size_bytes(source_path)
        migrate_tree_to_tier(source_path, archive_path)
        replace_with_canonical_symlink(source_path, archive_path)
        archived_paths.append(
            ArchivedScratchPath(
                source_path=source_path.as_posix(),
                archive_path=archive_path.as_posix(),
                size_bytes=size_bytes,
            )
        )
    return archived_paths


def run_scratch_remediation(
    *,
    source_paths: list[Path],
    scratch_root: Path = DEFAULT_SCRATCH_ROOT,
    storage_archive_root: Path = DEFAULT_STORAGE_ARCHIVE_ROOT,
    required_free_bytes: int = DEFAULT_REQUIRED_FREE_BYTES,
    prune_docker_state: bool,
) -> ScratchRemediationReport:
    """Archive explicit paths and optionally prune Docker to recover scratch headroom."""
    free_bytes_before = scratch_free_bytes(scratch_root)
    docker_before = _docker_system_df_or_error()
    archived_paths = archive_scratch_paths(
        source_paths,
        scratch_root=scratch_root,
        storage_archive_root=storage_archive_root,
    )
    if prune_docker_state:
        cleanup_non_active_docker_state()
    free_bytes_after = scratch_free_bytes(scratch_root)
    docker_after = _docker_system_df_or_error()
    return ScratchRemediationReport(
        checked_at=utc_now_iso(),
        scratch_root=scratch_root.as_posix(),
        storage_archive_root=storage_archive_root.as_posix(),
        required_free_bytes=required_free_bytes,
        scratch_free_bytes_before=free_bytes_before,
        scratch_free_bytes_after=free_bytes_after,
        meets_required_headroom_after=free_bytes_after >= required_free_bytes,
        archived_paths=archived_paths,
        pruned_docker_state=prune_docker_state,
        docker_system_df_before=docker_before,
        docker_system_df_after=docker_after,
    )
