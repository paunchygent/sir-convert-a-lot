"""Tests for the Sir STT sidecar container workload adapter.

Purpose:
    Check that `ContainerWorkloadAdapter` starts existing sidecar containers
    against their declared images and reports status and bounded readiness.

Relationships:
    - Exercises `scripts/sir_convert_a_lot/devops/hemma_workload_container_adapter.py`
      through `hemma_workload.py`.
"""

import subprocess
from pathlib import Path

import pytest
from repository_governance.hemma_workload import ExpectedState, TerminalOutcome

from scripts.sir_convert_a_lot.devops import hemma_workload
from tests.sir_convert_a_lot.operations.hemma_workload_fakes import QueueRunner


class CommandMapRunner:
    def __init__(self, results: dict[tuple[str, ...], hemma_workload.CommandResult]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        self.commands.append(argv)
        try:
            return self.results[argv]
        except KeyError as error:
            raise AssertionError(f"unexpected command: {argv}") from error


def _sidecar_adapter(
    runner: QueueRunner, project_root: Path
) -> hemma_workload.ContainerWorkloadAdapter:
    return hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID,
        hemma_workload.STT_CONTAINER,
        runner,
        project_root=project_root,
    )


def _sidecar_compose_query(project_root: Path) -> tuple[str, ...]:
    return (
        *hemma_workload.DOCKER_COMMAND,
        "compose",
        "--env-file",
        str(project_root / ".env"),
        "--project-directory",
        str(project_root),
        "-f",
        str(project_root / "compose.yaml"),
        "config",
        "--no-env-resolution",
        "--images",
        hemma_workload.STT_CONTAINER,
    )


def test_container_start_existing_starts_matching_declared_image(tmp_path: Path) -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            hemma_workload.CommandResult(0, "sir-convert-a-lot-stt-sidecar:shift-check\n"),
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    adapter = _sidecar_adapter(runner, tmp_path)

    assert adapter.start_existing().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[1] == _sidecar_compose_query(tmp_path)
    assert runner.commands[2] == (
        *hemma_workload.DOCKER_COMMAND,
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        "sir-convert-a-lot-stt-sidecar:shift-check",
    )
    assert runner.commands[-1] == (
        *hemma_workload.DOCKER_COMMAND,
        "start",
        hemma_workload.STT_CONTAINER,
    )


def test_container_start_existing_uses_configured_compose_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "deploy" / "prod.env"
    env_file.parent.mkdir()
    env_file.write_text("SIR_CONVERT_A_LOT_STT_SIDECAR_IMAGE_TAG=shift-check\n")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_COMPOSE_ENV_FILE", str(env_file))
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            hemma_workload.CommandResult(0, "sir-convert-a-lot-stt-sidecar:shift-check\n"),
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    adapter = _sidecar_adapter(runner, tmp_path)

    assert adapter.start_existing().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[1] == (
        *hemma_workload.DOCKER_COMMAND,
        "compose",
        "--env-file",
        str(env_file),
        "--project-directory",
        str(tmp_path),
        "-f",
        str(tmp_path / "compose.yaml"),
        "config",
        "--no-env-resolution",
        "--images",
        hemma_workload.STT_CONTAINER,
    )


def test_container_start_existing_refuses_stale_declared_image(tmp_path: Path) -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sha256:old\n"),
            hemma_workload.CommandResult(0, "sir-convert-a-lot-stt-sidecar:shift-check\n"),
            hemma_workload.CommandResult(0, "sha256:new\n"),
        ]
    )
    adapter = _sidecar_adapter(runner, tmp_path)

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "stale sidecar image" in result.reason
    assert all(command[3:4] != ("start",) for command in runner.commands)


def test_container_start_existing_refuses_absent_container(tmp_path: Path) -> None:
    runner = QueueRunner([hemma_workload.CommandResult(1, "No such object")])
    adapter = _sidecar_adapter(runner, tmp_path)

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "absent" in result.reason


def test_container_start_existing_refuses_absent_declared_image(tmp_path: Path) -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            hemma_workload.CommandResult(0, "sir-convert-a-lot-stt-sidecar:local\n"),
            hemma_workload.CommandResult(1, "No such image"),
        ]
    )
    adapter = _sidecar_adapter(runner, tmp_path)

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "declared sidecar image" in result.reason
    assert all(command[3:4] != ("start",) for command in runner.commands)


