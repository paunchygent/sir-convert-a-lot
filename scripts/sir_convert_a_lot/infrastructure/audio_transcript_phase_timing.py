"""Audio transcript phase timing and pipeline progress helpers.

Purpose:
    Centralize Task-364 timing accumulation and current-phase progress
    projection so the audio transcript runtime can focus on sidecar orchestration
    and artifact packaging.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime` while executing
      `audio -> transcript_bundle` jobs.
    - Uses `infrastructure.audio_transcript_progress` to emit public progress
      updates with content-safe timing metadata.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_progress import (
    AUDIO_PIPELINE_PERCENT_TRANSCRIBING_END,
    AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START,
    emit_phase_progress,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    AudioProgressUpdateV2,
)


def record_phase_timing(
    *,
    phase_timings_ms: dict[str, int],
    key: str,
    started_at: float,
) -> None:
    """Accumulate one nonnegative elapsed phase timing."""

    elapsed_ms = max(0, int((time.perf_counter() - started_at) * 1000))
    phase_timings_ms[key] = phase_timings_ms.get(key, 0) + elapsed_ms


def current_transcription_pipeline_percent(
    *,
    total_media_seconds: float,
    processed_media_seconds: float,
) -> float:
    """Return the whole-pipeline estimate for accepted transcription coverage."""

    if total_media_seconds <= 0.0:
        return AUDIO_PIPELINE_PERCENT_TRANSCRIBING_END
    chunk_fraction = min(1.0, max(0.0, processed_media_seconds / total_media_seconds))
    return AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START + (
        (AUDIO_PIPELINE_PERCENT_TRANSCRIBING_END - AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START)
        * chunk_fraction
    )


def emit_audio_phase_checkpoint(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    stage: str,
    phase_timings_ms: dict[str, int],
    audio_pipeline_percent_complete: float,
    total_media_seconds: float,
    processed_media_seconds: float,
    current_chunk_index: int,
    total_chunks: int,
) -> None:
    """Emit one current audio phase checkpoint with observed media progress."""

    percent_complete = (
        (processed_media_seconds / total_media_seconds) * 100.0
        if total_media_seconds > 0.0
        else 100.0
    )
    emit_phase_progress(
        progress_callback=progress_callback,
        stage=stage,
        phase_timings_ms=phase_timings_ms,
        audio_pipeline_percent_complete=audio_pipeline_percent_complete,
        audio_total_media_seconds=total_media_seconds,
        audio_processed_media_seconds=min(total_media_seconds, processed_media_seconds),
        audio_percent_complete=min(100.0, percent_complete),
        audio_current_chunk_index=max(0, current_chunk_index),
        audio_total_chunks=total_chunks,
    )
