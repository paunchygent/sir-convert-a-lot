"""Runtime helpers for Task 113 Hemma Docker storage-root migration.

Purpose:
    Move Hemma's Docker daemon bytes onto SSD scratch without changing the
    snap-visible logical Docker root path, by bind-mounting a scratch-backed
    directory onto Docker's canonical snap root.

Relationships:
    - Used by `run_task113_hemma_docker_storage_remediation.py`.
    - Complements Task 112 by fixing Docker's host-wide storage contract.
    - Replaces the earlier failed home-path bind-mount approach with a
      snap-compatible mount onto `/var/snap/docker/common/var-lib-docker`.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DOCKER_ROOT = Path("/var/snap/docker/common/var-lib-docker")
DEFAULT_SCRATCH_DOCKER_ROOT = Path("/srv/scratch/docker/data-root")
DEFAULT_DOCKER_ROOT_BACKUP = Path("/var/snap/docker/common/var-lib-docker.task113-backup")
DEFAULT_LEGACY_HOME_DOCKER_ROOT = Path("/home/paunchygent/.data/docker/data-root")
DEFAULT_FSTAB_PATH = Path("/etc/fstab")


@dataclass(frozen=True)
class Task113DockerStorageSettings:
    """Normalized settings for the Task 113 Docker storage migration runner."""

    docker_root: Path
    scratch_docker_root: Path
    docker_root_backup: Path
    legacy_home_docker_root: Path
    fstab_path: Path
    remove_backup_after_success: bool


@dataclass(frozen=True)
class Task113DockerStorageReport:
    """Deterministic report for one Task 113 Docker storage migration pass."""

    docker_root: str
    scratch_docker_root: str
    docker_root_backup: str
    legacy_home_docker_root: str
    docker_root_before: str
    docker_root_after: str
    docker_root_mount_source_before: str | None
    docker_root_mount_source_after: str | None
    legacy_home_mount_source_before: str | None
    legacy_home_mount_source_after: str | None
    snap_data_root_before: str
    snap_data_root_after: str
    removed_backup_after_success: bool
    filesystem_df_before: str
    filesystem_df_after: str
    docker_ps_before: str
    docker_ps_after: str


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


def docker_root_dir() -> str:
    """Return Docker's current effective root directory."""
    return run_checked(
        ["sudo", "-n", "docker", "info", "--format", "{{.DockerRootDir}}"],
        label="docker info root dir task113",
    )


def snap_data_root() -> str:
    """Return the configured Docker snap data-root value when present."""
    return run_checked(
        ["sudo", "-n", "snap", "get", "docker", "data-root"],
        label="snap get data-root task113",
    )


def docker_ps() -> str:
    """Return one deterministic snapshot of Docker container state."""
    return run_checked(
        [
            "sudo",
            "-n",
            "docker",
            "ps",
            "-a",
            "--format",
            "table {{.Names}}\t{{.Status}}\t{{.Image}}",
        ],
        label="docker ps task113",
    )


def filesystem_df() -> str:
    """Return the key Hemma filesystem usage summary."""
    return run_checked(["df", "-h", "/", "/srv/scratch", "/srv/storage"], label="df task113")


