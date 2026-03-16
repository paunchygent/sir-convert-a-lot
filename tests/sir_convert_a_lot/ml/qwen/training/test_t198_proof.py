"""Tests for the canonical Task 198 proof surface."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.t198_proof import main


def test_prepare_uses_t198_defaults_and_commands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Preparing Task 198 should default to the accumulation-2 proof lane."""
    result = main(["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t198-proof"])
    capsys.readouterr()

    assert result == 0
    proof_root = tmp_path / "t198-proof"
    config_payload = json.loads((proof_root / "proof-config.json").read_text(encoding="utf-8"))
    plan_markdown = (proof_root / "plan.md").read_text(encoding="utf-8")
    checklist_markdown = (proof_root / "checklist.md").read_text(encoding="utf-8")

    assert config_payload["task_label"] == "Task 198"
    assert config_payload["command_name"] == "qwen-t198-proof"
    assert config_payload["gradient_accumulation_steps"] == 2
    assert "Task 198 Proof Plan" in plan_markdown
    assert "qwen-t198-proof prepare" in plan_markdown
    assert "Task 198 Proof Checklist" in checklist_markdown
    assert "gradient_accumulation_steps=2" in checklist_markdown


def test_launch_window_defaults_to_accumulation_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Task 198 replay launch should default to accumulation 2."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t198-proof"]
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
            json.dumps({"launch_id": "t198-proof-window", "container_name": "qwen-diagnose"}),
            "",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_runtime.subprocess.run",
        fake_run,
    )

    result = main(
        ["launch-window", "--output-root", tmp_path.as_posix(), "--proof-id", "t198-proof"]
    )
    capsys.readouterr()

    assert result == 0
    assert len(calls) == 2
    assert "qwen-scratch-policy" in calls[0]
    command = calls[1]
    assert isinstance(command, list)
    assert "--gradient-accumulation-steps" in command
    assert "2" in command
    assert "text_span_only" in command
