"""Canonical phase timing contract helpers for v2 conversion telemetry.

Purpose:
    Define canonical timing keys and deterministic normalization/merge helpers
    so v2 timing payloads stay stable across runtime emitters and persisted
    manifests.

Relationships:
    - Used by `infrastructure.job_store_manifest_v2` when parsing/merging
      diagnostics timing payloads.
    - Used by v2 runtime/executor paths to emit canonical timing keys.
"""

from __future__ import annotations

from collections.abc import Mapping

TIMING_KEY_OCR_LAYOUT_EXTRACT_MS = "ocr_layout_extract_ms"
TIMING_KEY_MARKDOWN_NORMALIZE_MS = "markdown_normalize_ms"
TIMING_KEY_FORMULA_ENRICHMENT_MS = "formula_enrichment_ms"
TIMING_KEY_CHECKPOINT_PERSIST_MS = "checkpoint_persist_ms"
TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS = "final_artifact_persist_ms"
TIMING_KEY_CHUNK_TOTAL_MS = "chunk_total_ms"
TIMING_KEY_CONVERSION_TOTAL_MS = "conversion_total_ms"
TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS = "audio_probe_normalize_ms"
TIMING_KEY_AUDIO_DIARIZATION_MS = "audio_diarization_ms"
TIMING_KEY_AUDIO_TRANSCRIPTION_MS = "audio_transcription_ms"
TIMING_KEY_AUDIO_ALIGNMENT_MS = "audio_alignment_ms"
TIMING_KEY_AUDIO_PACKAGING_MS = "audio_packaging_ms"

CANONICAL_PHASE_TIMING_KEYS: frozenset[str] = frozenset(
    {
        TIMING_KEY_OCR_LAYOUT_EXTRACT_MS,
        TIMING_KEY_MARKDOWN_NORMALIZE_MS,
        TIMING_KEY_FORMULA_ENRICHMENT_MS,
        TIMING_KEY_CHECKPOINT_PERSIST_MS,
        TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS,
        TIMING_KEY_CHUNK_TOTAL_MS,
        TIMING_KEY_CONVERSION_TOTAL_MS,
        TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS,
        TIMING_KEY_AUDIO_DIARIZATION_MS,
        TIMING_KEY_AUDIO_TRANSCRIPTION_MS,
        TIMING_KEY_AUDIO_ALIGNMENT_MS,
        TIMING_KEY_AUDIO_PACKAGING_MS,
    }
)


def _coerce_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(0, int(value))


def canonical_timing_key(key: str) -> str | None:
    """Resolve one timing key to canonical v2 key or return None when unsupported."""
    if key in CANONICAL_PHASE_TIMING_KEYS:
        return key
    return None


def normalize_phase_timings_map(phase_timings: Mapping[str, object]) -> dict[str, int]:
    """Normalize one timing mapping into canonical keys with non-negative values."""
    normalized: dict[str, int] = {}
    for key, value in phase_timings.items():
        canonical_key = canonical_timing_key(key)
        if canonical_key is None:
            continue
        normalized_value = _coerce_nonnegative_int(value)
        if normalized_value is None:
            continue
        normalized[canonical_key] = normalized.get(canonical_key, 0) + normalized_value
    return normalized


def merge_phase_timings(
    *,
    current: Mapping[str, object],
    additional: Mapping[str, object],
) -> dict[str, int]:
    """Return canonical merged timings for two timing maps."""
    merged = normalize_phase_timings_map(current)
    normalized_additional = normalize_phase_timings_map(additional)
    for key, value in normalized_additional.items():
        merged[key] = merged.get(key, 0) + value
    return merged
