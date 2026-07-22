"""Row-processing stage tests for Qwen preprocessing.

Purpose:
    Verify the transformation from source records to durable spool rows,
    including 24 kHz audio materialization, ASR scoring, and manifest-family
    assignment.

Relationships:
    - Tests `ml.qwen.preprocessing.row_processing.process_rows_to_spool`.
    - Uses fixtures from `tests.preprocessing.test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.common.models import AudioLocator
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.row_processing import (
    process_rows_to_spool,
)

from tests.preprocessing.test_support import (
    FakeAsrScorer,
    preprocessing_settings_fixture,
    source_record_fixture,
    write_test_wav,
)


def test_process_rows_to_spool_materializes_audio_and_writes_spool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Row processing should materialize 24 kHz audio and write durable spool JSON."""
    output_root = tmp_path / "output"
    settings = preprocessing_settings_fixture(output_root)
    source_audio_path = tmp_path / "source.wav"
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    source_record = source_record_fixture(source_audio_locator=AudioLocator(source_audio_path))

    def _fake_resample(source: Path, target: Path) -> float:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fake-audio", encoding="utf-8")
        return 5.0

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.row_processing._resample_and_write_audio",
        _fake_resample,
    )

    fake_scorer = FakeAsrScorer(
        transcripts={
            output_root / "audio_24k/test_dataset/smoke/speaker-001/row-001.wav": "Hej världen."
        }
    )

    process_rows_to_spool(
        settings,
        output_root=output_root,
        source_records=[source_record],
        scorer_factory=lambda *_: fake_scorer,
    )

    spool_path = output_root / "spool/rows/test_dataset/smoke/speaker-001/row-001.json"
    assert spool_path.is_file()
    assert (output_root / "audio_24k/test_dataset/smoke/speaker-001/row-001.wav").is_file()
