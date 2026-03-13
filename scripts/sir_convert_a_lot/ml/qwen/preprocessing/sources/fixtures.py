"""Repo-local fixture source adapter for the Qwen corpus pipeline.

Purpose:
    Provide a deterministic, zero-download source of Swedish speech records
    for unit testing and pipeline smoke-runs.

Relationships:
    - Emits `SourceRecord` rows from `ml.qwen.common.models`.
    - Used by the preprocessing pipeline tests to avoid external HF dependencies.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import AudioLocator, SourceRecord


def repo_fixture_source_records(repo_root: Path) -> list[SourceRecord]:
    """Return a bounded list of source records from repo-local fixtures."""
    fixtures_dir = repo_root / "tests/fixtures/qwen3_tts_swedish_corpus"
    if not fixtures_dir.is_dir():
        raise FileNotFoundError(f"Missing repo fixtures directory: {fixtures_dir}")

    # For now, we manually enumerate the fixtures known to be in the repo.
    # As the fixture set grows, this can move to a discovery pattern.
    records = []

    # Waxholm smoke row
    waxholm_wav = fixtures_dir / "waxholm/scenes_formatted/fp2060/fp2060.p1.wav"
    if waxholm_wav.is_file():
        records.append(
            SourceRecord(
                dataset="waxholm_fixture",
                source_split="smoke",
                dataset_row_id="fp2060.p1",
                speaker_id="waxholm_fp2060",
                speaker_name="fp2060",
                speaker_from_id=True,
                source_audio_path=waxholm_wav.as_posix(),
                source_audio_locator=AudioLocator(waxholm_wav),
                text_raw="Välkommen till Waxholm.",
                language="sv-SE",
                speaker_total_hours=0.001,
                has_label_files=True,
                speaker_audio_meta_ok=True,
                source_sample_rate_hz=16_000,
                duration_seconds=2.5,
            )
        )

    # FLEURS smoke row
    fleurs_wav = fixtures_dir / "fleurs/data/sv_se/audio/dev/10001.wav"
    if fleurs_wav.is_file():
        records.append(
            SourceRecord(
                dataset="fleurs_fixture",
                source_split="smoke",
                dataset_row_id="dev-10001",
                speaker_id="fleurs_sv_se_10001",
                speaker_name="FLEURS 10001",
                speaker_from_id=True,
                source_audio_path=fleurs_wav.as_posix(),
                source_audio_locator=AudioLocator(fleurs_wav),
                text_raw="Detta är ett FLEURS-exempel.",
                language="sv-SE",
                speaker_total_hours=0.001,
                has_label_files=True,
                speaker_audio_meta_ok=True,
                source_sample_rate_hz=16_000,
                duration_seconds=3.0,
            )
        )

    return records
