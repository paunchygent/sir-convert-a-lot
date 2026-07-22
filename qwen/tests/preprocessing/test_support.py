"""Shared test support for Qwen preprocessing tests.

Purpose:
    Provide reusable factories, fake implementations, and stable constants for
    testing the Swedish Qwen preprocessing pipeline.

Relationships:
    - Consumed by `test_row_processing`, `test_pipeline`, and other
      preprocessing test modules.
    - Reuses data contracts from `ml.qwen.common.models` and
      `ml.qwen.preprocessing.models`.
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Sequence, TypeGuard

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    AudioLocator,
    SourceRecord,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    InventoryRow,
    PreprocessingReport,
    PreprocessingSettings,
    SpoolRow,
)


def source_record_fixture(
    *,
    dataset: str = "test_dataset",
    source_split: str = "smoke",
    dataset_row_id: str = "row-001",
    speaker_id: str = "speaker-001",
    text_raw: str = "Hej världen.",
    source_audio_locator: AudioLocator | None = None,
) -> SourceRecord:
    """Build one source-record fixture for unit tests."""
    return SourceRecord(
        dataset=dataset,
        source_split=source_split,
        dataset_row_id=dataset_row_id,
        speaker_id=speaker_id,
        speaker_name=f"Speaker {speaker_id}",
        speaker_from_id=True,
        source_audio_path=f"path/to/{dataset_row_id}.wav",
        source_audio_locator=source_audio_locator,
        text_raw=text_raw,
        language="sv-SE",
        speaker_total_hours=0.01,
        has_label_files=True,
        speaker_audio_meta_ok=True,
        source_sample_rate_hz=16_000,
        duration_seconds=5.0,
    )


def inventory_row_fixture(
    source_record: SourceRecord,
    *,
    text_normalized: str = "Hej världen.",
) -> InventoryRow:
    """Build one inventory-row fixture projected from a source record."""
    return InventoryRow(
        dataset=source_record.dataset,
        source_split=source_record.source_split,
        dataset_row_id=source_record.dataset_row_id,
        source_audio_path=source_record.source_audio_path,
        source_sample_rate_hz=source_record.source_sample_rate_hz or 16_000,
        duration_seconds=source_record.duration_seconds or 5.0,
        text_raw=source_record.text_raw,
        text_normalized=text_normalized,
        speaker_id=source_record.speaker_id,
        speaker_name=source_record.speaker_name,
        speaker_from_id=source_record.speaker_from_id,
        speaker_total_hours=source_record.speaker_total_hours or 0.01,
        language=source_record.language,
        has_label_files=source_record.has_label_files,
        speaker_audio_meta_ok=source_record.speaker_audio_meta_ok,
        boilerplate_group=None,
        notes=None,
    )


def spool_row_fixture(
    inventory_row: InventoryRow,
    *,
    asr_transcript: str = "Hej världen.",
    asr_wer: float = 0.0,
) -> SpoolRow:
    """Build one spool-row fixture projected from an inventory row."""
    return SpoolRow(
        dataset=inventory_row.dataset,
        source_split=inventory_row.source_split,
        dataset_row_id=inventory_row.dataset_row_id,
        speaker_id=inventory_row.speaker_id,
        speaker_name=inventory_row.speaker_name,
        speaker_from_id=inventory_row.speaker_from_id,
        source_audio_path=inventory_row.source_audio_path,
        audio_24k_path=f"audio_24k/{inventory_row.dataset_row_id}.wav",
        duration_seconds=inventory_row.duration_seconds,
        text_normalized=inventory_row.text_normalized,
        reference_audio_24k_paths={},
        asr_model="test-asr",
        asr_revision="strict",
        asr_transcript=asr_transcript,
        asr_wer=asr_wer,
        quality_tier="high_trust" if asr_wer < 0.1 else "medium_trust",
        speaker_quality_gate="speaker_from_id",
        dedup_applied=False,
        admission_decision="admit",
        manifest_targets=("swedish_smoke_train",),
    )


def preprocessing_settings_fixture(output_root: Path) -> PreprocessingSettings:
    """Build one preprocessing-settings fixture for unit tests."""
    return PreprocessingSettings(
        output_root=output_root,
        asr_model="test-asr",
        asr_revision="strict",
        tokenizer_model="test-tokenizer",
        stage="all",
    )


def write_test_wav(path: Path, *, sample_rate_hz: int, duration_seconds: float) -> None:
    """Write one deterministic mono WAV fixture for preprocessing tests."""
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
    """Build one local-audio source-record fixture for preprocessing tests."""
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


def report_only_preprocessing_runner(expected_report: PreprocessingReport):
    """Return one stub preprocessing runner that simply returns the expected report."""

    def _runner(
        settings: PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> PreprocessingReport:
        del settings
        del source_records
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        return expected_report

    return _runner


class FakeAsrScorer:
    """Fake ASR scorer that returns deterministic transcripts from a map."""

    def __init__(self, transcripts: dict[Path, str] | None = None) -> None:
        self.transcripts = transcripts or {}
        self.call_count = 0

    def ensure_loaded(self) -> None:
        """Stub for eager model loading."""

    def transcribe(self, audio_path: Path) -> str:
        """Return one fake transcript for the provided audio path."""
        self.call_count += 1
        return self.transcripts.get(audio_path, "Hej världen.")


def write_jsonl_fixture(path: Path, rows: Sequence[object]) -> None:
    """Write one bounded sequence of objects to one JSONL fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = asdict(row) if _is_dataclass_instance(row) else row
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _is_dataclass_instance(value: object) -> TypeGuard[DataclassInstance]:
    """Return whether one object is a dataclass instance and not a dataclass type."""
    return not isinstance(value, type) and is_dataclass(value)


def stub_whisper_strict_scorer(
    monkeypatch,
    *,
    transcript: str = "Hej från Sverige.",
    transcribed_paths: list[str] | None = None,
) -> None:
    """Stub ASR loading and transcription for lightweight processing tests."""

    def _fake_ensure_loaded(self: object) -> None:
        del self

    def _fake_transcribe(self: object, audio_path: Path) -> str:
        del self
        if transcribed_paths is not None:
            transcribed_paths.append(audio_path.name)
        return transcript

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.pipeline.WhisperStrictScorer.ensure_loaded",
        _fake_ensure_loaded,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.pipeline.WhisperStrictScorer.transcribe",
        _fake_transcribe,
    )
