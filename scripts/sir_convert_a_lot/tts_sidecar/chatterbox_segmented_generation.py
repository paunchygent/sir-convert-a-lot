"""Deterministic segmented generation helpers for Chatterbox long-form audio.

Purpose:
    Provide one repo-owned segmentation and stitching layer for Chatterbox so
    longer normal-text synthesis can stay on the documented text-input path
    while avoiding a single oversized `model.generate(...)` call.

Relationships:
    - Called by `chatterbox_runtime.py` when segmented generation is enabled.
    - Keeps segmentation, chunk execution, and stitching outside the benchmark
      runners so the sidecar remains the canonical synthesis behavior.
"""

from __future__ import annotations

import json
import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import numpy as np

from scripts.sir_convert_a_lot.tts_sidecar.contracts import SidecarRequestError

if TYPE_CHECKING:
    import torch

_HARD_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")
_SOFT_BOUNDARY_RE = re.compile(r"(?<=[,;:])\s+")


@dataclass(frozen=True)
class SegmentGenerationSettings:
    """Internal segmented-generation settings for the Chatterbox sidecar."""

    enabled: bool
    max_chars: int
    cross_fade_ms: int
    debug_dir: Path | None


@dataclass(frozen=True)
class SegmentPlan:
    """Deterministic plan for one segmented synthesis request."""

    original_text: str
    segment_count: int
    segments: list[str]
    max_chars: int
    cross_fade_ms: int


def generate_audio_bytes(
    *,
    generate_fn: Callable[..., torch.Tensor] | None,
    sample_rate_hz: int,
    generate_kwargs: dict[str, object],
    settings: SegmentGenerationSettings,
) -> bytes:
    """Run one segmented or single-pass generation request and return WAV bytes."""
    text = str(generate_kwargs["text"])
    if not settings.enabled:
        waveform = _run_generate_tensor(generate_fn, generate_kwargs)
        return _wave_bytes_from_waveform(waveform, sample_rate_hz=sample_rate_hz)

    plan = build_segment_plan(
        text=text,
        max_chars=settings.max_chars,
        cross_fade_ms=settings.cross_fade_ms,
    )
    waveforms: list[torch.Tensor] = []
    for segment in plan.segments:
        segment_kwargs = dict(generate_kwargs)
        segment_kwargs["text"] = segment
        waveforms.append(_run_generate_tensor(generate_fn, segment_kwargs))
    stitched_waveform = stitch_waveforms(
        waveforms=waveforms,
        sample_rate_hz=sample_rate_hz,
        cross_fade_ms=settings.cross_fade_ms,
    )
    _write_debug_artifacts(
        plan=plan,
        waveforms=waveforms,
        stitched_waveform=stitched_waveform,
        sample_rate_hz=sample_rate_hz,
        debug_dir=settings.debug_dir,
    )
    return _wave_bytes_from_waveform(stitched_waveform, sample_rate_hz=sample_rate_hz)


def build_segment_plan(*, text: str, max_chars: int, cross_fade_ms: int) -> SegmentPlan:
    """Build one deterministic segment plan from normal text."""
    stripped = text.strip()
    if stripped == "":
        raise SidecarRequestError(
            code="empty_text",
            message="The synthesis request text is empty after normalization.",
            status_code=422,
        )
    segments = _segment_text(stripped, max_chars=max_chars)
    return SegmentPlan(
        original_text=stripped,
        segment_count=len(segments),
        segments=segments,
        max_chars=max_chars,
        cross_fade_ms=cross_fade_ms,
    )


def stitch_waveforms(
    *,
    waveforms: list[torch.Tensor],
    sample_rate_hz: int,
    cross_fade_ms: int,
) -> torch.Tensor:
    """Stitch per-segment waveforms into one mono waveform tensor."""
    if len(waveforms) == 0:
        raise SidecarRequestError(
            code="missing_segment_waveforms",
            message="No segment waveforms were produced for stitching.",
            status_code=500,
        )
    if len(waveforms) == 1:
        return _normalize_waveform_tensor(waveforms[0])
    cross_fade_samples = max(int(round(sample_rate_hz * (cross_fade_ms / 1000.0))), 0)
    stitched = _tensor_to_numpy(_normalize_waveform_tensor(waveforms[0]))
    for waveform in waveforms[1:]:
        next_waveform = _tensor_to_numpy(_normalize_waveform_tensor(waveform))
        overlap = min(cross_fade_samples, stitched.shape[0], next_waveform.shape[0])
        if overlap <= 0:
            stitched = np.concatenate([stitched, next_waveform])
            continue
        fade_out = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
        blended = (stitched[-overlap:] * fade_out) + (next_waveform[:overlap] * fade_in)
        stitched = np.concatenate([stitched[:-overlap], blended, next_waveform[overlap:]])
    from torch import from_numpy

    return from_numpy(stitched.astype(np.float32, copy=False)).unsqueeze(0)


