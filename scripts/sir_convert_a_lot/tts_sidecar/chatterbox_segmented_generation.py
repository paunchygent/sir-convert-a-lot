"""Deterministic segmented generation helpers for Chatterbox long-form audio.

Purpose:
    Provide one repo-owned segmentation and stitching layer for Chatterbox so
    longer normal-text synthesis can stay on the documented text-input path
    while avoiding a single oversized ``model.generate(...)`` call.

Relationships:
    - Called by ``chatterbox_runtime.py`` when segmented generation is enabled.
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
    stitch_mode: str


@dataclass(frozen=True)
class SegmentPlan:
    """Deterministic plan for one segmented synthesis request."""

    original_text: str
    segment_count: int
    segments: list[str]
    max_chars: int
    cross_fade_ms: int


@dataclass(frozen=True)
class ChunkAnalysis:
    """Per-chunk speech-edge analysis for debug evidence."""

    chunk_index: int
    text: str
    leading_trim_ms: float
    trailing_trim_ms: float
    original_duration_ms: float
    processed_duration_ms: float


@dataclass(frozen=True)
class BoundaryDecision:
    """Per-boundary stitch decision for debug evidence."""

    boundary_index: int
    boundary_type: str
    previous_chunk_index: int
    next_chunk_index: int
    inserted_pause_ms: float
    edge_fade_ms: float
    previous_trailing_trim_ms: float
    next_leading_trim_ms: float


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
        segment_texts=plan.segments,
        stitch_mode=settings.stitch_mode,
    )
    _write_debug_artifacts(
        plan=plan,
        waveforms=waveforms,
        stitched_result=stitched_waveform,
        sample_rate_hz=sample_rate_hz,
        debug_dir=settings.debug_dir,
    )
    return _wave_bytes_from_waveform(stitched_waveform.waveform, sample_rate_hz=sample_rate_hz)


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
    segment_texts: list[str],
    stitch_mode: str,
) -> "StitchResult":
    """Stitch per-segment waveforms into one mono waveform tensor."""
    if len(waveforms) == 0:
        raise SidecarRequestError(
            code="missing_segment_waveforms",
            message="No segment waveforms were produced for stitching.",
            status_code=500,
        )
    if len(waveforms) == 1:
        waveform = _normalize_waveform_tensor(waveforms[0])
        return StitchResult(
            waveform=waveform,
            processed_waveforms=[_tensor_to_numpy(waveform)],
            chunk_analyses=[
                ChunkAnalysis(
                    chunk_index=1,
                    text=segment_texts[0],
                    leading_trim_ms=0.0,
                    trailing_trim_ms=0.0,
                    original_duration_ms=_duration_ms(_tensor_to_numpy(waveform), sample_rate_hz),
                    processed_duration_ms=_duration_ms(_tensor_to_numpy(waveform), sample_rate_hz),
                )
            ],
            boundary_decisions=[],
        )
    if stitch_mode == "simple":
        return _stitch_waveforms_simple(
            waveforms=waveforms,
            sample_rate_hz=sample_rate_hz,
            cross_fade_ms=cross_fade_ms,
            segment_texts=segment_texts,
        )
    if stitch_mode == "speech_aware":
        return _stitch_waveforms_speech_aware(
            waveforms=waveforms,
            sample_rate_hz=sample_rate_hz,
            cross_fade_ms=cross_fade_ms,
            segment_texts=segment_texts,
        )
    raise RuntimeError(f"Unsupported stitch_mode `{stitch_mode}`.")


@dataclass(frozen=True)
class StitchResult:
    """Full stitch result plus debug metadata."""

    waveform: torch.Tensor
    processed_waveforms: list[np.ndarray]
    chunk_analyses: list[ChunkAnalysis]
    boundary_decisions: list[BoundaryDecision]


def _stitch_waveforms_simple(
    *,
    waveforms: list[torch.Tensor],
    sample_rate_hz: int,
    cross_fade_ms: int,
    segment_texts: list[str],
) -> StitchResult:
    """Preserve the original Task 90 waveform-only stitcher as a baseline."""
    cross_fade_samples = max(int(round(sample_rate_hz * (cross_fade_ms / 1000.0))), 0)
    processed_waveforms = [
        _tensor_to_numpy(_normalize_waveform_tensor(waveform)) for waveform in waveforms
    ]
    stitched = processed_waveforms[0]
    for next_waveform in processed_waveforms[1:]:
        overlap = min(cross_fade_samples, stitched.shape[0], next_waveform.shape[0])
        if overlap <= 0:
            stitched = np.concatenate([stitched, next_waveform])
            continue
        fade_out = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
        blended = (stitched[-overlap:] * fade_out) + (next_waveform[:overlap] * fade_in)
        stitched = np.concatenate([stitched[:-overlap], blended, next_waveform[overlap:]])
    from torch import from_numpy

    return StitchResult(
        waveform=from_numpy(stitched.astype(np.float32, copy=False)).unsqueeze(0),
        processed_waveforms=processed_waveforms,
        chunk_analyses=[
            ChunkAnalysis(
                chunk_index=index,
                text=text,
                leading_trim_ms=0.0,
                trailing_trim_ms=0.0,
                original_duration_ms=_duration_ms(processed, sample_rate_hz),
                processed_duration_ms=_duration_ms(processed, sample_rate_hz),
            )
            for index, (text, processed) in enumerate(
                zip(segment_texts, processed_waveforms), start=1
            )
        ],
        boundary_decisions=[],
    )


def _stitch_waveforms_speech_aware(
    *,
    waveforms: list[torch.Tensor],
    sample_rate_hz: int,
    cross_fade_ms: int,
    segment_texts: list[str],
) -> StitchResult:
    """Trim noisy edges, preserve intended pauses, and fade edges softly."""
    processed_waveforms: list[np.ndarray] = []
    chunk_analyses: list[ChunkAnalysis] = []
    for index, (waveform, text) in enumerate(zip(waveforms, segment_texts), start=1):
        original = _tensor_to_numpy(_normalize_waveform_tensor(waveform))
        processed, leading_trim_samples, trailing_trim_samples = _trim_chunk_edges(
            original,
            sample_rate_hz=sample_rate_hz,
        )
        edge_fade_samples = min(
            int(round(sample_rate_hz * (min(cross_fade_ms, 16) / 1000.0))),
            max(processed.shape[0] // 2, 0),
        )
        processed = _apply_edge_fades(processed, edge_fade_samples=edge_fade_samples)
        processed_waveforms.append(processed)
        chunk_analyses.append(
            ChunkAnalysis(
                chunk_index=index,
                text=text,
                leading_trim_ms=_samples_to_ms(leading_trim_samples, sample_rate_hz),
                trailing_trim_ms=_samples_to_ms(trailing_trim_samples, sample_rate_hz),
                original_duration_ms=_duration_ms(original, sample_rate_hz),
                processed_duration_ms=_duration_ms(processed, sample_rate_hz),
            )
        )
    stitched = processed_waveforms[0]
    boundary_decisions: list[BoundaryDecision] = []
    edge_fade_ms = _samples_to_ms(
        int(round(sample_rate_hz * (min(cross_fade_ms, 16) / 1000.0))),
        sample_rate_hz,
    )
    for boundary_index, next_waveform in enumerate(processed_waveforms[1:], start=1):
        boundary_type = _classify_boundary_type(segment_texts[boundary_index - 1])
        pause_ms = _target_pause_ms(boundary_type)
        pause_samples = int(round(sample_rate_hz * (pause_ms / 1000.0)))
        if pause_samples > 0:
            stitched = np.concatenate(
                [stitched, np.zeros(pause_samples, dtype=np.float32), next_waveform]
            )
        else:
            stitched = np.concatenate([stitched, next_waveform])
        previous_analysis = chunk_analyses[boundary_index - 1]
        next_analysis = chunk_analyses[boundary_index]
        boundary_decisions.append(
            BoundaryDecision(
                boundary_index=boundary_index,
                boundary_type=boundary_type,
                previous_chunk_index=boundary_index,
                next_chunk_index=boundary_index + 1,
                inserted_pause_ms=float(pause_ms),
                edge_fade_ms=edge_fade_ms,
                previous_trailing_trim_ms=previous_analysis.trailing_trim_ms,
                next_leading_trim_ms=next_analysis.leading_trim_ms,
            )
        )
    from torch import from_numpy

    return StitchResult(
        waveform=from_numpy(stitched.astype(np.float32, copy=False)).unsqueeze(0),
        processed_waveforms=processed_waveforms,
        chunk_analyses=chunk_analyses,
        boundary_decisions=boundary_decisions,
    )


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
    word_segments: list[str] = []
    current_words: list[str] = []
    current_length = 0
    for word in words:
        proposed_length = len(word) if not current_words else current_length + 1 + len(word)
        if current_words and proposed_length > max_chars:
            word_segments.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
            continue
        current_words.append(word)
        current_length = proposed_length
    if current_words:
        word_segments.append(" ".join(current_words))
    return word_segments


def _split_text_with_pattern(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Split text while preserving punctuation in the preceding segment."""
    parts = [part.strip() for part in pattern.split(text.strip())]
    return [part for part in parts if part != ""]


