import subprocess
from pathlib import Path

import pytest
from repository_governance.hemma_workload import (
    ExpectedState,
    TerminalOutcome,
    WorkloadController,
    WorkloadTransactionError,
)

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


class StatefulRunner:
    def __init__(self) -> None:
        self.running = {hemma_workload.STT_CONTAINER}
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        self.commands.append(argv)
        if argv == (*hemma_workload.DOCKER_COMMAND, "ps", "--format", "{{.Names}}"):
            return hemma_workload.CommandResult(
                0, "".join(f"{name}\n" for name in sorted(self.running))
            )
        if argv == ("rocm-smi", "--showpids", "--json"):
            return hemma_workload.CommandResult(0, "")
        if argv[:4] == (*hemma_workload.DOCKER_COMMAND, "top"):
            return hemma_workload.CommandResult(0, "PID\n")
        if argv[:4] == (*hemma_workload.DOCKER_COMMAND, "stop"):
            self.running.remove(argv[4])
            return hemma_workload.CommandResult(0, "")
        if argv[:4] == (*hemma_workload.DOCKER_COMMAND, "start"):
            self.running.add(argv[4])
            return hemma_workload.CommandResult(0, "")
        if argv == ("pdm", "run", "prod-start-bounded"):
            self.running.update(hemma_workload.PRODUCTION_CONTAINERS)
            return hemma_workload.CommandResult(0, "outcome=succeeded\n")
        if argv[:3] == ("pdm", "run", "prod-stop"):
            self.running.difference_update(hemma_workload.PRODUCTION_CONTAINERS)
            return hemma_workload.CommandResult(0, "")
        if argv[:6] == (
            *hemma_workload.DOCKER_COMMAND,
            "inspect",
            "--format",
            hemma_workload.CONTAINER_STATE_FORMAT,
        ):
            state = "running" if argv[6] in self.running else "exited"
            restart = (
                hemma_workload.PRODUCTION_RESTART_POLICY
                if argv[6] in hemma_workload.PRODUCTION_CONTAINERS
                else hemma_workload.SIDECAR_RESTART_POLICY
            )
            return hemma_workload.CommandResult(0, f"{state}\t{restart}\n")
        if argv[:6] == (
            *hemma_workload.DOCKER_COMMAND,
            "inspect",
            "--format",
            hemma_workload.CONTAINER_HEALTH_FORMAT,
        ):
            return hemma_workload.CommandResult(0, "healthy\n")
        raise AssertionError(f"unexpected command: {argv}")


