"""Tests for the Chatterbox speech-aware stitching Chatterbox speech-aware stitching experiment
runners.

Purpose:
    Protect the committed Chatterbox speech-aware stitching orchestration surfaces so speech-aware
    stitching comparisons stay reproducible before live Hemma runs.

Relationships:
    - Exercises both local and Hemma Chatterbox speech-aware stitching runners.
    - Reuses the Chatterbox benchmark runner as the underlying synthesis surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch

from scripts.sir_convert_a_lot.devops import (
    run_chatterbox_saved_chunk_restitch,
    run_chatterbox_speech_stitching_experiment,
    run_chatterbox_speech_stitching_hemma_experiment,
)
from scripts.sir_convert_a_lot.tts_sidecar.chatterbox_segmented_generation import (
    wave_bytes_from_waveform,
)


def test_local_parse_args_accepts_segment_controls() -> None:
    args = run_chatterbox_speech_stitching_experiment._parse_args(
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


def test_hemma_parse_args_accepts_segment_controls() -> None:
    settings = run_chatterbox_speech_stitching_hemma_experiment._parse_args(
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


def test_write_summary_records_both_stitch_modes(tmp_path: Path) -> None:
    settings = run_chatterbox_speech_stitching_hemma_experiment.ExperimentSettings(
        output_root=tmp_path,
        reference_audio_path=tmp_path / "ref.m4a",
        probe_text="Hej världen. Det här är ett långt test.",
        exaggeration=0.5,
        cfg_weight=0.5,
        segment_max_chars=320,
        segment_cross_fade_ms=80,
        build_image=False,
    )
    simple_lane = run_chatterbox_speech_stitching_hemma_experiment.LaneSummary(
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
    speech_aware_lane = run_chatterbox_speech_stitching_hemma_experiment.LaneSummary(
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

    run_chatterbox_speech_stitching_hemma_experiment._write_summary(
        output_root=tmp_path,
        settings=settings,
        simple_lane=simple_lane,
        speech_aware_lane=speech_aware_lane,
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert payload["simple_lane"]["segment_stitch_mode"] == "simple"
    assert payload["speech_aware_lane"]["segment_stitch_mode"] == "speech_aware"


def test_restitch_parse_args_accepts_small_fade_adjustment() -> None:
    args = run_chatterbox_saved_chunk_restitch._parse_args(
        [
            "--edge-fade-cap-ms",
            "12.0",
            "--cross-fade-ms",
            "80",
        ]
    )

    assert args.edge_fade_cap_ms == 12.0
    assert args.cross_fade_ms == 80


def test_restitch_reuses_saved_chunks(tmp_path: Path) -> None:
    source_debug_dir = tmp_path / "source-debug"
    source_debug_dir.mkdir(parents=True)
    (source_debug_dir / "segment_plan.json").write_text(
        json.dumps(
            {
                "original_text": "Första delen. Andra delen.",
                "segment_count": 2,
                "segments": ["Första delen.", "Andra delen."],
                "max_chars": 320,
                "cross_fade_ms": 80,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (source_debug_dir / "chunk_01.wav").write_bytes(
        wave_bytes_from_waveform(
            torch.tensor([[0.0, 0.0, 0.1, 0.2, 0.2, 0.1, 0.0]], dtype=torch.float32),
            sample_rate_hz=24000,
        )
    )
    (source_debug_dir / "chunk_02.wav").write_bytes(
        wave_bytes_from_waveform(
            torch.tensor([[0.0, 0.05, 0.2, 0.25, 0.1, 0.0]], dtype=torch.float32),
            sample_rate_hz=24000,
        )
    )

    output_root = tmp_path / "restitch-output"
    returncode = run_chatterbox_saved_chunk_restitch.main(
        [
            "--source-debug-dir",
            source_debug_dir.as_posix(),
            "--output-root",
            output_root.as_posix(),
            "--edge-fade-cap-ms",
            "12.0",
        ]
    )

    assert returncode == 0
    payload = json.loads((output_root / "report.json").read_text(encoding="utf-8"))
    assert payload["edge_fade_cap_ms"] == 12.0
    assert payload["segment_count"] == 2
    assert (output_root / "artifacts" / "scenario-a-sv-ref-sv-out.wav").exists()
    assert (output_root / "segment-debug" / "boundary_decisions.json").exists()
