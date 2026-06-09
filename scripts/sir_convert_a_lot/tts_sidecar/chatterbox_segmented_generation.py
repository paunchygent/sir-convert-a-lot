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
_LIST_ITEM_RE = re.compile(
    r"^(?:"
    r"(?:ett|två|tre|fyra|fem|sex|sju|åtta|nio|tio|elva|tolv)"
    r"|(?:\d+)"
    r")\s*[:.)-]\s+",
    re.IGNORECASE,
)
_BRACKETED_CUE_RE = re.compile(r"\[[^\]]+\]")
_WEAK_BOUNDARY_STARTERS = (
    ("för", "att"),
    ("så", "att"),
    ("och",),
    ("men",),
    ("när",),
    ("om",),
    ("medan",),
    ("eftersom",),
    ("som",),
    ("att",),
)
_TARGET_SEGMENT_SECONDS_MIN = 4.0
_TARGET_SEGMENT_SECONDS_MAX = 6.0
_HARD_MAX_SEGMENT_SECONDS = 9.0
_PLANNER_VERSION = "clause_duration_v1"
_ESTIMATED_WORDS_PER_SECOND = 3.1
_ESTIMATED_CHARS_PER_SECOND = 20.0
_JOIN_PENALTY_SECONDS = 0.12
_MIN_LIST_ITEM_STANDALONE_SECONDS = 1.5


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
    planner_version: str
    target_seconds_min: float
    target_seconds_max: float
    hard_max_seconds: float
    segment_predictions: list["PlannedSegment"]


@dataclass(frozen=True)
class PlannedSegment:
    """Debug-friendly segment planning metadata."""

    text: str
    boundary_type: str
    predicted_duration_seconds: float
    unit_count: int


@dataclass(frozen=True)
class PlanningUnit:
    """Internal clause-sized planning unit used before chunk packing."""

    text: str
    boundary_type: str
    predicted_duration_seconds: float


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
    planned_segments = _plan_text_segments(stripped, max_chars=max_chars)
    return SegmentPlan(
        original_text=stripped,
        segment_count=len(planned_segments),
        segments=[segment.text for segment in planned_segments],
        max_chars=max_chars,
        cross_fade_ms=cross_fade_ms,
        planner_version=_PLANNER_VERSION,
        target_seconds_min=_TARGET_SEGMENT_SECONDS_MIN,
        target_seconds_max=_TARGET_SEGMENT_SECONDS_MAX,
        hard_max_seconds=_HARD_MAX_SEGMENT_SECONDS,
        segment_predictions=planned_segments,
    )


