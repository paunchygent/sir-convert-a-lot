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

    assert plan.segment_count == 3
    assert plan.segments == [
        "Hej världen. Det här är en längre mening,",
        "med en tydlig paus, och ytterligare några ord för",
        "att kräva mer än ett segment.",
    ]
    assert all(
        segment.predicted_duration_seconds <= plan.hard_max_seconds
        for segment in plan.segment_predictions
    )


def test_build_segment_plan_prefers_list_item_boundaries_for_structured_text() -> None:
    plan = build_segment_plan(
        text=(
            "Sex saker att ta med er. Ett: ni är delegater – representera ert land. "
            "Två: lyft landskylten för att begära ordet. "
            "Tre: börja alltid med Herr och Fru ordförande på svenska. "
            "Fyra: håll er inom taltiden."
        ),
        max_chars=320,
        cross_fade_ms=80,
    )

    assert (
        plan.segments[0] == "Sex saker att ta med er. Ett: ni är delegater – representera ert land."
    )
    assert plan.segments[1] == "Två: lyft landskylten för att begära ordet."
    assert plan.segments[2] == "Tre: börja alltid med Herr och Fru ordförande på svenska."
    assert plan.segments[3] == "Fyra: håll er inom taltiden."
    assert plan.segment_predictions[0].boundary_type == "list_item"
    assert all(
        segment.predicted_duration_seconds <= plan.hard_max_seconds
        for segment in plan.segment_predictions
    )


def test_build_segment_plan_splits_oversized_list_item_before_hard_cap() -> None:
    plan = build_segment_plan(
        text=(
            "Ett: ni ska tala lugnt och tydligt för att alla i rummet ska kunna följa med "
            "och för att tempot inte ska bli för högt när instruktionerna blir längre än vanligt."
        ),
        max_chars=320,
        cross_fade_ms=80,
    )

    assert plan.segment_count >= 2
    assert all(
        segment.predicted_duration_seconds <= plan.hard_max_seconds
        for segment in plan.segment_predictions
    )
    assert plan.segments[0].startswith("Ett:")


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
        segment_texts=["Första delen,", "andra delen."],
        stitch_mode="simple",
    )

    assert stitched.waveform.shape == (1, 6)
    assert torch.allclose(
        stitched.waveform,
        torch.tensor([[0.0, 0.5, 1.0, 0.5, 0.0, 0.0]], dtype=torch.float32),
    )
    assert stitched.boundary_decisions == []


def test_stitch_waveforms_speech_aware_trims_noise_and_records_boundaries() -> None:
    waveform_a = torch.tensor(
        [[0.0, 0.0, 0.0, 0.2, 0.2, 0.2, 0.01, 0.0, 0.0, 0.0]],
        dtype=torch.float32,
    )
    waveform_b = torch.tensor(
        [[0.0, 0.0, 0.05, 0.3, 0.3, 0.3, 0.0, 0.0, 0.0, 0.0]],
        dtype=torch.float32,
    )

    stitched = stitch_waveforms(
        waveforms=[waveform_a, waveform_b],
        sample_rate_hz=100,
        cross_fade_ms=40,
        segment_texts=["Första delen,", "andra delen."],
        stitch_mode="speech_aware",
    )

    assert stitched.waveform.shape[0] == 1
    assert len(stitched.chunk_analyses) == 2
    assert len(stitched.boundary_decisions) == 1
    assert stitched.chunk_analyses[0].leading_trim_ms > 0
    assert stitched.chunk_analyses[0].trailing_trim_ms > 0
    assert stitched.boundary_decisions[0].boundary_type == "clause"
    assert stitched.boundary_decisions[0].inserted_pause_ms == 110.0


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
            stitch_mode="speech_aware",
            debug_dir=tmp_path,
        ),
    )

    assert len(calls) == 3
    plan_payload = json.loads((tmp_path / "segment_plan.json").read_text(encoding="utf-8"))
    assert plan_payload["segment_count"] == 3
    assert (tmp_path / "chunk_01.wav").exists()
    assert (tmp_path / "chunk_02.wav").exists()
    assert (tmp_path / "chunk_01_post.wav").exists()
    assert (tmp_path / "chunk_analysis.json").exists()
    assert (tmp_path / "boundary_decisions.json").exists()
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
            stitch_mode="simple",
            debug_dir=None,
        ),
    )

    assert calls == ["Hej världen. Det här är ett prov."]
