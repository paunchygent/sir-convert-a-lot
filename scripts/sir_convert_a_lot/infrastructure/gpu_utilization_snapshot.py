"""GPU utilization snapshot helpers for v2 conversion telemetry.

Purpose:
    Provide best-effort, bounded parsing of runtime GPU utilization tools so
    v2 conversion metadata can include lightweight utilization evidence for
    production tuning.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` when persisting successful
      job conversion metadata.
    - Complements `infrastructure.gpu_runtime_probe` runtime-kind detection.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Literal

DEFAULT_GPU_SNAPSHOT_TIMEOUT_SECONDS = 1.0


@dataclass(frozen=True)
class GpuUtilizationSnapshot:
    """Best-effort utilization snapshot from ROCm or CUDA host tooling."""

    runtime_kind: Literal["rocm", "cuda"]
    gpu_busy_percent: int | None
    gpu_memory_used_percent: int | None


class GpuUtilizationSnapshotTimeoutError(RuntimeError):
    """Raised when GPU snapshot host tooling exceeds the configured timeout."""


def _clamp_percent(value: int) -> int:
    return max(0, min(100, int(value)))


def parse_rocm_gpu_busy_percent(smi_output: str) -> int | None:
    """Parse max GPU busy percent from `rocm-smi --showuse` output."""
    values: list[int] = []
    for match in re.finditer(r"GPU use \(%\):\s*([0-9]+)", smi_output):
        values.append(_clamp_percent(int(match.group(1))))
    if len(values) == 0:
        return None
    return max(values)


def parse_rocm_gpu_memory_percent(smi_output: str) -> int | None:
    """Parse max GPU memory percent from `rocm-smi --showmemuse` output."""
    values: list[int] = []
    patterns = (
        r"GPU memory use \(%\):\s*([0-9]+)",
        r"GPU Memory Allocated \(VRAM%\):\s*([0-9]+)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, smi_output):
            values.append(_clamp_percent(int(match.group(1))))
    if len(values) == 0:
        return None
    return max(values)


def _parse_nvidia_gpu_snapshot(csv_output: str) -> tuple[int | None, int | None]:
    busy_values: list[int] = []
    memory_values: list[int] = []
    for raw_line in csv_output.splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            busy = int(parts[0])
            memory_used_mb = int(parts[1])
            memory_total_mb = int(parts[2])
        except ValueError:
            continue
        if memory_total_mb <= 0:
            continue
        busy_values.append(_clamp_percent(busy))
        memory_ratio = int(round((float(memory_used_mb) / float(memory_total_mb)) * 100.0))
        memory_values.append(_clamp_percent(memory_ratio))
    busy_percent = max(busy_values) if len(busy_values) > 0 else None
    memory_percent = max(memory_values) if len(memory_values) > 0 else None
    return busy_percent, memory_percent


def _sample_rocm_snapshot(*, timeout_seconds: float) -> GpuUtilizationSnapshot | None:
    try:
        result = subprocess.run(
            ["rocm-smi", "--showuse", "--showmemuse"],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(0.05, float(timeout_seconds)),
        )
    except subprocess.TimeoutExpired as exc:
        raise GpuUtilizationSnapshotTimeoutError("rocm-smi snapshot timed out") from exc
    except OSError:
        return None
    output = result.stdout
    busy_percent = parse_rocm_gpu_busy_percent(output)
    memory_percent = parse_rocm_gpu_memory_percent(output)
    if busy_percent is None and memory_percent is None:
        return None
    return GpuUtilizationSnapshot(
        runtime_kind="rocm",
        gpu_busy_percent=busy_percent,
        gpu_memory_used_percent=memory_percent,
    )


def _sample_cuda_snapshot(*, timeout_seconds: float) -> GpuUtilizationSnapshot | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(0.05, float(timeout_seconds)),
        )
    except subprocess.TimeoutExpired as exc:
        raise GpuUtilizationSnapshotTimeoutError("nvidia-smi snapshot timed out") from exc
    except OSError:
        return None
    busy_percent, memory_percent = _parse_nvidia_gpu_snapshot(result.stdout)
    if busy_percent is None and memory_percent is None:
        return None
    return GpuUtilizationSnapshot(
        runtime_kind="cuda",
        gpu_busy_percent=busy_percent,
        gpu_memory_used_percent=memory_percent,
    )


def sample_gpu_utilization_snapshot(
    *,
    runtime_kind: Literal["rocm", "cuda", "none"],
    timeout_seconds: float = DEFAULT_GPU_SNAPSHOT_TIMEOUT_SECONDS,
) -> GpuUtilizationSnapshot | None:
    """Sample host GPU utilization for the supplied runtime kind."""
    if runtime_kind == "rocm":
        return _sample_rocm_snapshot(timeout_seconds=timeout_seconds)
    if runtime_kind == "cuda":
        return _sample_cuda_snapshot(timeout_seconds=timeout_seconds)
    return None