def _classify_boundary_type(text: str) -> str:
    """Classify one segment boundary from the preceding text."""
    stripped = text.rstrip()
    if stripped.endswith((".", "!", "?")):
        return "sentence"
    if stripped.endswith((",", ";", ":")):
        return "clause"
    return "generic"


def _target_pause_ms(boundary_type: str) -> int:
    """Return the intended pause target for one boundary type."""
    if boundary_type == "sentence":
        return 180
    if boundary_type == "clause":
        return 110
    return 80


def _trim_chunk_edges(
    waveform: np.ndarray,
    *,
    sample_rate_hz: int,
) -> tuple[np.ndarray, int, int]:
    """Trim low-energy leading and trailing regions from one waveform."""
    frame_samples = max(int(round(sample_rate_hz * 0.02)), 1)
    frame_rms = _frame_rms(waveform, frame_samples=frame_samples)
    if frame_rms.size == 0:
        return waveform, 0, 0
    peak_rms = float(np.max(frame_rms))
    threshold = max(peak_rms * 0.08, 0.003)
    active_indexes = np.where(frame_rms >= threshold)[0]
    if active_indexes.size == 0:
        return waveform, 0, 0
    start_sample = int(active_indexes[0] * frame_samples)
    end_sample = min(int((active_indexes[-1] + 1) * frame_samples), waveform.shape[0])
    max_leading_trim = int(round(sample_rate_hz * 0.25))
    max_trailing_trim = int(round(sample_rate_hz * 0.5))
    leading_trim = min(start_sample, max_leading_trim)
    trailing_trim = min(waveform.shape[0] - end_sample, max_trailing_trim)
    if waveform.shape[0] - trailing_trim <= leading_trim:
        return waveform, 0, 0
    trimmed = waveform[leading_trim : waveform.shape[0] - trailing_trim]
    if trimmed.size == 0:
        return waveform, 0, 0
    return trimmed, leading_trim, trailing_trim


