"""Bind exact Sir GPU workloads to the shared Hemma transaction engine."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from repository_governance.hemma_workload import (
    AdapterResult,
    ExpectedState,
    HostLock,
    InventoryInspectionError,
    InventorySnapshot,
    ReceiptStore,
    TerminalOutcome,
    WorkloadController,
    WorkloadDeclaration,
    WorkloadRegistry,
)
from repository_governance.retained_context.json_contract import JsonValue, strict_pairs

from scripts.sir_convert_a_lot.devops.bounded_production_startup import (
    TOTAL_TIMEOUT_SECONDS,
    _poll_ready,
    _prove_gpu_readiness,
    _repository_head,
)
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    CommandRunner as BoundedCommandRunner,
)
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    StartupFailure,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_runtime import (
    CommandExecutor,
    CommandResult,
    CommandRunner,
)

HOST_IDENTITY = "hemma"
GPU_CLAIM = "gpu:amdgpu"
PRODUCTION_WORKLOAD_ID = "sir-production"
STT_WORKLOAD_ID = "sir-stt-sidecar"
QWEN_WORKLOAD_ID = "sir-qwen-answer-key"
API_CONTAINER = "sir_convert_a_lot_prod"
GPU_WORKER_CONTAINER = "sir_convert_a_lot_gpu_worker"
STT_CONTAINER = "sir_convert_a_lot_stt_sidecar"
QWEN_CONTAINER = "sir_convert_qwen_answer_key"
RESERVED_EDGE_CONTAINER = "sir_convert_a_lot_public_reserved"
PRODUCTION_CONTAINERS = (API_CONTAINER, GPU_WORKER_CONTAINER)
DECLARED_GPU_CONTAINERS = (GPU_WORKER_CONTAINER, STT_CONTAINER, QWEN_CONTAINER)
HOST_STATE_ROOT = Path("/var/lib/hemma/workload-switch")
RECEIPT_PATH = HOST_STATE_ROOT / "active-receipt.json"
LOCK_PATH = HOST_STATE_ROOT / "active.lock"
CONTAINER_STATE_FORMAT = "{{.State.Status}}\t{{.HostConfig.RestartPolicy.Name}}"
CONTAINER_HEALTH_FORMAT = (
    "{{if .Config.Healthcheck}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}"
)
SIDECAR_READINESS_TIMEOUT_SECONDS = 15 * 60.0
SIDECAR_READINESS_INTERVAL_SECONDS = 2.0
PRODUCTION_RESTART_POLICY = "no"
SIDECAR_RESTART_POLICY = "unless-stopped"
DOCKER_COMMAND = ("sudo", "-n", "docker")


class ProductionWorkloadAdapter:
    """Treat the production API and GPU worker as one exact workload."""

    def __init__(self, runner: CommandExecutor, project_root: Path) -> None:
        self._runner = runner
        self._project_root = project_root

    def start(self) -> AdapterResult:
        try:
            result = self._runner.run(("pdm", "run", "prod-start-bounded"))
            outcome = _terminal_outcome(result.stdout)
        except subprocess.TimeoutExpired as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.TIMED_OUT, str(error))
        except (OSError, ValueError) as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.FAILED, str(error))
        if outcome is TerminalOutcome.SUCCEEDED and result.returncode != 0:
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                TerminalOutcome.FAILED,
                "bounded production startup reported succeeded with a nonzero exit",
            )
        if outcome is not TerminalOutcome.SUCCEEDED and result.returncode == 0:
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                TerminalOutcome.FAILED,
                "bounded production startup reported failure with a zero exit",
            )
        return AdapterResult(
            PRODUCTION_WORKLOAD_ID,
            outcome,
            "" if outcome is TerminalOutcome.SUCCEEDED else _diagnostic(result),
        )

    def stop(self) -> AdapterResult:
        return _command_result(
            PRODUCTION_WORKLOAD_ID,
            self._runner,
            ("pdm", "run", "prod-stop", GPU_WORKER_CONTAINER, API_CONTAINER),
            "bounded production stop failed",
        )

    def status(self, expected: ExpectedState) -> AdapterResult:
        try:
            states = tuple(_container_state(self._runner, name) for name in PRODUCTION_CONTAINERS)
        except subprocess.TimeoutExpired as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.TIMED_OUT, str(error))
        except (OSError, ValueError) as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.REFUSED, str(error))
        if any(restart != PRODUCTION_RESTART_POLICY for _, restart in states):
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                TerminalOutcome.FAILED,
                f"production restart policy is not {PRODUCTION_RESTART_POLICY}",
            )
        categories = tuple(_state_category(state) for state, _ in states)
        if None in categories or categories[0] != categories[1]:
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                TerminalOutcome.REFUSED,
                "production API and GPU worker have a mixed or transitional state",
            )
        running = categories[0] == "running"
        if expected is ExpectedState.RUNNING:
            if running:
                return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.SUCCEEDED)
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                TerminalOutcome.FAILED,
                "production API and GPU worker are not running",
            )
        if running:
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                TerminalOutcome.FAILED,
                "production API and GPU worker are not stopped",
            )
        return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.SUCCEEDED)

    def readiness(self) -> AdapterResult:
        runner = BoundedCommandRunner(
            project_root=self._project_root,
            deadline=time.monotonic() + TOTAL_TIMEOUT_SECONDS,
        )
        try:
            head = _repository_head(runner)
            _poll_ready(runner, head=head, docker_prefix=DOCKER_COMMAND)
            _prove_gpu_readiness(runner, docker_prefix=DOCKER_COMMAND)
        except subprocess.TimeoutExpired as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.TIMED_OUT, str(error))
        except StartupFailure as error:
            try:
                outcome = _known_outcome(error.outcome)
            except ValueError:
                outcome = TerminalOutcome.FAILED
            return AdapterResult(
                PRODUCTION_WORKLOAD_ID,
                outcome,
                str(error),
            )
        except (OSError, ValueError, json.JSONDecodeError, SystemExit) as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.FAILED, str(error))
        return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.SUCCEEDED)


class ContainerWorkloadAdapter:
    """Operate one exact pre-existing sidecar and require declared Docker health."""

    def __init__(
        self,
        identity: str,
        container: str,
        runner: CommandExecutor,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        readiness_timeout_seconds: float = SIDECAR_READINESS_TIMEOUT_SECONDS,
        readiness_interval_seconds: float = SIDECAR_READINESS_INTERVAL_SECONDS,
    ) -> None:
        if readiness_timeout_seconds <= 0 or readiness_interval_seconds < 0:
            raise ValueError(
                "sidecar readiness requires a positive timeout and nonnegative interval"
            )
        self._identity = identity
        self._container = container
        self._runner = runner
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._readiness_timeout_seconds = readiness_timeout_seconds
        self._readiness_interval_seconds = readiness_interval_seconds

    def start(self) -> AdapterResult:
        return _command_result(
            self._identity,
            self._runner,
            (*DOCKER_COMMAND, "start", self._container),
            f"declared container {self._container} start failed",
        )

    def stop(self) -> AdapterResult:
        return _command_result(
            self._identity,
            self._runner,
            (*DOCKER_COMMAND, "stop", self._container),
            f"declared container {self._container} stop failed",
        )

    def status(self, expected: ExpectedState) -> AdapterResult:
        try:
            state, restart = _container_state(self._runner, self._container)
        except subprocess.TimeoutExpired as error:
            return AdapterResult(self._identity, TerminalOutcome.TIMED_OUT, str(error))
        except (OSError, ValueError) as error:
            return AdapterResult(self._identity, TerminalOutcome.REFUSED, str(error))
        if restart != SIDECAR_RESTART_POLICY:
            return AdapterResult(
                self._identity,
                TerminalOutcome.FAILED,
                f"container {self._container} restart policy is not {SIDECAR_RESTART_POLICY}",
            )
        category = _state_category(state)
        if category is None:
            return AdapterResult(
                self._identity,
                TerminalOutcome.REFUSED,
                f"container {self._container} has transitional state {state}",
            )
        running = category == "running"
        if running is (expected is ExpectedState.RUNNING):
            return AdapterResult(self._identity, TerminalOutcome.SUCCEEDED)
        return AdapterResult(
            self._identity,
            TerminalOutcome.FAILED,
            f"container {self._container} is not {expected.value}",
        )

    def readiness(self) -> AdapterResult:
        deadline = self._monotonic() + self._readiness_timeout_seconds
        while True:
            try:
                result = self._runner.run(
                    (
                        *DOCKER_COMMAND,
                        "inspect",
                        "--format",
                        CONTAINER_HEALTH_FORMAT,
                        self._container,
                    )
                )
            except subprocess.TimeoutExpired as error:
                return AdapterResult(self._identity, TerminalOutcome.TIMED_OUT, str(error))
            except OSError as error:
                return AdapterResult(self._identity, TerminalOutcome.FAILED, str(error))
            if result.returncode != 0:
                return AdapterResult(
                    self._identity,
                    TerminalOutcome.FAILED,
                    f"cannot inspect declared container {self._container} readiness",
                )
            health = result.stdout.strip()
            if health == "healthy":
                return AdapterResult(self._identity, TerminalOutcome.SUCCEEDED)
            if health != "starting":
                return AdapterResult(
                    self._identity,
                    TerminalOutcome.DEPENDENCY_UNHEALTHY,
                    f"container {self._container} health is {health or 'unreported'}",
                )
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                return AdapterResult(
                    self._identity,
                    TerminalOutcome.TIMED_OUT,
                    f"container {self._container} readiness timed out",
                )
            self._sleeper(min(self._readiness_interval_seconds, remaining))


@dataclass(frozen=True)
class GpuProcess:
    pid: int
    vram_bytes: int


class SirGpuInventory:
    """Inventory exact Sir GPU workloads and fail closed on unknown consumers."""

    def __init__(self, runner: CommandExecutor) -> None:
        self._runner = runner

    def inspect(self, resource_claims: frozenset[str]) -> InventorySnapshot:
        try:
            if resource_claims != frozenset({GPU_CLAIM}):
                raise ValueError(f"Sir inventory cannot inspect claims {sorted(resource_claims)}")
            running = _running_containers(self._runner)
            production_members = frozenset(PRODUCTION_CONTAINERS) & running
            if production_members and production_members != frozenset(PRODUCTION_CONTAINERS):
                raise ValueError("production API and GPU worker have a partial running state")
            workloads: set[str] = set()
            if production_members:
                workloads.add(PRODUCTION_WORKLOAD_ID)
            if STT_CONTAINER in running:
                workloads.add(STT_WORKLOAD_ID)
            if QWEN_CONTAINER in running:
                workloads.add(QWEN_WORKLOAD_ID)
            declared_services = frozenset(
                (*PRODUCTION_CONTAINERS, STT_CONTAINER, QWEN_CONTAINER, RESERVED_EDGE_CONTAINER)
            )
            unknown = {
                f"container {name}"
                for name in running - declared_services
                if name.startswith(("sir_convert", "sir-convert"))
            }
            owned_pids = _declared_container_pids(self._runner, running)
            unknown.update(
                f"PID {process.pid}"
                for process in _rocm_processes(self._runner)
                if process.vram_bytes > 0 and process.pid not in owned_pids
            )
            return InventorySnapshot(frozenset(workloads), tuple(sorted(unknown)))
        except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
            raise InventoryInspectionError(str(error)) from error


def sir_workload_registry(
    *, runner: CommandExecutor | None = None, project_root: Path | None = None
) -> WorkloadRegistry:
    command_runner = runner or CommandRunner()
    root = project_root or Path.cwd()
    production_conflicts = frozenset({STT_WORKLOAD_ID, QWEN_WORKLOAD_ID})
    registry = WorkloadRegistry(
        HOST_IDENTITY,
        (
            WorkloadDeclaration(
                PRODUCTION_WORKLOAD_ID,
                PRODUCTION_CONTAINERS,
                (),
                frozenset({GPU_CLAIM}),
                production_conflicts,
                ProductionWorkloadAdapter(command_runner, root),
                frozenset({TerminalOutcome.SUCCEEDED}),
            ),
            WorkloadDeclaration(
                STT_WORKLOAD_ID,
                (STT_CONTAINER,),
                (),
                frozenset({GPU_CLAIM}),
                frozenset({PRODUCTION_WORKLOAD_ID, QWEN_WORKLOAD_ID}),
                ContainerWorkloadAdapter(STT_WORKLOAD_ID, STT_CONTAINER, command_runner),
                frozenset({TerminalOutcome.SUCCEEDED}),
            ),
            WorkloadDeclaration(
                QWEN_WORKLOAD_ID,
                (QWEN_CONTAINER,),
                (),
                frozenset({GPU_CLAIM}),
                frozenset({PRODUCTION_WORKLOAD_ID, STT_WORKLOAD_ID}),
                ContainerWorkloadAdapter(QWEN_WORKLOAD_ID, QWEN_CONTAINER, command_runner),
                frozenset({TerminalOutcome.SUCCEEDED}),
            ),
        ),
    )
    registry.validate()
    return registry


def sir_workload_controller(
    *,
    runner: CommandExecutor | None = None,
    project_root: Path | None = None,
    state_root: Path = HOST_STATE_ROOT,
) -> WorkloadController:
    command_runner = runner or CommandRunner()
    return WorkloadController(
        sir_workload_registry(runner=command_runner, project_root=project_root),
        SirGpuInventory(command_runner),
        ReceiptStore(state_root / RECEIPT_PATH.name),
        HostLock(state_root / LOCK_PATH.name),
    )


def _command_result(
    identity: str,
    runner: CommandExecutor,
    argv: tuple[str, ...],
    failure_reason: str,
) -> AdapterResult:
    try:
        result = runner.run(argv)
    except subprocess.TimeoutExpired as error:
        return AdapterResult(identity, TerminalOutcome.TIMED_OUT, str(error))
    except OSError as error:
        return AdapterResult(identity, TerminalOutcome.FAILED, str(error))
    if result.returncode == 0:
        return AdapterResult(identity, TerminalOutcome.SUCCEEDED)
    return AdapterResult(
        identity,
        TerminalOutcome.FAILED,
        f"{failure_reason}: {_diagnostic(result)}",
    )


def _terminal_outcome(stdout: str) -> TerminalOutcome:
    output_lines = stdout.splitlines()
    outcome_lines = tuple(line for line in output_lines if line.startswith("outcome="))
    if not output_lines or len(outcome_lines) != 1 or outcome_lines[0] != output_lines[-1]:
        raise ValueError("bounded production startup must emit exactly one terminal outcome line")
    return _known_outcome(outcome_lines[0].removeprefix("outcome="))


def _known_outcome(value: str) -> TerminalOutcome:
    try:
        return TerminalOutcome(value)
    except ValueError as error:
        raise ValueError(f"unknown terminal outcome {value!r}") from error


def _diagnostic(result: CommandResult) -> str:
    return result.stderr.strip() or result.stdout.strip() or "no diagnostic"


def _container_state(runner: CommandExecutor, container: str) -> tuple[str, str]:
    result = runner.run((*DOCKER_COMMAND, "inspect", "--format", CONTAINER_STATE_FORMAT, container))
    if result.returncode != 0:
        raise ValueError(f"cannot inspect declared container {container}")
    fields = result.stdout.strip().split("\t")
    known_states = {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
    if len(fields) != 2 or fields[0] not in known_states:
        raise ValueError(f"declared container {container} has an unknown state record")
    return fields[0], fields[1]


def _running_containers(runner: CommandExecutor) -> frozenset[str]:
    result = runner.run((*DOCKER_COMMAND, "ps", "--format", "{{.Names}}"))
    if result.returncode != 0:
        raise ValueError("cannot inspect Docker running-container state")
    return frozenset(line for line in result.stdout.splitlines() if line)


def _state_category(state: str) -> str | None:
    if state == "running":
        return "running"
    if state in {"created", "exited"}:
        return "stopped"
    return None


def _rocm_processes(runner: CommandExecutor) -> tuple[GpuProcess, ...]:
    result = runner.run(("rocm-smi", "--showpids", "--json"))
    if result.returncode != 0:
        raise ValueError("cannot inspect current ROCm KFD process state")
    if not result.stdout.strip():
        return ()
    value: JsonValue = json.loads(result.stdout, object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError("ROCm KFD process payload must be a mapping")
    system = value.get("system")
    if not isinstance(system, dict):
        raise ValueError("ROCm KFD process payload has no system map")
    processes: list[GpuProcess] = []
    for key, record in system.items():
        if not isinstance(key, str) or not key.startswith("PID") or not key[3:].isdigit():
            raise ValueError("ROCm KFD process payload has an invalid PID key")
        if not isinstance(record, str):
            raise ValueError("ROCm KFD process payload has an invalid process record")
        fields = tuple(field.strip() for field in record.split(","))
        if len(fields) < 3 or not fields[2].isdigit():
            raise ValueError("ROCm KFD process payload has an invalid VRAM field")
        processes.append(GpuProcess(int(key[3:]), int(fields[2])))
    return tuple(processes)


def _declared_container_pids(runner: CommandExecutor, running: frozenset[str]) -> frozenset[int]:
    pids: set[int] = set()
    for container in DECLARED_GPU_CONTAINERS:
        if container not in running:
            continue
        result = runner.run((*DOCKER_COMMAND, "top", container, "-eo", "pid"))
        if result.returncode != 0:
            raise ValueError(f"cannot inspect declared GPU container {container}")
        lines = result.stdout.splitlines()
        if not lines or lines[0].strip() != "PID":
            raise ValueError(f"declared GPU container {container} has malformed PID output")
        for value in lines[1:]:
            if not value.strip().isdigit():
                raise ValueError(f"declared GPU container {container} has malformed PID output")
            pids.add(int(value.strip()))
    return frozenset(pids)
