"""Audio transcript chunk planning domain model.

Purpose:
    Define deterministic service-owned audio chunk windows for transcript
    bundle execution so public progress and checkpoint state are derived from
    Sir Convert lifecycle decisions rather than provider telemetry.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime` before sidecar
      chunk transcription requests are scheduled.
    - Checkpoint records in `infrastructure.audio_transcript_checkpoints`
      reference these windows by chunk index and media hashes.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_AUDIO_CHUNK_SECONDS = 300.0
DEFAULT_AUDIO_CHUNK_OVERLAP_SECONDS = 0.0
CHECKPOINT_PROCESSING_PROFILE = "audio_chunk_v1_300s_global_diarization"


@dataclass(frozen=True, slots=True)
class AudioChunkWindow:
    """Deterministic audio chunk window owned by the main service."""

    chunk_index: int
    start_seconds: float
    end_seconds: float
    overlap_seconds: float

    @property
    def duration_seconds(self) -> float:
        """Return non-overlap media seconds represented by this chunk."""

        return max(0.0, self.end_seconds - self.start_seconds)

    def to_payload(self) -> dict[str, object]:
        """Return the provider-neutral payload sent to the sidecar."""

        return {
            "chunk_index": self.chunk_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "overlap_seconds": self.overlap_seconds,
            "processing_profile": CHECKPOINT_PROCESSING_PROFILE,
        }


@dataclass(frozen=True, slots=True)
class AudioChunkPlan:
    """Complete deterministic chunk plan for one normalized media source."""

    total_media_seconds: float
    chunks: tuple[AudioChunkWindow, ...]
    processing_profile: str

    @property
    def total_chunks(self) -> int:
        """Return the planned chunk count."""

        return len(self.chunks)


def plan_audio_chunks(
    *,
    total_media_seconds: float,
    chunk_seconds: float = DEFAULT_AUDIO_CHUNK_SECONDS,
) -> AudioChunkPlan:
    """Create a deterministic duration-based chunk plan for one source."""

    bounded_total = max(0.0, total_media_seconds)
    bounded_chunk_seconds = max(1.0, chunk_seconds)
    chunks: list[AudioChunkWindow] = []
    next_start = 0.0
    while next_start < bounded_total or not chunks:
        chunk_index = len(chunks)
        end_seconds = min(bounded_total, next_start + bounded_chunk_seconds)
        if end_seconds <= next_start:
            end_seconds = next_start
        chunks.append(
            AudioChunkWindow(
                chunk_index=chunk_index,
                start_seconds=round(next_start, 6),
                end_seconds=round(end_seconds, 6),
                overlap_seconds=DEFAULT_AUDIO_CHUNK_OVERLAP_SECONDS,
            )
        )
        if end_seconds >= bounded_total:
            break
        next_start = end_seconds
    return AudioChunkPlan(
        total_media_seconds=bounded_total,
        chunks=tuple(chunks),
        processing_profile=CHECKPOINT_PROCESSING_PROFILE,
    )