def ensure_directory(path: Path) -> None:
    """Create one directory tree, escalating when the parent is root-owned."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        run_checked(
            ["sudo", "-n", "mkdir", "-p", path.as_posix()],
            label="sudo mkdir -p task113",
        )


def find_mount_source(target: Path) -> str | None:
    """Return the current mount source for one target, if it is a mountpoint."""
    is_mount_result = subprocess.run(
        ["mountpoint", "-q", target.as_posix()],
        check=False,
        capture_output=True,
        text=True,
    )
    if is_mount_result.returncode != 0:
        return None
    result = subprocess.run(
        ["findmnt", "-n", "-o", "SOURCE", "--target", target.as_posix()],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    rendered = result.stdout.strip()
    return rendered if rendered != "" else None


def ensure_fstab_bind_entry_text(*, current_text: str, source: Path, target: Path) -> str:
    """Ensure one bind-mount entry exists in fstab text exactly once."""
    entry = f"{source.as_posix()} {target.as_posix()} none bind 0 0"
    lines = current_text.splitlines()
    filtered_lines = [line for line in lines if line.strip() != entry]
    filtered_lines.append(entry)
    return "\n".join(filtered_lines).rstrip() + "\n"


def remove_fstab_bind_entry_text(*, current_text: str, target: Path) -> str:
    """Remove one bind-mount fstab entry that targets the given path."""
    filtered_lines = [
        line
        for line in current_text.splitlines()
        if f" {target.as_posix()} none bind " not in f" {line} "
    ]
    if not filtered_lines:
        return ""
    return "\n".join(filtered_lines).rstrip() + "\n"


def _write_text(path: Path, *, text: str) -> None:
    """Write one text file, using sudo for system-owned paths when needed."""
    if path == DEFAULT_FSTAB_PATH:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(text)
            temp_path = Path(handle.name)
        try:
            run_checked(
                ["sudo", "-n", "cp", temp_path.as_posix(), path.as_posix()],
                label="sudo cp fstab task113",
            )
        finally:
            temp_path.unlink(missing_ok=True)
        return
    path.write_text(text, encoding="utf-8")


def update_fstab_for_bind(
    *,
    fstab_path: Path,
    source: Path,
    target: Path,
    legacy_target: Path,
) -> None:
    """Persist the new bind mount and remove any legacy home-path entry."""
    current_text = fstab_path.read_text(encoding="utf-8") if fstab_path.exists() else ""
    updated_text = remove_fstab_bind_entry_text(current_text=current_text, target=legacy_target)
    updated_text = ensure_fstab_bind_entry_text(
        current_text=updated_text,
        source=source,
        target=target,
    )
    if updated_text != current_text:
        _write_text(fstab_path, text=updated_text)


def stop_docker_snap() -> None:
    """Stop the Docker snap before migrating the daemon state."""
    run_checked(["sudo", "-n", "snap", "stop", "docker"], label="snap stop docker task113")


def start_docker_snap() -> None:
    """Start the Docker snap after migrating the daemon state."""
    run_checked(["sudo", "-n", "snap", "start", "docker"], label="snap start docker task113")


def set_snap_data_root(docker_root: Path) -> None:
    """Set the Docker snap data-root to the canonical snap root path."""
    run_checked(
        ["sudo", "-n", "snap", "set", "docker", f"data-root={docker_root.as_posix()}"],
        label="snap set docker data-root task113",
    )


def rsync_tree(*, source: Path, destination: Path) -> None:
    """Copy one directory tree with rsync while preserving Docker state details."""
    ensure_directory(destination)
    run_checked(
        [
            "sudo",
            "-n",
            "rsync",
            "-aHAX",
            "--delete",
            f"{source.as_posix()}/",
            f"{destination.as_posix()}/",
        ],
        label="rsync docker root task113",
    )


def move_tree(source: Path, destination: Path) -> None:
    """Move one directory tree inside the same filesystem with sudo."""
    if source.exists():
        run_checked(
            ["sudo", "-n", "mv", source.as_posix(), destination.as_posix()],
            label="mv docker root task113",
        )


def remove_tree(path: Path) -> None:
    """Delete one tree with sudo."""
    run_checked(["sudo", "-n", "rm", "-rf", path.as_posix()], label="rm -rf task113")


def unmount_path(path: Path) -> None:
    """Unmount one existing bind mount."""
    run_checked(["sudo", "-n", "umount", path.as_posix()], label="umount task113")


def mount_bind(source: Path, target: Path) -> None:
    """Create one live bind mount."""
    run_checked(
        ["sudo", "-n", "mount", "--bind", source.as_posix(), target.as_posix()],
        label="mount --bind task113",
    )


def wait_for_docker_root(expected_root: Path, *, timeout_seconds: float) -> str:
    """Wait until Docker reports the expected root or fail deterministically."""
    deadline = time.time() + timeout_seconds
    last_error = "docker root not ready"
    while time.time() < deadline:
        try:
            rendered_root = docker_root_dir()
        except SystemExit as exc:
            last_error = str(exc)
            time.sleep(1.0)
            continue
        if rendered_root == expected_root.as_posix():
            return rendered_root
        last_error = f"docker reported `{rendered_root}` instead of `{expected_root.as_posix()}`"
        time.sleep(1.0)
    raise SystemExit(
        "Docker root did not converge after restart. "
        f"Last observed error: {last_error}"
    )


def build_storage_report(
    settings: Task113DockerStorageSettings,
    *,
    docker_root_before_text: str,
    docker_root_after_text: str,
    docker_root_mount_source_before: str | None,
    docker_root_mount_source_after: str | None,
    legacy_home_mount_source_before: str | None,
    legacy_home_mount_source_after: str | None,
    snap_data_root_before_text: str,
    snap_data_root_after_text: str,
    removed_backup_after_success: bool,
    filesystem_df_before_text: str,
    filesystem_df_after_text: str,
    docker_ps_before_text: str,
    docker_ps_after_text: str,
) -> Task113DockerStorageReport:
    """Build the deterministic Task 113 post-migration report."""
    return Task113DockerStorageReport(
        docker_root=settings.docker_root.as_posix(),
        scratch_docker_root=settings.scratch_docker_root.as_posix(),
        docker_root_backup=settings.docker_root_backup.as_posix(),
        legacy_home_docker_root=settings.legacy_home_docker_root.as_posix(),
        docker_root_before=docker_root_before_text,
        docker_root_after=docker_root_after_text,
        docker_root_mount_source_before=docker_root_mount_source_before,
        docker_root_mount_source_after=docker_root_mount_source_after,
        legacy_home_mount_source_before=legacy_home_mount_source_before,
        legacy_home_mount_source_after=legacy_home_mount_source_after,
        snap_data_root_before=snap_data_root_before_text,
        snap_data_root_after=snap_data_root_after_text,
        removed_backup_after_success=removed_backup_after_success,
        filesystem_df_before=filesystem_df_before_text,
        filesystem_df_after=filesystem_df_after_text,
        docker_ps_before=docker_ps_before_text,
        docker_ps_after=docker_ps_after_text,
    )


def run_task113_docker_storage_migration(
    settings: Task113DockerStorageSettings,
) -> Task113DockerStorageReport:
    """Execute the Task 113 Docker storage migration and return one report."""
    docker_root_before = docker_root_dir()
    snap_before = snap_data_root()
    filesystem_before = filesystem_df()
    docker_ps_before_text = docker_ps()
    docker_root_mount_before = find_mount_source(settings.docker_root)
    legacy_home_mount_before = find_mount_source(settings.legacy_home_docker_root)

    stop_docker_snap()
    ensure_directory(settings.scratch_docker_root.parent)
    if legacy_home_mount_before is not None:
        unmount_path(settings.legacy_home_docker_root)
    update_fstab_for_bind(
        fstab_path=settings.fstab_path,
        source=settings.scratch_docker_root,
        target=settings.docker_root,
        legacy_target=settings.legacy_home_docker_root,
    )

    if docker_root_mount_before != find_mount_source(settings.docker_root):
        docker_root_mount_before = find_mount_source(settings.docker_root)

    if docker_root_mount_before is None:
        rsync_tree(source=settings.docker_root, destination=settings.scratch_docker_root)
        if settings.docker_root_backup.exists():
            remove_tree(settings.docker_root_backup)
        move_tree(settings.docker_root, settings.docker_root_backup)
        ensure_directory(settings.docker_root)
        mount_bind(settings.scratch_docker_root, settings.docker_root)
    else:
        rsync_tree(source=settings.docker_root, destination=settings.scratch_docker_root)

    set_snap_data_root(settings.docker_root)
    start_docker_snap()
    docker_root_after = wait_for_docker_root(settings.docker_root, timeout_seconds=30.0)

    removed_backup_after_success = False
    if settings.remove_backup_after_success and settings.docker_root_backup.exists():
        remove_tree(settings.docker_root_backup)
        removed_backup_after_success = True

    docker_root_mount_after = find_mount_source(settings.docker_root)
    legacy_home_mount_after = find_mount_source(settings.legacy_home_docker_root)
    snap_after = snap_data_root()
    filesystem_after = filesystem_df()
    docker_ps_after_text = docker_ps()
    return build_storage_report(
        settings,
        docker_root_before_text=docker_root_before,
        docker_root_after_text=docker_root_after,
        docker_root_mount_source_before=docker_root_mount_before,
        docker_root_mount_source_after=docker_root_mount_after,
        legacy_home_mount_source_before=legacy_home_mount_before,
        legacy_home_mount_source_after=legacy_home_mount_after,
        snap_data_root_before_text=snap_before,
        snap_data_root_after_text=snap_after,
        removed_backup_after_success=removed_backup_after_success,
        filesystem_df_before_text=filesystem_before,
        filesystem_df_after_text=filesystem_after,
        docker_ps_before_text=docker_ps_before_text,
        docker_ps_after_text=docker_ps_after_text,
    )
