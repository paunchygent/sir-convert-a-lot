"""Repo-fixture source adapter for the first Task 103 Qwen preprocessing smoke run.

Purpose:
    Preserve the existing deterministic repo-fixture smoke rows behind the same
    adapter contract used by the real public corpus loaders.

Relationships:
    - Consumed by `task103_qwen_preprocessing_core.py` as the default local
      source adapter when no explicit public corpus inputs are requested.
    - Produces `SourceRecord` rows from checked-in local verification assets.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import AudioLocator, SourceRecord


def repo_fixture_source_records(workspace_root: Path) -> list[SourceRecord]:
    """Return deterministic Swedish smoke source rows from local repo artifacts."""
    olof_audio_path = (
        workspace_root
        / "build/verification/task-85-f5-tts-hemma-voice-sample-new/inputs/reference_24k_sv.wav"
    )
    olof_text_path = (
        workspace_root
        / "build/verification/task-85-f5-tts-hemma-voice-sample-new/inputs/reference_source_sv.txt"
    )
    christian_audio_path = workspace_root / (
        "build/verification/task-94-youtube-reference-audio-for-chatterbox-ptole/"
        "inputs/reference_2m09_2m20p5_prompt.wav"
    )
    christian_ref_path = workspace_root / (
        "build/verification/task-94-youtube-reference-audio-for-chatterbox-ptole/"
        "inputs/reference_2m00_2m10_prompt.wav"
    )
    christian_text_path = workspace_root / (
        "build/verification/task-94-youtube-reference-audio-for-chatterbox-ptole/"
        "inputs/reference_2m09_2m20p5_prompt.txt"
    )
    fixture_rows = [
        SourceRecord(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-olof-001",
            speaker_id="speaker_olof_larsson",
            speaker_name="Olof Larsson",
            speaker_from_id=True,
            source_audio_path=olof_audio_path.as_posix(),
            source_audio_locator=AudioLocator(olof_audio_path),
            reference_audio_locator=AudioLocator(olof_audio_path),
            text_raw=olof_text_path.read_text(encoding="utf-8").strip(),
            language="sv-SE",
            speaker_total_hours=None,
            has_label_files=True,
            speaker_audio_meta_ok=True,
        ),
        SourceRecord(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-christian-001",
            speaker_id="speaker_christian_hedlund",
            speaker_name="Christian Hedlund",
            speaker_from_id=True,
            source_audio_path=christian_audio_path.as_posix(),
            source_audio_locator=AudioLocator(christian_audio_path),
            reference_audio_locator=AudioLocator(christian_ref_path),
            text_raw=christian_text_path.read_text(encoding="utf-8").strip(),
            language="sv-SE",
            speaker_total_hours=None,
            has_label_files=True,
            speaker_audio_meta_ok=True,
        ),
    ]
    for row in fixture_rows:
        source_locator = row.source_audio_locator
        reference_locator = row.reference_audio_locator
        assert source_locator is not None
        assert reference_locator is not None
        for required_path in (source_locator.path, reference_locator.path):
            if not required_path.is_file():
                raise FileNotFoundError(f"Task 103 fixture source is missing: {required_path}")
    return fixture_rows
