"""Run public Qwen commands through the isolated nested PDM project.

The root command surface remains stable while dependency ownership, lock
freshness, and the installed environment belong exclusively to ``qwen/``.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

CommandRunner = Callable[[tuple[str, ...], Path], int]


def _run_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


def run_qwen_project(
    project_root: Path,
    arguments: Sequence[str],
    command_runner: CommandRunner = _run_command,
) -> int:
    """Validate and execute one command through the Qwen-owned environment."""
    qwen_root = project_root / "qwen"
    required_paths = (
        qwen_root / "pyproject.toml",
        qwen_root / "pdm.lock",
        qwen_root / ".venv" / "bin" / "python",
    )
    missing_paths = tuple(path for path in required_paths if not path.exists())
    if missing_paths:
        missing = ", ".join(path.relative_to(project_root).as_posix() for path in missing_paths)
        print(
            f"nested Qwen environment is missing required paths: {missing}; "
            "run `pdm install -p qwen -G dev`",
            file=sys.stderr,
        )
        return 2
    if not arguments:
        print("a nested Qwen command is required", file=sys.stderr)
        return 2

    lock_check = ("pdm", "lock", "-p", "qwen", "--check")
    if command_runner(lock_check, project_root) != 0:
        print(
            "nested Qwen lock is stale; run `pdm lock -p qwen` and reinstall the environment",
            file=sys.stderr,
        )
        return 2

    command = ("pdm", "run", "-p", "qwen", *arguments)
    return command_runner(command, project_root)
