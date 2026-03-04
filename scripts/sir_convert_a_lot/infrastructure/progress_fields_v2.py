"""Shared parsing/normalization helpers for v2 job progress fields.

Purpose:
    Centralize best-effort parsing and monotonic update rules for the optional
    PDF-only page progress fields introduced by ADR-0005.

Relationships:
    - Used by v2 manifest parsing (`job_store_manifest_v2`) and lifecycle event
      parsing/serialization (`job_events_v2`).
    - Used by v2 job-store transition helpers (`job_store_v2_core`, `job_store_v2`)
      to enforce monotonic progress counters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ProgressPageFieldsV2:
    """Optional PDF-only page progress fields carried by v2 job payloads."""

    total_pages: int | None
    processed_pages: int | None
    failed_pages: int | None
    percent_complete: float | None
    pages_per_minute: float | None
    eta_seconds: int | None


def parse_optional_nonneg_int(value: object) -> int | None:
    """Parse a non-negative integer or return None when absent/invalid."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def parse_optional_nonneg_float(value: object) -> float | None:
    """Parse a non-negative float/int or return None when absent/invalid."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if parsed < 0.0:
        return None
    return parsed


def parse_optional_percent(value: object) -> float | None:
    """Parse a percent value in range 0..100 or return None when absent/invalid."""
    parsed = parse_optional_nonneg_float(value)
    if parsed is None:
        return None
    if parsed > 100.0:
        return None
    return parsed


def parse_progress_page_fields(progress: Mapping[str, object]) -> ProgressPageFieldsV2:
    """Parse the optional v2 progress page fields from a progress mapping."""
    return ProgressPageFieldsV2(
        total_pages=parse_optional_nonneg_int(progress.get("total_pages")),
        processed_pages=parse_optional_nonneg_int(progress.get("processed_pages")),
        failed_pages=parse_optional_nonneg_int(progress.get("failed_pages")),
        percent_complete=parse_optional_percent(progress.get("percent_complete")),
        pages_per_minute=parse_optional_nonneg_float(progress.get("pages_per_minute")),
        eta_seconds=parse_optional_nonneg_int(progress.get("eta_seconds")),
    )


def clamp_monotonic_int(previous: int | None, updated: int | None) -> int | None:
    """Apply monotonic non-decreasing semantics for integer counters."""
    if updated is None:
        return previous
    if previous is None:
        return updated
    return previous if updated < previous else updated


def clamp_monotonic_float(previous: float | None, updated: float | None) -> float | None:
    """Apply monotonic non-decreasing semantics for float percent counters."""
    if updated is None:
        return previous
    if previous is None:
        return updated
    return previous if updated < previous else updated
