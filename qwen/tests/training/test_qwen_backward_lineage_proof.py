"""Tests for the Qwen backward-lineage and fresh-start proof lane backward-lineage proof surface.

Purpose:
    Verify the backward-lineage proof CLI prepares deterministic proof packages and drives
    the committed remote Hemma surface without ad hoc shell glue.

Relationships:
    - Exercises `qwen_backward_lineage_proof.py`.
    - Reuses the mini-bundle helper test contract indirectly through remote
      launch handling.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_proof import main


def test_prepare_writes_backward_lineage_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Preparing backward-lineage should write a deterministic proof package."""
    result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "backward_lineage-proof"]
    )
    capsys.readouterr()

    assert result == 0
    proof_root = tmp_path / "backward_lineage-proof"
    config_payload = json.loads((proof_root / "proof-config.json").read_text(encoding="utf-8"))
    plan_markdown = (proof_root / "plan.md").read_text(encoding="utf-8")
    checklist_markdown = (proof_root / "checklist.md").read_text(encoding="utf-8")

    assert config_payload["command_name"] == "qwen-backward-lineage"
    assert config_payload["source_lines"] == [13, 4]
    assert config_payload["hook_profile"] == "baseline"
    assert "qwen-backward-lineage launch --proof-id backward_lineage-proof" in plan_markdown
    assert "main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation" in plan_markdown
    assert "Detached Hemma worker launched" in checklist_markdown


def test_prepare_persists_custom_boundary_hook_profile(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Preparing layer-16/layer-15 boundary trace should persist the finer talker-core boundary
    profile.
    """
    result = main(
        [
            "prepare",
            "--output-root",
            tmp_path.as_posix(),
            "--proof-id",
            "boundary_trace-proof",
            "--hook-profile",
            "talker_core_boundary",
        ]
    )
    capsys.readouterr()

    assert result == 0
    config_payload = json.loads(
        (tmp_path / "boundary_trace-proof" / "proof-config.json").read_text(encoding="utf-8")
    )

    assert config_payload["hook_profile"] == "talker_core_boundary"
    assert config_payload["task_label"] == "Qwen talker-core boundary lineage"


def test_launch_uses_remote_qwen_lineage_backward_lineage_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public launch command should route through the committed remote proof surface."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "backward_lineage-proof"]
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
                        "scratch_free_bytes": 32 * 1024**3,
                        "required_free_bytes": 16 * 1024**3,
                        "meets_required_headroom": True,
                    }
                ),
                "",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"launch_id": "backward_lineage-proof-backward-lineage", "pid": 1234}),
            "",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_runtime.subprocess.run",
        fake_run,
    )

    result = main(
        ["launch", "--output-root", tmp_path.as_posix(), "--proof-id", "backward_lineage-proof"]
    )
    capsys.readouterr()

    assert result == 0
    assert len(calls) == 2
    assert "qwen-scratch-policy" in calls[0]
    assert calls[1][:7] == [
        "pdm",
        "run",
        "run-hemma",
        "--",
        "pdm",
        "run",
        "qwen-backward-lineage",
    ]
    assert "remote-launch" in calls[1]
    assert "--source-lines" in calls[1]
    assert "13,4" in calls[1]
    assert "--hook-profile" in calls[1]
    assert "baseline" in calls[1]
    assert (tmp_path / "backward_lineage-proof" / "launch.json").exists() is True


def test_remote_launch_starts_detached_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Remote launch should start the detached backward-lineage worker with runner args."""
    captured: dict[str, object] = {}

    def fake_launch(**kwargs: object) -> object:
        captured.update(kwargs)
        return type(
            "LaunchPayload",
            (),
            {
                "generated_at": "2026-03-17T00:00:00Z",
                "launch_id": "backward_lineage-proof-backward-lineage",
                "pid": 4321,
                "repo_root": Path.cwd().as_posix(),
                "output_root": (tmp_path / "remote-proof" / "backward_lineage-proof").as_posix(),
                "log_path": (
                    tmp_path / "remote-proof" / "backward_lineage-proof" / "proof.log"
                ).as_posix(),
                "worker_status_path": (
                    tmp_path / "remote-proof" / "backward_lineage-proof" / "worker-status.json"
                ).as_posix(),
                "report_path": (
                    tmp_path / "remote-proof" / "backward_lineage-proof" / "report.json"
                ).as_posix(),
                "failure_path": (
                    tmp_path / "remote-proof" / "backward_lineage-proof" / "failure.txt"
                ).as_posix(),
                "proof_args": ["--source-lines", "13,4"],
                "command": ["python", "-m", "worker"],
            },
        )()

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_proof.launch_detached_backward_lineage_proof",
        fake_launch,
    )

    result = main(
        [
            "remote-launch",
            "--proof-id",
            "backward_lineage-proof",
            "--remote-proof-output-root",
            (tmp_path / "remote-proof").as_posix(),
            "--source-bundle-root",
            (tmp_path / "source-bundle").as_posix(),
            "--manifest-family",
            "swedish_pilot_train",
            "--source-lines",
            "13,4",
            "--text-embedding-mask-policy",
            "text_span_only",
            "--hook-profile",
            "talker_core",
            "--launch-id",
            "backward_lineage-proof-backward-lineage",
            "--skip-build",
        ]
    )
    capsys.readouterr()

    assert result == 0
    assert captured["launch_id"] == "backward_lineage-proof-backward-lineage"
    assert captured["proof_args"] == [
        "--source-bundle-root",
        (tmp_path / "source-bundle").as_posix(),
        "--manifest-family",
        "swedish_pilot_train",
        "--source-lines",
        "13,4",
        "--text-embedding-mask-policy",
        "text_span_only",
        "--hook-profile",
        "talker_core",
        "--skip-build",
    ]
