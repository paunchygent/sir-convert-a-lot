"""Staged public-corpus source loading for the Task 103 Qwen pipeline.

Purpose:
    Resolve the real staged Swedish corpus assets on Hemma into adapter-shaped
    `SourceRecord` rows so Task 103 can run against public corpora without
    relying on repo-fixture smoke inputs or deprecated dataset scripts.

Relationships:
    - Used by `run_task103_qwen_swedish_preprocessing.py` when the runner is
      invoked in staged-public-corpus mode.
    - Consumes the staged raw asset layout produced by
      `task106_qwen_corpus_acquisition_runtime.py`.
    - Delegates dataset parsing to the committed `fleurs`, `waxholm`, and
      `rixvox` source adapters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Final, Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_source_fleurs import (
    FLEURS_ALLOWED_SPLITS,
    fleurs_sv_source_records,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import SourceRecord
from scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox import (
    RIXVOX_ALLOWED_SPLITS,
    attach_audio_locators_to_source_records,
    build_rixvox_audio_locator_index,
    rixvox_source_records_from_parquet_with_audio_locators,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_selection import (
    Task103SourceSelectionHeartbeat,
    Task103SourceSelectionHeartbeatCallback,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_waxholm import (
    waxholm_labeled_source_records,
)

RAW_CORPUS_SUBDIR: Final[str] = "raw"
FLEURS_STAGED_SUBDIR: Final[str] = "google_fleurs"
WAXHOLM_STAGED_SUBDIR: Final[str] = "kth_waxholm"
RIXVOX_STAGED_SUBDIR: Final[str] = "kblab_rixvox"


def _source_selection_batch_callback(
    *,
    split: str,
    target_row_cap: int,
    heartbeat_callback: Task103SourceSelectionHeartbeatCallback,
) -> Callable[[int, int], None]:
    """Build one bounded parquet-selection heartbeat callback."""

    def _callback(batch_index: int, selected_row_count: int) -> None:
        heartbeat_callback(
            Task103SourceSelectionHeartbeat(
                phase="resolving-source-records",
                current_split=split,
                selected_row_count=selected_row_count,
                target_row_cap=target_row_cap,
                current_parquet_batch_index=batch_index,
                resolved_audio_locator_count=None,
                required_audio_locator_count=None,
            )
        )

    return _callback


def _source_selection_locator_callback(
    *,
    split: str,
    selected_row_count: int,
    target_row_cap: int,
    heartbeat_callback: Task103SourceSelectionHeartbeatCallback,
) -> Callable[[int, int], None]:
    """Build one bounded audio-locator heartbeat callback."""

    def _callback(resolved_count: int, required_count: int) -> None:
        heartbeat_callback(
            Task103SourceSelectionHeartbeat(
                phase="resolving-audio-locators",
                current_split=split,
                selected_row_count=selected_row_count,
                target_row_cap=target_row_cap,
                current_parquet_batch_index=None,
                resolved_audio_locator_count=resolved_count,
                required_audio_locator_count=required_count,
            )
        )

    return _callback


def staged_public_corpus_source_records(
    data_root: Path,
    *,
    fleurs_splits: Sequence[str] = FLEURS_ALLOWED_SPLITS,
    fleurs_max_rows_per_split: int | None = None,
    rixvox_splits: Sequence[str] = ("dev", "test"),
    rixvox_max_rows_per_split: int | None = None,
    include_waxholm: bool = True,
    source_selection_heartbeat_callback: Task103SourceSelectionHeartbeatCallback | None = None,
) -> list[SourceRecord]:
    """Load staged public-corpus source records from Hemma's bulk-data root."""
    raw_root = data_root / RAW_CORPUS_SUBDIR
    if not raw_root.is_dir():
        raise FileNotFoundError(f"Missing staged raw corpus root: {raw_root}")

    source_records: list[SourceRecord] = []

    requested_fleurs_splits = tuple(fleurs_splits)
    invalid_fleurs_splits = sorted(set(requested_fleurs_splits) - set(FLEURS_ALLOWED_SPLITS))
    if invalid_fleurs_splits:
        raise ValueError(f"Unsupported staged FLEURS splits: {invalid_fleurs_splits}")
    fleurs_root = raw_root / FLEURS_STAGED_SUBDIR
    fleurs_source_records = fleurs_sv_source_records(fleurs_root, splits=requested_fleurs_splits)
    source_records.extend(
        _limit_rows_per_split(
            fleurs_source_records,
            max_rows_per_split=fleurs_max_rows_per_split,
        )
    )

    if include_waxholm:
        waxholm_root = raw_root / WAXHOLM_STAGED_SUBDIR
        source_records.extend(waxholm_labeled_source_records(waxholm_root))

    requested_rixvox_splits = tuple(rixvox_splits)
    invalid_rixvox_splits = sorted(set(requested_rixvox_splits) - set(RIXVOX_ALLOWED_SPLITS))
    if invalid_rixvox_splits:
        raise ValueError(f"Unsupported staged RixVox splits: {invalid_rixvox_splits}")
    rixvox_root = raw_root / RIXVOX_STAGED_SUBDIR
    for split in requested_rixvox_splits:
        parquet_path = rixvox_root / f"data/{split}_metadata.parquet"
        if not parquet_path.is_file():
            raise FileNotFoundError(f"Missing staged RixVox parquet file: {parquet_path}")
        archive_root = rixvox_root / "data" / split
        if archive_root.is_dir():
            archive_paths = sorted(archive_root.glob(f"{split}_*.tar.gz"))
        else:
            archive_paths = []
        if archive_paths and split == "train" and rixvox_max_rows_per_split is not None:
            selected_source_records = rixvox_source_records_from_parquet_with_audio_locators(
                parquet_path,
                split=split,
                audio_locators_by_source_path=None,
                max_rows=rixvox_max_rows_per_split,
                batch_progress_callback=(
                    None
                    if (
                        source_selection_heartbeat_callback is None
                        or rixvox_max_rows_per_split is None
                    )
                    else _source_selection_batch_callback(
                        split=split,
                        target_row_cap=rixvox_max_rows_per_split,
                        heartbeat_callback=source_selection_heartbeat_callback,
                    )
                ),
            )
            required_source_paths = {row.source_audio_path for row in selected_source_records}
            audio_locators_by_source_path = build_rixvox_audio_locator_index(
                archive_paths,
                required_source_paths=required_source_paths,
                progress_callback=(
                    None
                    if (
                        source_selection_heartbeat_callback is None
                        or rixvox_max_rows_per_split is None
                    )
                    else _source_selection_locator_callback(
                        split=split,
                        selected_row_count=len(selected_source_records),
                        target_row_cap=rixvox_max_rows_per_split,
                        heartbeat_callback=source_selection_heartbeat_callback,
                    )
                ),
            )
            source_records.extend(
                attach_audio_locators_to_source_records(
                    selected_source_records,
                    audio_locators_by_source_path=audio_locators_by_source_path,
                    include_metadata_only_rows=False,
                )
            )
            continue
        if archive_paths:
            source_records.extend(
                _limit_rows_per_split(
                    rixvox_source_records_from_parquet_with_audio_locators(
                        parquet_path,
                        split=split,
                        audio_locators_by_source_path=build_rixvox_audio_locator_index(
                            archive_paths
                        ),
                        include_metadata_only_rows=split != "train",
                    ),
                    max_rows_per_split=rixvox_max_rows_per_split,
                )
            )
            continue
        source_records.extend(
            _limit_rows_per_split(
                rixvox_source_records_from_parquet_with_audio_locators(
                    parquet_path,
                    split=split,
                    audio_locators_by_source_path=None,
                ),
                max_rows_per_split=rixvox_max_rows_per_split,
            )
        )

    return sorted(
        source_records,
        key=lambda row: (row.dataset, row.source_split, row.speaker_id, row.dataset_row_id),
    )


def _limit_rows_per_split(
    source_records: Sequence[SourceRecord],
    *,
    max_rows_per_split: int | None,
) -> list[SourceRecord]:
    """Apply one deterministic per-split cap when the caller requests it."""
    if max_rows_per_split is None:
        return list(source_records)
    if max_rows_per_split <= 0:
        raise ValueError("max_rows_per_split must be positive when provided.")

    rows_by_split: dict[str, list[SourceRecord]] = {}
    for source_record in source_records:
        rows_by_split.setdefault(source_record.source_split, []).append(source_record)

    limited_rows: list[SourceRecord] = []
    for split_name in sorted(rows_by_split):
        limited_rows.extend(rows_by_split[split_name][:max_rows_per_split])
    return limited_rows
