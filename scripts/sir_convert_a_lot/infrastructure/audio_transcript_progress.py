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

from collections.abc import Callable

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_chunking import (
    AudioChunkPlan,
    AudioChunkWindow,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    AudioProgressUpdateV2,
)


def emit_progress(
    callback: Callable[[AudioProgressUpdateV2], None] | None,
    update: AudioProgressUpdateV2,
) -> None:
    """Emit one audio progress update when a callback is available."""

    if callback is not None:
        callback(update)


def emit_planned_progress(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    plan: AudioChunkPlan,
) -> None:
    """Emit initial non-null audio totals after probe and chunk planning."""

    emit_progress(
        progress_callback,
        AudioProgressUpdateV2(
            stage="transcribing",
            audio_total_media_seconds=plan.total_media_seconds,
            audio_processed_media_seconds=0.0,
            audio_percent_complete=0.0,
            audio_current_chunk_index=0,
            audio_total_chunks=plan.total_chunks,
        ),
    )


def emit_chunk_progress(
    *,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    plan: AudioChunkPlan,
    chunk: AudioChunkWindow,
) -> None:
    """Emit monotonic progress after a chunk has been accepted."""

    processed_seconds = min(plan.total_media_seconds, chunk.end_seconds)
    percent_complete = (
        (processed_seconds / plan.total_media_seconds) * 100.0
        if plan.total_media_seconds > 0.0
        else 100.0
    )
    emit_progress(
        progress_callback,
        AudioProgressUpdateV2(
            stage="transcribing",
            audio_total_media_seconds=plan.total_media_seconds,
            audio_processed_media_seconds=processed_seconds,
            audio_percent_complete=min(100.0, percent_complete),
            audio_current_chunk_index=min(chunk.chunk_index, plan.total_chunks - 1),
            audio_total_chunks=plan.total_chunks,
        ),
    )
