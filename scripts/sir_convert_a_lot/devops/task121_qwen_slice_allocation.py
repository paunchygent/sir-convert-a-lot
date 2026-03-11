"""Row-key allocation helpers for Task 121 portable Qwen slices.

Purpose:
    Keep portable-slice issuance and salvage flows deterministic by loading one
    canonical row-key identity for completed Task 103 run roots and selected
    source-record manifests, then filtering new or in-flight slice manifests
    against those keys.

Relationships:
    - Used by `task121_qwen_colab_slice_bundle.py` for guarded future slice
      allocation and live dedupe of in-flight Colab manifests.
    - Reuses Task 103 completed-row loading from
      `task103_qwen_preprocessing_storage.py`.
    - Reuses `SourceRecord` serialization contracts from
      `task103_qwen_source_models.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    load_completed_row_keys,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_row_keys import (
    RowKey,
    load_row_key_records,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    SourceRecord,
    source_record_from_payload,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_selection import (
    load_selected_source_records,
)


@dataclass(frozen=True)
class SliceExclusionSummary:
    """Summarize how many row keys came from each exclusion source."""

    completed_run_root_count: int
    reserved_selected_source_count: int
    explicit_row_key_count: int
    total_excluded_key_count: int
    excluded_keys: frozenset[RowKey]


def row_key_for_source_record(source_record: SourceRecord) -> RowKey:
    """Return the canonical row key for one source record."""
    return (
        source_record.dataset,
        source_record.source_split,
        source_record.dataset_row_id,
    )


def load_source_records_from_jsonl_path(source_records_path: Path) -> list[SourceRecord]:
    """Load serialized source records from one arbitrary JSONL artifact path."""
    source_records: list[SourceRecord] = []
    for payload in _iter_jsonl_objects(source_records_path):
        if not isinstance(payload, dict):
            raise ValueError(
                f"Selected-source payload rows must be JSON objects: {source_records_path}"
            )
        source_records.append(source_record_from_payload(payload))
    return source_records


def load_completed_row_keys_for_run_root(run_root: Path) -> set[RowKey]:
    """Load completed Task 103 row keys from one run root."""
    completed_row_keys, _ = load_completed_row_keys(run_root)
    return completed_row_keys


def collect_excluded_row_keys(
    *,
    exclude_completed_run_roots: Sequence[Path],
    exclude_selected_source_records_paths: Sequence[Path],
    exclude_row_keys_paths: Sequence[Path],
) -> SliceExclusionSummary:
    """Collect one deduplicated exclusion set from run roots and selected manifests."""
    excluded_keys: set[RowKey] = set()
    completed_run_root_count = 0
    reserved_selected_source_count = 0
    explicit_row_key_count = 0

    for run_root in exclude_completed_run_roots:
        completed_keys = load_completed_row_keys_for_run_root(run_root)
        excluded_keys.update(completed_keys)
        completed_run_root_count += len(completed_keys)

    for source_records_path in exclude_selected_source_records_paths:
        reserved_keys = {
            row_key_for_source_record(source_record)
            for source_record in load_source_records_from_jsonl_path(source_records_path)
        }
        excluded_keys.update(reserved_keys)
        reserved_selected_source_count += len(reserved_keys)

    for row_keys_path in exclude_row_keys_paths:
        explicit_row_keys = load_row_key_records(row_keys_path)
        excluded_keys.update(explicit_row_keys)
        explicit_row_key_count += len(explicit_row_keys)

    return SliceExclusionSummary(
        completed_run_root_count=completed_run_root_count,
        reserved_selected_source_count=reserved_selected_source_count,
        explicit_row_key_count=explicit_row_key_count,
        total_excluded_key_count=len(excluded_keys),
        excluded_keys=frozenset(excluded_keys),
    )


def filter_source_records_against_excluded_keys(
    source_records: Sequence[SourceRecord],
    *,
    excluded_keys: set[RowKey],
) -> list[SourceRecord]:
    """Return source records whose row keys are not present in the exclusion set."""
    return [
        source_record
        for source_record in source_records
        if row_key_for_source_record(source_record) not in excluded_keys
    ]


def load_selected_source_records_from_run_root(run_root: Path) -> list[SourceRecord]:
    """Load selected source records from one Task 103 source-selection run root."""
    selected_source_records = load_selected_source_records(run_root)
    if selected_source_records is None:
        raise FileNotFoundError(
            "The source run root does not contain selected_source_records.jsonl."
        )
    return selected_source_records


def _iter_jsonl_objects(path: Path) -> Iterable[object]:
    """Iterate decoded JSON objects from one JSONL file."""
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)
