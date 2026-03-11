"""Immutable shard registry for Task 121 Qwen allocation.

Purpose:
    Materialize the remaining source-selection universe into immutable shard
    manifests that become the only valid allocation units for future Qwen
    preprocessing work.

Relationships:
    - Consumes completed-row and selected-source exclusion helpers from
      `task121_qwen_slice_allocation.py`.
    - Reuses source-record contracts from `task103_qwen_source_models.py`.
    - Feeds shard ids and selected-source manifests into
      `task121_qwen_assignment_ledger.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_jsonl_objects,
    write_json,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    SourceRecord,
    source_record_from_payload,
    source_record_to_payload,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_planning import (
    load_train_source_records_from_run_root,
    sort_train_source_records,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_slice_allocation import (
    collect_excluded_row_keys,
    filter_source_records_against_excluded_keys,
    row_key_for_source_record,
)


@dataclass(frozen=True)
class QwenShardSummary:
    """Stable summary for one immutable shard."""

    shard_id: str
    universe_id: str
    shard_ordinal: int
    selected_row_count: int
    first_row_key: tuple[str, str, str] | None
    last_row_key: tuple[str, str, str] | None


@dataclass(frozen=True)
class QwenShardRegistrySummary:
    """Stable summary for one shard registry."""

    registry_root: str
    source_run_root: str
    universe_id: str
    source_selection_row_count: int
    remaining_row_count: int
    target_rows_per_shard: int
    shard_count: int
    excluded_completed_row_count: int
    excluded_reserved_row_count: int
    total_excluded_key_count: int


@dataclass(frozen=True)
class QwenShardRegistryIndex:
    """Typed registry index for one immutable shard universe."""

    universe_id: str
    source_run_root: str
    target_rows_per_shard: int
    shard_ids: list[str]


def shard_registry_summary_path(registry_root: Path) -> Path:
    """Return the registry summary path."""
    return registry_root / "registry_summary.json"


def shard_registry_index_path(registry_root: Path) -> Path:
    """Return the registry index path."""
    return registry_root / "shard_index.json"


def shard_assignment_ledger_path(registry_root: Path) -> Path:
    """Return the assignment-ledger path."""
    return registry_root / "assignment_ledger.jsonl"


def shard_dir(registry_root: Path, shard_id: str) -> Path:
    """Return the directory for one immutable shard."""
    return registry_root / "shards" / shard_id


def shard_selected_source_records_path(registry_root: Path, shard_id: str) -> Path:
    """Return the selected-source path for one shard."""
    return shard_dir(registry_root, shard_id) / "selected_source_records.jsonl"


def shard_summary_path(registry_root: Path, shard_id: str) -> Path:
    """Return the summary path for one shard."""
    return shard_dir(registry_root, shard_id) / "shard_summary.json"


def build_shard_registry(
    *,
    source_run_root: Path,
    registry_root: Path,
    target_rows_per_shard: int,
    exclude_completed_run_roots: Sequence[Path],
    exclude_selected_source_records_paths: Sequence[Path],
) -> QwenShardRegistrySummary:
    """Build one immutable shard registry from the remaining source-selection universe."""
    if target_rows_per_shard <= 0:
        raise ValueError("target_rows_per_shard must be positive.")
    if registry_root.exists():
        raise ValueError("Shard registry root must be a new path.")

    train_source_records = load_train_source_records_from_run_root(source_run_root)
    exclusion_summary = collect_excluded_row_keys(
        exclude_completed_run_roots=exclude_completed_run_roots,
        exclude_selected_source_records_paths=exclude_selected_source_records_paths,
    )
    remaining_source_records = sort_train_source_records(
        filter_source_records_against_excluded_keys(
            train_source_records,
            excluded_keys=set(exclusion_summary.excluded_keys),
        )
    )
    universe_id = _universe_id_for_source_records(
        source_run_root=source_run_root,
        source_records=remaining_source_records,
    )

    shard_ids: list[str] = []
    for shard_ordinal, start_index in enumerate(
        range(0, len(remaining_source_records), target_rows_per_shard),
        start=1,
    ):
        shard_source_records = remaining_source_records[
            start_index : start_index + target_rows_per_shard
        ]
        shard_id = _shard_id_for_source_records(
            universe_id=universe_id,
            shard_ordinal=shard_ordinal,
            source_records=shard_source_records,
        )
        shard_ids.append(shard_id)
        write_jsonl(
            shard_selected_source_records_path(registry_root, shard_id),
            [source_record_to_payload(source_record) for source_record in shard_source_records],
        )
        write_json(
            shard_summary_path(registry_root, shard_id),
            QwenShardSummary(
                shard_id=shard_id,
                universe_id=universe_id,
                shard_ordinal=shard_ordinal,
                selected_row_count=len(shard_source_records),
                first_row_key=(
                    None
                    if not shard_source_records
                    else row_key_for_source_record(shard_source_records[0])
                ),
                last_row_key=(
                    None
                    if not shard_source_records
                    else row_key_for_source_record(shard_source_records[-1])
                ),
            ),
        )

    write_json(
        shard_registry_index_path(registry_root),
        QwenShardRegistryIndex(
            universe_id=universe_id,
            source_run_root=source_run_root.as_posix(),
            target_rows_per_shard=target_rows_per_shard,
            shard_ids=shard_ids,
        ),
    )
    write_jsonl(shard_assignment_ledger_path(registry_root), [])
    summary = QwenShardRegistrySummary(
        registry_root=registry_root.as_posix(),
        source_run_root=source_run_root.as_posix(),
        universe_id=universe_id,
        source_selection_row_count=len(train_source_records),
        remaining_row_count=len(remaining_source_records),
        target_rows_per_shard=target_rows_per_shard,
        shard_count=len(shard_ids),
        excluded_completed_row_count=exclusion_summary.completed_run_root_count,
        excluded_reserved_row_count=exclusion_summary.reserved_selected_source_count,
        total_excluded_key_count=exclusion_summary.total_excluded_key_count,
    )
    write_json(shard_registry_summary_path(registry_root), summary)
    return summary


def load_shard_registry_index(registry_root: Path) -> QwenShardRegistryIndex:
    """Load the typed shard-registry index."""
    from json import loads

    payload = loads(shard_registry_index_path(registry_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Malformed shard-registry index.")
    shard_ids = payload.get("shard_ids")
    if not isinstance(shard_ids, list) or not all(isinstance(item, str) for item in shard_ids):
        raise ValueError("Malformed shard-registry shard ids.")
    return QwenShardRegistryIndex(
        universe_id=_required_string(payload, "universe_id"),
        source_run_root=_required_string(payload, "source_run_root"),
        target_rows_per_shard=_required_int(payload, "target_rows_per_shard"),
        shard_ids=shard_ids,
    )


def load_shard_source_records(*, registry_root: Path, shard_id: str) -> list[SourceRecord]:
    """Load the selected-source manifest for one shard id."""
    return [
        source_record_from_payload(payload)
        for payload in iter_jsonl_objects(
            shard_selected_source_records_path(registry_root, shard_id)
        )
    ]


def _required_string(payload: dict[str, object], key: str) -> str:
    """Return one required string field from one JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in shard payload.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from one JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Malformed `{key}` in shard payload.")
    return value


def _universe_id_for_source_records(
    *,
    source_run_root: Path,
    source_records: Sequence[SourceRecord],
) -> str:
    """Render one deterministic remaining-universe id from ordered row keys."""
    digest = sha256()
    digest.update(source_run_root.as_posix().encode("utf-8"))
    for source_record in source_records:
        digest.update("|".join(row_key_for_source_record(source_record)).encode("utf-8"))
        digest.update(b"\n")
    return f"qwen-universe-{digest.hexdigest()[:16]}"


def _shard_id_for_source_records(
    *,
    universe_id: str,
    shard_ordinal: int,
    source_records: Sequence[SourceRecord],
) -> str:
    """Render one deterministic shard id from one ordered shard row set."""
    digest = sha256()
    for source_record in source_records:
        digest.update("|".join(row_key_for_source_record(source_record)).encode("utf-8"))
        digest.update(b"\n")
    return f"{universe_id}-shard-{shard_ordinal:04d}-{digest.hexdigest()[:8]}"
