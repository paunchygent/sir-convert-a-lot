import json
import subprocess

import pytest
from repository_governance.hemma_workload import (
    ExpectedState,
    InventoryInspectionError,
    TerminalOutcome,
)

from scripts.sir_convert_a_lot.devops import hemma_workload, hemma_workload_runtime


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


class SequenceRunner:
    def __init__(self, results: list[hemma_workload.CommandResult]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        self.commands.append(argv)
        if not self.results:
            raise AssertionError(f"unexpected command: {argv}")
        return self.results.pop(0)


def _inventory_runner(
    *, running: tuple[str, ...], rocm: str = "", pids: dict[str, tuple[int, ...]] | None = None
) -> CommandMapRunner:
    results = {
        (
            *hemma_workload.DOCKER_COMMAND,
            "ps",
            "--format",
            "{{.Names}}",
        ): hemma_workload.CommandResult(0, "".join(f"{name}\n" for name in running)),
        ("rocm-smi", "--showpids", "--json"): hemma_workload.CommandResult(0, rocm),
    }
    for container, values in (pids or {}).items():
        results[(*hemma_workload.DOCKER_COMMAND, "top", container, "-eo", "pid")] = (
            hemma_workload.CommandResult(0, "PID\n" + "".join(f"{value}\n" for value in values))
        )
    return CommandMapRunner(results)


@pytest.mark.parametrize(
    ("identity", "container"),
    [
        (hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER),
        (hemma_workload.QWEN_WORKLOAD_ID, hemma_workload.QWEN_CONTAINER),
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
            ): hemma_workload.CommandResult(0, "running\tunless-stopped\n"),
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
                hemma_workload.QWEN_CONTAINER,
            ): hemma_workload.CommandResult(0, "no-healthcheck\n")
        }
    )
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.QWEN_WORKLOAD_ID, hemma_workload.QWEN_CONTAINER, runner
    )

    assert adapter.readiness().outcome is TerminalOutcome.DEPENDENCY_UNHEALTHY


def test_sidecar_status_enforces_restart_policy_when_stopped() -> None:
    runner = SequenceRunner([hemma_workload.CommandResult(0, "exited\tno\n")])
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER, runner
    )

    assert adapter.status(ExpectedState.STOPPED).outcome is TerminalOutcome.FAILED


def test_sidecar_readiness_polls_starting_until_healthy() -> None:
    runner = SequenceRunner(
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
        hemma_workload.QWEN_WORKLOAD_ID,
        hemma_workload.QWEN_CONTAINER,
        SequenceRunner([hemma_workload.CommandResult(0, "starting\n")]),
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


def test_inventory_maps_exact_group_and_sidecars_with_blank_rocm_output() -> None:
    running = (
        hemma_workload.API_CONTAINER,
        hemma_workload.GPU_WORKER_CONTAINER,
        hemma_workload.STT_CONTAINER,
        hemma_workload.QWEN_CONTAINER,
    )
    runner = _inventory_runner(
        running=running,
        pids={
            hemma_workload.GPU_WORKER_CONTAINER: (),
            hemma_workload.STT_CONTAINER: (),
            hemma_workload.QWEN_CONTAINER: (),
        },
    )

    snapshot = hemma_workload.SirGpuInventory(runner).inspect(frozenset({hemma_workload.GPU_CLAIM}))

    assert snapshot.running_workloads == frozenset(
        {
            hemma_workload.PRODUCTION_WORKLOAD_ID,
            hemma_workload.STT_WORKLOAD_ID,
            hemma_workload.QWEN_WORKLOAD_ID,
        }
    )
    assert snapshot.unknown_consumers == ()


def test_inventory_refuses_partial_production_group() -> None:
    runner = _inventory_runner(running=(hemma_workload.API_CONTAINER,))

    with pytest.raises(InventoryInspectionError, match="partial running state"):
        hemma_workload.SirGpuInventory(runner).inspect(frozenset({hemma_workload.GPU_CLAIM}))


def test_inventory_timeout_fails_closed() -> None:
    class TimeoutRunner:
        def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
            raise subprocess.TimeoutExpired(argv, 1)

    with pytest.raises(InventoryInspectionError, match="timed out"):
        hemma_workload.SirGpuInventory(TimeoutRunner()).inspect(
            frozenset({hemma_workload.GPU_CLAIM})
        )


def test_inventory_reports_prefixed_container_and_unmapped_nonzero_vram_pid() -> None:
    rocm = json.dumps({"system": {"PID123": "python, card0, 4096"}})
    runner = _inventory_runner(running=("sir_convert_unknown_gpu",), rocm=rocm)

    snapshot = hemma_workload.SirGpuInventory(runner).inspect(frozenset({hemma_workload.GPU_CLAIM}))

    assert snapshot.unknown_consumers == ("PID 123", "container sir_convert_unknown_gpu")


def test_inventory_leaves_known_non_gpu_reserved_edge_outside_gpu_workloads() -> None:
    runner = _inventory_runner(running=(hemma_workload.RESERVED_EDGE_CONTAINER,))

    snapshot = hemma_workload.SirGpuInventory(runner).inspect(frozenset({hemma_workload.GPU_CLAIM}))

    assert snapshot.running_workloads == frozenset()
    assert snapshot.unknown_consumers == ()


def test_inventory_reports_reserved_edge_for_exact_product_claim() -> None:
    runner = _inventory_runner(running=(hemma_workload.RESERVED_EDGE_CONTAINER,))

    snapshot = hemma_workload.SirGpuInventory(runner).inspect(
        frozenset({hemma_workload.PRODUCT_RESOURCE_CLAIM})
    )

    assert snapshot.running_workloads == frozenset({hemma_workload.RESERVED_EDGE_WORKLOAD_ID})
    assert snapshot.unknown_consumers == ()


@pytest.mark.parametrize(
    "resource_claims",
    [
        frozenset(),
        frozenset({hemma_workload.GPU_CLAIM, hemma_workload.PRODUCT_RESOURCE_CLAIM}),
    ],
)
def test_inventory_refuses_nonexclusive_claim_sets(resource_claims: frozenset[str]) -> None:
    runner = _inventory_runner(running=())

    with pytest.raises(InventoryInspectionError, match="cannot inspect claims"):
        hemma_workload.SirGpuInventory(runner).inspect(resource_claims)


@pytest.mark.parametrize(
    "payload",
    ["[]", "{}", '{"system":{"bad":"python, card0, 1"}}', '{"system":'],
)
def test_inventory_raises_typed_error_for_malformed_rocm_payload(payload: str) -> None:
    runner = _inventory_runner(running=(), rocm=payload)

    with pytest.raises(InventoryInspectionError):
        hemma_workload.SirGpuInventory(runner).inspect(frozenset({hemma_workload.GPU_CLAIM}))


def test_inventory_maps_nonzero_vram_pid_to_exact_declared_gpu_container() -> None:
    rocm = json.dumps({"system": {"PID321": "python, card0, 8192"}})
    runner = _inventory_runner(
        running=(hemma_workload.STT_CONTAINER,),
        rocm=rocm,
        pids={hemma_workload.STT_CONTAINER: (321,)},
    )

    snapshot = hemma_workload.SirGpuInventory(runner).inspect(frozenset({hemma_workload.GPU_CLAIM}))

    assert snapshot.running_workloads == frozenset({hemma_workload.STT_WORKLOAD_ID})
    assert snapshot.unknown_consumers == ()
