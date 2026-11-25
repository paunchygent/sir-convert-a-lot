"""Declare exact Sir GPU workloads for the shared Hemma claim queue.

Purpose:
    Declare the Sir production and STT sidecar workloads and operate the
    production API and GPU worker as one workload. Claims, the controller and
    the GPU inventory belong to `hemma-services` in skill-repository.

Relationships:
    - The skill-repository product worker imports `sir_workload_declarations`
      from this module and runs the adapters; operators claim through
      `hemma-services claim|redeploy sir-production`.
    - Public surface for the operations tests; re-exports constants,
      `ContainerWorkloadAdapter`, `CommandResult`, and `TOTAL_TIMEOUT_SECONDS`.
    - Constants live in `hemma_workload_constants.py` and the sidecar adapter
      plus shared adapter helpers in `hemma_workload_container_adapter.py`.
    - Reuses bounded production startup helpers from
      `bounded_production_startup.py` for production readiness.
"""

from __future__ import annotations

import json
import os
import pwd
import subprocess
import time
from pathlib import Path

from repository_governance.hemma_workload import (
    AdapterResult,
    ClaimKind,
    ExpectedState,
    TerminalOutcome,
    WorkloadDeclaration,
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
    DOCKER_COMMAND,
    GPU_CLAIM,
    GPU_WORKER_CONTAINER,
    PRODUCTION_CONTAINERS,
    PRODUCTION_RESTART_POLICY,
    PRODUCTION_WORKLOAD_ID,
    SIDECAR_READINESS_INTERVAL_SECONDS,
    SIDECAR_READINESS_TIMEOUT_SECONDS,
    SIDECAR_RESTART_POLICY,
    STT_CONTAINER,
    STT_WORKLOAD_ID,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_container_adapter import (
    ContainerWorkloadAdapter,
    _command_result,
    _container_image_id,
    _container_state,
    _diagnostic,
    _state_category,
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
    "DOCKER_COMMAND",
    "GPU_CLAIM",
    "GPU_WORKER_CONTAINER",
    "PRODUCTION_CONTAINERS",
    "PRODUCTION_RESTART_POLICY",
    "PRODUCTION_WORKLOAD_ID",
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
    "ProductionWorkloadAdapter",
    "sir_workload_declarations",
]


def _operator_account() -> pwd.struct_passwd | None:
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            return pwd.getpwnam(sudo_user)
        except KeyError:
            return None
    sudo_uid = os.environ.get("SUDO_UID")
    if sudo_uid:
        try:
            return pwd.getpwuid(int(sudo_uid))
        except (KeyError, ValueError):
            return None
    return None


def _operator_command(argv: tuple[str, ...]) -> tuple[str, ...] | None:
    """Wrap one argv so it executes as the invoking operator account.

    The root worker that `hemma-services` launches runs the production adapter,
    but the bounded production paths must read the operator's agent-secrets
    store, so under effective UID 0 the command re-enters the invoking sudo
    user's account with a PATH that can resolve that user's installed tools.
    """
    if os.geteuid() != 0:
        return argv
    account = _operator_account()
    if account is None:
        return None
    operator_path = f"{account.pw_dir}/.local/bin:{os.environ.get('PATH', '')}"
    return (
        "sudo",
        "-n",
        "-u",
        account.pw_name,
        "env",
        f"PATH={operator_path}",
        *argv,
    )


def _operator_pdm_command(*arguments: str) -> tuple[str, ...] | None:
    """Build one `pdm run` command that executes as the operator account."""
    return _operator_command(("pdm", "run", *arguments))


def _missing_operator_account_result() -> AdapterResult:
    return AdapterResult(
        PRODUCTION_WORKLOAD_ID,
        TerminalOutcome.FAILED,
        "production commands require the invoking operator account",
    )


class ProductionWorkloadAdapter:
    """Treat the production API and GPU worker as one exact workload."""

    def __init__(self, runner: CommandExecutor, project_root: Path) -> None:
        self._runner = runner
        self._project_root = project_root

    def start(self) -> AdapterResult:
        command = _operator_pdm_command("prod-workload-start")
        if command is None:
            return _missing_operator_account_result()
        try:
            result = self._runner.run(command)
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

    def start_existing(self) -> AdapterResult:
        """Start the existing API and GPU worker only; never create or replace them."""
        try:
            expected_image = _application_image_id(self._runner, self._project_root)
            for name in PRODUCTION_CONTAINERS:
                image_id = _container_image_id(self._runner, name)
                if image_id is None:
                    return AdapterResult(
                        PRODUCTION_WORKLOAD_ID,
                        TerminalOutcome.FAILED,
                        f"production container {name} is absent",
                    )
                if image_id != expected_image:
                    return AdapterResult(
                        PRODUCTION_WORKLOAD_ID,
                        TerminalOutcome.FAILED,
                        f"production container {name} has a stale application image",
                    )
        except subprocess.TimeoutExpired as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.TIMED_OUT, str(error))
        except (OSError, ValueError) as error:
            return AdapterResult(PRODUCTION_WORKLOAD_ID, TerminalOutcome.FAILED, str(error))
        return _command_result(
            PRODUCTION_WORKLOAD_ID,
            self._runner,
            (*DOCKER_COMMAND, "start", *PRODUCTION_CONTAINERS),
            "production container start failed",
        )

    def stop(self) -> AdapterResult:
        command = _operator_pdm_command("prod-stop", GPU_WORKER_CONTAINER, API_CONTAINER)
        if command is None:
            return _missing_operator_account_result()
        return _command_result(
            PRODUCTION_WORKLOAD_ID,
            self._runner,
            command,
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


def _application_image_id(runner: CommandExecutor, project_root: Path) -> str:
    head_result = runner.run(("git", "-C", str(project_root), "rev-parse", "HEAD"))
    head = head_result.stdout.strip() if head_result.returncode == 0 else ""
    if len(head) != 40:
        raise ValueError("cannot resolve repository HEAD for the application image")
    image = f"sir-convert-a-lot-runtime:{head}"
    result = runner.run((*DOCKER_COMMAND, "image", "inspect", "--format", "{{.Id}}", image))
    image_id = result.stdout.strip()
    if result.returncode != 0 or not image_id:
        raise ValueError(f"application image {image} is absent")
    return image_id


def sir_workload_declarations(
    *, runner: CommandExecutor | None = None, project_root: Path | None = None
) -> tuple[WorkloadDeclaration, ...]:
    """Publish only Sir's owner-local declarations; publication never composes."""
    command_runner = runner or CommandRunner()
    root = project_root or Path.cwd()
    return (
        WorkloadDeclaration(
            PRODUCTION_WORKLOAD_ID,
            PRODUCTION_CONTAINERS,
            (),
            frozenset({GPU_CLAIM}),
            frozenset({STT_WORKLOAD_ID}),
            ProductionWorkloadAdapter(command_runner, root),
            frozenset({TerminalOutcome.SUCCEEDED}),
            kind=ClaimKind.SERVICE,
        ),
        WorkloadDeclaration(
            STT_WORKLOAD_ID,
            (STT_CONTAINER,),
            (),
            frozenset({GPU_CLAIM}),
            frozenset({PRODUCTION_WORKLOAD_ID}),
            ContainerWorkloadAdapter(
                STT_WORKLOAD_ID, STT_CONTAINER, command_runner, project_root=root
            ),
            frozenset({TerminalOutcome.SUCCEEDED}),
            kind=ClaimKind.SERVICE,
        ),
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