def _segment_text(text: str, *, max_chars: int) -> list[str]:
    """Split text deterministically on sentence and softer boundary heuristics."""
    sentences = _split_text_with_pattern(text, _HARD_BOUNDARY_RE)
    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0
    for sentence in sentences:
        normalized_sentence = sentence.strip()
        if normalized_sentence == "":
            continue
        sentence_parts = _expand_oversized_unit(normalized_sentence, max_chars=max_chars)
        for part in sentence_parts:
            if current_parts and current_length + 1 + len(part) > max_chars:
                chunks.append(" ".join(current_parts))
                current_parts = [part]
                current_length = len(part)
                continue
            if not current_parts:
                current_parts = [part]
                current_length = len(part)
                continue
            current_parts.append(part)
            current_length += 1 + len(part)
    if current_parts:
        chunks.append(" ".join(current_parts))
    return chunks if chunks else [text]


def _expand_oversized_unit(text: str, *, max_chars: int) -> list[str]:
    """Split an oversized sentence first on soft punctuation, then on words."""
    if len(text) <= max_chars:
        return [text]
    clauses = _split_text_with_pattern(text, _SOFT_BOUNDARY_RE)
    if len(clauses) > 1:
        segments: list[str] = []
        for clause in clauses:
            segments.extend(_expand_oversized_unit(clause.strip(), max_chars=max_chars))
        return segments
    words = text.split()
    if len(words) <= 1:
        return [text]
    segments = []
    current_words: list[str] = []
    current_length = 0
    for word in words:
        proposed_length = len(word) if not current_words else current_length + 1 + len(word)
        if current_words and proposed_length > max_chars:
            segments.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
            continue
        current_words.append(word)
        current_length = proposed_length
    if current_words:
        segments.append(" ".join(current_words))
    return segments


def _split_text_with_pattern(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Split text while preserving punctuation in the preceding segment."""
    parts = [part.strip() for part in pattern.split(text.strip())]
    return [part for part in parts if part != ""]


def _run_generate_tensor(
    generate_fn: Callable[..., torch.Tensor] | None,
    generate_kwargs: dict[str, object],
) -> torch.Tensor:
    """Run one Chatterbox generation call and return the waveform tensor."""
    if generate_fn is None:
        raise RuntimeError("Chatterbox generate function was not initialized.")
    try:
        return generate_fn(**generate_kwargs)
    except ValueError as exc:
        raise SidecarRequestError(
            code="invalid_generation_request",
            message=str(exc),
            status_code=422,
        ) from exc
    except AssertionError as exc:
        raise SidecarRequestError(
            code="missing_conditionals",
            message=str(exc),
            status_code=422,
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive runtime envelope
        raise SidecarRequestError(
            code="chatterbox_generate_failed",
            message=f"Chatterbox generation failed: {exc}",
            status_code=500,
        ) from exc


def _normalize_waveform_tensor(waveform: torch.Tensor) -> torch.Tensor:
    """Normalize one waveform tensor into shape `(1, samples)`."""
    tensor = getattr(waveform, "detach", lambda: waveform)()
    tensor = getattr(tensor, "cpu", lambda: tensor)()
    tensor = getattr(tensor, "float", lambda: tensor)()
    if getattr(tensor, "ndim", None) == 1:
        tensor = tensor.unsqueeze(0)
    if getattr(tensor, "ndim", None) != 2:
        raise RuntimeError("Expected a 2D waveform tensor from Chatterbox generate().")
    if tensor.shape[0] > 1:
        tensor = tensor[:1, :]
    return tensor


def _tensor_to_numpy(waveform: torch.Tensor) -> np.ndarray:
    """Convert one normalized waveform tensor into a mono numpy array."""
    clipped = waveform.clamp(-1.0, 1.0)
    return clipped.squeeze(0).numpy().astype(np.float32, copy=False)


def _wave_bytes_from_waveform(waveform: torch.Tensor, *, sample_rate_hz: int) -> bytes:
    """Serialize one waveform tensor into deterministic mono WAV bytes."""
    pcm16 = (_tensor_to_numpy(_normalize_waveform_tensor(waveform)) * 32767.0).round().astype("<i2")
    return _wave_bytes_from_pcm16(pcm16=pcm16, sample_rate_hz=sample_rate_hz)


def _wave_bytes_from_pcm16(*, pcm16: np.ndarray, sample_rate_hz: int) -> bytes:
    """Serialize one PCM16 mono array into deterministic WAV bytes."""
    from io import BytesIO

    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate_hz)
            wav_file.writeframes(pcm16.tobytes())
        return buffer.getvalue()


def _write_debug_artifacts(
    *,
    plan: SegmentPlan,
    waveforms: list[torch.Tensor],
    stitched_waveform: torch.Tensor,
    sample_rate_hz: int,
    debug_dir: Path | None,
) -> None:
    """Write deterministic segment-plan and chunk artifacts when requested."""
    if debug_dir is None:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / "segment_plan.json").write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for index, waveform in enumerate(waveforms, start=1):
        chunk_bytes = _wave_bytes_from_waveform(waveform, sample_rate_hz=sample_rate_hz)
        (debug_dir / f"chunk_{index:02d}.wav").write_bytes(chunk_bytes)
    (debug_dir / "stitched.wav").write_bytes(
        _wave_bytes_from_waveform(stitched_waveform, sample_rate_hz=sample_rate_hz)
    )
