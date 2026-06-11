"""Audio transcript diarization alignment.

Purpose:
    Validate and align service-owned chunk transcript segments against global
    diarization windows before any canonical transcript JSON artifact can be
    persisted.

Relationships:
    - Used by `infrastructure.audio_transcript_bundle_runtime` after global
      sidecar diarization and each accepted chunk transcription.
    - Enforces ADR-0013 fail-closed diarization semantics for successful audio
      transcript jobs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError

PLACEHOLDER_SPEAKER_LABELS = frozenset(
    {
        "",
        "diarization_unavailable",
        "speaker",
        "speaker_unknown",
        "unknown",
    }
)


@dataclass(frozen=True, slots=True)
class DiarizationWindow:
    """Global diarization interval used for chunk transcript alignment."""

    window_id: str
    start_seconds: float
    end_seconds: float
    speaker_label: str


def parse_diarization_windows(payload: Mapping[str, object]) -> tuple[DiarizationWindow, ...]:
    """Parse and validate fail-closed global diarization windows."""

    diarization = _required_mapping(payload, "diarization")
    if _required_string(diarization, "status") != "succeeded":
        raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
    windows_obj = diarization.get("windows")
    if not isinstance(windows_obj, Sequence) or isinstance(windows_obj, str | bytes | bytearray):
        raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
    windows: list[DiarizationWindow] = []
    for entry in windows_obj:
        if not isinstance(entry, Mapping):
            raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
        speaker_label = _required_string(entry, "speaker_label")
        if speaker_label.strip().lower() in PLACEHOLDER_SPEAKER_LABELS:
            raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
        window = DiarizationWindow(
            window_id=_required_string(entry, "window_id"),
            start_seconds=_required_float(entry, "start_seconds"),
            end_seconds=_required_float(entry, "end_seconds"),
            speaker_label=speaker_label,
        )
        if window.end_seconds <= window.start_seconds:
            raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
        windows.append(window)
    if not windows:
        raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
    return tuple(windows)


def align_chunk_segments(
    *,
    segments: Sequence[object],
    diarization_windows: tuple[DiarizationWindow, ...],
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...], tuple[str, ...]]:
    """Align one chunk response to global diarization windows."""

    aligned: list[dict[str, object]] = []
    transcript_ids: list[str] = []
    diarization_ids: list[str] = []
    previous_end = 0.0
    for entry in segments:
        if not isinstance(entry, Mapping):
            raise _service_error(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        start_seconds = _required_float(entry, "start_seconds")
        end_seconds = _required_float(entry, "end_seconds")
        if start_seconds < previous_end or end_seconds <= start_seconds:
            raise _service_error(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)
        window = _window_for_segment(
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            windows=diarization_windows,
        )
        segment_id = _required_string(entry, "segment_id")
        transcript_ids.append(segment_id)
        diarization_ids.append(window.window_id)
        previous_end = end_seconds
        aligned.append(
            {
                "segment_id": segment_id,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "speaker_label": window.speaker_label,
                "text": _required_string(entry, "text"),
                "language": _optional_string(entry, "language"),
                "confidence": _optional_float(entry, "confidence"),
            }
        )
    if not aligned:
        raise _service_error(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
    return tuple(aligned), tuple(transcript_ids), tuple(diarization_ids)


def validate_global_segment_order(segments: Sequence[Mapping[str, object]]) -> None:
    """Validate final cross-chunk segment ordering before artifact persistence."""

    previous_end = 0.0
    seen_segment_ids: set[str] = set()
    for segment in segments:
        segment_id = _required_string(segment, "segment_id")
        if segment_id in seen_segment_ids:
            raise _service_error(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)
        seen_segment_ids.add(segment_id)
        start_seconds = _required_float(segment, "start_seconds")
        end_seconds = _required_float(segment, "end_seconds")
        if start_seconds < previous_end or end_seconds <= start_seconds:
            raise _service_error(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)
        previous_end = end_seconds


def _window_for_segment(
    *,
    start_seconds: float,
    end_seconds: float,
    windows: tuple[DiarizationWindow, ...],
) -> DiarizationWindow:
    midpoint = start_seconds + ((end_seconds - start_seconds) / 2.0)
    for window in windows:
        if window.start_seconds <= midpoint <= window.end_seconds:
            return window
    raise _service_error(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise _service_error(AudioTranscriptionErrorCode.DIARIZATION_FAILED)
    return {str(nested_key): nested_value for nested_key, nested_value in value.items()}


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    raise _service_error(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _required_float(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise _service_error(AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED)


def _optional_float(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _service_error(error_code: AudioTranscriptionErrorCode) -> ServiceError:
    return ServiceError(
        status_code=502,
        code=error_code.value,
        message="Audio transcript chunk alignment failed validation.",
        retryable=False,
    )
