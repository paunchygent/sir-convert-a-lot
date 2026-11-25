"""Tests for the Sir Hemma workload host command runner.

Purpose:
    Check the host command timeout and that `CommandRunner` passes it to the
    subprocess.

Relationships:
    - Exercises `scripts/sir_convert_a_lot/devops/hemma_workload_runtime.py`.
"""

import subprocess

import pytest

from scripts.sir_convert_a_lot.devops import hemma_workload, hemma_workload_runtime


def test_host_command_timeout_exceeds_task04_bounded_startup_timeout() -> None:
    assert (
        hemma_workload_runtime.HOST_COMMAND_TIMEOUT_SECONDS > hemma_workload.TOTAL_TIMEOUT_SECONDS
    )


def test_command_runner_passes_named_timeout_to_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeouts: list[float] = []

    def fake_run(
        argv: tuple[str, ...],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        timeouts.append(timeout)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(hemma_workload_runtime.subprocess, "run", fake_run)

    hemma_workload_runtime.CommandRunner().run(("docker", "ps"))

    assert timeouts == [hemma_workload_runtime.HOST_COMMAND_TIMEOUT_SECONDS]
