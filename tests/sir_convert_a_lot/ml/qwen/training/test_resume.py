"""Tests for the canonical Qwen interruption/resume proof runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.resume_proof import (
    build_parser,
    main,
    run_remote_training_json,
)


def test_resume_parser_defaults_are_bounded() -> None:
    """The proof runner should expose conservative bounded defaults."""
    parser = build_parser()
    args = parser.parse_args([])

    assert args.max_steps == 24
    assert args.checkpoint_interval_steps == 2
    assert args.poll_interval_seconds == 10
    assert args.poll_timeout_seconds == 1800
    assert args.skip_build is False


def test_resume_runner_orchestrates_launch_stop_resume_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The proof runner should record launch, interruption, resume, and final report."""
    proof_id = "qwen-resume-test"
    initial_run_root = (
        "/srv/scratch/sir-convert-a-lot/build/runs/"
        "qwen3-tts-swedish-finetune/qwen-resume-test-initial"
    )
    initial_checkpoint = f"{initial_run_root}/checkpoints/state-step-00000002"
    final_checkpoint = f"{initial_run_root}/checkpoints/state-step-00000024"
    captured_commands: list[tuple[str, list[str]]] = []
    status_call_count = 0

    def fake_default_proof_id() -> str:
        return proof_id

    def fake_run_remote_training_json(args: list[str], *, label: str) -> dict[str, object]:
        nonlocal status_call_count
        captured_commands.append((label, args))
        if args[0] == "launch":
            return {
                "launch_id": "qwen-resume-test-initial",
                "run_root": initial_run_root,
                "resumed_from_checkpoint_path": None,
            }
        if args[0] == "stop":
            return {
                "launch_id": "qwen-resume-test-initial",
                "container_name": "qwen-proof-container",
                "stop_output": "qwen-proof-container",
            }
        if args[0] == "resume":
            return {
                "launch_id": "qwen-resume-test-resume",
                "run_root": initial_run_root,
                "resumed_from_checkpoint_path": initial_checkpoint,
            }
        if args[0] == "status":
            status_call_count += 1
            if status_call_count == 1:
                return {
                    "status": "running",
                    "running": True,
                    "exit_code": 0,
                    "pilot_report_found": False,
                    "latest_checkpoint_found": True,
                    "latest_checkpoint": {
                        "checkpoint_path": initial_checkpoint,
                        "optimizer_steps_completed": 2,
                    },
                }
            if status_call_count == 2:
                return {
                    "status": "exited",
                    "running": False,
                    "exit_code": 143,
                    "pilot_report_found": False,
                    "latest_checkpoint_found": True,
                    "latest_checkpoint": {
                        "checkpoint_path": initial_checkpoint,
                        "optimizer_steps_completed": 2,
                    },
                }
            return {
                "status": "exited",
                "running": False,
                "exit_code": 0,
                "pilot_report_found": True,
                "pilot_report": {
                    "training_summary": {
                        "optimizer_steps_completed": 24,
                    }
                },
                "latest_checkpoint_found": True,
                "latest_checkpoint": {
                    "checkpoint_path": final_checkpoint,
                    "optimizer_steps_completed": 24,
                },
            }
        raise AssertionError(f"Unexpected resume-proof remote args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.resume_proof.default_proof_id",
        fake_default_proof_id,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.resume_proof.run_remote_training_json",
        fake_run_remote_training_json,
    )

    result = main(["--output-root", tmp_path.as_posix(), "--skip-build"])

    assert result == 0
    proof_root = tmp_path / proof_id
    report_payload = json.loads((proof_root / "report.json").read_text(encoding="utf-8"))
    assert report_payload["interrupted_checkpoint_step"] == 2
    assert report_payload["final_optimizer_steps_completed"] == 24
    assert report_payload["final_latest_checkpoint_step"] == 24
    assert (proof_root / "initial_launch.json").exists() is True
    assert (proof_root / "stop.json").exists() is True
    assert (proof_root / "resumed_launch.json").exists() is True
    assert (proof_root / "final_status.json").exists() is True
    assert len(captured_commands) == 6


def test_run_remote_training_json_accepts_valid_json_stdout_even_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remote polling should accept valid JSON stdout despite noisy exit codes."""

    def fake_subprocess_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del command, check, capture_output, text
        return subprocess.CompletedProcess(
            args=[],
            returncode=139,
            stdout=json.dumps({"status": "exited", "exit_code": 137}),
            stderr="segfault",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.resume_proof.subprocess.run",
        fake_subprocess_run,
    )

    payload = run_remote_training_json(["status"], label="qwen training status poll")

    assert payload["status"] == "exited"
    assert payload["exit_code"] == 137
