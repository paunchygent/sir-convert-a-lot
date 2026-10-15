"""Sir-owned Hot workspace and shared Docker-cleanup ownership.

Purpose:
    Keep nonvisual build, proof and legacy evacuation destinations in the
    Hot-backed home tree. The shared host owns physical backing and cutover.

Relationships:
    Used by the legacy storage and scratch-maintenance adapters. Historical
    scratch-named settings remain accepted for logical-path compatibility.
"""

import filecmp
from pathlib import Path

DEFAULT_OWNER_ROOT = Path("/home/paunchygent/.local/share/sir-convert-a-lot")
DEFAULT_HOT_JOBS_ROOT = DEFAULT_OWNER_ROOT / "jobs"
DEFAULT_HOT_BUILD_ROOT = DEFAULT_HOT_JOBS_ROOT / "build"
DEFAULT_HOT_ARCHIVE_ROOT = DEFAULT_HOT_JOBS_ROOT / "legacy-scratch-archive"
DEFAULT_HOT_QWEN_DATA_ROOT = DEFAULT_OWNER_ROOT / "data/qwen3-tts-swedish-corpus"
DOCKER_CLEANUP_REFUSAL = (
    "Sir Docker cleanup is unsupported; shared weekly hemma-docker-cleanup "
    "owns host Docker maintenance. Sir will not prune containers, images, volumes or builder cache."
)


def validate_hot_destination(destination: Path) -> None:
    """Refuse the retired scratch and backup-only primary destinations."""
    for path in (destination, destination.resolve()):
        if any(path.is_relative_to(root) for root in (Path("/srv/scratch"), Path("/srv/storage"))):
            raise SystemExit(
                f"Nonvisual Sir primary data requires Hot owner storage; refused `{destination}`. "
                "Scratch is visual-only and /srv/storage is backup-only."
            )


def validate_migration_source(source: Path, destination: Path) -> None:
    """Preserve an existing logical path until its owner has moved its backing."""
    validate_hot_destination(destination)
    if source.is_symlink() and source.resolve() != destination.resolve():
        raise SystemExit(
            f"Refusing to retarget existing logical path `{source}` from `{source.resolve()}` "
            f"to `{destination}`; the parent must first migrate and verify its backing."
        )
    validate_migration_tree(source, destination)


def validate_migration_tree(source: Path, destination: Path) -> None:
    """Check all destinations and occupied paths before merging any source bytes."""
    validate_hot_destination(destination)
    if not source.exists() or source.is_symlink():
        return
    source_root, destination_root = source.resolve(), destination.resolve()
    if source_root.is_relative_to(destination_root) or destination_root.is_relative_to(source_root):
        raise SystemExit(f"Refusing overlapping migration paths: `{source}` and `{destination}`.")
    try:
        _validate_merge_paths(source, destination)
    except OSError as exc:
        raise SystemExit(f"Cannot verify migration collision safety for `{source}`: {exc}") from exc


def _validate_merge_paths(source: Path, destination: Path) -> None:
    """Accept only absent targets, mergeable directories and identical payloads."""
    validate_hot_destination(destination)
    occupied = destination.exists() or destination.is_symlink()
    if source.is_symlink():
        if not occupied or (
            destination.is_symlink() and source.readlink() == destination.readlink()
        ):
            return
    elif source.is_dir():
        if not occupied or destination.is_dir():
            for child in sorted(source.iterdir()):
                _validate_merge_paths(child, destination / child.name)
            return
    elif source.is_file():
        if not occupied or (
            not destination.is_symlink()
            and destination.is_file()
            and filecmp.cmp(source, destination, shallow=False)
        ):
            return
    raise SystemExit(
        f"Refusing migration collision between `{source}` and `{destination}`; "
        "preserve both payloads for owner resolution."
    )
