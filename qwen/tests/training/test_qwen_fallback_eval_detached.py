"""Tests for the detached Qwen fallback proof lane fallback standalone eval helper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_fallback_eval_detached import (
    DetachedQwenFallbackEvalLaunch,
    eval_status_path,
    inspect_detached_qwen_fallback_eval,
    launch_detached_qwen_fallback_eval,
    log_path,
    report_path,
    worker_status_path,
)


def test_launch_injects_eval_output_dir_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Launching the detached helper should guarantee an explicit eval output dir."""

    class DummyProcess:
        pid = 4242

    def fake_popen(
        command: list[str],
        *,
        cwd: Path,
        stdout: object,
        stderr: int,
        text: bool,
        start_new_session: bool,
    ) -> DummyProcess:
        assert cwd == tmp_path
        assert stderr == subprocess.STDOUT
        assert text is True
        assert start_new_session is True
        assert "--eval-output-dir" in command
        assert tmp_path.as_posix() in command
        return DummyProcess()

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_fallback_eval_detached.subprocess.Popen",
        fake_popen,
    )

    launch = launch_detached_qwen_fallback_eval(
        output_root=tmp_path,
        repo_root=tmp_path,
        eval_args=[
            "--output-root",
            "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training",
            "--launch-root",
            "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/qwen-fallback-accumulation-fallback1470",
        ],
        launch_id="fallback-eval-launch",
    )

    assert launch.launch_id == "fallback-eval-launch"
    assert launch.pid == 4242
    assert "--eval-output-dir" in launch.eval_args
    assert tmp_path.as_posix() in launch.eval_args
    assert log_path(tmp_path).exists() is True


def test_inspect_reads_report_eval_status_and_worker_state(tmp_path: Path) -> None:
    """Inspecting the detached helper should surface canonical eval artifacts."""
    launch = DetachedQwenFallbackEvalLaunch(
        generated_at="2026-03-16T22:10:00Z",
        launch_id="fallback-eval-launch",
        pid=4242,
        repo_root=tmp_path.as_posix(),
        output_root=tmp_path.as_posix(),
        log_path=log_path(tmp_path).as_posix(),
        worker_status_path=worker_status_path(tmp_path).as_posix(),
        report_path=report_path(tmp_path).as_posix(),
        eval_status_path=eval_status_path(tmp_path).as_posix(),
        failure_path=(tmp_path / "failure.txt").as_posix(),
        eval_args=["--eval-output-dir", tmp_path.as_posix()],
        command=["python", "-m", "worker"],
    )
    log_path(tmp_path).write_text("tail line\n", encoding="utf-8")
    worker_status_path(tmp_path).write_text(
        json.dumps({"finished_at": "2026-03-16T22:12:00Z", "exit_code": 0}),
        encoding="utf-8",
    )
    report_path(tmp_path).write_text(
        json.dumps({"status": "completed", "eval_summary": {"eval_loss": 1.5}}),
        encoding="utf-8",
    )
    eval_status_path(tmp_path).write_text(
        json.dumps({"stage": "eval", "status": "completed"}),
        encoding="utf-8",
    )

    status = inspect_detached_qwen_fallback_eval(launch)

    assert status.running is False
    assert status.exit_code == 0
    assert status.report_found is True
    assert status.eval_status_found is True
    assert status.report == {"status": "completed", "eval_summary": {"eval_loss": 1.5}}
    assert status.eval_status == {"stage": "eval", "status": "completed"}
    assert "tail line" in status.logs_tail
