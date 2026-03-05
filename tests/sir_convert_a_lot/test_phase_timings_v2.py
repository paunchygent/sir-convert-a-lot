"""Tests for canonical v2 phase timing normalization and merge behavior.

Purpose:
    Ensure v2 timing payloads are normalized to canonical keys with deterministic
    alias handling and bounded value semantics.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.phase_timings_v2`.
    - Guards v2 diagnostics persistence normalization in manifest merge paths.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CHECKPOINT_PERSIST_MS,
    TIMING_KEY_CONVERSION_TOTAL_MS,
    TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS,
    TIMING_KEY_MARKDOWN_NORMALIZE_MS,
    TIMING_KEY_OCR_LAYOUT_EXTRACT_MS,
    merge_phase_timings,
    normalize_phase_timings_map,
)


def test_normalize_phase_timings_map_maps_legacy_aliases_to_canonical_keys() -> None:
    normalized = normalize_phase_timings_map(
        {
            "backend_convert_ms": 10,
            "normalize_ms": 3,
            "conversion_attempt_ms": 11,
            "persist_ms": 2,
            "chunk_elapsed_ms": 7,
        }
    )
    assert normalized[TIMING_KEY_OCR_LAYOUT_EXTRACT_MS] == 10
    assert normalized[TIMING_KEY_MARKDOWN_NORMALIZE_MS] == 3
    assert normalized[TIMING_KEY_CONVERSION_TOTAL_MS] == 11
    assert normalized[TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS] == 2
    assert normalized["chunk_total_ms"] == 7
    assert "backend_convert_ms" not in normalized
    assert "normalize_ms" not in normalized
    assert "conversion_attempt_ms" not in normalized
    assert "persist_ms" not in normalized


def test_normalize_phase_timings_map_drops_unknown_keys_and_invalid_values() -> None:
    normalized = normalize_phase_timings_map(
        {
            "unknown_key": 4,
            "backend_convert_ms": -3,
            "normalize_ms": True,
            "checkpoint_persist_ms": "12",
        }
    )
    assert normalized == {TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: 0}


def test_merge_phase_timings_merges_alias_and_canonical_values_deterministically() -> None:
    merged = merge_phase_timings(
        current={
            "backend_convert_ms": 5,
            TIMING_KEY_MARKDOWN_NORMALIZE_MS: 4,
            TIMING_KEY_CHECKPOINT_PERSIST_MS: 8,
        },
        additional={
            TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: 6,
            "normalize_ms": 1,
            "persist_ms": 9,
        },
    )
    assert merged[TIMING_KEY_OCR_LAYOUT_EXTRACT_MS] == 11
    assert merged[TIMING_KEY_MARKDOWN_NORMALIZE_MS] == 5
    assert merged[TIMING_KEY_CHECKPOINT_PERSIST_MS] == 8
    assert merged[TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS] == 9
