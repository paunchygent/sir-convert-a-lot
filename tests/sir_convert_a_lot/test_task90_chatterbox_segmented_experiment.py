"""Tests for the Task 90 Chatterbox segmented experiment runners.

Purpose:
    Protect the committed Task 90 orchestration surfaces so segmented-vs-
    single-pass comparisons stay reproducible before live Hemma runs.

Relationships:
    - Exercises both local and Hemma Task 90 runners.
    - Reuses the Task 86 runner as the underlying synthesis surface.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.devops import (
    run_task90_chatterbox_segmented_experiment,
    run_task90_hemma_chatterbox_segmented_experiment,
)


def test_task90_local_parse_args_accepts_segment_controls() -> None:
    args = run_task90_chatterbox_segmented_experiment._parse_args(
        [
            "--segment-max-chars",
            "140",
            "--segment-cross-fade-ms",
            "60",
            "--skip-build",
        ]
    )

    assert args.segment_max_chars == 140
    assert args.segment_cross_fade_ms == 60
    assert args.skip_build is True


def test_task90_hemma_parse_args_accepts_segment_controls() -> None:
    settings = run_task90_hemma_chatterbox_segmented_experiment._parse_args(
        [
            "--segment-max-chars",
            "140",
            "--segment-cross-fade-ms",
            "60",
            "--skip-build",
        ]
    )

    assert settings.segment_max_chars == 140
    assert settings.segment_cross_fade_ms == 60
    assert settings.build_image is False


def test_task90_write_summary_records_both_lanes(tmp_path: Path) -> None:
    settings = run_task90_hemma_chatterbox_segmented_experiment.ExperimentSettings(
        output_root=tmp_path,
        reference_audio_path=tmp_path / "ref.m4a",
        probe_text="Hej världen. Det här är ett långt test.",
        exaggeration=0.5,
        cfg_weight=0.5,
        segment_max_chars=160,
        segment_cross_fade_ms=80,
        build_image=False,
    )
    single_pass = run_task90_hemma_chatterbox_segmented_experiment.LaneSummary(
        lane_id="single_pass",
        output_root="/tmp/single_pass",
        synthesized_ok=True,
        output_path="/tmp/single_pass/artifacts/sample.wav",
        duration_seconds=10.0,
        sha256="abc",
        peak_vram_used_bytes=100,
        segment_text=False,
        segment_max_chars=160,
        segment_cross_fade_ms=80,
        segment_debug_dir=None,
    )
    segmented = run_task90_hemma_chatterbox_segmented_experiment.LaneSummary(
        lane_id="segmented",
        output_root="/tmp/segmented",
        synthesized_ok=True,
        output_path="/tmp/segmented/artifacts/sample.wav",
        duration_seconds=9.0,
        sha256="def",
        peak_vram_used_bytes=120,
        segment_text=True,
        segment_max_chars=160,
        segment_cross_fade_ms=80,
        segment_debug_dir="/tmp/segmented/segment-debug",
    )

    run_task90_hemma_chatterbox_segmented_experiment._write_summary(
        output_root=tmp_path,
        settings=settings,
        single_pass_lane=single_pass,
        segmented_lane=segmented,
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert payload["single_pass_lane"]["segment_text"] is False
    assert payload["segmented_lane"]["segment_text"] is True
    assert payload["segmented_lane"]["segment_debug_dir"] == "/tmp/segmented/segment-debug"
