"""Shared helpers for Task 103 preprocessing tests.

Purpose:
    Centralize the small deterministic builders that multiple Task 103 test
    modules need so the decomposed test surface stays consistent and avoids
    copy-pasted fixture logic.

Relationships:
    - Imported by the domain-focused Task 103 test modules.
    - Builds typed `SourceRecord` and report-runner fixtures used across
      runner, processing, source-adapter, and ASR-adjacent tests.
"""

from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Sequence

import pytest

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    AudioLocator,
    SourceRecord,
)


def write_test_wav(path: Path, *, sample_rate_hz: int, duration_seconds: float) -> None:
    """Write one deterministic mono WAV fixture for Task 103 tests."""
    frame_count = int(sample_rate_hz * duration_seconds)
    amplitude = 12_000
    frequency_hz = 220.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(path.as_posix(), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        frames = bytearray()
        for frame_index in range(frame_count):
            sample = int(
                amplitude * math.sin((2.0 * math.pi * frequency_hz * frame_index) / sample_rate_hz)
            )
            frames.extend(sample.to_bytes(length=2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))


def build_source_record(
    *,
    dataset: str,
    source_split: str,
    dataset_row_id: str,
    speaker_id: str,
    speaker_name: str,
    source_audio_path: Path,
    reference_audio_path: Path | None,
    text_raw: str,
) -> SourceRecord:
    """Build one local-audio `SourceRecord` fixture for preprocessing tests."""
    return SourceRecord(
        dataset=dataset,
        source_split=source_split,
        dataset_row_id=dataset_row_id,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        speaker_from_id=True,
        source_audio_path=source_audio_path.as_posix(),
        source_audio_locator=AudioLocator(source_audio_path),
        reference_audio_locator=(
            None if reference_audio_path is None else AudioLocator(reference_audio_path)
        ),
        text_raw=text_raw,
        language="sv-SE",
        speaker_total_hours=None,
        has_label_files=True,
        speaker_audio_meta_ok=True,
    )


def report_only_preprocessing_runner(
    expected_report: Task103PreprocessingReport,
):
    """Return one stub Task 103 runner that simply returns the expected report."""

    def _runner(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        del settings
        del source_records
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        return expected_report

    return _runner


def stub_whisper_strict_scorer(
    monkeypatch: pytest.MonkeyPatch,
    *,
    transcript: str = "Hej från Sverige.",
    transcribed_paths: list[str] | None = None,
) -> None:
    """Stub Task 103 ASR loading and transcription for lightweight processing tests."""

    def _fake_ensure_loaded(self: object) -> None:
        del self

    def _fake_transcribe(self: object, audio_path: Path) -> str:
        del self
        if transcribed_paths is not None:
            transcribed_paths.append(audio_path.name)
        return transcript

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.ensure_loaded",
        _fake_ensure_loaded,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        _fake_transcribe,
    )
