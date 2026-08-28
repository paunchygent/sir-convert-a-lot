import json

import pytest
from repository_governance.hemma_workload import (
    StartCommand,
    TerminalOutcome,
    TransactionResult,
    WorkloadTransactionError,
)

from scripts.sir_convert_a_lot.devops import hemma_workload_cli


def test_cli_dispatches_through_shared_seam_and_renders_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    command = StartCommand("sir-production", "tx-1")
    result = TransactionResult(TerminalOutcome.SUCCEEDED, "sir-production", "tx-1")
    calls: list[str] = []
    monkeypatch.setattr(hemma_workload_cli, "parse_command", lambda argv: command)
    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(hemma_workload_cli, "sir_workload_controller", lambda: None)

    def execute(controller: None, received: StartCommand) -> TransactionResult:
        calls.append(received.target_identity)
        return result

    monkeypatch.setattr(hemma_workload_cli, "execute_command", execute)

    exit_code = hemma_workload_cli.main(("start", "sir-production", "tx-1"))

    assert exit_code == 0
    assert calls == ["sir-production"]
    assert json.loads(capsys.readouterr().out) == {
        "outcome": "succeeded",
        "reason": "",
        "target_identity": "sir-production",
        "transaction_id": "tx-1",
    }


def test_cli_guard_refusal_is_structured_and_skips_controller(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        hemma_workload_cli,
        "_guard_reason",
        lambda: "hemma-workload-cli: this command is Hemma Server-only.",
    )
    monkeypatch.setattr(
        hemma_workload_cli,
        "sir_workload_controller",
        lambda: pytest.fail("controller must not be built after guard refusal"),
    )

    exit_code = hemma_workload_cli.main(("restore", "sir-production"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == "sir-production"
    assert rendered["transaction_id"] is None


def test_cli_catches_provider_error_as_structured_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hemma_workload_cli, "_guard_reason", lambda: None)
    monkeypatch.setattr(hemma_workload_cli, "sir_workload_controller", lambda: None)

    def fail(controller: None, command: StartCommand) -> TransactionResult:
        raise WorkloadTransactionError("inventory refused unknown consumer")

    monkeypatch.setattr(hemma_workload_cli, "execute_command", fail)

    exit_code = hemma_workload_cli.main(("start", "sir-production", "tx-2"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered == {
        "outcome": "refused",
        "reason": "inventory refused unknown consumer",
        "target_identity": "sir-production",
        "transaction_id": "tx-2",
    }


def test_cli_parse_error_is_structured_and_nonzero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = hemma_workload_cli.main(("status", "sir-production"))

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rendered["outcome"] == "refused"
    assert rendered["target_identity"] == ""
    assert "usage: start" in rendered["reason"]
