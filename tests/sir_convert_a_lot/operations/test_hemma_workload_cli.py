import json
import subprocess
import sys
from pathlib import Path

import pytest
from repository_governance.hemma_workload import (
    ControllerCommand,
    TerminalOutcome,
    TransactionResult,
    WorkloadTransactionError,
    render_result,
)

from scripts.sir_convert_a_lot.devops import hemma_workload_cli


def _rendered(
    outcome: TerminalOutcome,
    target: str = "sir-production",
    transaction_id: str | None = "tx-1",
    reason: str = "",
) -> str:
    return render_result(TransactionResult(outcome, target, transaction_id, reason))


def test_public_cli_launches_exact_root_worker_and_propagates_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[tuple[str, ...], Path, float]] = []

    def run_worker(
        argv: tuple[str, ...],
        *,
        capture_output: bool,
        check: bool,
        cwd: Path,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((argv, cwd, timeout))
        return subprocess.CompletedProcess(argv, 0, _rendered(TerminalOutcome.SUCCEEDED), "")

    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(hemma_workload_cli.subprocess, "run", run_worker)

    exit_code = hemma_workload_cli.main(("start", "sir-production", "tx-1"))

    assert exit_code == 0
    assert capsys.readouterr().out == _rendered(TerminalOutcome.SUCCEEDED) + "\n"
    assert calls == [
        (
            (
                "sudo",
                "-n",
                sys.executable,
                "-m",
                hemma_workload_cli.MODULE_NAME,
                "--worker",
                "start",
                "sir-production",
                "tx-1",
            ),
            hemma_workload_cli.REPOSITORY_ROOT,
            hemma_workload_cli.WORKER_TIMEOUT_SECONDS,
        )
    ]


def test_public_cli_propagates_provider_nonzero_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    refused = _rendered(TerminalOutcome.REFUSED, reason="inventory refused")
    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(
        hemma_workload_cli.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 7, refused, ""),
    )

    assert hemma_workload_cli.main(("start", "sir-production", "tx-1")) == 7
    assert capsys.readouterr().out == refused + "\n"


def test_worker_timeout_covers_sidecar_readiness_and_one_host_command() -> None:
    assert hemma_workload_cli.WORKER_TIMEOUT_SECONDS > (
        hemma_workload_cli.SIDECAR_READINESS_TIMEOUT_SECONDS
        + hemma_workload_cli.HOST_COMMAND_TIMEOUT_SECONDS
    )


def test_public_guard_refusal_is_structured_and_skips_worker(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        hemma_workload_cli,
        "_guard_reason",
        lambda: "hemma-workload-cli: this command is Hemma Server-only.",
    )
    monkeypatch.setattr(
        hemma_workload_cli.subprocess,
        "run",
        lambda argv, **kwargs: pytest.fail("root worker must not run after guard refusal"),
    )

    exit_code = hemma_workload_cli.main(("restore", "sir-production"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == "sir-production"
    assert rendered["transaction_id"] is None


@pytest.mark.parametrize(
    "failure", [OSError("sudo unavailable"), subprocess.TimeoutExpired("sudo", 2)]
)
def test_public_worker_launch_failure_is_structured(
    failure: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(
        argv: tuple[str, ...],
        *,
        capture_output: bool,
        check: bool,
        cwd: Path,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        raise failure

    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(hemma_workload_cli.subprocess, "run", fail)

    exit_code = hemma_workload_cli.main(("stop", "sir-production", "tx-2"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == "sir-production"
    assert rendered["transaction_id"] == "tx-2"


def test_public_worker_without_structured_output_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(
        hemma_workload_cli.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, "", "sudo refused"),
    )

    exit_code = hemma_workload_cli.main(("start", "sir-production", "tx-3"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == "sir-production"
    assert rendered["transaction_id"] == "tx-3"
    assert "sudo refused" in rendered["reason"]


def test_root_worker_refuses_unprivileged_execution_before_guard(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hemma_workload_cli.os, "geteuid", lambda: 501)
    monkeypatch.setattr(
        hemma_workload_cli,
        "_guard_reason",
        lambda: pytest.fail("unprivileged worker must fail before the guard"),
    )

    exit_code = hemma_workload_cli.main(("--worker", "start", "sir-production", "tx-root"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == "sir-production"
    assert rendered["transaction_id"] == "tx-root"
    assert "effective UID 0" in rendered["reason"]


def test_root_worker_reapplies_guard_and_executes_provider_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    guards: list[str] = []
    result = TransactionResult(TerminalOutcome.SUCCEEDED, "sir-production", "tx-worker")
    monkeypatch.setattr(hemma_workload_cli.os, "geteuid", lambda: 0)

    def guard_reason() -> None:
        guards.append("guard")

    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", guard_reason)
    monkeypatch.setattr(hemma_workload_cli, "sir_workload_controller", lambda: None)
    monkeypatch.setattr(
        hemma_workload_cli,
        "execute_command",
        lambda controller, command: result,
    )

    exit_code = hemma_workload_cli.main(("--worker", "start", "sir-production", "tx-worker"))

    assert exit_code == 0
    assert guards == ["guard"]
    assert capsys.readouterr().out == render_result(result) + "\n"


def test_root_worker_provider_error_is_structured(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hemma_workload_cli.os, "geteuid", lambda: 0)
    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(hemma_workload_cli, "sir_workload_controller", lambda: None)

    def fail(controller: None, command: ControllerCommand) -> TransactionResult:
        raise WorkloadTransactionError("unknown consumer")

    monkeypatch.setattr(hemma_workload_cli, "execute_command", fail)

    exit_code = hemma_workload_cli.main(("--worker", "start", "sir-production", "tx-error"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["reason"] == "unknown consumer"


def test_public_parse_error_is_structured_and_nonzero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = hemma_workload_cli.main(("status", "sir-production"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == ""
    assert "usage: start" in rendered["reason"]