def _frame_rms(waveform: np.ndarray, *, frame_samples: int) -> np.ndarray:
    """Return frame RMS values for one mono waveform."""
    frames = [
        waveform[start : start + frame_samples]
        for start in range(0, waveform.shape[0], frame_samples)
        if waveform[start : start + frame_samples].size > 0
    ]
    if len(frames) == 0:
        return np.array([], dtype=np.float32)
    return np.array(
        [float(np.sqrt(np.mean(np.square(frame, dtype=np.float32)))) for frame in frames],
        dtype=np.float32,
    )


def _apply_edge_fades(waveform: np.ndarray, *, edge_fade_samples: int) -> np.ndarray:
    """Apply short edge fades to reduce clicks after trimming."""
    if edge_fade_samples <= 0 or waveform.shape[0] <= edge_fade_samples * 2:
        return waveform
    faded = waveform.copy()
    fade_in = np.linspace(0.0, 1.0, edge_fade_samples, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, edge_fade_samples, dtype=np.float32)
    faded[:edge_fade_samples] *= fade_in
    faded[-edge_fade_samples:] *= fade_out
    return faded


def _samples_to_ms(sample_count: int, sample_rate_hz: int) -> float:
    """Convert one sample count to milliseconds."""
    return round((sample_count / sample_rate_hz) * 1000.0, 3)


def _duration_ms(waveform: np.ndarray, sample_rate_hz: int) -> float:
    """Return one waveform duration in milliseconds."""
    return _samples_to_ms(waveform.shape[0], sample_rate_hz)


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
    """Normalize one waveform tensor into shape ``(1, samples)``."""
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
    stitched_result: StitchResult,
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
    for index, processed in enumerate(stitched_result.processed_waveforms, start=1):
        (debug_dir / f"chunk_{index:02d}_post.wav").write_bytes(
            _wave_bytes_from_pcm16(
                pcm16=(processed * 32767.0).round().astype("<i2"),
                sample_rate_hz=sample_rate_hz,
            )
        )
    (debug_dir / "chunk_analysis.json").write_text(
        json.dumps(
            [asdict(chunk_analysis) for chunk_analysis in stitched_result.chunk_analyses],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (debug_dir / "boundary_decisions.json").write_text(
        json.dumps(
            [asdict(boundary_decision) for boundary_decision in stitched_result.boundary_decisions],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (debug_dir / "stitched.wav").write_bytes(
        _wave_bytes_from_waveform(stitched_result.waveform, sample_rate_hz=sample_rate_hz)
    )
