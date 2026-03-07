"""Tests for deterministic Chatterbox segmentation and stitching helpers.

Purpose:
    Protect the repo-owned long-form generation helpers that segment normal
    text, synthesize one chunk at a time, and stitch the results into one
    deterministic output waveform.

Relationships:
    - Exercises `chatterbox_segmented_generation.py`.
    - Supports Task 90 quality work without requiring live model downloads.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import torch

from scripts.sir_convert_a_lot.tts_sidecar.chatterbox_segmented_generation import (
    SegmentGenerationSettings,
    build_segment_plan,
    generate_audio_bytes,
    stitch_waveforms,
)


def test_build_segment_plan_prefers_sentence_and_clause_boundaries() -> None:
    plan = build_segment_plan(
        text=(
            "Hej världen. Det här är en längre mening, med en tydlig paus, "
            "och ytterligare några ord för att kräva mer än ett segment."
        ),
        max_chars=55,
        cross_fade_ms=80,
    )

    assert plan.segment_count == 4
    assert plan.segments == [
        "Hej världen. Det här är en längre mening,",
        "med en tydlig paus,",
        "och ytterligare några ord för att kräva mer än ett",
        "segment.",
    ]


def test_build_segment_plan_splits_oversized_sentence_on_words() -> None:
    plan = build_segment_plan(
        text="ett två tre fyra fem sex sju åtta nio tio elva tolv tretton fjorton",
        max_chars=18,
        cross_fade_ms=80,
    )

    assert all(len(segment) <= 18 for segment in plan.segments)
    assert plan.segments == [
        "ett två tre fyra",
        "fem sex sju åtta",
        "nio tio elva tolv",
        "tretton fjorton",
    ]


def test_stitch_waveforms_cross_fades_overlapping_edges() -> None:
    waveform_a = torch.tensor([[0.0, 0.5, 1.0, 1.0]], dtype=torch.float32)
    waveform_b = torch.tensor([[1.0, 0.5, 0.0, 0.0]], dtype=torch.float32)

    stitched = stitch_waveforms(
        waveforms=[waveform_a, waveform_b],
        sample_rate_hz=1000,
        cross_fade_ms=2,
    )

    assert stitched.shape == (1, 6)
    assert torch.allclose(
        stitched,
        torch.tensor([[0.0, 0.5, 1.0, 0.5, 0.0, 0.0]], dtype=torch.float32),
    )


def test_generate_audio_bytes_writes_debug_artifacts_for_segmented_lane(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def _fake_generate(**kwargs: object) -> torch.Tensor:
        text = str(kwargs["text"])
        calls.append(text)
        return torch.full((1, 240), 0.25 * len(calls), dtype=torch.float32)

    audio_bytes = generate_audio_bytes(
        generate_fn=_fake_generate,
        sample_rate_hz=24000,
        generate_kwargs={
            "text": "Hej världen. Det här är ett andra segment.",
            "language_id": "sv",
        },
        settings=SegmentGenerationSettings(
            enabled=True,
            max_chars=20,
            cross_fade_ms=10,
            debug_dir=tmp_path,
        ),
    )

    assert len(calls) == 3
    plan_payload = json.loads((tmp_path / "segment_plan.json").read_text(encoding="utf-8"))
    assert plan_payload["segment_count"] == 3
    assert (tmp_path / "chunk_01.wav").exists()
    assert (tmp_path / "chunk_02.wav").exists()
    assert (tmp_path / "stitched.wav").exists()
    with wave.open(Path(tmp_path / "stitched.wav").as_posix(), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnchannels() == 1
    assert audio_bytes[:4] == b"RIFF"


def test_generate_audio_bytes_skips_segmentation_when_disabled() -> None:
    calls: list[str] = []

    def _fake_generate(**kwargs: object) -> torch.Tensor:
        calls.append(str(kwargs["text"]))
        return torch.zeros(1, 4)

    generate_audio_bytes(
        generate_fn=_fake_generate,
        sample_rate_hz=24000,
        generate_kwargs={"text": "Hej världen. Det här är ett prov.", "language_id": "sv"},
        settings=SegmentGenerationSettings(
            enabled=False,
            max_chars=20,
            cross_fade_ms=10,
            debug_dir=None,
        ),
    )

    assert calls == ["Hej världen. Det här är ett prov."]
