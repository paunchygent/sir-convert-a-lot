"""Tests for the Task 121 immutable shard registry and allocation ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task103_qwen_row_keys import write_row_key_records
from scripts.sir_convert_a_lot.devops.task103_qwen_source_selection import (
    Task103SourceSelectionSummary,
    write_selected_source_records,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_assignment_ledger import (
    complete_processing_unit,
    issue_processing_unit_from_shards,
    processing_unit_summary_path,
    release_processing_unit,
    replay_shard_assignment_ledger,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_shard_registry import (
    build_shard_registry,
    shard_registry_index_path,
)
from tests.sir_convert_a_lot.test_task121_qwen_colab_slice_bundle import (
    _build_rixvox_source_record,
    _write_completed_row_keys_index,
)


def test_build_shard_registry_cuts_remaining_universe_into_target_sized_shards(
    tmp_path: Path,
) -> None:
    """Shard-registry build should cut the remaining universe into immutable chunks."""
    source_run_root = tmp_path / "selection-run"
    archive_path = tmp_path / "train_0.tar.gz"
    source_records = [
        _build_rixvox_source_record(
            dataset_row_id=f"row-{row_index}",
            speaker_id=f"speaker-{row_index % 2}",
            source_audio_path=f"speaker-{row_index}/clip-{row_index}.wav",
            archive_path=archive_path,
        )
        for row_index in range(7)
    ]
    write_selected_source_records(
        source_run_root,
        source_records=source_records,
        summary=Task103SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=7,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=7,
        ),
    )
    processed_run_root = tmp_path / "processed-run"
    _write_completed_row_keys_index(processed_run_root, ["row-0"])

    registry_root = tmp_path / "registry"
    summary = build_shard_registry(
        source_run_root=source_run_root,
        registry_root=registry_root,
        target_rows_per_shard=3,
        exclude_completed_run_roots=[processed_run_root],
        exclude_selected_source_records_paths=[],
        exclude_row_keys_paths=[],
    )

    index_payload = json.loads(shard_registry_index_path(registry_root).read_text(encoding="utf-8"))
    assert summary.remaining_row_count == 6
    assert summary.shard_count == 2
    assert summary.excluded_explicit_row_count == 0
    assert len(index_payload["shard_ids"]) == 2


def test_issue_processing_unit_from_shards_rejects_already_assigned_shards(
    tmp_path: Path,
) -> None:
    """Shard issuance should reserve shard ids and reject a second overlapping assignment."""
    source_run_root = tmp_path / "selection-run"
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
        source_run_root,
        source_records=source_records,
        summary=Task103SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=6,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=6,
        ),
    )

    registry_root = tmp_path / "registry"
    build_shard_registry(
        source_run_root=source_run_root,
        registry_root=registry_root,
        target_rows_per_shard=3,
        exclude_completed_run_roots=[],
        exclude_selected_source_records_paths=[],
        exclude_row_keys_paths=[],
    )
    index_payload = json.loads(shard_registry_index_path(registry_root).read_text(encoding="utf-8"))
    first_shard_id = index_payload["shard_ids"][0]

    first_unit_root = tmp_path / "processing-unit-a"
    summary = issue_processing_unit_from_shards(
        registry_root=registry_root,
        processing_unit_root=first_unit_root,
        processing_unit_id="unit-a",
        executor="colab-a",
        shard_ids=[first_shard_id],
    )

    assert summary.selected_row_count == 3
    assert processing_unit_summary_path(first_unit_root).is_file()

    with pytest.raises(ValueError):
        issue_processing_unit_from_shards(
            registry_root=registry_root,
            processing_unit_root=tmp_path / "processing-unit-b",
            processing_unit_id="unit-b",
            executor="colab-b",
            shard_ids=[first_shard_id],
        )


def test_release_and_complete_processing_unit_update_shard_state(tmp_path: Path) -> None:
    """Shard ledger replay should reflect release and completion transitions."""
    source_run_root = tmp_path / "selection-run"
    archive_path = tmp_path / "train_0.tar.gz"
    source_records = [
        _build_rixvox_source_record(
            dataset_row_id=f"row-{row_index}",
            speaker_id=f"speaker-{row_index % 2}",
            source_audio_path=f"speaker-{row_index}/clip-{row_index}.wav",
            archive_path=archive_path,
        )
        for row_index in range(3)
    ]
    write_selected_source_records(
        source_run_root,
        source_records=source_records,
        summary=Task103SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=3,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=3,
        ),
    )

    registry_root = tmp_path / "registry"
    build_shard_registry(
        source_run_root=source_run_root,
        registry_root=registry_root,
        target_rows_per_shard=3,
        exclude_completed_run_roots=[],
        exclude_selected_source_records_paths=[],
        exclude_row_keys_paths=[],
    )
    shard_id = json.loads(shard_registry_index_path(registry_root).read_text(encoding="utf-8"))[
        "shard_ids"
    ][0]

    first_unit_root = tmp_path / "processing-unit-a"
    issue_processing_unit_from_shards(
        registry_root=registry_root,
        processing_unit_root=first_unit_root,
        processing_unit_id="unit-a",
        executor="colab-a",
        shard_ids=[shard_id],
    )
    release_processing_unit(
        registry_root=registry_root,
        processing_unit_root=first_unit_root,
        executor="colab-a",
    )
    released_state = replay_shard_assignment_ledger(registry_root)[shard_id]
    assert released_state.status == "available"

    second_unit_root = tmp_path / "processing-unit-b"
    issue_processing_unit_from_shards(
        registry_root=registry_root,
        processing_unit_root=second_unit_root,
        processing_unit_id="unit-b",
        executor="colab-b",
        shard_ids=[shard_id],
    )
    complete_processing_unit(
        registry_root=registry_root,
        processing_unit_root=second_unit_root,
        executor="colab-b",
    )
    completed_state = replay_shard_assignment_ledger(registry_root)[shard_id]
    assert completed_state.status == "completed"


def test_build_shard_registry_excludes_explicit_conflict_row_keys(tmp_path: Path) -> None:
    """Shard-registry build should exclude explicit row-key manifests such as conflicts."""
    source_run_root = tmp_path / "selection-run"
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
        source_run_root,
        source_records=source_records,
        summary=Task103SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=6,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=6,
        ),
    )
    conflict_row_keys_path = tmp_path / "conflicts.jsonl"
    write_row_key_records(
        conflict_row_keys_path,
        [
            ("rixvox", "train", "row-1"),
            ("rixvox", "train", "row-4"),
        ],
    )

    registry_root = tmp_path / "registry"
    summary = build_shard_registry(
        source_run_root=source_run_root,
        registry_root=registry_root,
        target_rows_per_shard=10,
        exclude_completed_run_roots=[],
        exclude_selected_source_records_paths=[],
        exclude_row_keys_paths=[conflict_row_keys_path],
    )

    index_payload = json.loads(shard_registry_index_path(registry_root).read_text(encoding="utf-8"))
    shard_id = index_payload["shard_ids"][0]
    processing_summary = issue_processing_unit_from_shards(
        registry_root=registry_root,
        processing_unit_root=tmp_path / "processing-unit",
        processing_unit_id="unit-a",
        executor="colab-a",
        shard_ids=[shard_id],
    )

    assert summary.remaining_row_count == 4
    assert summary.excluded_explicit_row_count == 2
    assert processing_summary.selected_row_count == 4
