"""Audio transcription sidecar observation command execution.

Purpose:
    Provide the bounded subprocess command boundary used by live STT
    observation producers and their tests.

Relationships:
    - Shared by the live observation runtime and CLI runner.
    - Keeps command capture separate from observation projection and backend
      probe semantics.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompletedCommand:
    """Completed subprocess output used by the observation producer."""

    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    """Command execution boundary for host and Docker runtime probes."""

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
    ) -> CompletedCommand:
        """Run one command and return captured output."""


@dataclass(frozen=True, slots=True)
class SubprocessCommandRunner:
    """Subprocess-backed command runner for operator CLI execution."""

    environment: Mapping[str, str] | None = None

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
    ) -> CompletedCommand:
        """Run a command without stdin and return bounded captured output."""

        try:
            result = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                stdin=subprocess.DEVNULL,
                env=dict(self.environment) if self.environment is not None else None,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return CompletedCommand(returncode=127, stdout="", stderr=str(exc))
        return CompletedCommand(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
