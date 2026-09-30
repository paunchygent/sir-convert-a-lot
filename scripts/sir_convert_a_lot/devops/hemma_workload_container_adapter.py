"""Docker sidecar adapter and shared adapter helpers for Sir Hemma workloads.

Purpose:
    Operate one exact pre-existing Sir sidecar container through start, stop,
    status, and Docker-health readiness, and own the command-result, diagnostic,
    and container-state helpers that every Sir workload adapter shares.

Relationships:
    - Imported by `hemma_workload.py`, which declares sidecar workloads with
      `ContainerWorkloadAdapter` and builds `ProductionWorkloadAdapter` on the
      shared helpers defined here.
    - Uses `hemma_workload_constants.py` for the privileged Docker prefix,
      inspect formats, readiness timeouts, and sidecar restart policy.
    - Runs host commands through `hemma_workload_runtime.CommandExecutor`.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable

from repository_governance.hemma_workload import (
    AdapterResult,
    ExpectedState,
    TerminalOutcome,
)

from scripts.sir_convert_a_lot.devops.hemma_workload_constants import (
    CONTAINER_HEALTH_FORMAT,
    CONTAINER_STATE_FORMAT,
    DOCKER_COMMAND,
    SIDECAR_READINESS_INTERVAL_SECONDS,
    SIDECAR_READINESS_TIMEOUT_SECONDS,
    SIDECAR_RESTART_POLICY,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_runtime import (
    CommandExecutor,
    CommandResult,
)


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


def _state_category(state: str) -> str | None:
    if state == "running":
        return "running"
    if state in {"created", "exited"}:
        return "stopped"
    return None
