"""Sandboxed Pandoc subprocess execution helpers.

Purpose:
    Provide a bounded-memory, timeout-aware subprocess runner for Pandoc
    command invocations used across conversion wrappers.

Relationships:
    - Used by `pandoc_*` wrapper modules in this package.
    - Centralizes stderr capture limits and timeout process cleanup semantics.
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from collections.abc import Sequence

PANDOC_MAX_STDERR_BYTES = 64 * 1024


def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except PermissionError:
            pass
    process.kill()


def run_pandoc_command(
    *,
    command: Sequence[str],
    timeout_seconds: int,
    stderr_max_bytes: int = PANDOC_MAX_STDERR_BYTES,
) -> tuple[int, str]:
    """Run Pandoc with bounded stderr capture and timeout cleanup."""

    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _kill_process_tree(process)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise
        stderr_file.seek(0)
        stderr_value = stderr_file.read(stderr_max_bytes).decode("utf-8", errors="replace")
    return return_code, stderr_value.strip()
