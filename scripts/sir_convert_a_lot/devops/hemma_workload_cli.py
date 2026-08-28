"""Run Sir's Hemma workload controller through one fixed root worker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from repository_governance.hemma_workload import (
    ControllerCommand,
    InventoryInspectionError,
    LockContendedError,
    ReceiptError,
    RestoreCommand,
    TerminalOutcome,
    TransactionResult,
    WorkloadTransactionError,
    execute_command,
    parse_command,
    render_result,
)
from repository_governance.retained_context.json_contract import JsonValue, strict_pairs

from scripts.sir_convert_a_lot.devops.hemma_workload import (
    SIDECAR_READINESS_TIMEOUT_SECONDS,
    sir_workload_controller,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_runtime import (
    HOST_COMMAND_TIMEOUT_SECONDS,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HEMMA_GUARD = REPOSITORY_ROOT / "scripts/devops/require-hemma-server.sh"
MODULE_NAME = "scripts.sir_convert_a_lot.devops.hemma_workload_cli"
GUARD_TIMEOUT_SECONDS = 5.0
WORKER_TIMEOUT_SECONDS = SIDECAR_READINESS_TIMEOUT_SECONDS + HOST_COMMAND_TIMEOUT_SECONDS + 60.0
WORKER_FLAG = "--worker"


def _command_identifiers(command: ControllerCommand) -> tuple[str, str | None]:
    if isinstance(command, RestoreCommand):
        return command.target_identity, None
    return command.target_identity, command.transaction_id


def _raw_identifiers(arguments: tuple[str, ...]) -> tuple[str, str | None]:
    target_identity = arguments[1] if len(arguments) > 1 else ""
    transaction_id = (
        arguments[2] if len(arguments) > 2 and arguments[0] in {"start", "stop"} else None
    )
    return target_identity, transaction_id


def _guard_reason() -> str | None:
    guard = subprocess.run(
        (
            "bash",
            "-c",
            'source "$1"; sir_convert_require_hemma_server "$2"',
            "hemma-workload-cli",
            HEMMA_GUARD.as_posix(),
            "hemma-workload-cli",
        ),
        capture_output=True,
        check=False,
        cwd=REPOSITORY_ROOT,
        text=True,
        timeout=GUARD_TIMEOUT_SECONDS,
    )
    if guard.returncode == 0:
        return None
    return guard.stderr.strip() or (
        f"hemma-workload-cli: Hemma Server guard refused execution (exit {guard.returncode})"
    )


def _refused_result(
    target_identity: str,
    transaction_id: str | None,
    reason: str,
) -> TransactionResult:
    return TransactionResult(
        outcome=TerminalOutcome.REFUSED,
        target_identity=target_identity,
        transaction_id=transaction_id,
        reason=reason,
    )


def _validated_worker_output(raw: str) -> tuple[str, TransactionResult]:
    lines = raw.splitlines()
    if len(lines) != 1:
        raise ValueError("root worker did not emit exactly one structured result")
    value: JsonValue = json.loads(lines[0], object_pairs_hook=strict_pairs)
    expected_fields = {"outcome", "target_identity", "transaction_id", "reason"}
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise ValueError("root worker result fields are malformed")
    outcome_value = value["outcome"]
    target_value = value["target_identity"]
    transaction_value = value["transaction_id"]
    reason_value = value["reason"]
    if not isinstance(outcome_value, str):
        raise ValueError("root worker result outcome is malformed")
    if not isinstance(target_value, str) or not isinstance(reason_value, str):
        raise ValueError("root worker result identity or reason is malformed")
    if transaction_value is not None and not isinstance(transaction_value, str):
        raise ValueError("root worker result transaction ID is malformed")
    result = TransactionResult(
        TerminalOutcome(outcome_value),
        target_value,
        transaction_value,
        reason_value,
    )
    rendered = render_result(result)
    if rendered != lines[0]:
        raise ValueError("root worker result is not provider-rendered output")
    return rendered, result


def _render_refusal(
    target_identity: str,
    transaction_id: str | None,
    reason: str,
) -> int:
    print(render_result(_refused_result(target_identity, transaction_id, reason)))
    return 1


def _public_main(arguments: tuple[str, ...]) -> int:
    target_identity = ""
    transaction_id: str | None = None
    try:
        command = parse_command(arguments)
        target_identity, transaction_id = _command_identifiers(command)
        guard_reason = _guard_reason()
        if guard_reason is not None:
            return _render_refusal(target_identity, transaction_id, guard_reason)
        worker = subprocess.run(
            (
                "sudo",
                "-n",
                sys.executable,
                "-m",
                MODULE_NAME,
                WORKER_FLAG,
                *arguments,
            ),
            capture_output=True,
            check=False,
            cwd=REPOSITORY_ROOT,
            text=True,
            timeout=WORKER_TIMEOUT_SECONDS,
        )
        try:
            rendered, result = _validated_worker_output(worker.stdout)
        except (json.JSONDecodeError, ValueError) as error:
            diagnostic = worker.stderr.strip() or "no worker diagnostic"
            raise ValueError(f"{error}; worker stderr: {diagnostic}") from error
        if (worker.returncode == 0) is not (result.outcome is TerminalOutcome.SUCCEEDED):
            raise ValueError("root worker exit code contradicts its provider result")
        if (result.target_identity, result.transaction_id) != (
            target_identity,
            transaction_id,
        ):
            raise ValueError("root worker result identifiers contradict the parsed command")
        print(rendered)
        return worker.returncode
    except (
        json.JSONDecodeError,
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
    ) as error:
        return _render_refusal(target_identity, transaction_id, str(error))


def _worker_main(arguments: tuple[str, ...]) -> int:
    target_identity, transaction_id = _raw_identifiers(arguments)
    try:
        if os.geteuid() != 0:
            raise PermissionError("hemma-workload root worker requires effective UID 0")
        guard_reason = _guard_reason()
        if guard_reason is not None:
            raise OSError(guard_reason)
        command = parse_command(arguments)
        target_identity, transaction_id = _command_identifiers(command)
        result = execute_command(sir_workload_controller(), command)
    except (
        InventoryInspectionError,
        LockContendedError,
        OSError,
        ReceiptError,
        ValueError,
        WorkloadTransactionError,
        subprocess.TimeoutExpired,
    ) as error:
        result = _refused_result(target_identity, transaction_id, str(error))
    print(render_result(result))
    return 0 if result.outcome is TerminalOutcome.SUCCEEDED else 1


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == WORKER_FLAG:
        return _worker_main(arguments[1:])
    return _public_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
