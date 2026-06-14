"""Audio transcript progress projection helpers.

Purpose:
    Project service-owned chunk plans and accepted checkpoints into public
    audio progress fields without using heartbeat freshness as numeric work.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime` while executing
      Task 357 checkpointed audio transcript jobs.
    - Consumes chunk plans from `infrastructure.audio_transcript_chunking` and
      emits `AudioProgressUpdateV2` records for the runtime job runner.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from math import ceil

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_chunking import (
    AudioChunkPlan,
    AudioChunkWindow,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    AudioProgressUpdateV2,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_AUDIO_ALIGNMENT_MS,
    TIMING_KEY_AUDIO_DIARIZATION_MS,
    TIMING_KEY_AUDIO_PACKAGING_MS,
    TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS,
    TIMING_KEY_AUDIO_TRANSCRIPTION_MS,
)

AUDIO_PIPELINE_PERCENT_DIARIZING = 15.0
AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START = 35.0
AUDIO_PIPELINE_PERCENT_TRANSCRIBING_END = 85.0
AUDIO_PIPELINE_PERCENT_ALIGNING = 90.0
AUDIO_PIPELINE_PERCENT_PACKAGING = 95.0
AUDIO_PIPELINE_PERCENT_COMPLETE = 100.0

_AUDIO_ESTIMATE_TIMING_KEYS = (
    TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS,
    TIMING_KEY_AUDIO_DIARIZATION_MS,
    TIMING_KEY_AUDIO_TRANSCRIPTION_MS,
    TIMING_KEY_AUDIO_ALIGNMENT_MS,
    TIMING_KEY_AUDIO_PACKAGING_MS,
)


def emit_progress(
    callback: Callable[[AudioProgressUpdateV2], None] | None,
    update: AudioProgressUpdateV2,
) -> None:
    """Emit one audio progress update when a callback is available."""

    if callback is not None:
        callback(update)


def pipeline_eta_seconds(
    *,
    phase_timings_ms: Mapping[str, int],
    pipeline_percent_complete: float | None,
) -> int | None:
    """Estimate full-pipeline ETA from explicit phase timing checkpoints."""

    if pipeline_percent_complete is None or pipeline_percent_complete <= 0.0:
        return None
    if pipeline_percent_complete >= AUDIO_PIPELINE_PERCENT_COMPLETE:
        return 0
    measured_ms = 0
    for key in _AUDIO_ESTIMATE_TIMING_KEYS:
        value = phase_timings_ms.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            measured_ms += max(0, value)
    remaining_ratio = (
        AUDIO_PIPELINE_PERCENT_COMPLETE - pipeline_percent_complete
    ) / pipeline_percent_complete
    return max(0, ceil((measured_ms * remaining_ratio) / 1000.0))


def emit_phase_progress(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    stage: str,
    phase_timings_ms: Mapping[str, int],
    audio_pipeline_percent_complete: float | None,
    audio_total_media_seconds: float | None = None,
    audio_processed_media_seconds: float | None = None,
    audio_percent_complete: float | None = None,
    audio_current_chunk_index: int | None = None,
    audio_total_chunks: int | None = None,
) -> None:
    """Emit progress for an explicit audio phase transition or timing checkpoint."""

    emit_progress(
        progress_callback,
        AudioProgressUpdateV2(
            stage=stage,
            audio_total_media_seconds=audio_total_media_seconds,
            audio_processed_media_seconds=audio_processed_media_seconds,
            audio_percent_complete=audio_percent_complete,
            audio_current_chunk_index=audio_current_chunk_index,
            audio_total_chunks=audio_total_chunks,
            audio_pipeline_percent_complete=audio_pipeline_percent_complete,
            audio_pipeline_eta_seconds=pipeline_eta_seconds(
                phase_timings_ms=phase_timings_ms,
                pipeline_percent_complete=audio_pipeline_percent_complete,
            ),
            phase_timings_ms=dict(phase_timings_ms),
        ),
    )


def emit_diarizing_progress(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    plan: AudioChunkPlan,
    phase_timings_ms: Mapping[str, int],
) -> None:
    """Emit planned totals and a diarizing stage before the blocking sidecar call."""

    emit_phase_progress(
        progress_callback=progress_callback,
        stage="diarizing",
        phase_timings_ms=phase_timings_ms,
        audio_pipeline_percent_complete=AUDIO_PIPELINE_PERCENT_DIARIZING,
        audio_total_media_seconds=plan.total_media_seconds,
        audio_processed_media_seconds=0.0,
        audio_percent_complete=0.0,
        audio_current_chunk_index=0,
        audio_total_chunks=plan.total_chunks,
    )


def emit_planned_progress(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    plan: AudioChunkPlan,
    phase_timings_ms: Mapping[str, int] | None = None,
) -> None:
    """Emit initial non-null audio totals after probe and chunk planning."""

    timings = dict(phase_timings_ms or {})
    emit_phase_progress(
        progress_callback=progress_callback,
        stage="transcribing",
        phase_timings_ms=timings,
        audio_pipeline_percent_complete=AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START,
        audio_total_media_seconds=plan.total_media_seconds,
        audio_processed_media_seconds=0.0,
        audio_percent_complete=0.0,
        audio_current_chunk_index=0,
        audio_total_chunks=plan.total_chunks,
    )


def emit_chunk_progress(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    plan: AudioChunkPlan,
    chunk: AudioChunkWindow,
    phase_timings_ms: Mapping[str, int] | None = None,
) -> None:
    """Emit monotonic progress after a chunk has been accepted."""

    processed_seconds = min(plan.total_media_seconds, chunk.end_seconds)
    percent_complete = (
        (processed_seconds / plan.total_media_seconds) * 100.0
        if plan.total_media_seconds > 0.0
        else 100.0
    )
    chunk_fraction = (
        processed_seconds / plan.total_media_seconds if plan.total_media_seconds > 0.0 else 1.0
    )
    pipeline_percent_complete = AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START + (
        (AUDIO_PIPELINE_PERCENT_TRANSCRIBING_END - AUDIO_PIPELINE_PERCENT_TRANSCRIBING_START)
        * chunk_fraction
    )
    emit_phase_progress(
        progress_callback=progress_callback,
        stage="transcribing",
        phase_timings_ms=dict(phase_timings_ms or {}),
        audio_pipeline_percent_complete=min(
            AUDIO_PIPELINE_PERCENT_TRANSCRIBING_END,
            pipeline_percent_complete,
        ),
        audio_total_media_seconds=plan.total_media_seconds,
        audio_processed_media_seconds=processed_seconds,
        audio_percent_complete=min(100.0, percent_complete),
        audio_current_chunk_index=min(chunk.chunk_index, plan.total_chunks - 1),
        audio_total_chunks=plan.total_chunks,
    )
