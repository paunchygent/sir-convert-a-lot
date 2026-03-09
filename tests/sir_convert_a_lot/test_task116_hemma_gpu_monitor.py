"""Tests for the detached Task 116 Hemma GPU monitor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task116_hemma_gpu_monitor import (
    DEFAULT_OUTPUT_ROOT,
    _build_parser,
    main,
)
from scripts.sir_convert_a_lot.devops.task116_hemma_gpu_monitor_runtime import (
    Task116GpuSample,
    build_status,
    run_worker,
    summarize_samples,
)


def test_task116_gpu_monitor_parser_launch_defaults() -> None:
    """The GPU monitor should expose deterministic detached defaults."""
    parser = _build_parser()
    args = parser.parse_args(["launch"])

    assert args.output_root == DEFAULT_OUTPUT_ROOT
    assert args.runtime_kind == "rocm"
    assert args.interval_seconds == 30.0
    assert args.duration_seconds is None


def test_summarize_samples_computes_min_median_and_max() -> None:
    """Summary statistics should reflect the recorded GPU sample distribution."""
    summary = summarize_samples(
        "task116-gpu-20260309t120000z",
        [
            Task116GpuSample(
                captured_at="2026-03-09T12:00:00Z",
                runtime_kind="rocm",
                gpu_busy_percent=10,
                gpu_memory_used_percent=32,
            ),
            Task116GpuSample(
                captured_at="2026-03-09T12:00:30Z",
                runtime_kind="rocm",
                gpu_busy_percent=40,
                gpu_memory_used_percent=35,
            ),
            Task116GpuSample(
                captured_at="2026-03-09T12:01:00Z",
                runtime_kind="rocm",
                gpu_busy_percent=25,
                gpu_memory_used_percent=37,
            ),
        ],
    )

    assert summary.sample_count == 3
    assert summary.gpu_busy_percent_min == 10
    assert summary.gpu_busy_percent_median == 25.0
    assert summary.gpu_busy_percent_max == 40
    assert summary.gpu_memory_used_percent_min == 32
    assert summary.gpu_memory_used_percent_median == 35.0
    assert summary.gpu_memory_used_percent_max == 37


def test_build_status_reads_latest_pointer_and_samples(tmp_path: Path) -> None:
    """Status should merge launch metadata, worker state, and sample summary."""
    launch_root = tmp_path / "task116-gpu-20260309t120000z"
    launch_root.mkdir(parents=True, exist_ok=True)
    (launch_root / "launch.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-09T12:00:00Z",
                "launch_id": "task116-gpu-20260309t120000z",
                "repo_root": "/repo",
                "pid": 999999,
                "runtime_kind": "rocm",
                "interval_seconds": 30.0,
                "duration_seconds": None,
                "command": ["python", "-m", "monitor"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (launch_root / "worker-state.json").write_text(
        json.dumps(
            {
                "launch_id": "task116-gpu-20260309t120000z",
                "started_at": "2026-03-09T12:00:00Z",
                "finished_at": None,
                "exit_reason": None,
                "sample_count": 2,
                "latest_sample_at": "2026-03-09T12:00:30Z",
                "latest_gpu_busy_percent": 16,
                "latest_gpu_memory_used_percent": 34,
                "error": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (launch_root / "samples.jsonl").write_text(
        json.dumps(
            {
                "captured_at": "2026-03-09T12:00:00Z",
                "runtime_kind": "rocm",
                "gpu_busy_percent": 8,
                "gpu_memory_used_percent": 33,
            }
        )
        + "\n"
        + json.dumps(
            {
                "captured_at": "2026-03-09T12:00:30Z",
                "runtime_kind": "rocm",
                "gpu_busy_percent": 16,
                "gpu_memory_used_percent": 34,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    status = build_status(launch_root)

    assert status.launch_id == "task116-gpu-20260309t120000z"
    assert status.worker_state_found is True
    assert status.summary["sample_count"] == 2
    assert status.summary["gpu_busy_percent_median"] == 12.0
    assert status.summary["gpu_busy_percent_max"] == 16


def test_main_launch_writes_launch_metadata_and_latest_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Launch should persist metadata and point latest-launch at the new run."""

    def _fake_spawn_detached_worker(
        command: list[str],
        *,
        stdout_path: Path,
        stderr_path: Path,
    ) -> int:
        assert command[0].endswith("python")
        assert stdout_path.name == "worker.stdout.log"
        assert stderr_path.name == "worker.stderr.log"
        return 4242

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task116_hemma_gpu_monitor.spawn_detached_worker",
        _fake_spawn_detached_worker,
    )

    exit_code = main(
        [
            "launch",
            "--output-root",
            tmp_path.as_posix(),
            "--launch-id",
            "task116-gpu-test",
            "--interval-seconds",
            "15",
        ]
    )

    assert exit_code == 0
    launch_payload = json.loads(
        (tmp_path / "task116-gpu-test/launch.json").read_text(encoding="utf-8")
    )
    assert launch_payload["pid"] == 4242
    pointer_payload = json.loads((tmp_path / "latest-launch.json").read_text(encoding="utf-8"))
    assert pointer_payload["launch_root"] == (tmp_path / "task116-gpu-test").as_posix()


def test_run_worker_does_not_depend_on_launch_metadata_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The worker should record samples even when launch metadata is written later."""
    launch_root = tmp_path / "task116-gpu-worker"
    launch_root.mkdir(parents=True, exist_ok=True)

    class _FakeSnapshot:
        def __init__(self) -> None:
            self.gpu_busy_percent = 22
            self.gpu_memory_used_percent = 41

    def _fake_snapshot(*, runtime_kind: str) -> _FakeSnapshot | None:
        assert runtime_kind == "rocm"
        return _FakeSnapshot()

    def _fake_sleep(seconds: float) -> None:
        del seconds
        (launch_root / "stop.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task116_hemma_gpu_monitor_runtime.sample_gpu_utilization_snapshot",
        _fake_snapshot,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task116_hemma_gpu_monitor_runtime.time.sleep",
        _fake_sleep,
    )

    exit_code = run_worker(
        launch_root=launch_root,
        launch_id="task116-gpu-worker",
        started_at="2026-03-09T12:00:00Z",
        runtime_kind="rocm",
        interval_seconds=15.0,
        duration_seconds=None,
    )

    assert exit_code == 0
    worker_state = json.loads((launch_root / "worker-state.json").read_text(encoding="utf-8"))
    assert worker_state["sample_count"] == 1
    samples = (launch_root / "samples.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(samples) == 1
    assert json.loads(samples[0])["gpu_busy_percent"] == 22


def test_main_stop_writes_stop_request(tmp_path: Path) -> None:
    """Stop should create one durable stop-request marker for the worker."""
    launch_root = tmp_path / "task116-gpu-test"
    launch_root.mkdir(parents=True, exist_ok=True)
    (launch_root / "launch.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-09T12:00:00Z",
                "launch_id": "task116-gpu-test",
                "repo_root": "/repo",
                "pid": 1234,
                "runtime_kind": "rocm",
                "interval_seconds": 30.0,
                "duration_seconds": None,
                "command": ["python", "-m", "monitor"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        ["stop", "--output-root", tmp_path.as_posix(), "--launch-root", launch_root.as_posix()]
    )

    assert exit_code == 0
    stop_payload = json.loads((launch_root / "stop.json").read_text(encoding="utf-8"))
    assert stop_payload["launch_root"] == launch_root.as_posix()
