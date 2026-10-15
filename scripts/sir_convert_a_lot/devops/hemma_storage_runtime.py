"""Runtime helpers for Hemma storage remediation.

Purpose:
    Place nonvisual generated build and corpus data in Hot owner storage,
    preserving logical paths. Refuse the retired Sir Docker cleanup surface.

Relationships:
    - Used by `run_hemma_storage_remediation.py`.
    - Aligns live Hemma storage with Hemma storage remediation, Hemma Docker storage remediation,
    and the Qwen
      preprocessing runbooks.
    - Preserves repo-relative `build/...` semantics by replacing the Hemma repo
      `build/` directory with a symlink to the canonical Hot-backed build
      root.
"""

from __future__ import annotations

import filecmp
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.devops.hemma_storage_contracts import (
    DEFAULT_HOT_BUILD_ROOT,
    DEFAULT_HOT_QWEN_DATA_ROOT,
    DOCKER_CLEANUP_REFUSAL,
    validate_migration_source,
    validate_migration_tree,
)

DEFAULT_REPO_ROOT = Path("/home/paunchygent/apps/sir-convert-a-lot")
DEFAULT_REPO_BUILD_ROOT = DEFAULT_REPO_ROOT / "build"
DEFAULT_SCRATCH_BUILD_ROOT = DEFAULT_HOT_BUILD_ROOT
DEFAULT_OLD_QWEN_DATA_ROOT = Path("/srv/scratch/sir-convert-a-lot/data/qwen3-tts-swedish-corpus")
DEFAULT_NEW_QWEN_DATA_ROOT = DEFAULT_HOT_QWEN_DATA_ROOT


@dataclass(frozen=True)
class HemmaStorageSettings:
    """Normalized settings for the Hemma storage remediation storage remediation runner."""

    repo_root: Path
    repo_build_root: Path
    scratch_build_root: Path
    old_qwen_data_root: Path
    new_qwen_data_root: Path
    migrate_repo_build: bool
    migrate_qwen_data: bool
    cleanup_docker_state: bool


@dataclass(frozen=True)
class HemmaStorageReport:
    """Deterministic report for one Hemma storage remediation remediation pass."""

    repo_build_root: str
    repo_build_is_symlink: bool
    repo_build_target: str | None
    scratch_build_root: str
    old_qwen_data_root: str
    old_qwen_data_is_symlink: bool
    old_qwen_data_target: str | None
    new_qwen_data_root: str
    migrated_repo_build: bool
    migrated_qwen_data: bool
    cleaned_docker_state: bool
    docker_system_df_before: str
    docker_system_df_after: str
    filesystem_df_before: str
    filesystem_df_after: str


def run_checked(command: list[str], *, label: str) -> str:
    """Run one subprocess command and return stdout or raise with diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def ensure_directory(path: Path) -> None:
    """Create one directory tree when it does not already exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        run_checked(
            ["sudo", "-n", "mkdir", "-p", path.as_posix()], label="sudo mkdir hemma-storage"
        )


def _migrate_tree(source: Path, destination: Path) -> None:
    """Move one tree between storage tiers, merging when the destination exists."""
    if not source.exists() or source.is_symlink():
        return
    validate_migration_tree(source, destination)
    ensure_directory(destination.parent)
    try:
        if destination.exists():
            if not destination.is_dir():
                raise SystemExit(f"Refusing to merge into non-directory destination: {destination}")
            for child in sorted(source.iterdir()):
                target_child = destination / child.name
                if target_child.exists() or target_child.is_symlink():
                    if child.is_symlink() and target_child.is_symlink():
                        if child.readlink() == target_child.readlink():
                            child.unlink()
                            continue
                    if child.is_dir() and target_child.is_dir():
                        _migrate_tree(child, target_child)
                        continue
                    if child.is_file() and target_child.is_file():
                        if filecmp.cmp(child.as_posix(), target_child.as_posix(), shallow=False):
                            child.unlink()
                            continue
                    raise SystemExit(f"Refusing migration collision at `{target_child}`.")
                shutil.move(child.as_posix(), target_child.as_posix())
            source.rmdir()
            return
        shutil.move(source.as_posix(), destination.as_posix())
    except (OSError, shutil.Error):
        _sudo_rsync_tree(source=source, destination=destination)


def _sudo_rsync_tree(*, source: Path, destination: Path) -> None:
    """Move one tree with sudo-backed rsync when user-space moves cannot succeed."""
    validate_migration_tree(source, destination)
    run_checked(
        ["sudo", "-n", "mkdir", "-p", destination.as_posix()],
        label="sudo mkdir hemma-storage",
    )
    run_checked(
        [
            "sudo",
            "-n",
            "rsync",
            "-aHAX",
            f"{source.as_posix()}/",
            f"{destination.as_posix()}/",
        ],
        label="sudo rsync hemma-storage",
    )
    run_checked(
        ["sudo", "-n", "rm", "-rf", source.as_posix()],
        label="sudo rm source hemma-storage",
    )


