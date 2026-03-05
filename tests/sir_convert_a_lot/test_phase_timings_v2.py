"""Tests for canonical v2 phase timing normalization and merge behavior.

Purpose:
    Ensure v2 timing payloads are normalized to canonical keys with deterministic
    key handling and bounded value semantics.

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


def test_normalize_phase_timings_map_keeps_canonical_keys() -> None:
    normalized = normalize_phase_timings_map(
        {
            TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: 10,
            TIMING_KEY_MARKDOWN_NORMALIZE_MS: 3,
            TIMING_KEY_CONVERSION_TOTAL_MS: 11,
            TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS: 2,
            "chunk_total_ms": 7,
        }
    )
    assert normalized[TIMING_KEY_OCR_LAYOUT_EXTRACT_MS] == 10
    assert normalized[TIMING_KEY_MARKDOWN_NORMALIZE_MS] == 3
    assert normalized[TIMING_KEY_CONVERSION_TOTAL_MS] == 11
    assert normalized[TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS] == 2
    assert normalized["chunk_total_ms"] == 7


def test_normalize_phase_timings_map_drops_unknown_keys_and_invalid_values() -> None:
    normalized = normalize_phase_timings_map(
        {
            "unknown_key": 4,
            TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: -3,
            TIMING_KEY_MARKDOWN_NORMALIZE_MS: True,
            "checkpoint_persist_ms": "12",
        }
    )
    assert normalized == {TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: 0}


def test_merge_phase_timings_merges_canonical_values_deterministically() -> None:
    merged = merge_phase_timings(
        current={
            TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: 5,
            TIMING_KEY_MARKDOWN_NORMALIZE_MS: 4,
            TIMING_KEY_CHECKPOINT_PERSIST_MS: 8,
        },
        additional={
            TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: 6,
            TIMING_KEY_MARKDOWN_NORMALIZE_MS: 1,
            TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS: 9,
        },
    )
    assert merged[TIMING_KEY_OCR_LAYOUT_EXTRACT_MS] == 11
    assert merged[TIMING_KEY_MARKDOWN_NORMALIZE_MS] == 5
    assert merged[TIMING_KEY_CHECKPOINT_PERSIST_MS] == 8
    assert merged[TIMING_KEY_FINAL_ARTIFACT_PERSIST_MS] == 9
