"""Tests for canonical Task 103 processed-root dedupe."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_canonical_processed_root import (
    build_canonical_processed_root,
    canonical_processed_root_conflicts_path,
    canonical_processed_root_duplicates_path,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import SpoolRow
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    spool_rows_dir,
    write_spool_row,
)
from tests.sir_convert_a_lot.task103_test_support import write_test_wav


def _write_spool_row_fixture(
    *,
    run_root: Path,
    dataset_row_id: str,
    audio_name: str,
    transcript: str = "Hej från Sverige.",
    quality_tier: str = "high_trust",
) -> None:
    """Persist one minimal spool-row fixture and its referenced audio file."""
    audio_path = run_root / "audio_24k" / "rixvox" / "train" / "speaker-a" / audio_name
    write_test_wav(audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    write_spool_row(
        run_root,
        SpoolRow(
            dataset="rixvox",
            source_split="train",
            dataset_row_id=dataset_row_id,
            speaker_id="speaker-a",
            speaker_name="speaker-a",
            speaker_from_id=True,
            source_audio_path=f"speaker-a/{audio_name}",
            audio_24k_path=audio_path.relative_to(run_root).as_posix(),
            duration_seconds=1.0,
            text_normalized="hej från sverige",
            reference_audio_24k_paths={},
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            asr_transcript=transcript,
            asr_wer=0.0,
            quality_tier=quality_tier,
            speaker_quality_gate="speaker_from_id",
            dedup_applied=False,
            admission_decision="admit",
            manifest_targets=("swedish_smoke_train",),
        ),
    )


def test_build_canonical_processed_root_keeps_unique_and_identical_duplicate_rows(
    tmp_path: Path,
) -> None:
    """Canonical processed-root build should keep one winner for identical duplicates."""
    preferred_root = tmp_path / "preferred"
    secondary_root = tmp_path / "secondary"
    _write_spool_row_fixture(
        run_root=preferred_root,
        dataset_row_id="row-1",
        audio_name="row-1.wav",
    )
    _write_spool_row_fixture(
        run_root=secondary_root,
        dataset_row_id="row-1",
        audio_name="row-1.wav",
    )
    _write_spool_row_fixture(
        run_root=secondary_root,
        dataset_row_id="row-2",
        audio_name="row-2.wav",
    )

    output_root = tmp_path / "canonical-root"
    summary = build_canonical_processed_root(
        output_root=output_root,
        run_roots=[preferred_root, secondary_root],
    )

    retained_rows = sorted(spool_rows_dir(output_root).rglob("*.json"))
    assert summary.retained_row_count == 2
    assert summary.dropped_duplicate_row_count == 1
    assert summary.conflict_row_count == 0
    assert len(retained_rows) == 2
    duplicates = [
        json.loads(line)
        for line in canonical_processed_root_duplicates_path(output_root).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert duplicates[0]["winning_run_root"] == preferred_root.as_posix()
    assert duplicates[0]["dropped_run_root"] == secondary_root.as_posix()


def test_build_canonical_processed_root_quarantines_conflicting_rows(tmp_path: Path) -> None:
    """Canonical processed-root build should quarantine same-row conflicts."""
    preferred_root = tmp_path / "preferred"
    secondary_root = tmp_path / "secondary"
    _write_spool_row_fixture(
        run_root=preferred_root,
        dataset_row_id="row-1",
        audio_name="row-1.wav",
        transcript="Hej från Sverige.",
    )
    _write_spool_row_fixture(
        run_root=secondary_root,
        dataset_row_id="row-1",
        audio_name="row-1.wav",
        transcript="Annan transkription.",
    )

    output_root = tmp_path / "canonical-root"
    summary = build_canonical_processed_root(
        output_root=output_root,
        run_roots=[preferred_root, secondary_root],
    )

    assert summary.retained_row_count == 0
    assert summary.conflict_row_count == 1
    assert list(spool_rows_dir(output_root).rglob("*.json")) == []
    conflicts = [
        json.loads(line)
        for line in canonical_processed_root_conflicts_path(output_root).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert conflicts[0]["reason"] == "payload_mismatch"
    assert sorted(conflicts[0]["candidate_run_roots"]) == [
        preferred_root.as_posix(),
        secondary_root.as_posix(),
    ]


def test_build_canonical_processed_root_resolves_unicode_normalized_audio_paths(
    tmp_path: Path,
) -> None:
    """Canonical processed-root build should survive Unicode filename normalization drift."""
    preferred_root = tmp_path / "preferred"
    audio_name = "GS01FÖU5-14-0.wav"
    decomposed_audio_name = unicodedata.normalize("NFD", audio_name)
    audio_path = (
        preferred_root
        / "audio_24k"
        / "rixvox"
        / "train"
        / "speaker-a"
        / decomposed_audio_name
    )
    audio_24k_path = (
        preferred_root / "audio_24k" / "rixvox" / "train" / "speaker-a" / audio_name
    ).relative_to(preferred_root)
    write_test_wav(audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    write_spool_row(
        preferred_root,
        SpoolRow(
            dataset="rixvox",
            source_split="train",
            dataset_row_id="row-unicode",
            speaker_id="speaker-a",
            speaker_name="speaker-a",
            speaker_from_id=True,
            source_audio_path=f"speaker-a/{audio_name}",
            audio_24k_path=audio_24k_path.as_posix(),
            duration_seconds=1.0,
            text_normalized="hej från sverige",
            reference_audio_24k_paths={},
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            asr_transcript="Hej från Sverige.",
            asr_wer=0.0,
            quality_tier="high_trust",
            speaker_quality_gate="speaker_from_id",
            dedup_applied=False,
            admission_decision="admit",
            manifest_targets=("swedish_smoke_train",),
        ),
    )

    output_root = tmp_path / "canonical-root"
    summary = build_canonical_processed_root(
        output_root=output_root,
        run_roots=[preferred_root],
    )

    assert summary.retained_row_count == 1
    retained_audio = output_root / "audio_24k" / "rixvox" / "train" / "speaker-a" / audio_name
    assert retained_audio.is_file()
