"""Deterministic free-space helpers for Qwen checkpoint tests.

Purpose:
    Provide a typed disk-usage record for tests that exercise durable
    checkpoint capacity policy without depending on the host filesystem.

Relationships:
    - Used by Qwen training test fixtures and low-space checkpoint tests.
    - Mirrors the `free` attribute consumed by the patched checkpoint runtime.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FakeDiskUsage:
    """Minimal disk-usage record for deterministic checkpoint tests."""

    total: int
    used: int
    free: int


def fake_disk_usage(*, free: int) -> FakeDiskUsage:
    """Return one fake disk-usage record with the requested free byte count."""
    return FakeDiskUsage(total=free * 2, used=free, free=free)