@pytest.mark.parametrize(
    "query_result",
    [
        hemma_workload.CommandResult(1, "", "compose config failed"),
        hemma_workload.CommandResult(0, ""),
        hemma_workload.CommandResult(0, "  \n\n"),
        hemma_workload.CommandResult(
            0, "sir-convert-a-lot-stt-sidecar:a\nsir-convert-a-lot-stt-sidecar:b\n"
        ),
    ],
)
def test_container_start_existing_refuses_unresolved_compose_image(
    tmp_path: Path, query_result: hemma_workload.CommandResult
) -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            query_result,
        ]
    )
    adapter = _sidecar_adapter(runner, tmp_path)

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "exactly one" in result.reason
    assert len(runner.commands) == 2
    assert all(command[3:4] != ("start",) for command in runner.commands)


@pytest.mark.parametrize(
    ("identity", "container"),
    [
        (hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER),
    ],
)
def test_sidecars_use_exact_container_commands_and_declared_health(
    identity: str, container: str
) -> None:
    assert hemma_workload.DOCKER_COMMAND == ("sudo", "-n", "docker")
    runner = CommandMapRunner(
        {
            (*hemma_workload.DOCKER_COMMAND, "start", container): hemma_workload.CommandResult(
                0, ""
            ),
            (*hemma_workload.DOCKER_COMMAND, "stop", container): hemma_workload.CommandResult(
                0, ""
            ),
            (
                *hemma_workload.DOCKER_COMMAND,
                "inspect",
                "--format",
                hemma_workload.CONTAINER_STATE_FORMAT,
                container,
            ): hemma_workload.CommandResult(0, "running\tno\n"),
            (
                *hemma_workload.DOCKER_COMMAND,
                "inspect",
                "--format",
                hemma_workload.CONTAINER_HEALTH_FORMAT,
                container,
            ): hemma_workload.CommandResult(0, "healthy\n"),
        }
    )
    adapter = hemma_workload.ContainerWorkloadAdapter(identity, container, runner)

    assert adapter.start().outcome is TerminalOutcome.SUCCEEDED
    assert adapter.stop().outcome is TerminalOutcome.SUCCEEDED
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.SUCCEEDED
    assert adapter.readiness().outcome is TerminalOutcome.SUCCEEDED
    assert all("compose" not in command and "--build" not in command for command in runner.commands)


def test_sidecar_readiness_refuses_missing_declared_health() -> None:
    runner = CommandMapRunner(
        {
            (
                *hemma_workload.DOCKER_COMMAND,
                "inspect",
                "--format",
                hemma_workload.CONTAINER_HEALTH_FORMAT,
                hemma_workload.STT_CONTAINER,
            ): hemma_workload.CommandResult(0, "no-healthcheck\n")
        }
    )
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER, runner
    )

    assert adapter.readiness().outcome is TerminalOutcome.DEPENDENCY_UNHEALTHY


def test_sidecar_status_enforces_restart_policy_when_stopped() -> None:
    runner = QueueRunner([hemma_workload.CommandResult(0, "exited\tunless-stopped\n")])
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER, runner
    )

    assert adapter.status(ExpectedState.STOPPED).outcome is TerminalOutcome.FAILED


def test_sidecar_readiness_polls_starting_until_healthy() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "starting\n"),
            hemma_workload.CommandResult(0, "healthy\n"),
        ]
    )
    sleeps: list[float] = []
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID,
        hemma_workload.STT_CONTAINER,
        runner,
        monotonic=lambda: 0.0,
        sleeper=sleeps.append,
        readiness_timeout_seconds=5.0,
        readiness_interval_seconds=1.0,
    )

    assert adapter.readiness().outcome is TerminalOutcome.SUCCEEDED
    assert sleeps == [1.0]
    assert len(runner.commands) == 2


def test_sidecar_starting_health_returns_typed_timeout() -> None:
    times = iter((0.0, 2.0))
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID,
        hemma_workload.STT_CONTAINER,
        QueueRunner([hemma_workload.CommandResult(0, "starting\n")]),
        monotonic=lambda: next(times),
        sleeper=lambda seconds: None,
        readiness_timeout_seconds=1.0,
        readiness_interval_seconds=0.0,
    )

    assert adapter.readiness().outcome is TerminalOutcome.TIMED_OUT


def test_sidecar_operations_normalize_subprocess_timeouts() -> None:
    class TimeoutRunner:
        def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
            raise subprocess.TimeoutExpired(argv, 1)

    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID,
        hemma_workload.STT_CONTAINER,
        TimeoutRunner(),
    )

    assert adapter.start().outcome is TerminalOutcome.TIMED_OUT
    assert adapter.stop().outcome is TerminalOutcome.TIMED_OUT
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.TIMED_OUT
    assert adapter.readiness().outcome is TerminalOutcome.TIMED_OUT
