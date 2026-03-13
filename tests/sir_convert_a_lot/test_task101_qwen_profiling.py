"""Tests for Task 101 profiling orchestration surfaces."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task162_hemma_task101_profiling import (
    _build_parser as _build_task162_parser,
)
from scripts.sir_convert_a_lot.devops.run_task162_hemma_task101_profiling import (
    main as run_task162_main,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe_with_rocprof import (
    main as rocprof_wrapper_main,
)


def test_task162_parser_defaults_are_bounded() -> None:
    """Task 162 CLI should expose bounded profiling defaults."""
    parser = _build_task162_parser()
    args = parser.parse_args([])

    assert args.max_steps == 80
    assert args.checkpoint_interval_steps == 100
    assert args.poll_interval_seconds == 15
    assert args.poll_timeout_seconds == 3600
    assert args.torch_profiler_enabled == "true"
    assert args.rocm_profiler_enabled == "true"


def test_task162_runner_writes_profile_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 162 runner should emit launch/status/artifact/report bundles."""
    profiling_id = "task162-proof-test"
    remote_output_root = Path(
        "/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot"
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task162_hemma_task101_profiling._default_profiling_id",
        lambda: profiling_id,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task162_hemma_task101_profiling.run_remote_task101_json",
        lambda args, label: {
            "launch_id": f"{profiling_id}-profile",
            "run_root": (
                "/srv/scratch/sir-convert-a-lot/build/runs/"
                "qwen3-tts-swedish-finetune/task162-proof-test-profile"
            ),
        },
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task162_hemma_task101_profiling.poll_remote_task101_status",
        lambda **kwargs: {
            "status": "exited",
            "exit_code": 0,
            "pilot_report_found": True,
            "pilot_report": {
                "training_summary": {
                    "profiling": {
                        "enabled": True,
                        "trace_files": ["/srv/scratch/.../pytorch/trace.pt.trace.json"],
                    }
                }
            },
        },
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task162_hemma_task101_profiling._run_remote_profile_artifacts",
        lambda run_root, label: {
            "run_root": run_root,
            "pytorch_trace_files": ["/srv/scratch/.../pytorch/trace.pt.trace.json"],
            "rocm_trace_files": ["/srv/scratch/.../rocm/results.csv"],
        },
    )

    result = run_task162_main(
        [
            "--output-root",
            tmp_path.as_posix(),
            "--remote-task101-output-root",
            remote_output_root.as_posix(),
        ]
    )

    assert result == 0
    profile_root = tmp_path / profiling_id
    report_payload = json.loads((profile_root / "report.json").read_text(encoding="utf-8"))
    assert report_payload["launch_id"] == f"{profiling_id}-profile"
    assert report_payload["torch_profiling_enabled"] is True
    assert report_payload["rocm_profiling_enabled"] is True
    assert len(report_payload["artifact_summary"]["pytorch_trace_files"]) == 1
    assert len(report_payload["artifact_summary"]["rocm_trace_files"]) == 1


def test_rocprof_wrapper_requires_probe_separator() -> None:
    """ROCm wrapper should fail fast when probe args are missing."""
    with pytest.raises(SystemExit):
        rocprof_wrapper_main(
            [
                "--rocprof-output-dir",
                "/tmp/task162",
                "--rocprof-trace-name",
                "trace",
            ]
        )


def test_rocprof_wrapper_executes_rocprof_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ROCm wrapper should invoke rocprofv3 with deterministic arguments."""
    captured: list[str] = []

    def _fake_subprocess_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        del check
        captured.extend(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe_with_rocprof.subprocess.run",
        _fake_subprocess_run,
    )

    result = rocprof_wrapper_main(
        [
            "--rocprof-output-dir",
            tmp_path.as_posix(),
            "--rocprof-trace-name",
            "trace",
            "--",
            "--launch-id",
            "task101-test",
            "--train-jsonl",
            "/tmp/train.jsonl",
        ]
    )

    assert result == 0
    assert captured[0] == "rocprofv3"
    assert "--output-file" in captured
    assert "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe" in captured
