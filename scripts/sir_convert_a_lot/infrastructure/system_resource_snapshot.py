"""Host CPU and RAM snapshot helpers for detached Hemma monitoring.

Purpose:
    Provide lightweight Linux host CPU and RAM sampling without introducing a
    new third-party dependency for bounded operational probes.

Relationships:
    - Used by `hemma_resource_monitor_runtime.py` so Hemma resource monitor can persist
      host CPU and RAM alongside GPU utilization for long preprocessing runs.
    - Reads `/proc/stat` and `/proc/meminfo`, so this helper is Linux-only by
      design and intended for Hemma execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HostResourceSnapshot:
    """One host CPU and RAM sample derived from Linux procfs."""

    host_cpu_busy_percent: int | None
    host_memory_used_percent: int | None


@dataclass(frozen=True)
class _HostCpuTimes:
    """One normalized CPU total and idle reading."""

    total_ticks: int
    idle_ticks: int


def _read_cpu_times() -> _HostCpuTimes:
    """Read aggregate CPU counters from `/proc/stat`."""
    cpu_line = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0]
    fields = cpu_line.split()
    if len(fields) < 5 or fields[0] != "cpu":
        raise RuntimeError("Unable to parse aggregate CPU counters from `/proc/stat`.")
    values = [int(value) for value in fields[1:]]
    idle_ticks = values[3] + (values[4] if len(values) > 4 else 0)
    return _HostCpuTimes(total_ticks=sum(values), idle_ticks=idle_ticks)


def _read_memory_used_percent() -> int:
    """Read host RAM utilization from `/proc/meminfo`."""
    payload: dict[str, int] = {}
    for raw_line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        parts = raw_line.split()
        if len(parts) < 2:
            continue
        key = parts[0].rstrip(":")
        payload[key] = int(parts[1])
    total_kib = payload.get("MemTotal")
    available_kib = payload.get("MemAvailable")
    if total_kib is None or available_kib is None or total_kib <= 0:
        raise RuntimeError("Unable to parse host RAM totals from `/proc/meminfo`.")
    used_ratio = (total_kib - available_kib) / total_kib
    return max(0, min(100, int(round(used_ratio * 100))))


class HostResourceSampler:
    """Stateful host CPU/RAM sampler for repeated monitor-loop snapshots."""

    def __init__(self) -> None:
        """Prime the sampler with the current CPU counters."""
        try:
            self._previous_cpu_times: _HostCpuTimes | None = _read_cpu_times()
        except (OSError, RuntimeError):
            self._previous_cpu_times = None

    def sample(self) -> HostResourceSnapshot:
        """Return one host CPU/RAM snapshot."""
        try:
            current_cpu_times: _HostCpuTimes | None = _read_cpu_times()
        except (OSError, RuntimeError):
            current_cpu_times = None
        host_cpu_busy_percent: int | None = None
        if current_cpu_times is not None and self._previous_cpu_times is not None:
            total_delta = current_cpu_times.total_ticks - self._previous_cpu_times.total_ticks
            idle_delta = current_cpu_times.idle_ticks - self._previous_cpu_times.idle_ticks
            if total_delta > 0:
                busy_ratio = 1.0 - (idle_delta / total_delta)
                host_cpu_busy_percent = max(0, min(100, int(round(busy_ratio * 100))))
        self._previous_cpu_times = current_cpu_times
        try:
            host_memory_used_percent = _read_memory_used_percent()
        except (OSError, RuntimeError):
            host_memory_used_percent = None
        return HostResourceSnapshot(
            host_cpu_busy_percent=host_cpu_busy_percent,
            host_memory_used_percent=host_memory_used_percent,
        )