def stitch_waveforms(
    *,
    waveforms: list[torch.Tensor],
    sample_rate_hz: int,
    cross_fade_ms: int,
    segment_texts: list[str],
    stitch_mode: str,
    edge_fade_cap_ms: float = 12.0,
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
            edge_fade_cap_ms=edge_fade_cap_ms,
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
    """Stitch Chatterbox segment waveforms with waveform-only cross-fading."""
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
    edge_fade_cap_ms: float,
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
            int(round(sample_rate_hz * (min(cross_fade_ms, edge_fade_cap_ms) / 1000.0))),
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
        int(round(sample_rate_hz * (min(cross_fade_ms, edge_fade_cap_ms) / 1000.0))),
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


def _plan_text_segments(text: str, *, max_chars: int) -> list[PlannedSegment]:
    """Plan duration-bounded segments from clause-aware atomic units."""
    units = _segment_text(text, max_chars=max_chars)
    planned_segments: list[PlannedSegment] = []
    current_units: list[PlanningUnit] = []
    for unit in units:
        if current_units and _should_close_segment_before_adding(
            current_units=current_units,
            next_unit=unit,
            max_chars=max_chars,
        ):
            planned_segments.append(_finalize_planned_segment(current_units))
            current_units = [unit]
            continue
        current_units.append(unit)
    if current_units:
        planned_segments.append(_finalize_planned_segment(current_units))
    return planned_segments


def _segment_text(text: str, *, max_chars: int) -> list[PlanningUnit]:
    """Split text deterministically into clause-aware planning units."""
    sentences = _split_text_with_pattern(text, _HARD_BOUNDARY_RE)
    units: list[PlanningUnit] = []
    for sentence in sentences:
        normalized_sentence = sentence.strip()
        if normalized_sentence == "":
            continue
        units.extend(_expand_sentence_to_units(normalized_sentence, max_chars=max_chars))
    return units


def _expand_sentence_to_units(text: str, *, max_chars: int) -> list[PlanningUnit]:
    """Split one sentence into bounded planning units."""
    if _unit_within_limits(text=text, max_chars=max_chars):
        return [_build_planning_unit(text)]
    structural_clauses = _split_on_structural_boundaries(text)
    if len(structural_clauses) > 1:
        segments: list[PlanningUnit] = []
        for clause in structural_clauses:
            segments.extend(_expand_sentence_to_units(clause.strip(), max_chars=max_chars))
        return segments
    weak_clauses = _split_on_weak_boundaries(text)
    if len(weak_clauses) > 1:
        segments = []
        for clause in weak_clauses:
            segments.extend(_expand_sentence_to_units(clause.strip(), max_chars=max_chars))
        return segments
    return _split_words_to_units(text, max_chars=max_chars)


def _split_words_to_units(text: str, *, max_chars: int) -> list[PlanningUnit]:
    """Split one oversized unit on words while honoring duration ceilings."""
    words = text.split()
    if len(words) <= 1:
        return [_build_planning_unit(text)]
    word_segments: list[PlanningUnit] = []
    current_words: list[str] = []
    for word in words:
        proposed_words = current_words + [word]
        proposed_text = " ".join(proposed_words)
        if current_words and not _unit_within_limits(text=proposed_text, max_chars=max_chars):
            word_segments.append(_build_planning_unit(" ".join(current_words)))
            current_words = [word]
            continue
        current_words = proposed_words
    if current_words:
        word_segments.append(_build_planning_unit(" ".join(current_words)))
    return word_segments


def _split_on_structural_boundaries(text: str) -> list[str]:
    """Split one unit on strong structural boundaries before word fallback."""
    clauses = _split_text_with_pattern(text, _SOFT_BOUNDARY_RE)
    if len(clauses) > 1:
        return clauses
    dash_clauses = _split_on_dash_boundaries(text)
    if len(dash_clauses) > 1:
        return dash_clauses
    cue_clauses = _split_on_bracketed_cues(text)
    if len(cue_clauses) > 1:
        return cue_clauses
    return [text]


def _split_on_dash_boundaries(text: str) -> list[str]:
    """Split one unit on spoken dash boundaries while preserving the marker."""
    parts = [part.strip() for part in re.split(r"\s+[–-]\s+", text.strip()) if part.strip() != ""]
    if len(parts) <= 1:
        return [text]
    segments: list[str] = []
    for index, part in enumerate(parts):
        if index < len(parts) - 1:
            segments.append(f"{part} –")
        else:
            segments.append(part)
    return segments


def _split_on_bracketed_cues(text: str) -> list[str]:
    """Split one unit so bracketed cues can form their own short planning unit."""
    matches = list(_BRACKETED_CUE_RE.finditer(text))
    if not matches:
        return [text]
    segments: list[str] = []
    cursor = 0
    for match in matches:
        prefix = text[cursor : match.start()].strip()
        cue = match.group(0).strip()
        if prefix != "":
            segments.append(prefix)
        if cue != "":
            segments.append(cue)
        cursor = match.end()
    suffix = text[cursor:].strip()
    if suffix != "":
        segments.append(suffix)
    return segments if len(segments) > 1 else [text]


def _split_on_weak_boundaries(text: str) -> list[str]:
    """Split an oversized unit on weaker clause starters when needed."""
    words = text.split()
    if len(words) <= 1:
        return [text]
    segments: list[list[str]] = [[]]
    index = 0
    while index < len(words):
        split_marker = _match_weak_boundary_starter(words, index)
        if split_marker is not None and segments[-1]:
            segments.append([])
        segments[-1].append(words[index])
        index += 1
    built_segments = [" ".join(segment).strip() for segment in segments if segment]
    return built_segments if len(built_segments) > 1 else [text]


def _match_weak_boundary_starter(words: list[str], index: int) -> tuple[str, ...] | None:
    """Return the matching weak boundary starter at one word index."""
    for starter in _WEAK_BOUNDARY_STARTERS:
        if index + len(starter) > len(words):
            continue
        candidate = tuple(
            word.casefold().strip(".,;:!?()[]{}\"'") for word in words[index : index + len(starter)]
        )
        if candidate == starter:
            return starter
    return None


def _should_close_segment_before_adding(
    *,
    current_units: list[PlanningUnit],
    next_unit: PlanningUnit,
    max_chars: int,
) -> bool:
    """Decide whether one segment should be closed before adding the next unit."""
    current_seconds = _predicted_duration_for_units(current_units)
    proposed_units = [*current_units, next_unit]
    proposed_text = _join_units(proposed_units)
    proposed_seconds = _predicted_duration_for_units(proposed_units)
    current_has_list_item = any(unit.boundary_type == "list_item" for unit in current_units)

    if current_has_list_item and next_unit.boundary_type == "list_item":
        return True
    if (
        current_has_list_item
        and next_unit.boundary_type in {"sentence", "cue"}
        and current_seconds >= _MIN_LIST_ITEM_STANDALONE_SECONDS
    ):
        return True
    if len(proposed_text) > max_chars:
        return True
    if proposed_seconds > _HARD_MAX_SEGMENT_SECONDS:
        return True
    if (
        current_seconds >= _TARGET_SEGMENT_SECONDS_MIN * 0.75
        and proposed_seconds > _TARGET_SEGMENT_SECONDS_MAX
        and next_unit.boundary_type in {"list_item", "sentence", "cue"}
    ):
        return True
    if current_seconds >= _TARGET_SEGMENT_SECONDS_MIN and next_unit.boundary_type in {
        "list_item",
        "sentence",
        "cue",
    }:
        return True
    return False


def _finalize_planned_segment(units: list[PlanningUnit]) -> PlannedSegment:
    """Convert one packed unit group into emitted segment metadata."""
    text = _join_units(units)
    return PlannedSegment(
        text=text,
        boundary_type=units[-1].boundary_type,
        predicted_duration_seconds=round(_predicted_duration_for_units(units), 3),
        unit_count=len(units),
    )


def _join_units(units: list[PlanningUnit]) -> str:
    """Join planning units into one emitted segment text."""
    return " ".join(unit.text for unit in units).strip()


def _predicted_duration_for_units(units: list[PlanningUnit]) -> float:
    """Predict one segment duration from its planning units."""
    if len(units) == 0:
        return 0.0
    return sum(unit.predicted_duration_seconds for unit in units) + (
        max(len(units) - 1, 0) * _JOIN_PENALTY_SECONDS
    )


def _build_planning_unit(text: str) -> PlanningUnit:
    """Create one planning unit with normalized text and predicted duration."""
    stripped = text.strip()
    return PlanningUnit(
        text=stripped,
        boundary_type=_classify_planning_unit_type(stripped),
        predicted_duration_seconds=_estimate_text_duration_seconds(stripped),
    )


def _classify_planning_unit_type(text: str) -> str:
    """Classify one planning unit for chunk-boundary priority."""
    if _LIST_ITEM_RE.match(text):
        return "list_item"
    if _BRACKETED_CUE_RE.fullmatch(text):
        return "cue"
    return _classify_boundary_type(text)


def _estimate_text_duration_seconds(text: str) -> float:
    """Estimate speech duration conservatively from text length and word count."""
    cleaned = text.strip()
    if cleaned == "":
        return 0.0
    non_space_chars = len(re.sub(r"\s+", "", cleaned))
    word_count = len(cleaned.split())
    return max(
        non_space_chars / _ESTIMATED_CHARS_PER_SECOND,
        word_count / _ESTIMATED_WORDS_PER_SECOND,
    )


def _unit_within_limits(*, text: str, max_chars: int) -> bool:
    """Return whether one unit already fits the hard planning constraints."""
    return (
        len(text) <= max_chars
        and _estimate_text_duration_seconds(text) <= _HARD_MAX_SEGMENT_SECONDS
    )


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


def wave_bytes_from_waveform(waveform: torch.Tensor, *, sample_rate_hz: int) -> bytes:
    """Public wrapper for deterministic mono WAV serialization."""
    return _wave_bytes_from_waveform(waveform, sample_rate_hz=sample_rate_hz)


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


def read_wav_tensor(path: Path) -> tuple[torch.Tensor, int]:
    """Load one mono WAV file into the normalized waveform tensor shape."""
    with wave.open(path.as_posix(), "rb") as wav_file:
        if wav_file.getnchannels() != 1:
            raise RuntimeError(f"Expected mono WAV input, got {wav_file.getnchannels()} channels.")
        if wav_file.getsampwidth() != 2:
            raise RuntimeError(
                f"Expected PCM16 WAV input, got sample width {wav_file.getsampwidth()}."
            )
        sample_rate_hz = int(wav_file.getframerate())
        pcm16 = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype="<i2").astype(
            np.float32
        )
    from torch import from_numpy

    waveform = from_numpy((pcm16 / 32767.0).astype(np.float32, copy=False)).unsqueeze(0)
    return waveform, sample_rate_hz


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
