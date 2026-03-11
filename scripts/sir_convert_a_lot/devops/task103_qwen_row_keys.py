"""Canonical row-key records for Qwen preprocessing ownership and allocation.

Purpose:
    Hold the stable row-key identity and JSONL serialization helpers shared by
    canonical processed-root ownership, conflict exclusion manifests, and Task
    121 future-work allocation.

Relationships:
    - Used by `task103_qwen_canonical_processed_root.py` to emit immutable
      owned-row and conflict-row artifacts from a canonical processed root.
    - Used by `task121_qwen_slice_allocation.py` to load explicit row-key
      exclusion manifests for shard and slice issuance.
    - Keeps row-key serialization independent from spool-row or selected-source
      payload details.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

RowKey = tuple[str, str, str]


@dataclass(frozen=True)
class QwenRowKeyRecord:
    """One serialized row-key record for ownership or exclusion artifacts."""

    dataset: str
    source_split: str
    dataset_row_id: str


def row_key_record(row_key: RowKey) -> QwenRowKeyRecord:
    """Return the typed record for one canonical row key."""
    dataset, source_split, dataset_row_id = row_key
    return QwenRowKeyRecord(
        dataset=dataset,
        source_split=source_split,
        dataset_row_id=dataset_row_id,
    )


def row_key_from_payload(payload: object) -> RowKey:
    """Parse one canonical row key from one JSON payload."""
    if not isinstance(payload, dict):
        raise ValueError("Row-key payload rows must be JSON objects.")
    dataset = payload.get("dataset")
    source_split = payload.get("source_split")
    dataset_row_id = payload.get("dataset_row_id")
    if not isinstance(dataset, str):
        raise ValueError("Malformed `dataset` in row-key payload.")
    if not isinstance(source_split, str):
        raise ValueError("Malformed `source_split` in row-key payload.")
    if not isinstance(dataset_row_id, str):
        raise ValueError("Malformed `dataset_row_id` in row-key payload.")
    return (dataset, source_split, dataset_row_id)


def write_row_key_records(path: Path, row_keys: Sequence[RowKey]) -> None:
    """Write one deterministic JSONL artifact for ordered canonical row keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row_key in row_keys:
            handle.write(json.dumps(row_key_record(row_key).__dict__, ensure_ascii=False))
            handle.write("\n")


def load_row_key_records(path: Path) -> set[RowKey]:
    """Load one deduplicated canonical row-key set from a JSONL artifact."""
    return {row_key_from_payload(payload) for payload in _iter_jsonl_objects(path)}


def _iter_jsonl_objects(path: Path) -> Iterable[object]:
    """Iterate decoded JSON objects from one JSONL artifact."""
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)
