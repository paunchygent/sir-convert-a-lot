"""Portable-slice planning and dedupe operations for Task 121.

Purpose:
    Own the deterministic planning rules for portable Qwen preprocessing
    bundles, including bounded slice selection, remaining-universe deduction,
    and selected-source dedupe against completed or already-reserved work.

Relationships:
    - Uses portable artifact contracts from
      `task121_qwen_portable_slice_models.py`.
    - Uses exclusion and source-loading helpers from
      `task121_qwen_slice_allocation.py`.
    - Supplies bundle-shaped artifacts to the canonical Task 121 CLI and shard
      assignment ledger.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    write_json,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    SourceRecord,
    source_record_to_payload,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox import RIXVOX_DATASET_ID
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_models import (
    DedupedSelectedSourceSummary,
    PortableSliceRequiredFile,
    PortableSliceSummary,
    UniqueAllocationSummary,
    deduped_selected_source_summary_path,
    portable_required_files_path,
    portable_selected_source_records_path,
    portable_slice_summary_path,
    unique_allocation_summary_path,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_slice_allocation import (
    collect_excluded_row_keys,
    filter_source_records_against_excluded_keys,
    load_selected_source_records_from_run_root,
    load_source_records_from_jsonl_path,
)


def build_portable_slice_bundle(
    *,
    source_run_root: Path,
    output_root: Path,
    slice_count: int,
    slice_index: int,
    rixvox_revision: str | None,
) -> PortableSliceSummary:
    """Create one deterministic portable slice bundle from a source-selection run root."""
    if slice_count <= 0:
        raise ValueError("slice_count must be positive.")
    if slice_index < 0 or slice_index >= slice_count:
        raise ValueError("slice_index must satisfy 0 <= slice_index < slice_count.")

    train_source_records = load_train_source_records_from_run_root(source_run_root)
    slice_source_records = [
        source_record
        for row_index, source_record in enumerate(train_source_records)
        if row_index % slice_count == slice_index
    ]
    required_files = required_files_for_source_records(
        source_records=slice_source_records,
        rixvox_revision=rixvox_revision,
    )
    return write_portable_bundle_for_source_records(
        output_root=output_root,
        source_records=slice_source_records,
        required_files=required_files,
        slice_summary=PortableSliceSummary(
            source_run_root=source_run_root.as_posix(),
            slice_count=slice_count,
            slice_index=slice_index,
            selected_row_count=len(slice_source_records),
            datasets=sorted({row.dataset for row in slice_source_records}),
            source_splits=sorted({row.source_split for row in slice_source_records}),
            required_files_count=len(required_files),
        ),
    )


def build_remaining_unique_portable_slice_bundle(
    *,
    source_run_root: Path,
    output_root: Path,
    slice_count: int,
    slice_index: int,
    rixvox_revision: str | None,
    exclude_completed_run_roots: Sequence[Path],
    exclude_selected_source_records_paths: Sequence[Path],
) -> UniqueAllocationSummary:
    """Create one deterministic portable slice from the remaining unallocated universe."""
    if not exclude_completed_run_roots and not exclude_selected_source_records_paths:
        raise ValueError("Guarded unique allocation requires at least one exclusion source.")
    if slice_count <= 0:
        raise ValueError("slice_count must be positive.")
    if slice_index < 0 or slice_index >= slice_count:
        raise ValueError("slice_index must satisfy 0 <= slice_index < slice_count.")

    train_source_records = load_train_source_records_from_run_root(source_run_root)
    exclusion_summary = collect_excluded_row_keys(
        exclude_completed_run_roots=exclude_completed_run_roots,
        exclude_selected_source_records_paths=exclude_selected_source_records_paths,
    )
    remaining_train_source_records = sort_train_source_records(
        filter_source_records_against_excluded_keys(
            train_source_records,
            excluded_keys=set(exclusion_summary.excluded_keys),
        )
    )
    slice_source_records = [
        source_record
        for row_index, source_record in enumerate(remaining_train_source_records)
        if row_index % slice_count == slice_index
    ]
    required_files = required_files_for_source_records(
        source_records=slice_source_records,
        rixvox_revision=rixvox_revision,
    )
    portable_slice_summary = write_portable_bundle_for_source_records(
        output_root=output_root,
        source_records=slice_source_records,
        required_files=required_files,
        slice_summary=PortableSliceSummary(
            source_run_root=source_run_root.as_posix(),
            slice_count=slice_count,
            slice_index=slice_index,
            selected_row_count=len(slice_source_records),
            datasets=sorted({row.dataset for row in slice_source_records}),
            source_splits=sorted({row.source_split for row in slice_source_records}),
            required_files_count=len(required_files),
        ),
    )
    summary = UniqueAllocationSummary(
        source_run_root=source_run_root.as_posix(),
        output_root=output_root.as_posix(),
        slice_count=slice_count,
        slice_index=slice_index,
        remaining_train_row_count=len(remaining_train_source_records),
        selected_row_count=portable_slice_summary.selected_row_count,
        excluded_completed_row_count=exclusion_summary.completed_run_root_count,
        excluded_reserved_row_count=exclusion_summary.reserved_selected_source_count,
        total_excluded_key_count=exclusion_summary.total_excluded_key_count,
    )
    write_json(unique_allocation_summary_path(output_root), summary)
    return summary


def dedupe_selected_source_records(
    *,
    selected_source_records_path: Path,
    output_path: Path,
    exclude_completed_run_roots: Sequence[Path],
    exclude_selected_source_records_paths: Sequence[Path],
) -> DedupedSelectedSourceSummary:
    """Write one selected-source manifest with already owned rows removed."""
    input_source_records = load_source_records_from_jsonl_path(selected_source_records_path)
    exclusion_summary = collect_excluded_row_keys(
        exclude_completed_run_roots=exclude_completed_run_roots,
        exclude_selected_source_records_paths=exclude_selected_source_records_paths,
    )
    filtered_source_records = filter_source_records_against_excluded_keys(
        input_source_records,
        excluded_keys=set(exclusion_summary.excluded_keys),
    )
    write_jsonl(
        output_path,
        [source_record_to_payload(source_record) for source_record in filtered_source_records],
    )
    summary = DedupedSelectedSourceSummary(
        input_selected_source_records_path=selected_source_records_path.as_posix(),
        output_selected_source_records_path=output_path.as_posix(),
        input_row_count=len(input_source_records),
        output_row_count=len(filtered_source_records),
        excluded_completed_row_count=exclusion_summary.completed_run_root_count,
        excluded_reserved_row_count=exclusion_summary.reserved_selected_source_count,
        total_excluded_key_count=exclusion_summary.total_excluded_key_count,
    )
    write_json(deduped_selected_source_summary_path(output_path), summary)
    return summary


def load_portable_selected_source_records(slice_root: Path) -> list[SourceRecord]:
    """Load the portable selected-source bundle for a notebook or remote worker."""
    return load_source_records_from_jsonl_path(portable_selected_source_records_path(slice_root))


def load_train_source_records_from_run_root(source_run_root: Path) -> list[SourceRecord]:
    """Load `rixvox/train` rows from one source-selection run root in canonical order."""
    return sort_train_source_records(load_selected_source_records_from_run_root(source_run_root))


def sort_train_source_records(source_records: Sequence[SourceRecord]) -> list[SourceRecord]:
    """Return `rixvox/train` rows in the canonical allocation order."""
    return sorted(
        [
            source_record
            for source_record in source_records
            if source_record.dataset == "rixvox" and source_record.source_split == "train"
        ],
        key=lambda row: (row.dataset, row.source_split, row.speaker_id, row.dataset_row_id),
    )


def required_files_for_source_records(
    *,
    source_records: Sequence[SourceRecord],
    rixvox_revision: str | None,
) -> list[PortableSliceRequiredFile]:
    """Render one deduplicated required-file set for resolved portable source records."""
    required_files_by_filename: dict[str, PortableSliceRequiredFile] = {}
    for source_record in source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None:
            raise ValueError(
                "Portable bundle planning requires resolved source_audio_locator values."
            )
        archive_path_name = source_audio_locator.path.name
        if not archive_path_name.endswith(".tar.gz"):
            raise ValueError(
                "Portable bundle planning currently supports only archive-backed "
                "RixVox rows."
            )
        filename = f"data/{source_record.source_split}/{archive_path_name}"
        required_files_by_filename.setdefault(
            filename,
            PortableSliceRequiredFile(
                repo_id=RIXVOX_DATASET_ID,
                repo_type="dataset",
                filename=filename,
                local_relative_path=f"kblab_rixvox/{filename}",
                revision=rixvox_revision,
            ),
        )
    return [required_files_by_filename[key] for key in sorted(required_files_by_filename)]


def write_portable_bundle_for_source_records(
    *,
    output_root: Path,
    source_records: Sequence[SourceRecord],
    required_files: Sequence[PortableSliceRequiredFile],
    slice_summary: PortableSliceSummary,
) -> PortableSliceSummary:
    """Write one portable bundle-shaped artifact root from resolved source records."""
    portable_source_records = [
        replace(source_record, source_audio_locator=None, reference_audio_locator=None)
        for source_record in source_records
    ]
    write_jsonl(
        portable_selected_source_records_path(output_root),
        [source_record_to_payload(source_record) for source_record in portable_source_records],
    )
    write_json(
        portable_required_files_path(output_root),
        [asdict(required_file) for required_file in required_files],
    )
    write_json(portable_slice_summary_path(output_root), slice_summary)
    return slice_summary
