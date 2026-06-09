"""Tests for Linux host CPU and RAM snapshots used by Hemma resource monitor."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.system_resource_snapshot import (
    HostResourceSampler,
)


def test_host_resource_sampler_reads_cpu_and_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sampler should derive host CPU and RAM percentages from procfs."""
    proc_stat_payloads = iter(
        [
            "cpu  100 0 100 700 0 0 0 0 0 0\n",
            "cpu  150 0 150 750 0 0 0 0 0 0\n",
        ]
    )
    meminfo_payload = "\n".join(
        [
            "MemTotal:       1000 kB",
            "MemAvailable:    300 kB",
        ]
    )

    def _fake_read_text(path: Path, *, encoding: str) -> str:
        del encoding
        if path.as_posix() == "/proc/stat":
            return next(proc_stat_payloads)
        if path.as_posix() == "/proc/meminfo":
            return meminfo_payload
        raise AssertionError(f"Unexpected procfs path: {path}")

    monkeypatch.setattr(Path, "read_text", _fake_read_text)

    sampler = HostResourceSampler()
    sample = sampler.sample()

    assert sample.host_cpu_busy_percent == 67
    assert sample.host_memory_used_percent == 70


def test_host_resource_sampler_handles_zero_delta_cpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sampler should emit `None` when CPU counters do not advance."""
    proc_stat_payloads = iter(
        [
            "cpu  100 0 100 700 0 0 0 0 0 0\n",
            "cpu  100 0 100 700 0 0 0 0 0 0\n",
        ]
    )
    meminfo_payload = "\n".join(
        [
            "MemTotal:       1000 kB",
            "MemAvailable:    400 kB",
        ]
    )

    def _fake_read_text(path: Path, *, encoding: str) -> str:
        del encoding
        if path.as_posix() == "/proc/stat":
            return next(proc_stat_payloads)
        if path.as_posix() == "/proc/meminfo":
            return meminfo_payload
        raise AssertionError(f"Unexpected procfs path: {path}")

    monkeypatch.setattr(Path, "read_text", _fake_read_text)

    sampler = HostResourceSampler()
    sample = sampler.sample()

    assert sample.host_cpu_busy_percent is None
    assert sample.host_memory_used_percent == 60


def test_host_resource_sampler_tolerates_missing_procfs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sampler should degrade to `None` values when procfs is unavailable."""

    def _raise_file_not_found(path: Path, *, encoding: str) -> str:
        del path, encoding
        raise FileNotFoundError("procfs unavailable")

    monkeypatch.setattr(Path, "read_text", _raise_file_not_found)

    sampler = HostResourceSampler()
    sample = sampler.sample()

    assert sample.host_cpu_busy_percent is None
    assert sample.host_memory_used_percent is None
