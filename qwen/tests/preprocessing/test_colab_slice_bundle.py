"""Tests for the portable Colab Qwen slice-bundle surface."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    AudioLocator,
    SourceRecord,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import (
    SourceSelectionSummary,
    build_portable_slice_bundle,
    build_remaining_unique_portable_slice_bundle,
    dedupe_selected_source_records,
    deduped_selected_source_summary_path,
    load_portable_selected_source_records,
    localize_portable_slice,
    localized_selected_source_records_path,
    localized_slice_summary_path,
    portable_required_files_path,
    portable_slice_summary_path,
    source_record_from_payload,
    source_record_to_payload,
    stage_required_files_for_portable_slice,
    unique_allocation_summary_path,
    write_row_key_records,
    write_selected_source_records,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    completed_row_keys_index_path,
    iter_jsonl_objects,
    write_jsonl,
)

from tests.preprocessing.test_support import write_test_wav


def _build_rixvox_source_record(
    *,
    dataset_row_id: str,
    speaker_id: str,
    source_audio_path: str,
    archive_path: Path,
) -> SourceRecord:
    """Build one archive-backed RixVox source record for portable slice tests."""
    return SourceRecord(
        dataset="rixvox",
        source_split="train",
        dataset_row_id=dataset_row_id,
        speaker_id=speaker_id,
        speaker_name=speaker_id,
        speaker_from_id=True,
        source_audio_path=source_audio_path,
        source_audio_locator=AudioLocator(path=archive_path, archive_member=source_audio_path),
        text_raw="Hej från Sverige.",
        language="sv-SE",
        speaker_total_hours=1.0,
        has_label_files=False,
        speaker_audio_meta_ok=True,
        source_sample_rate_hz=16_000,
        duration_seconds=5.0,
    )


def _write_completed_row_keys_index(run_root: Path, row_ids: list[str]) -> None:
    """Persist one lightweight completed-row index for a test run root."""
    write_jsonl(
        completed_row_keys_index_path(run_root),
        [
            {
                "dataset": "rixvox",
                "source_split": "train",
                "dataset_row_id": row_id,
            }
            for row_id in row_ids
        ],
    )


def test_build_portable_slice_bundle_is_disjoint(tmp_path: Path) -> None:
    """Portable slice planning should partition one bounded source-selection deterministically."""
    run_root = tmp_path / "run"
    archive_path = tmp_path / "train_0.tar.gz"
    source_records = [
        _build_rixvox_source_record(
            dataset_row_id=f"row-{row_index}",
            speaker_id=f"speaker-{row_index % 2}",
            source_audio_path=f"speaker-{row_index}/clip-{row_index}.wav",
            archive_path=archive_path,
        )
        for row_index in range(6)
    ]
    write_selected_source_records(
        run_root,
        source_records=source_records,
        summary=SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=6,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=6,
        ),
    )

    first_slice_root = tmp_path / "slice-0"
    second_slice_root = tmp_path / "slice-1"
    first_summary = build_portable_slice_bundle(
        source_run_root=run_root,
        output_root=first_slice_root,
        slice_count=2,
        slice_index=0,
        rixvox_revision="rev-a",
    )
    second_summary = build_portable_slice_bundle(
        source_run_root=run_root,
        output_root=second_slice_root,
        slice_count=2,
        slice_index=1,
        rixvox_revision="rev-a",
    )

    first_slice_ids = {
        source_record.dataset_row_id
        for source_record in load_portable_selected_source_records(first_slice_root)
    }
    second_slice_ids = {
        source_record.dataset_row_id
        for source_record in load_portable_selected_source_records(second_slice_root)
    }

    assert first_summary.selected_row_count == 3
    assert second_summary.selected_row_count == 3
    assert first_slice_ids.isdisjoint(second_slice_ids)
    assert first_slice_ids | second_slice_ids == {f"row-{row_index}" for row_index in range(6)}

    first_required_files = json.loads(portable_required_files_path(first_slice_root).read_text())
    assert first_required_files == [
        {
            "repo_id": "KBLab/rixvox",
            "repo_type": "dataset",
            "filename": "data/train/train_0.tar.gz",
            "local_relative_path": "kblab_rixvox/data/train/train_0.tar.gz",
            "revision": "rev-a",
        }
    ]
    first_slice_rows = load_portable_selected_source_records(first_slice_root)
    assert all(row.source_audio_locator is None for row in first_slice_rows)
    assert portable_slice_summary_path(first_slice_root).is_file()


def test_plan_remaining_unique_excludes_prior_allocations(tmp_path: Path) -> None:
    """Guarded slice allocation should subtract completed and reserved row keys first."""
    run_root = tmp_path / "selection-run"
    archive_path = tmp_path / "train_0.tar.gz"
    source_records = [
        _build_rixvox_source_record(
            dataset_row_id=f"row-{row_index}",
            speaker_id=f"speaker-{row_index % 2}",
            source_audio_path=f"speaker-{row_index}/clip-{row_index}.wav",
            archive_path=archive_path,
        )
        for row_index in range(8)
    ]
    write_selected_source_records(
        run_root,
        source_records=source_records,
        summary=SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=8,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=8,
        ),
    )
    processed_run_root = tmp_path / "processed-run"
    _write_completed_row_keys_index(processed_run_root, ["row-0", "row-3"])
    reserved_records_path = tmp_path / "reserved.jsonl"
    write_jsonl(
        reserved_records_path,
        [
            source_record_to_payload(source_records[5]),
            source_record_to_payload(source_records[6]),
        ],
    )

    output_root = tmp_path / "remaining-slice"
    summary = build_remaining_unique_portable_slice_bundle(
        source_run_root=run_root,
        output_root=output_root,
        slice_count=2,
        slice_index=0,
        rixvox_revision="rev-a",
        exclude_completed_run_roots=[processed_run_root],
        exclude_selected_source_records_paths=[reserved_records_path],
        exclude_row_keys_paths=[],
    )

    planned_ids = {row.dataset_row_id for row in load_portable_selected_source_records(output_root)}
    assert summary.remaining_train_row_count == 4
    assert summary.selected_row_count == 2
    assert summary.excluded_completed_row_count == 2
    assert summary.excluded_reserved_row_count == 2
    assert summary.excluded_explicit_row_count == 0
    assert summary.total_excluded_key_count == 4
    assert planned_ids == {"row-1", "row-2"}
    assert unique_allocation_summary_path(output_root).is_file()


def test_dedupe_selected_source_records_filters_completed_rows(tmp_path: Path) -> None:
    """Dedupe should emit only rows not already completed or reserved elsewhere."""
    selected_source_records_path = tmp_path / "selected_source_records.jsonl"
    archive_path = tmp_path / "train_0.tar.gz"
    source_records = [
        _build_rixvox_source_record(
            dataset_row_id=f"row-{row_index}",
            speaker_id=f"speaker-{row_index % 2}",
            source_audio_path=f"speaker-{row_index}/clip-{row_index}.wav",
            archive_path=archive_path,
        )
        for row_index in range(5)
    ]
    write_jsonl(
        selected_source_records_path,
        [source_record_to_payload(source_record) for source_record in source_records],
    )
    processed_run_root = tmp_path / "processed-run"
    _write_completed_row_keys_index(processed_run_root, ["row-0", "row-2"])
    reserved_records_path = tmp_path / "reserved.jsonl"
    write_jsonl(
        reserved_records_path,
        [source_record_to_payload(source_records[4])],
    )

    output_path = tmp_path / "deduped-slice" / "selected_source_records.jsonl"
    summary = dedupe_selected_source_records(
        selected_source_records_path=selected_source_records_path,
        output_path=output_path,
        exclude_completed_run_roots=[processed_run_root],
        exclude_selected_source_records_paths=[reserved_records_path],
        exclude_row_keys_paths=[],
    )

    remaining_rows = load_portable_selected_source_records(output_path.parent)
    assert [row.dataset_row_id for row in remaining_rows] == ["row-1", "row-3"]
    assert summary.input_row_count == 5
    assert summary.output_row_count == 2
    assert summary.excluded_completed_row_count == 2
    assert summary.excluded_reserved_row_count == 1
    assert summary.excluded_explicit_row_count == 0
    assert summary.total_excluded_key_count == 3
    assert deduped_selected_source_summary_path(output_path).is_file()


def test_dedupe_selected_source_records_filters_explicit_row_key_exclusions(
    tmp_path: Path,
) -> None:
    """Dedupe should also subtract explicit row-key exclusion manifests."""
    selected_source_records_path = tmp_path / "selected_source_records.jsonl"
    archive_path = tmp_path / "train_0.tar.gz"
    source_records = [
        _build_rixvox_source_record(
            dataset_row_id=f"row-{row_index}",
            speaker_id=f"speaker-{row_index % 2}",
            source_audio_path=f"speaker-{row_index}/clip-{row_index}.wav",
            archive_path=archive_path,
        )
        for row_index in range(4)
    ]
    write_jsonl(
        selected_source_records_path,
        [source_record_to_payload(source_record) for source_record in source_records],
    )
    conflict_row_keys_path = tmp_path / "conflicts.jsonl"
    write_row_key_records(
        conflict_row_keys_path,
        [("rixvox", "train", "row-1")],
    )

    output_path = tmp_path / "deduped-slice" / "selected_source_records.jsonl"
    summary = dedupe_selected_source_records(
        selected_source_records_path=selected_source_records_path,
        output_path=output_path,
        exclude_completed_run_roots=[],
        exclude_selected_source_records_paths=[],
        exclude_row_keys_paths=[conflict_row_keys_path],
    )

    remaining_rows = load_portable_selected_source_records(output_path.parent)
    assert [row.dataset_row_id for row in remaining_rows] == ["row-0", "row-2", "row-3"]
    assert summary.excluded_explicit_row_count == 1
    assert summary.total_excluded_key_count == 1


def test_stage_required_files_for_portable_slice(tmp_path: Path, monkeypatch) -> None:
    """Portable slice staging should materialize the exact required archive."""
    slice_root = tmp_path / "slice"
    cached_archive_path = tmp_path / "cached/train_0.tar.gz"
    staged_audio_path = tmp_path / "needed.wav"
    write_test_wav(staged_audio_path, sample_rate_hz=16_000, duration_seconds=0.5)
    cached_archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(cached_archive_path, "w:gz") as archive:
        audio_bytes = staged_audio_path.read_bytes()
        member = tarfile.TarInfo(name="speaker-0/clip-0.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    write_jsonl(
        slice_root / "selected_source_records.jsonl",
        [
            source_record_to_payload(
                SourceRecord(
                    dataset="rixvox",
                    source_split="train",
                    dataset_row_id="row-0",
                    speaker_id="speaker-0",
                    speaker_name="speaker-0",
                    speaker_from_id=True,
                    source_audio_path="speaker-0/clip-0.wav",
                    source_audio_locator=None,
                    text_raw="Hej från Sverige.",
                    language="sv-SE",
                    speaker_total_hours=1.0,
                    has_label_files=False,
                    speaker_audio_meta_ok=True,
                    source_sample_rate_hz=16_000,
                    duration_seconds=5.0,
                )
            )
        ],
    )
    (slice_root / "required_hub_files.json").write_text(
        json.dumps(
            [
                {
                    "repo_id": "KBLab/rixvox",
                    "repo_type": "dataset",
                    "filename": "data/train/train_0.tar.gz",
                    "local_relative_path": "kblab_rixvox/data/train/train_0.tar.gz",
                    "revision": "rev-a",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding.hf_hub_download",
        lambda **_kwargs: cached_archive_path.as_posix(),
    )

    staged_paths = stage_required_files_for_portable_slice(
        slice_root=slice_root,
        data_root=tmp_path / "data_root",
        cache_dir=tmp_path / "cache",
    )

    assert staged_paths == [tmp_path / "data_root/raw/kblab_rixvox/data/train/train_0.tar.gz"]
    assert staged_paths[0].is_file()


def test_stage_required_files_emits_progress(tmp_path: Path, monkeypatch, capsys) -> None:
    """Portable slice staging should emit per-archive progress and elapsed timing."""
    slice_root = tmp_path / "slice"
    cached_archive_path = tmp_path / "cached/train_0.tar.gz"
    staged_audio_path = tmp_path / "needed.wav"
    write_test_wav(staged_audio_path, sample_rate_hz=16_000, duration_seconds=0.5)
    cached_archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(cached_archive_path, "w:gz") as archive:
        audio_bytes = staged_audio_path.read_bytes()
        member = tarfile.TarInfo(name="speaker-0/clip-0.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    write_jsonl(
        slice_root / "selected_source_records.jsonl",
        [
            source_record_to_payload(
                SourceRecord(
                    dataset="rixvox",
                    source_split="train",
                    dataset_row_id="row-0",
                    speaker_id="speaker-0",
                    speaker_name="speaker-0",
                    speaker_from_id=True,
                    source_audio_path="speaker-0/clip-0.wav",
                    source_audio_locator=None,
                    text_raw="Hej från Sverige.",
                    language="sv-SE",
                    speaker_total_hours=1.0,
                    has_label_files=False,
                    speaker_audio_meta_ok=True,
                    source_sample_rate_hz=16_000,
                    duration_seconds=5.0,
                )
            )
        ],
    )
    (slice_root / "required_hub_files.json").write_text(
        json.dumps(
            [
                {
                    "repo_id": "KBLab/rixvox",
                    "repo_type": "dataset",
                    "filename": "data/train/train_0.tar.gz",
                    "local_relative_path": "kblab_rixvox/data/train/train_0.tar.gz",
                    "revision": "rev-a",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding.hf_hub_download",
        lambda **_kwargs: cached_archive_path.as_posix(),
    )

    stage_required_files_for_portable_slice(
        slice_root=slice_root,
        data_root=tmp_path / "data_root",
        cache_dir=tmp_path / "cache",
    )

    captured = capsys.readouterr()
    assert "[qwen-portable-slice] staging required archives count=1" in captured.out
    assert (
        "[qwen-portable-slice] staging archive start index=1/1 filename=data/train/train_0.tar.gz"
        in (captured.out)
    )
    assert "[qwen-portable-slice] staging archive done index=1/1" in captured.out
    assert "[qwen-portable-slice] staging required archives done count=1" in captured.out


def test_localize_portable_slice_persists_plain_file_manifest(tmp_path: Path) -> None:
    """Portable slice localization should persist plain local files plus a manifest."""
    slice_root = tmp_path / "slice"
    staged_audio_path = tmp_path / "needed.wav"
    write_test_wav(staged_audio_path, sample_rate_hz=16_000, duration_seconds=0.5)

    staged_archive_path = tmp_path / "data_root/raw/kblab_rixvox/data/train/train_0.tar.gz"
    staged_archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(staged_archive_path, "w:gz") as archive:
        audio_bytes = staged_audio_path.read_bytes()
        member = tarfile.TarInfo(name="speaker-0/clip-0.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    write_jsonl(
        slice_root / "selected_source_records.jsonl",
        [
            source_record_to_payload(
                SourceRecord(
                    dataset="rixvox",
                    source_split="train",
                    dataset_row_id="row-0",
                    speaker_id="speaker-0",
                    speaker_name="speaker-0",
                    speaker_from_id=True,
                    source_audio_path="speaker-0/clip-0.wav",
                    source_audio_locator=None,
                    text_raw="Hej från Sverige.",
                    language="sv-SE",
                    speaker_total_hours=1.0,
                    has_label_files=False,
                    speaker_audio_meta_ok=True,
                    source_sample_rate_hz=16_000,
                    duration_seconds=5.0,
                )
            )
        ],
    )
    (slice_root / "required_hub_files.json").write_text("[]", encoding="utf-8")

    summary = localize_portable_slice(
        slice_root=slice_root,
        data_root=tmp_path / "data_root",
    )

    localized_rows = [
        source_record_from_payload(payload)
        for payload in iter_jsonl_objects(localized_selected_source_records_path(slice_root))
    ]
    assert summary.localized_row_count == 1
    assert summary.localized_audio_file_count == 1
    assert localized_slice_summary_path(slice_root).is_file()
    assert len(localized_rows) == 1
    localized_locator = localized_rows[0].source_audio_locator
    assert localized_locator is not None
    assert localized_locator.archive_member is None
    assert localized_locator.path.is_file()
    assert localized_locator.path.read_bytes() == staged_audio_path.read_bytes()


def test_localize_portable_slice_emits_progress(tmp_path: Path, capsys) -> None:
    """Portable slice localization should emit per-archive progress and timing."""
    slice_root = tmp_path / "slice"
    staged_audio_path = tmp_path / "needed.wav"
    write_test_wav(staged_audio_path, sample_rate_hz=16_000, duration_seconds=0.5)

    staged_archive_path = tmp_path / "data_root/raw/kblab_rixvox/data/train/train_0.tar.gz"
    staged_archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(staged_archive_path, "w:gz") as archive:
        audio_bytes = staged_audio_path.read_bytes()
        member = tarfile.TarInfo(name="speaker-0/clip-0.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    write_jsonl(
        slice_root / "selected_source_records.jsonl",
        [
            source_record_to_payload(
                SourceRecord(
                    dataset="rixvox",
                    source_split="train",
                    dataset_row_id="row-0",
                    speaker_id="speaker-0",
                    speaker_name="speaker-0",
                    speaker_from_id=True,
                    source_audio_path="speaker-0/clip-0.wav",
                    source_audio_locator=None,
                    text_raw="Hej från Sverige.",
                    language="sv-SE",
                    speaker_total_hours=1.0,
                    has_label_files=False,
                    speaker_audio_meta_ok=True,
                    source_sample_rate_hz=16_000,
                    duration_seconds=5.0,
                )
            )
        ],
    )
    (slice_root / "required_hub_files.json").write_text("[]", encoding="utf-8")

    localize_portable_slice(
        slice_root=slice_root,
        data_root=tmp_path / "data_root",
    )

    captured = capsys.readouterr()
    assert "[qwen-portable-slice] localize slice start" in captured.out
    assert "[qwen-portable-slice] localize archive start" in captured.out
    assert "required_member_count=1" in captured.out
    assert "[qwen-portable-slice] localize archive done" in captured.out
    assert "[qwen-portable-slice] localize slice done row_count=1 localized_audio_file_count=1" in (
        captured.out
    )
