"""Runtime helpers for Task 113 Hemma Docker storage-root migration.

Purpose:
    Move Hemma's Docker daemon state off the root disk by placing Docker's
    configured data-root on a home-visible bind mount backed by SSD scratch.

Relationships:
    - Used by `run_task113_hemma_docker_storage_remediation.py`.
    - Complements Task 112 by fixing the host-wide Docker storage contract.
    - Aligns the live Hemma Docker layout with the DevOps runbooks and skills
      that treat `/srv/scratch` as the fast working tier.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OLD_DOCKER_ROOT = Path("/var/snap/docker/common/var-lib-docker")
DEFAULT_SCRATCH_DOCKER_ROOT = Path("/srv/scratch/docker/data-root")
DEFAULT_HOME_DOCKER_ROOT = Path("/home/paunchygent/docker-data-root")
DEFAULT_FSTAB_PATH = Path("/etc/fstab")


@dataclass(frozen=True)
class Task113DockerStorageSettings:
    """Normalized settings for the Task 113 Docker storage migration runner."""

    old_docker_root: Path
    scratch_docker_root: Path
    home_docker_root: Path
    fstab_path: Path
    remove_old_root_after_success: bool


@dataclass(frozen=True)
class Task113DockerStorageReport:
    """Deterministic report for one Task 113 Docker storage migration pass."""

    old_docker_root: str
    scratch_docker_root: str
    home_docker_root: str
    docker_root_before: str
    docker_root_after: str
    snap_data_root_before: str
    snap_data_root_after: str
    bind_mount_source_before: str | None
    bind_mount_source_after: str | None
    removed_old_root_after_success: bool
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


def ensure_directory(path: Path) -> None:
    """Create one directory tree when it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def docker_root_dir() -> str:
    """Return Docker's current effective root directory."""
    return run_checked(
        ["sudo", "-n", "docker", "info", "--format", "{{.DockerRootDir}}"],
        label="docker info root dir task113",
    )


