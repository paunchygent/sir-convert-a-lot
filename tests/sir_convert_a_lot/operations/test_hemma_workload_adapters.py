import pwd
import subprocess
from pathlib import Path

import pytest
from repository_governance.hemma_workload import ExpectedState, TerminalOutcome

from scripts.sir_convert_a_lot.devops import hemma_workload, hemma_workload_runtime


class QueueRunner:
    def __init__(self, results: list[hemma_workload.CommandResult]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        self.commands.append(argv)
        if not self.results:
            raise AssertionError(f"unexpected command: {argv}")
        return self.results.pop(0)


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


def _operator_root_worker(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sudo_user: str | None = "operator",
    sudo_uid: str | None = None,
) -> None:
    monkeypatch.setattr(hemma_workload.os, "geteuid", lambda: 0)
    if sudo_user is None:
        monkeypatch.delenv("SUDO_USER", raising=False)
    else:
        monkeypatch.setenv("SUDO_USER", sudo_user)
    if sudo_uid is None:
        monkeypatch.delenv("SUDO_UID", raising=False)
    else:
        monkeypatch.setenv("SUDO_UID", sudo_uid)
    entry = pwd.struct_passwd(("operator", "x", 1000, 1000, "", "/home/operator", "/bin/bash"))
    monkeypatch.setattr(hemma_workload.pwd, "getpwnam", lambda name: entry)
    monkeypatch.setattr(hemma_workload.pwd, "getpwuid", lambda uid: entry)


def test_root_worker_runs_bounded_startup_as_operator_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    runner = QueueRunner([hemma_workload.CommandResult(0, "outcome=succeeded\n")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start().outcome is TerminalOutcome.SUCCEEDED
    command = runner.commands[0]
    assert command[:4] == ("sudo", "-n", "-u", "operator")
    assert command[4] == "env"
    assert command[5].startswith("PATH=/home/operator/.local/bin:")
    assert command[-3:] == ("pdm", "run", "prod-workload-start")


def test_root_worker_falls_back_to_sudo_uid_for_operator_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch, sudo_user=None, sudo_uid="1000")
    runner = QueueRunner([hemma_workload.CommandResult(0, "outcome=succeeded\n")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[0][:4] == ("sudo", "-n", "-u", "operator")


def test_root_worker_runs_production_stop_as_operator_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch)
    runner = QueueRunner([hemma_workload.CommandResult(0, "")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.stop().outcome is TerminalOutcome.SUCCEEDED
    command = runner.commands[0]
    assert command[:3] == ("sudo", "-n", "-u")
    assert command[-5:-3] == ("pdm", "run")
    assert command[-3:] == (
        "prod-stop",
        hemma_workload.GPU_WORKER_CONTAINER,
        hemma_workload.API_CONTAINER,
    )


def test_root_worker_without_operator_identity_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch, sudo_user=None)
    monkeypatch.setattr(
        hemma_workload.pwd,
        "getpwnam",
        lambda name: pytest.fail("operator lookup without SUDO_USER"),
    )
    runner = QueueRunner([])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start().outcome is TerminalOutcome.FAILED
    assert adapter.stop().outcome is TerminalOutcome.FAILED
    assert runner.commands == []


@pytest.mark.parametrize(
    "stdout",
    ["", "outcome=succeeded\noutcome=succeeded\n", "outcome=succeeded\ntrailing\n", "noise\n"],
)
def test_production_start_refuses_nonterminal_or_ambiguous_outcome(stdout: str) -> None:
    adapter = hemma_workload.ProductionWorkloadAdapter(
        QueueRunner([hemma_workload.CommandResult(0, stdout)]), Path("/srv/sir")
    )

    assert adapter.start().outcome is TerminalOutcome.FAILED


def test_host_command_timeout_exceeds_task04_bounded_startup_timeout() -> None:
    assert (
        hemma_workload_runtime.HOST_COMMAND_TIMEOUT_SECONDS > hemma_workload.TOTAL_TIMEOUT_SECONDS
    )


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