def test_registry_declares_sir_gpu_workloads_and_passive_reserved_edge() -> None:
    registry = hemma_workload.sir_workload_registry(
        runner=QueueRunner([]), project_root=Path("/srv/sir")
    )

    assert registry.host_identity == "hemma"
    assert registry.identities == frozenset(
        {
            hemma_workload.PRODUCTION_WORKLOAD_ID,
            hemma_workload.STT_WORKLOAD_ID,
            hemma_workload.QWEN_WORKLOAD_ID,
            hemma_workload.RESERVED_EDGE_WORKLOAD_ID,
        }
    )
    production = registry.declaration(hemma_workload.PRODUCTION_WORKLOAD_ID)
    stt = registry.declaration(hemma_workload.STT_WORKLOAD_ID)
    qwen = registry.declaration(hemma_workload.QWEN_WORKLOAD_ID)
    reserved_edge = registry.declaration(hemma_workload.RESERVED_EDGE_WORKLOAD_ID)
    assert production.service_identities == (
        hemma_workload.API_CONTAINER,
        hemma_workload.GPU_WORKER_CONTAINER,
    )
    assert stt.service_identities == (hemma_workload.STT_CONTAINER,)
    assert qwen.service_identities == (hemma_workload.QWEN_CONTAINER,)
    assert reserved_edge.service_identities == (hemma_workload.RESERVED_EDGE_CONTAINER,)
    for declaration in (production, stt, qwen):
        assert declaration.resource_claims == frozenset({"gpu:amdgpu"})
        assert declaration.dependencies == ()
        assert declaration.accepted_terminal_outcomes == frozenset({TerminalOutcome.SUCCEEDED})
    assert reserved_edge.resource_claims == frozenset({hemma_workload.PRODUCT_RESOURCE_CLAIM})
    assert reserved_edge.dependencies == ()
    assert reserved_edge.conflicts == frozenset()
    assert reserved_edge.accepted_terminal_outcomes == frozenset({TerminalOutcome.SUCCEEDED})
    assert hemma_workload.RESERVED_EDGE_CONTAINER not in hemma_workload.PRODUCTION_CONTAINERS
    assert hemma_workload.RESERVED_EDGE_CONTAINER not in hemma_workload.DECLARED_GPU_CONTAINERS
    assert production.conflicts == frozenset(
        {hemma_workload.STT_WORKLOAD_ID, hemma_workload.QWEN_WORKLOAD_ID}
    )
    assert stt.conflicts == frozenset(
        {hemma_workload.PRODUCTION_WORKLOAD_ID, hemma_workload.QWEN_WORKLOAD_ID}
    )
    assert qwen.conflicts == frozenset(
        {hemma_workload.PRODUCTION_WORKLOAD_ID, hemma_workload.STT_WORKLOAD_ID}
    )


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
    assert runner.commands == [("pdm", "run", "prod-start-bounded")]
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
        lambda runner, *, docker_prefix: calls.append(
            ("worker", " ".join(docker_prefix))
        ),
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


def test_controller_uses_public_provider_and_owner_state_constants(tmp_path: Path) -> None:
    controller = hemma_workload.sir_workload_controller(
        runner=QueueRunner([]), project_root=Path("/srv/sir"), state_root=tmp_path
    )

    assert isinstance(controller, WorkloadController)
    assert hemma_workload.HOST_STATE_ROOT == Path("/var/lib/hemma/workload-switch")
    assert hemma_workload.RECEIPT_PATH == Path("/var/lib/hemma/workload-switch/active-receipt.json")
    assert hemma_workload.LOCK_PATH == Path("/var/lib/hemma/workload-switch/active.lock")
    assert not (tmp_path / "active-receipt.json").exists()
    assert not (tmp_path / "active.lock").exists()


def test_provider_controller_refuses_unknown_consumer_before_transaction(tmp_path: Path) -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sir_convert_unknown_gpu\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    controller = hemma_workload.sir_workload_controller(
        runner=runner, project_root=Path("/srv/sir"), state_root=tmp_path
    )

    with pytest.raises(WorkloadTransactionError, match="unknown consumers require declaration"):
        controller.start(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-unknown")
    assert not (tmp_path / "active-receipt.json").exists()


def test_shared_controller_restores_only_receipted_conflict_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = StatefulRunner()
    monkeypatch.setattr(hemma_workload, "_repository_head", lambda bounded: "a" * 40)
    monkeypatch.setattr(
        hemma_workload,
        "_poll_ready",
        lambda bounded, *, head, docker_prefix: None,
    )
    monkeypatch.setattr(
        hemma_workload,
        "_prove_gpu_readiness",
        lambda bounded, *, docker_prefix: None,
    )
    controller = hemma_workload.sir_workload_controller(
        runner=runner, project_root=Path("/srv/sir"), state_root=tmp_path
    )

    started = controller.start(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-restore")
    assert started.outcome is TerminalOutcome.SUCCEEDED
    assert runner.running == set(hemma_workload.PRODUCTION_CONTAINERS)

    stopped = controller.stop(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-restore")
    assert stopped.outcome is TerminalOutcome.SUCCEEDED
    assert runner.running == {hemma_workload.STT_CONTAINER}
    assert (
        *hemma_workload.DOCKER_COMMAND,
        "start",
        hemma_workload.QWEN_CONTAINER,
    ) not in runner.commands
    assert not (tmp_path / "active-receipt.json").exists()