def snap_data_root() -> str:
    """Return the configured Docker snap data-root value when present."""
    return run_checked(
        ["sudo", "-n", "snap", "get", "docker", "data-root"], label="snap get data-root"
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


def find_mount_source(target: Path) -> str | None:
    """Return the current bind-mount source for one target, if mounted."""
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
    if entry in lines:
        return current_text if current_text.endswith("\n") else current_text + "\n"
    normalized = (
        current_text if current_text.endswith("\n") or current_text == "" else current_text + "\n"
    )
    return normalized + entry + "\n"


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


def ensure_persistent_bind_mount(
    *,
    source: Path,
    target: Path,
    fstab_path: Path,
) -> tuple[str | None, str | None]:
    """Ensure one persistent bind mount from SSD scratch into the home-visible path."""
    ensure_directory(source)
    ensure_directory(target)
    before_source = find_mount_source(target)
    if before_source is not None and not target.samefile(source):
        raise SystemExit(
            f"Refusing to replace unexpected mount at `{target}` from `{before_source}`."
        )
    if before_source is None:
        run_checked(
            ["sudo", "-n", "mount", "--bind", source.as_posix(), target.as_posix()],
            label="mount --bind task113",
        )
    current_text = fstab_path.read_text(encoding="utf-8") if fstab_path.exists() else ""
    updated_text = ensure_fstab_bind_entry_text(
        current_text=current_text,
        source=source,
        target=target,
    )
    if updated_text != current_text:
        _write_text(fstab_path, text=updated_text)
    after_source = find_mount_source(target)
    return before_source, after_source


def stop_docker_snap() -> None:
    """Stop the Docker snap before migrating the daemon state."""
    run_checked(["sudo", "-n", "snap", "stop", "docker"], label="snap stop docker task113")


def start_docker_snap() -> None:
    """Start the Docker snap after migrating the daemon state."""
    run_checked(["sudo", "-n", "snap", "start", "docker"], label="snap start docker task113")


def wait_for_docker_daemon(*, attempts: int = 30, sleep_seconds: float = 1.0) -> str:
    """Wait for the Docker daemon to accept `docker info` again after restart."""
    last_error: str | None = None
    for _ in range(attempts):
        try:
            return docker_root_dir()
        except SystemExit as exc:
            last_error = str(exc)
            time.sleep(sleep_seconds)
    raise SystemExit(
        "Docker daemon did not become ready after restart.\n"
        f"Last error:\n{last_error or 'unknown'}"
    )


def set_snap_data_root(home_docker_root: Path) -> None:
    """Set the Docker snap data-root to the home-visible bind mount path."""
    run_checked(
        ["sudo", "-n", "snap", "set", "docker", f"data-root={home_docker_root.as_posix()}"],
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


def remove_old_root(path: Path) -> None:
    """Delete the old Docker root after successful migration."""
    run_checked(
        ["sudo", "-n", "rm", "-rf", path.as_posix()], label="rm -rf old docker root task113"
    )


def build_storage_report(
    settings: Task113DockerStorageSettings,
    *,
    docker_root_before_text: str,
    docker_root_after_text: str,
    snap_data_root_before_text: str,
    snap_data_root_after_text: str,
    bind_mount_source_before: str | None,
    bind_mount_source_after: str | None,
    removed_old_root_after_success: bool,
    filesystem_df_before_text: str,
    filesystem_df_after_text: str,
    docker_ps_before_text: str,
    docker_ps_after_text: str,
) -> Task113DockerStorageReport:
    """Build the deterministic Task 113 post-migration report."""
    return Task113DockerStorageReport(
        old_docker_root=settings.old_docker_root.as_posix(),
        scratch_docker_root=settings.scratch_docker_root.as_posix(),
        home_docker_root=settings.home_docker_root.as_posix(),
        docker_root_before=docker_root_before_text,
        docker_root_after=docker_root_after_text,
        snap_data_root_before=snap_data_root_before_text,
        snap_data_root_after=snap_data_root_after_text,
        bind_mount_source_before=bind_mount_source_before,
        bind_mount_source_after=bind_mount_source_after,
        removed_old_root_after_success=removed_old_root_after_success,
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
    bind_before, bind_after = ensure_persistent_bind_mount(
        source=settings.scratch_docker_root,
        target=settings.home_docker_root,
        fstab_path=settings.fstab_path,
    )

    removed_old_root_after_success = False
    if docker_root_before != settings.home_docker_root.as_posix():
        stop_docker_snap()
        rsync_tree(source=settings.old_docker_root, destination=settings.scratch_docker_root)
        set_snap_data_root(settings.home_docker_root)
        start_docker_snap()
        docker_root_after = wait_for_docker_daemon()
        if docker_root_after != settings.home_docker_root.as_posix():
            raise SystemExit(
                "Docker data-root migration did not converge to the expected "
                "home-visible bind mount."
            )
        if settings.remove_old_root_after_success and settings.old_docker_root.exists():
            remove_old_root(settings.old_docker_root)
            removed_old_root_after_success = True
    else:
        docker_root_after = docker_root_before

    snap_after = snap_data_root()
    filesystem_after = filesystem_df()
    docker_ps_after_text = docker_ps()
    return build_storage_report(
        settings,
        docker_root_before_text=docker_root_before,
        docker_root_after_text=docker_root_after,
        snap_data_root_before_text=snap_before,
        snap_data_root_after_text=snap_after,
        bind_mount_source_before=bind_before,
        bind_mount_source_after=bind_after,
        removed_old_root_after_success=removed_old_root_after_success,
        filesystem_df_before_text=filesystem_before,
        filesystem_df_after_text=filesystem_after,
        docker_ps_before_text=docker_ps_before_text,
        docker_ps_after_text=docker_ps_after_text,
    )
