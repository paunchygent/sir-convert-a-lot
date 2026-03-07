"""Tests for the Task 91 Chatterbox speech-aware stitching experiment runners.

Purpose:
    Protect the committed Task 91 orchestration surfaces so speech-aware
    stitching comparisons stay reproducible before live Hemma runs.

Relationships:
    - Exercises both local and Hemma Task 91 runners.
    - Reuses the Task 86 runner as the underlying synthesis surface.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.devops import (
    run_task91_chatterbox_speech_aware_stitching_experiment,
    run_task91_hemma_chatterbox_speech_aware_stitching_experiment,
)


def test_task91_local_parse_args_accepts_segment_controls() -> None:
    args = run_task91_chatterbox_speech_aware_stitching_experiment._parse_args(
        [
            "--segment-max-chars",
            "280",
            "--segment-cross-fade-ms",
            "60",
            "--skip-build",
        ]
    )

    assert args.segment_max_chars == 280
    assert args.segment_cross_fade_ms == 60
    assert args.skip_build is True


def test_task91_hemma_parse_args_accepts_segment_controls() -> None:
    settings = run_task91_hemma_chatterbox_speech_aware_stitching_experiment._parse_args(
        [
            "--segment-max-chars",
            "280",
            "--segment-cross-fade-ms",
            "60",
            "--skip-build",
        ]
    )

    assert settings.segment_max_chars == 280
    assert settings.segment_cross_fade_ms == 60
    assert settings.build_image is False


def test_task91_write_summary_records_both_stitch_modes(tmp_path: Path) -> None:
    settings = run_task91_hemma_chatterbox_speech_aware_stitching_experiment.ExperimentSettings(
        output_root=tmp_path,
        reference_audio_path=tmp_path / "ref.m4a",
        probe_text="Hej världen. Det här är ett långt test.",
        exaggeration=0.5,
        cfg_weight=0.5,
        segment_max_chars=320,
        segment_cross_fade_ms=80,
        build_image=False,
    )
    simple_lane = run_task91_hemma_chatterbox_speech_aware_stitching_experiment.LaneSummary(
        lane_id="simple",
        stitch_mode="simple",
        output_root="/tmp/simple",
        synthesized_ok=True,
        output_path="/tmp/simple/artifacts/sample.wav",
        duration_seconds=10.0,
        sha256="abc",
        peak_vram_used_bytes=100,
        segment_text=True,
        segment_max_chars=320,
        segment_cross_fade_ms=80,
        segment_stitch_mode="simple",
        segment_debug_dir="/tmp/simple/segment-debug",
    )
    speech_aware_lane = run_task91_hemma_chatterbox_speech_aware_stitching_experiment.LaneSummary(
        lane_id="speech_aware",
        stitch_mode="speech_aware",
        output_root="/tmp/speech-aware",
        synthesized_ok=True,
        output_path="/tmp/speech-aware/artifacts/sample.wav",
        duration_seconds=9.0,
        sha256="def",
        peak_vram_used_bytes=120,
        segment_text=True,
        segment_max_chars=320,
        segment_cross_fade_ms=80,
        segment_stitch_mode="speech_aware",
        segment_debug_dir="/tmp/speech-aware/segment-debug",
    )

    run_task91_hemma_chatterbox_speech_aware_stitching_experiment._write_summary(
        output_root=tmp_path,
        settings=settings,
        simple_lane=simple_lane,
        speech_aware_lane=speech_aware_lane,
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert payload["simple_lane"]["segment_stitch_mode"] == "simple"
    assert payload["speech_aware_lane"]["segment_stitch_mode"] == "speech_aware"
