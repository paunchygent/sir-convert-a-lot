"""Bind exact Sir GPU workloads to the shared Hemma transaction engine.

Purpose:
    Declare the Sir production, STT sidecar, and reserved-edge workloads,
    operate the production API and GPU worker as one workload, and build the
    shared workload registry and controller for the Hemma host.

Relationships:
    - Public surface for `hemma_workload_cli.py` and the operations tests;
      re-exports constants, `SirGpuInventory`, `ContainerWorkloadAdapter`,
      `CommandResult`, and `TOTAL_TIMEOUT_SECONDS`.
    - Constants live in `hemma_workload_constants.py`, GPU inventory in
      `hemma_workload_inventory.py`, and the sidecar adapter plus shared
      adapter helpers in `hemma_workload_container_adapter.py`.
    - Reuses bounded production startup helpers from
      `bounded_production_startup.py` for production readiness.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from repository_governance.hemma_workload import (
    AdapterResult,
    ExpectedState,
    HostLock,
    ReceiptStore,
    TerminalOutcome,
    WorkloadController,
    WorkloadDeclaration,
    WorkloadRegistry,
)

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
from scripts.sir_convert_a_lot.devops.hemma_workload_constants import (
    API_CONTAINER,
    CONTAINER_HEALTH_FORMAT,
    CONTAINER_STATE_FORMAT,
    DECLARED_GPU_CONTAINERS,
    DOCKER_COMMAND,
    GPU_CLAIM,
    GPU_WORKER_CONTAINER,
    HOST_IDENTITY,
    HOST_STATE_ROOT,
    LOCK_PATH,
    PRODUCT_RESOURCE_CLAIM,
    PRODUCTION_CONTAINERS,
    PRODUCTION_RESTART_POLICY,
    PRODUCTION_WORKLOAD_ID,
    RECEIPT_PATH,
    RESERVED_EDGE_CONTAINER,
    RESERVED_EDGE_WORKLOAD_ID,
    SIDECAR_READINESS_INTERVAL_SECONDS,
    SIDECAR_READINESS_TIMEOUT_SECONDS,
    SIDECAR_RESTART_POLICY,
    STT_CONTAINER,
    STT_WORKLOAD_ID,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_container_adapter import (
    ContainerWorkloadAdapter,
    _command_result,
    _container_state,
    _diagnostic,
    _state_category,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_inventory import (
    GpuProcess,
    SirGpuInventory,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_runtime import (
    CommandExecutor,
    CommandResult,
    CommandRunner,
)

__all__ = [
    "API_CONTAINER",
    "CONTAINER_HEALTH_FORMAT",
    "CONTAINER_STATE_FORMAT",
    "DECLARED_GPU_CONTAINERS",
    "DOCKER_COMMAND",
    "GPU_CLAIM",
    "GPU_WORKER_CONTAINER",
    "HOST_IDENTITY",
    "HOST_STATE_ROOT",
    "LOCK_PATH",
    "PRODUCTION_CONTAINERS",
    "PRODUCTION_RESTART_POLICY",
    "PRODUCTION_WORKLOAD_ID",
    "PRODUCT_RESOURCE_CLAIM",
    "RECEIPT_PATH",
    "RESERVED_EDGE_CONTAINER",
    "RESERVED_EDGE_WORKLOAD_ID",
    "SIDECAR_READINESS_INTERVAL_SECONDS",
    "SIDECAR_READINESS_TIMEOUT_SECONDS",
    "SIDECAR_RESTART_POLICY",
    "STT_CONTAINER",
    "STT_WORKLOAD_ID",
    "TOTAL_TIMEOUT_SECONDS",
    "CommandExecutor",
    "CommandResult",
    "CommandRunner",
    "ContainerWorkloadAdapter",
    "GpuProcess",
    "ProductionWorkloadAdapter",
    "SirGpuInventory",
    "sir_workload_controller",
    "sir_workload_registry",
]


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


def sir_workload_registry(
    *, runner: CommandExecutor | None = None, project_root: Path | None = None
) -> WorkloadRegistry:
    command_runner = runner or CommandRunner()
    root = project_root or Path.cwd()
    production_conflicts = frozenset({STT_WORKLOAD_ID})
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
                frozenset({PRODUCTION_WORKLOAD_ID}),
                ContainerWorkloadAdapter(STT_WORKLOAD_ID, STT_CONTAINER, command_runner),
                frozenset({TerminalOutcome.SUCCEEDED}),
            ),
            WorkloadDeclaration(
                RESERVED_EDGE_WORKLOAD_ID,
                (RESERVED_EDGE_CONTAINER,),
                (),
                frozenset({PRODUCT_RESOURCE_CLAIM}),
                frozenset(),
                ContainerWorkloadAdapter(
                    RESERVED_EDGE_WORKLOAD_ID,
                    RESERVED_EDGE_CONTAINER,
                    command_runner,
                ),
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
