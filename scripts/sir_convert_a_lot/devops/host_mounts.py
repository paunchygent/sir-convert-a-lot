"""Shared host mount helpers for Hemma service and runtime contracts.

Purpose:
    Centralize small mount- and privilege-aware host helpers used by multiple
    Hemma DevOps and Qwen runtime surfaces.

Relationships:
    - Used by `qwen_docker_bind_roots_runtime.py` for persistent bind-root
      installation and inspection.
    - Used by `ml.qwen.common.runtime` to recognize already-installed
      Docker-visible home bind roots before falling back to ad hoc repair.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


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


def run_optional(command: list[str]) -> tuple[int, str, str]:
    """Run one subprocess command and return exit code, stdout, and stderr."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_root_checked(command: list[str], *, label: str) -> str:
    """Run one command as root, using sudo when the current process is unprivileged."""
    if os.geteuid() == 0:
        return run_checked(command, label=label)
    return run_checked(["sudo", "-n", *command], label=label)


def ensure_directory(path: Path, *, require_root: bool) -> None:
    """Create one directory tree, escalating to root when the path requires it."""
    runner = run_root_checked if require_root else run_checked
    runner(["mkdir", "-p", path.as_posix()], label=f"mkdir {path.name}")


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


def write_root_owned_text(path: Path, *, text: str) -> None:
    """Write one text file that may require root ownership."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    try:
        if os.geteuid() == 0:
            run_checked(["cp", temp_path.as_posix(), path.as_posix()], label=f"cp {path.name}")
        else:
            run_checked(
                ["sudo", "-n", "cp", temp_path.as_posix(), path.as_posix()],
                label=f"sudo cp {path.name}",
            )
    finally:
        temp_path.unlink(missing_ok=True)
