"""Tests for the Sir production workload adapter.

Purpose:
    Check that `ProductionWorkloadAdapter` starts, stops, reports status and
    readiness, and starts existing containers as one exact workload.

Relationships:
    - Exercises `scripts/sir_convert_a_lot/devops/hemma_workload.py`.
"""

import subprocess
from pathlib import Path

import pytest
from repository_governance.hemma_workload import ExpectedState, TerminalOutcome

from scripts.sir_convert_a_lot.devops import hemma_workload
from tests.sir_convert_a_lot.operations.hemma_workload_fakes import QueueRunner


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [
        (0, "detail\noutcome=succeeded\n", TerminalOutcome.SUCCEEDED),
        (1, "outcome=timed_out\n", TerminalOutcome.TIMED_OUT),
        (1, "outcome=dependency_unhealthy\n", TerminalOutcome.DEPENDENCY_UNHEALTHY),
        (1, "outcome=refused\n", TerminalOutcome.REFUSED),
        (1, "outcome=failed\n", TerminalOutcome.FAILED),
    ],
)
def test_production_start_uses_bounded_command_and_maps_terminal_outcome(
    returncode: int, stdout: str, expected: TerminalOutcome
) -> None:
    runner = QueueRunner([hemma_workload.CommandResult(returncode, stdout)])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    result = adapter.start()

    assert result.outcome is expected
    assert runner.commands == [("pdm", "run", "prod-workload-start")]
    assert "--build" not in runner.commands[0]


@pytest.mark.parametrize(
    "stdout",
    ["", "outcome=succeeded\noutcome=succeeded\n", "outcome=succeeded\ntrailing\n", "noise\n"],
)
def test_production_start_refuses_nonterminal_or_ambiguous_outcome(stdout: str) -> None:
    adapter = hemma_workload.ProductionWorkloadAdapter(
        QueueRunner([hemma_workload.CommandResult(0, stdout)]), Path("/srv/sir")
    )

    assert adapter.start().outcome is TerminalOutcome.FAILED


def test_production_stop_uses_only_named_worker_and_api() -> None:
    runner = QueueRunner([hemma_workload.CommandResult(0, "")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.stop().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands == [
        (
            "pdm",
            "run",
            "prod-stop",
            hemma_workload.GPU_WORKER_CONTAINER,
            hemma_workload.API_CONTAINER,
        )
    ]
    assert "--build" not in runner.commands[0]


def test_production_status_requires_exact_group_and_restart_no() -> None:
    mixed = QueueRunner(
        [
            hemma_workload.CommandResult(0, "running\tno\n"),
            hemma_workload.CommandResult(0, "exited\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(mixed, Path("/srv/sir"))
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.REFUSED

    running = QueueRunner(
        [
            hemma_workload.CommandResult(0, "running\tno\n"),
            hemma_workload.CommandResult(0, "running\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(running, Path("/srv/sir"))
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.SUCCEEDED

    wrong_restart = QueueRunner(
        [
            hemma_workload.CommandResult(0, "running\tunless-stopped\n"),
            hemma_workload.CommandResult(0, "running\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(wrong_restart, Path("/srv/sir"))
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.FAILED

    stopped_wrong_restart = QueueRunner(
        [
            hemma_workload.CommandResult(0, "exited\tunless-stopped\n"),
            hemma_workload.CommandResult(0, "exited\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(stopped_wrong_restart, Path("/srv/sir"))
    assert adapter.status(ExpectedState.STOPPED).outcome is TerminalOutcome.FAILED


def test_production_status_refuses_unknown_container_state() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "unknown\tno\n"),
            hemma_workload.CommandResult(0, "running\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.REFUSED


def test_production_readiness_reuses_task04_api_and_worker_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        hemma_workload,
        "_repository_head",
        lambda runner: "a" * 40,
    )
    monkeypatch.setattr(
        hemma_workload,
        "_poll_ready",
        lambda runner, *, head, docker_prefix: calls.append(
            ("api", f"{head}:{' '.join(docker_prefix)}")
        ),
    )
    monkeypatch.setattr(
        hemma_workload,
        "_prove_gpu_readiness",
        lambda runner, *, docker_prefix: calls.append(("worker", " ".join(docker_prefix))),
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(QueueRunner([]), Path("/srv/sir"))

    assert adapter.readiness().outcome is TerminalOutcome.SUCCEEDED
    privileged_docker = " ".join(hemma_workload.DOCKER_COMMAND)
    assert calls == [
        ("api", f"{'a' * 40}:{privileged_docker}"),
        ("worker", privileged_docker),
    ]


def test_production_operations_normalize_subprocess_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TimeoutRunner:
        def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
            raise subprocess.TimeoutExpired(argv, 1)

    adapter = hemma_workload.ProductionWorkloadAdapter(TimeoutRunner(), Path("/srv/sir"))
    assert adapter.start().outcome is TerminalOutcome.TIMED_OUT
    assert adapter.stop().outcome is TerminalOutcome.TIMED_OUT
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.TIMED_OUT

    monkeypatch.setattr(
        hemma_workload,
        "_repository_head",
        lambda bounded: (_ for _ in ()).throw(subprocess.TimeoutExpired("git", 1)),
    )
    assert adapter.readiness().outcome is TerminalOutcome.TIMED_OUT


def test_production_start_existing_starts_matching_containers() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start_existing().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[-1] == (
        *hemma_workload.DOCKER_COMMAND,
        "start",
        *hemma_workload.PRODUCTION_CONTAINERS,
    )


def test_production_start_existing_refuses_absent_container() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(1, "No such object"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "absent" in result.reason
    assert all(command[3:4] != ("start",) for command in runner.commands)


def test_production_start_existing_refuses_stale_image() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:old\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "stale application image" in result.reason
    assert all(command[3:4] != ("start",) for command in runner.commands)


def test_production_start_existing_refuses_missing_application_image() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(1, "No such image"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start_existing().outcome is TerminalOutcome.FAILED
