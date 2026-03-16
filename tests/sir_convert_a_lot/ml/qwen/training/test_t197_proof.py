"""Tests for the canonical Task 197 proof surface."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof import main


def test_prepare_writes_config_plan_and_checklist(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Preparing Task 197 should create one deterministic proof package."""
    result = main(["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"])
    capsys.readouterr()

    assert result == 0
    proof_root = tmp_path / "t197-proof"
    assert (proof_root / "proof-config.json").exists() is True
    assert (proof_root / "plan.md").exists() is True
    assert (proof_root / "checklist.md").exists() is True
    plan_markdown = (proof_root / "plan.md").read_text(encoding="utf-8")
    checklist_markdown = (proof_root / "checklist.md").read_text(encoding="utf-8")
    assert "1406 -> 1418" in plan_markdown
    assert "pdm run run-hemma -- pdm run qwen-train diagnose-non-finite" in plan_markdown
    assert "required_scratch_free_bytes" in plan_markdown
    assert "1406 -> 1418" in checklist_markdown
    assert "1500" in checklist_markdown
    assert "scratch free space" in checklist_markdown
    latest_pointer = json.loads((tmp_path / "latest-proof.json").read_text(encoding="utf-8"))
    assert latest_pointer["proof_id"] == "t197-proof"


def test_launch_window_uses_detached_diagnose_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The bounded replay launch should use the detached diagnose surface."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    assert prepare_result == 0
    capsys.readouterr()
    calls: list[list[str]] = []

    def fake_run(
        command: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(command))
        if "qwen-scratch-policy" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "scratch_free_bytes": 80 * 1024**3,
                        "required_free_bytes": 64 * 1024**3,
                        "meets_required_headroom": True,
                    }
                ),
                "",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"launch_id": "t197-proof-window", "container_name": "qwen-diagnose"}),
            "",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_runtime.subprocess.run",
        fake_run,
    )

    result = main(
        ["launch-window", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    capsys.readouterr()

    assert result == 0
    assert len(calls) == 2
    audit_command = calls[0]
    command = calls[1]
    assert "qwen-scratch-policy" in audit_command
    assert "audit" in audit_command
    assert isinstance(command, list)
    assert command[:7] == ["pdm", "run", "run-hemma", "--", "pdm", "run", "qwen-train"]
    assert "diagnose-non-finite" in command
    assert "--text-embedding-mask-policy" in command
    assert "text_span_only" in command
    assert "--gradient-accumulation-steps" in command
    assert "4" in command
    assert "--start-optimizer-step" in command
    assert "1406" in command
    assert "--end-optimizer-step" in command
    assert "1418" in command
    assert (tmp_path / "t197-proof" / "window-launch.json").exists() is True


def test_launch_gate1500_requires_clean_window_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The `1500` gate should only launch after a clean bounded replay."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    assert prepare_result == 0
    capsys.readouterr()
    calls: list[list[str]] = []

    def fake_run(
        command: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(command))
        if "qwen-scratch-policy" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "scratch_free_bytes": 80 * 1024**3,
                        "required_free_bytes": 64 * 1024**3,
                        "meets_required_headroom": True,
                    }
                ),
                "",
            )
        if "status" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "status": "exited",
                        "running": False,
                        "exit_code": 0,
                        "pilot_status": {"current_optimizer_step": 1418},
                    }
                ),
                "",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"launch_id": "t197-proof-gate1500", "container_name": "qwen-train"}),
            "",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_runtime.subprocess.run",
        fake_run,
    )

    result = main(
        ["launch-gate1500", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    capsys.readouterr()

    assert result == 0
    status_command = calls[0]
    audit_command = calls[1]
    gate_command = calls[2]
    assert "status" in status_command
    assert "qwen-scratch-policy" in audit_command
    assert "resume" in gate_command
    assert "--max-steps" in gate_command
    assert "1500" in gate_command
    assert "--checkpoint-interval-steps" in gate_command
    assert "500" in gate_command
    assert "--eval-interval-steps" in gate_command
    assert "100" in gate_command
    assert (tmp_path / "t197-proof" / "gate1500-launch.json").exists() is True


def test_status_commands_write_phase_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status commands should persist deterministic JSON and markdown artifacts."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    assert prepare_result == 0
    capsys.readouterr()

    def fake_run(
        command: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        if "t197-proof-gate1500" in command:
            payload = {
                "status": "running",
                "running": True,
                "exit_code": None,
                "pilot_status": {"current_optimizer_step": 1452, "eval_runs_completed": 0},
            }
        else:
            payload = {
                "status": "exited",
                "running": False,
                "exit_code": 0,
                "pilot_status": {"current_optimizer_step": 1418, "eval_runs_completed": 0},
            }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_runtime.subprocess.run",
        fake_run,
    )

    window_result = main(
        ["status-window", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    gate_result = main(
        ["status-gate1500", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    capsys.readouterr()

    assert window_result == 0
    assert gate_result == 0
    assert (tmp_path / "t197-proof" / "window-status.json").exists() is True
    assert (tmp_path / "t197-proof" / "window-status.md").exists() is True
    assert (tmp_path / "t197-proof" / "gate1500-status.json").exists() is True
    assert (tmp_path / "t197-proof" / "gate1500-status.md").exists() is True


def test_launch_window_fails_closed_on_insufficient_scratch_headroom(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The bounded replay launch should fail before remote work when scratch is too full."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"]
    )
    assert prepare_result == 0
    capsys.readouterr()

    def fake_run(
        command: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        assert "qwen-scratch-policy" in command
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "scratch_free_bytes": 8 * 1024**3,
                    "required_free_bytes": 64 * 1024**3,
                    "meets_required_headroom": False,
                }
            ),
            "",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_runtime.subprocess.run",
        fake_run,
    )

    with pytest.raises(SystemExit, match="scratch headroom is below the required threshold"):
        main(["launch-window", "--output-root", tmp_path.as_posix(), "--proof-id", "t197-proof"])
