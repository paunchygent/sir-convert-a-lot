"""Run bounded literal host commands for Sir workload adapters."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol

HOST_COMMAND_TIMEOUT_SECONDS = 150.0


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


class CommandExecutor(Protocol):
    def run(self, argv: tuple[str, ...]) -> CommandResult: ...


class CommandRunner:
    """Run one literal host command within the owner timeout."""

    def run(self, argv: tuple[str, ...]) -> CommandResult:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=HOST_COMMAND_TIMEOUT_SECONDS,
        )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)
