"""Unit tests for v2 GPU utilization snapshot helpers.

Purpose:
    Verify deterministic parsing and best-effort sampling behavior for ROCm and
    CUDA utilization snapshots used by v2 conversion metadata.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.gpu_utilization_snapshot`.
    - Protects runtime telemetry metadata enrichment in `runtime_engine_v2`.
"""

from __future__ import annotations

import subprocess

import pytest

from scripts.sir_convert_a_lot.infrastructure import gpu_utilization_snapshot


def test_parse_rocm_busy_and_memory_percent() -> None:
    output = """
GPU[0]          : GPU use (%): 31
GPU[0]          : GPU memory use (%): 44
GPU[1]          : GPU use (%): 67
GPU[1]          : GPU memory use (%): 40
"""
    assert gpu_utilization_snapshot.parse_rocm_gpu_busy_percent(output) == 67
    assert gpu_utilization_snapshot.parse_rocm_gpu_memory_percent(output) == 44


def test_parse_rocm_memory_percent_supports_vram_pattern() -> None:
    output = """
GPU[0]          : GPU Memory Allocated (VRAM%): 11
GPU[1]          : GPU Memory Allocated (VRAM%): 58
"""
    assert gpu_utilization_snapshot.parse_rocm_gpu_memory_percent(output) == 58


def test_sample_gpu_snapshot_returns_none_for_none_runtime_kind() -> None:
    snapshot = gpu_utilization_snapshot.sample_gpu_utilization_snapshot(runtime_kind="none")
    assert snapshot is None


def test_sample_rocm_snapshot_returns_none_when_command_missing(monkeypatch) -> None:
    def _raise_oserror(*_args: object, **_kwargs: object) -> str:
        raise OSError("missing rocm-smi")

    monkeypatch.setattr(gpu_utilization_snapshot.subprocess, "run", _raise_oserror)
    snapshot = gpu_utilization_snapshot.sample_gpu_utilization_snapshot(runtime_kind="rocm")
    assert snapshot is None


def test_sample_rocm_snapshot_passes_timeout_to_subprocess(monkeypatch) -> None:
    observed_timeout: float | None = None

    def _fake_run(*_args: object, **kwargs: object):
        nonlocal observed_timeout
        timeout_obj = kwargs.get("timeout")
        if isinstance(timeout_obj, (int, float)):
            observed_timeout = float(timeout_obj)
        else:
            observed_timeout = None
        raise OSError("missing rocm-smi")

    monkeypatch.setattr(gpu_utilization_snapshot.subprocess, "run", _fake_run)
    snapshot = gpu_utilization_snapshot.sample_gpu_utilization_snapshot(
        runtime_kind="rocm",
        timeout_seconds=2.5,
    )
    assert snapshot is None
    assert observed_timeout == pytest.approx(2.5)


def test_sample_cuda_snapshot_raises_typed_timeout(monkeypatch) -> None:
    def _raise_timeout(*_args: object, **kwargs: object):
        timeout_obj = kwargs.get("timeout")
        timeout_seconds = float(timeout_obj) if isinstance(timeout_obj, (int, float)) else 0.0
        raise subprocess.TimeoutExpired(
            cmd="nvidia-smi",
            timeout=timeout_seconds,
        )

    monkeypatch.setattr(gpu_utilization_snapshot.subprocess, "run", _raise_timeout)
    with pytest.raises(gpu_utilization_snapshot.GpuUtilizationSnapshotTimeoutError):
        gpu_utilization_snapshot.sample_gpu_utilization_snapshot(
            runtime_kind="cuda",
            timeout_seconds=1.25,
        )


def test_sample_cuda_snapshot_parses_csv_output(monkeypatch) -> None:
    class _Completed:
        returncode = 0
        stdout = "37, 1024, 4096\n11, 256, 4096\n"

    def _fake_run(*_args: object, **_kwargs: object) -> _Completed:
        return _Completed()

    monkeypatch.setattr(gpu_utilization_snapshot.subprocess, "run", _fake_run)
    snapshot = gpu_utilization_snapshot.sample_gpu_utilization_snapshot(runtime_kind="cuda")
    assert snapshot is not None
    assert snapshot.runtime_kind == "cuda"
    assert snapshot.gpu_busy_percent == 37
    assert snapshot.gpu_memory_used_percent == 25
