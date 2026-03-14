"""Focused tests for canonical Qwen training resource-monitor helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import (
    inspect_resource_monitor,
    launch_resource_monitor,
    resource_monitor_output_root,
)


def test_launch_resource_monitor_writes_launch_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Monitor launch should persist deterministic resource-monitor artifacts."""
    training_launch_root = tmp_path / "qwen-20260313t200000z"
    training_launch_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.monitoring.spawn_detached_worker",
        lambda command, *, stdout_path, stderr_path: 4242,
    )

    payload = launch_resource_monitor(
        training_launch_id="qwen-20260313t200000z",
        training_launch_root=training_launch_root,
        runtime_kind="rocm",
        interval_seconds=1.0,
        duration_seconds=None,
    )

    monitor_root = resource_monitor_output_root(training_launch_root)
    launch_root = monitor_root / "qwen-20260313t200000z-resource-monitor"
    launch_json = json.loads((launch_root / "launch.json").read_text(encoding="utf-8"))
    latest_pointer = json.loads((monitor_root / "latest-launch.json").read_text(encoding="utf-8"))

    assert payload["launch_root"] == launch_root.as_posix()
    assert launch_json["pid"] == 4242
    assert launch_json["interval_seconds"] == 1.0
    assert latest_pointer["launch_root"] == launch_root.as_posix()


def test_inspect_resource_monitor_splits_train_and_checkpoint_windows(
    tmp_path: Path,
) -> None:
    """Monitor summaries should split train and checkpoint-save windows by phase history."""
    launch_root = tmp_path / "monitor-launch"
    launch_root.mkdir(parents=True, exist_ok=True)
    (launch_root / "launch.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-13T20:00:00Z",
                "launch_id": "qwen-run-resource-monitor",
                "repo_root": "/repo",
                "pid": 999999,
                "runtime_kind": "rocm",
                "interval_seconds": 1.0,
                "duration_seconds": None,
                "command": ["python", "-m", "monitor"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (launch_root / "samples.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "captured_at": "2026-03-13T20:00:00Z",
                        "runtime_kind": "rocm",
                        "gpu_busy_percent": 99,
                        "gpu_memory_used_percent": 59,
                        "host_cpu_busy_percent": 29,
                        "host_memory_used_percent": 39,
                    }
                ),
                json.dumps(
                    {
                        "captured_at": "2026-03-13T20:00:01Z",
                        "runtime_kind": "rocm",
                        "gpu_busy_percent": 20,
                        "gpu_memory_used_percent": 60,
                        "host_cpu_busy_percent": 30,
                        "host_memory_used_percent": 40,
                    }
                ),
                json.dumps(
                    {
                        "captured_at": "2026-03-13T20:00:02Z",
                        "runtime_kind": "rocm",
                        "gpu_busy_percent": 40,
                        "gpu_memory_used_percent": 61,
                        "host_cpu_busy_percent": 32,
                        "host_memory_used_percent": 41,
                    }
                ),
                json.dumps(
                    {
                        "captured_at": "2026-03-13T20:00:03Z",
                        "runtime_kind": "rocm",
                        "gpu_busy_percent": 10,
                        "gpu_memory_used_percent": 62,
                        "host_cpu_busy_percent": 33,
                        "host_memory_used_percent": 42,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = inspect_resource_monitor(
        {
            "launch_id": "qwen-run-resource-monitor",
            "launch_root": launch_root.as_posix(),
            "output_root": tmp_path.as_posix(),
            "runtime_kind": "rocm",
            "interval_seconds": 1.0,
            "duration_seconds": None,
        },
        phase_history=[
            {"phase": "startup", "updated_at": "2026-03-13T20:00:00Z"},
            {"phase": "train", "updated_at": "2026-03-13T20:00:01Z"},
            {"phase": "checkpoint-save", "updated_at": "2026-03-13T20:00:03Z"},
        ],
    )

    assert payload is not None
    assert payload["available"] is True
    summary_train = payload["summary_train"]
    summary_checkpoint = payload["summary_checkpoint_save"]
    assert isinstance(summary_train, dict)
    assert isinstance(summary_checkpoint, dict)
    assert summary_train["sample_count"] == 2
    assert summary_train["gpu_busy_percent_median"] == 30.0
    assert summary_train["first_sample_at"] == "2026-03-13T20:00:01Z"
    assert summary_checkpoint["sample_count"] == 1
    assert summary_checkpoint["gpu_busy_percent_median"] == 10.0
