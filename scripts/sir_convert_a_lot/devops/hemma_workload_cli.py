"""Run Sir's Hemma-only workload controller through the shared command seam."""

from __future__ import annotations

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

from scripts.sir_convert_a_lot.devops.hemma_workload import sir_workload_controller

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HEMMA_GUARD = REPOSITORY_ROOT / "scripts/devops/require-hemma-server.sh"
GUARD_TIMEOUT_SECONDS = 5.0


def _command_identifiers(command: ControllerCommand) -> tuple[str, str | None]:
    """Extract shared command fields for a structured terminal result."""
    if isinstance(command, RestoreCommand):
        return command.target_identity, None
    return command.target_identity, command.transaction_id


def _guard_reason() -> str | None:
    """Return the existing Hemma guard's refusal without running a transaction."""
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
    detail = guard.stderr.strip()
    if detail:
        return detail
    return f"hemma-workload-cli: Hemma Server guard refused execution (exit {guard.returncode})"


def _refused_result(
    target_identity: str,
    transaction_id: str | None,
    error: Exception,
) -> TransactionResult:
    """Convert a declared owner or provider refusal to the shared result shape."""
    return TransactionResult(
        outcome=TerminalOutcome.REFUSED,
        target_identity=target_identity,
        transaction_id=transaction_id,
        reason=str(error),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one start, stop, or restore request on the canonical Hemma host."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    target_identity = ""
    transaction_id: str | None = None
    try:
        command = parse_command(arguments)
        target_identity, transaction_id = _command_identifiers(command)
        guard_reason = _guard_reason()
        if guard_reason is None:
            result = execute_command(sir_workload_controller(), command)
        else:
            result = TransactionResult(
                outcome=TerminalOutcome.REFUSED,
                target_identity=target_identity,
                transaction_id=transaction_id,
                reason=guard_reason,
            )
    except (
        InventoryInspectionError,
        LockContendedError,
        OSError,
        ReceiptError,
        ValueError,
        WorkloadTransactionError,
        subprocess.TimeoutExpired,
    ) as error:
        result = _refused_result(target_identity, transaction_id, error)
    print(render_result(result))
    return 0 if result.outcome is TerminalOutcome.SUCCEEDED else 1


if __name__ == "__main__":
    raise SystemExit(main())
