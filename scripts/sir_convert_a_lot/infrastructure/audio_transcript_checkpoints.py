"""Audio transcript checkpoint persistence.

Purpose:
    Persist accepted audio chunk outputs durably enough for retry and
    idempotent replay to skip completed chunks and merge transcript segments
    without duplication.

Relationships:
    - Consumed by `infrastructure.audio_transcript_bundle_runtime`.
    - References chunk windows from `infrastructure.audio_transcript_chunking`
      and stores only bounded metadata plus accepted segment/window ids.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_chunking import (
    AudioChunkWindow,
)
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import atomic_write_json

CHECKPOINT_FILENAME = "audio_chunk_checkpoints.json"


@dataclass(frozen=True, slots=True)
class AcceptedAudioChunkCheckpoint:
    """Durable accepted state for one completed audio chunk."""

    source_media_sha256: str
    normalized_audio_sha256: str
    chunk: AudioChunkWindow
    processing_profile: str
    transcript_segments: tuple[dict[str, object], ...]
    accepted_transcription_segment_ids: tuple[str, ...]
    accepted_diarization_window_ids: tuple[str, ...]
    alignment_validated: bool

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe checkpoint payload."""

        return {
            "source_media_sha256": self.source_media_sha256,
            "normalized_audio_sha256": self.normalized_audio_sha256,
            "chunk": self.chunk.to_payload(),
            "processing_profile": self.processing_profile,
            "transcript_segments": list(self.transcript_segments),
            "accepted_transcription_segment_ids": list(self.accepted_transcription_segment_ids),
            "accepted_diarization_window_ids": list(self.accepted_diarization_window_ids),
            "alignment_validated": self.alignment_validated,
        }


class AudioTranscriptCheckpointStore:
    """Filesystem-backed checkpoint store for one audio transcript job."""

    def __init__(self, *, artifact_path: Path) -> None:
        self._checkpoint_path = artifact_path.parent / CHECKPOINT_FILENAME
        self._checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def checkpoint_path(self) -> Path:
        """Return the concrete checkpoint JSON path."""

        return self._checkpoint_path

    def load(self) -> dict[int, AcceptedAudioChunkCheckpoint]:
        """Load accepted checkpoints keyed by chunk index."""

        if not self._checkpoint_path.exists():
            return {}
        payload = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        checkpoints_obj = payload.get("checkpoints")
        if not isinstance(checkpoints_obj, list):
            return {}
        checkpoints: dict[int, AcceptedAudioChunkCheckpoint] = {}
        for entry in checkpoints_obj:
            checkpoint = _checkpoint_from_payload(entry)
            if checkpoint is not None:
                checkpoints[checkpoint.chunk.chunk_index] = checkpoint
        return checkpoints

    def save_all(self, checkpoints: dict[int, AcceptedAudioChunkCheckpoint]) -> None:
        """Persist all accepted checkpoints atomically."""

        ordered = [checkpoints[index].to_payload() for index in sorted(checkpoints)]
        atomic_write_json(self._checkpoint_path, {"checkpoints": ordered})

    def purge(self) -> None:
        """Remove partial checkpoint state for failed or canceled jobs."""

        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()


def _checkpoint_from_payload(payload: object) -> AcceptedAudioChunkCheckpoint | None:
    if not isinstance(payload, dict):
        return None
    chunk_obj = payload.get("chunk")
    if not isinstance(chunk_obj, dict):
        return None
    chunk_index = _int_value(chunk_obj.get("chunk_index"))
    start_seconds = _float_value(chunk_obj.get("start_seconds"))
    end_seconds = _float_value(chunk_obj.get("end_seconds"))
    overlap_seconds = _float_value(chunk_obj.get("overlap_seconds"))
    if chunk_index is None or start_seconds is None or end_seconds is None:
        return None
    segments_obj = payload.get("transcript_segments")
    if not isinstance(segments_obj, list):
        return None
    segment_payloads = tuple(dict(segment) for segment in segments_obj if isinstance(segment, dict))
    return AcceptedAudioChunkCheckpoint(
        source_media_sha256=_string_value(payload.get("source_media_sha256")),
        normalized_audio_sha256=_string_value(payload.get("normalized_audio_sha256")),
        chunk=AudioChunkWindow(
            chunk_index=chunk_index,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            overlap_seconds=overlap_seconds or 0.0,
        ),
        processing_profile=_string_value(payload.get("processing_profile")),
        transcript_segments=segment_payloads,
        accepted_transcription_segment_ids=_string_tuple(
            payload.get("accepted_transcription_segment_ids")
        ),
        accepted_diarization_window_ids=_string_tuple(
            payload.get("accepted_diarization_window_ids")
        ),
        alignment_validated=payload.get("alignment_validated") is True,
    )


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _int_value(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _float_value(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None