def _replace_with_symlink(source_path: Path, target_path: Path) -> None:
    """Replace one path with a symlink to the canonical migrated target."""
    if source_path.is_symlink():
        if source_path.resolve() == target_path.resolve():
            return
        source_path.unlink()
    elif source_path.exists():
        raise SystemExit(f"Refusing to replace existing non-symlink path: {source_path}")
    ensure_directory(source_path.parent)
    source_path.symlink_to(target_path)


def migrate_repo_build_to_scratch(settings: HemmaStorageSettings) -> None:
    """Move the repo build tree into Hot owner jobs, preserving its logical path."""
    validate_migration_source(settings.repo_build_root, settings.scratch_build_root)
    ensure_directory(settings.scratch_build_root.parent)
    _migrate_tree(settings.repo_build_root, settings.scratch_build_root)
    _replace_with_symlink(settings.repo_build_root, settings.scratch_build_root)


def migrate_qwen_data_to_storage(settings: HemmaStorageSettings) -> None:
    """Evacuate legacy scratch corpus data to Hot and preserve its logical path."""
    validate_migration_source(settings.old_qwen_data_root, settings.new_qwen_data_root)
    ensure_directory(settings.new_qwen_data_root.parent)
    _migrate_tree(settings.old_qwen_data_root, settings.new_qwen_data_root)
    _replace_with_symlink(settings.old_qwen_data_root, settings.new_qwen_data_root)


def docker_system_df() -> str:
    """Return the current Docker storage summary from Hemma."""
    return run_checked(
        ["sudo", "-n", "docker", "system", "df"], label="docker system df hemma-storage"
    )


def filesystem_df() -> str:
    """Return the key Hemma filesystem usage summary."""
    return run_checked(["df", "-h", "/", "/srv/scratch", "/srv/storage"], label="df hemma-storage")


def cleanup_non_active_docker_state() -> None:
    """Refuse the retired Sir cleanup surface before executing any command."""
    raise SystemExit(DOCKER_CLEANUP_REFUSAL)


def build_storage_report(
    settings: HemmaStorageSettings,
    *,
    docker_system_df_before_text: str,
    docker_system_df_after_text: str,
    filesystem_df_before_text: str,
    filesystem_df_after_text: str,
) -> HemmaStorageReport:
    """Build the deterministic post-remediation storage report."""
    repo_build_target = None
    migrated_repo_build = False
    if settings.repo_build_root.is_symlink():
        repo_build_target = settings.repo_build_root.resolve().as_posix()
        migrated_repo_build = repo_build_target == settings.scratch_build_root.resolve().as_posix()
    old_qwen_data_target = None
    migrated_qwen_data = False
    if settings.old_qwen_data_root.is_symlink():
        old_qwen_data_target = settings.old_qwen_data_root.resolve().as_posix()
        migrated_qwen_data = (
            old_qwen_data_target == settings.new_qwen_data_root.resolve().as_posix()
        )
    return HemmaStorageReport(
        repo_build_root=settings.repo_build_root.as_posix(),
        repo_build_is_symlink=settings.repo_build_root.is_symlink(),
        repo_build_target=repo_build_target,
        scratch_build_root=settings.scratch_build_root.as_posix(),
        old_qwen_data_root=settings.old_qwen_data_root.as_posix(),
        old_qwen_data_is_symlink=settings.old_qwen_data_root.is_symlink(),
        old_qwen_data_target=old_qwen_data_target,
        new_qwen_data_root=settings.new_qwen_data_root.as_posix(),
        migrated_repo_build=migrated_repo_build,
        migrated_qwen_data=migrated_qwen_data,
        cleaned_docker_state=settings.cleanup_docker_state,
        docker_system_df_before=docker_system_df_before_text,
        docker_system_df_after=docker_system_df_after_text,
        filesystem_df_before=filesystem_df_before_text,
        filesystem_df_after=filesystem_df_after_text,
    )


def run_storage_remediation(settings: HemmaStorageSettings) -> HemmaStorageReport:
    """
    Execute the Hemma storage remediation storage remediation and return one deterministic report.
    """
    if settings.cleanup_docker_state:
        raise SystemExit(DOCKER_CLEANUP_REFUSAL)
    if settings.migrate_repo_build:
        validate_migration_source(settings.repo_build_root, settings.scratch_build_root)
    if settings.migrate_qwen_data:
        validate_migration_source(settings.old_qwen_data_root, settings.new_qwen_data_root)
    docker_before = docker_system_df()
    filesystem_before = filesystem_df()
    if settings.migrate_repo_build:
        migrate_repo_build_to_scratch(settings)
    if settings.migrate_qwen_data:
        migrate_qwen_data_to_storage(settings)
    docker_after = docker_system_df()
    filesystem_after = filesystem_df()
    return build_storage_report(
        settings,
        docker_system_df_before_text=docker_before,
        docker_system_df_after_text=docker_after,
        filesystem_df_before_text=filesystem_before,
        filesystem_df_after_text=filesystem_after,
    )
