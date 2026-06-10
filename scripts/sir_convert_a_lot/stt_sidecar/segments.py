"""Segment projection helpers for the STT sidecar.

Purpose:
    Convert backend transcription and diarization objects into provider-neutral
    transcript segment records with bounded speaker labels and timing metadata.

Relationships:
    - Used by `stt_sidecar.runtime` after FasterWhisper and pyannote execution.
    - Raises sidecar request errors for invalid backend segment shapes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """Provider-neutral transcript segment used in sidecar responses."""

    segment_id: str
    start_seconds: float
    end_seconds: float
    speaker_label: str
    text: str
    language: str
    confidence: float | None


@dataclass(frozen=True, slots=True)
class SpeakerSegment:
    """Diarized speaker interval projected from pyannote output."""

    start_seconds: float
    end_seconds: float
    speaker_label: str


def speaker_segments(diarization: object) -> list[SpeakerSegment]:
    """Project pyannote diarization intervals into speaker segments."""
    itertracks = getattr(diarization, "itertracks")
    speakers: list[SpeakerSegment] = []
    for item in itertracks(yield_label=True):
        if not isinstance(item, tuple) or len(item) != 3:
            continue
        segment_obj = item[0]
        speaker_obj = item[2]
        speakers.append(
            SpeakerSegment(
                start_seconds=float_attr(segment_obj, "start"),
                end_seconds=float_attr(segment_obj, "end"),
                speaker_label=str(speaker_obj),
            )
        )
    return speakers


def speaker_for_segment(segment: TranscriptSegment, speakers: list[SpeakerSegment]) -> str:
    """Return the diarized speaker label covering a transcript segment."""
    midpoint = segment.start_seconds + ((segment.end_seconds - segment.start_seconds) / 2.0)
    for speaker in speakers:
        if speaker.start_seconds <= midpoint <= speaker.end_seconds:
            return speaker.speaker_label
    return speakers[0].speaker_label


def detected_language(segments: list[TranscriptSegment], *, requested: str | None) -> str:
    """Return the detected language for the response language block."""
    if requested is not None:
        return requested
    for segment in segments:
        if segment.language in {"sv", "en"}:
            return segment.language
    return "auto"


def confidence(segment_obj: object) -> float | None:
    """Return average word probability when the backend supplied it."""
    words = getattr(segment_obj, "words", None)
    if not isinstance(words, Iterable):
        return None
    probabilities: list[float] = []
    for word in words:
        probability = getattr(word, "probability", None)
        if isinstance(probability, int | float) and not isinstance(probability, bool):
            probabilities.append(float(probability))
    if not probabilities:
        return None
    return sum(probabilities) / len(probabilities)


def float_attr(value: object, name: str) -> float:
    """Return a numeric backend attribute or raise a transcript failure."""
    raw = getattr(value, name, None)
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return float(raw)
    raise SttSidecarRequestError(
        code="audio_transcription_failed",
        message="Backend returned an invalid segment boundary.",
        status_code=502,
    )


def string_attr(value: object, name: str, *, fallback: str) -> str:
    """Return a non-empty backend string attribute or fallback."""
    raw = getattr(value, name, None)
    if isinstance(raw, str) and raw.strip() != "":
        return raw
    return fallback
