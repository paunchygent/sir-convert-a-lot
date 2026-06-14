"""Shared parsing/normalization helpers for v2 job progress fields.

Purpose:
    Centralize best-effort parsing and monotonic update rules for the optional
    PDF page progress fields and route-specific audio progress fields.

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


def apply_audio_progress_update(
    progress: dict[str, object],
    *,
    audio_total_media_seconds: float | None,
    audio_processed_media_seconds: float | None,
    audio_percent_complete: float | None,
    audio_current_chunk_index: int | None,
    audio_total_chunks: int | None,
    audio_pipeline_percent_complete: float | None,
    audio_pipeline_eta_seconds: int | None,
) -> bool:
    """Apply monotonic route-specific audio progress fields in-place."""

    progress.setdefault("audio_total_media_seconds", None)
    progress.setdefault("audio_processed_media_seconds", None)
    progress.setdefault("audio_percent_complete", None)
    progress.setdefault("audio_current_chunk_index", None)
    progress.setdefault("audio_total_chunks", None)
    progress.setdefault("audio_pipeline_percent_complete", None)
    progress.setdefault("audio_pipeline_eta_seconds", None)

    progress_changed = False
    existing_audio_total = parse_optional_nonneg_float(progress.get("audio_total_media_seconds"))
    updated_audio_total = parse_optional_nonneg_float(audio_total_media_seconds)
    if updated_audio_total is not None and existing_audio_total is None and updated_audio_total > 0:
        progress["audio_total_media_seconds"] = updated_audio_total
        existing_audio_total = updated_audio_total
        progress_changed = True

    existing_audio_processed = parse_optional_nonneg_float(
        progress.get("audio_processed_media_seconds")
    )
    updated_audio_processed = parse_optional_nonneg_float(audio_processed_media_seconds)
    if existing_audio_total is not None and updated_audio_processed is not None:
        updated_audio_processed = min(updated_audio_processed, existing_audio_total)
    resolved_audio_processed = clamp_monotonic_float(
        existing_audio_processed,
        updated_audio_processed,
    )
    if resolved_audio_processed != existing_audio_processed:
        progress["audio_processed_media_seconds"] = resolved_audio_processed
        progress_changed = True

    existing_audio_percent = parse_optional_percent(progress.get("audio_percent_complete"))
    resolved_audio_percent = clamp_monotonic_float(
        existing_audio_percent,
        parse_optional_percent(audio_percent_complete),
    )
    if resolved_audio_percent != existing_audio_percent:
        progress["audio_percent_complete"] = resolved_audio_percent
        progress_changed = True

    existing_audio_chunk_index = parse_optional_nonneg_int(
        progress.get("audio_current_chunk_index")
    )
    resolved_audio_chunk_index = clamp_monotonic_int(
        existing_audio_chunk_index,
        parse_optional_nonneg_int(audio_current_chunk_index),
    )
    if resolved_audio_chunk_index != existing_audio_chunk_index:
        progress["audio_current_chunk_index"] = resolved_audio_chunk_index
        progress_changed = True

    existing_audio_total_chunks = parse_optional_nonneg_int(progress.get("audio_total_chunks"))
    updated_audio_total_chunks = parse_optional_nonneg_int(audio_total_chunks)
    if (
        updated_audio_total_chunks is not None
        and existing_audio_total_chunks is None
        and updated_audio_total_chunks >= 0
    ):
        progress["audio_total_chunks"] = updated_audio_total_chunks
        progress_changed = True

    existing_audio_pipeline_percent = parse_optional_percent(
        progress.get("audio_pipeline_percent_complete")
    )
    resolved_audio_pipeline_percent = clamp_monotonic_float(
        existing_audio_pipeline_percent,
        parse_optional_percent(audio_pipeline_percent_complete),
    )
    if resolved_audio_pipeline_percent != existing_audio_pipeline_percent:
        progress["audio_pipeline_percent_complete"] = resolved_audio_pipeline_percent
        progress_changed = True

    existing_audio_pipeline_eta = parse_optional_nonneg_int(
        progress.get("audio_pipeline_eta_seconds")
    )
    updated_audio_pipeline_eta = parse_optional_nonneg_int(audio_pipeline_eta_seconds)
    if (
        updated_audio_pipeline_eta is not None
        and updated_audio_pipeline_eta != existing_audio_pipeline_eta
    ):
        progress["audio_pipeline_eta_seconds"] = updated_audio_pipeline_eta
        progress_changed = True

    return progress_changed
