"""Sharding and work-allocation helpers for the Qwen preprocessing pipeline.

Purpose:
    Provide stable logic for row-key identity, source-selection persistence,
    immutable shard registries, append-only assignment ledgers, and
    portable-slice planning.

Relationships:
    - Consumes base families from `ml.qwen.common.models`.
    - Persists allocation artifacts through `ml.qwen.preprocessing.storage`.
    - Used by CLI allocation scripts and the preprocessing pipeline preflight.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Literal, Mapping, Sequence

from scripts.sir_convert_a_lot.ml.qwen.common.models import SourceRecord
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    iter_jsonl_objects,
    load_completed_row_keys,
    write_jsonl,
)

RowKey = tuple[str, str, str]
RIXVOX_STAGING_PREFIX = Path("kblab_rixvox")

# --- Source Selection Models ---

SourceSelectionPhase = Literal[
    "resolving-source-records",
    "resolving-audio-locators",
    "writing-selection-artifacts",
]


@dataclass(frozen=True)
class SourceSelectionHeartbeat:
    """Heartbeat payload for bounded staged-public source selection."""

    phase: SourceSelectionPhase
    current_split: str | None
    selected_row_count: int
    target_row_cap: int | None
    current_parquet_batch_index: int | None
    resolved_audio_locator_count: int | None
    required_audio_locator_count: int | None


@dataclass(frozen=True)
class SourceSelectionSummary:
    """Stable summary for one persisted selected-source artifact set."""

    source_mode: str
    total_selected_rows: int
    datasets: list[str]
    fleurs_splits: list[str]
    rixvox_splits: list[str]
    rixvox_max_rows_per_split: int | None


SourceSelectionHeartbeatCallback = Callable[[SourceSelectionHeartbeat], None]

# --- Shard and Allocation Models ---


@dataclass(frozen=True)
class ShardSummary:
    """Stable summary for one immutable shard."""

    shard_id: str
    universe_id: str
    shard_ordinal: int
    selected_row_count: int
    first_row_key: RowKey | None
    last_row_key: RowKey | None


@dataclass(frozen=True)
class ShardRegistrySummary:
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
    excluded_explicit_row_count: int
    total_excluded_key_count: int


@dataclass(frozen=True)
class ShardRegistryIndex:
    """Typed registry index for one immutable shard universe."""

    universe_id: str
    source_run_root: str
    target_rows_per_shard: int
    shard_ids: list[str]


AssignmentEventType = Literal["assigned", "released", "completed"]
ShardStatus = Literal["available", "assigned", "completed"]


@dataclass(frozen=True)
class ShardAssignmentEvent:
    """One append-only shard-assignment ledger event."""

    event_type: AssignmentEventType
    event_timestamp: str
    processing_unit_id: str
    executor: str
    shard_ids: list[str]


@dataclass(frozen=True)
class ShardState:
    """Current replayed availability state for one shard."""

    shard_id: str
    status: ShardStatus
    processing_unit_id: str | None


@dataclass(frozen=True)
class ProcessingUnitSummary:
    """Stable summary for one shard-backed processing unit."""

    processing_unit_id: str
    registry_root: str
    processing_unit_root: str
    executor: str
    shard_ids: list[str]
    selected_row_count: int
    required_files_count: int


# --- Portable Slice Models ---


@dataclass(frozen=True)
class PortableSliceRequiredFile:
    """Describe one dataset file that must be staged before row-processing."""

    repo_id: str
    repo_type: str
    filename: str
    local_relative_path: str
    revision: str | None


@dataclass(frozen=True)
class PortableSliceSummary:
    """Stable summary for one portable preprocessing slice."""

    source_run_root: str
    slice_count: int
    slice_index: int
    selected_row_count: int
    datasets: list[str]
    source_splits: list[str]
    required_files_count: int


@dataclass(frozen=True)
class UniqueAllocationSummary:
    """Stable summary for one guarded unique-allocation planning pass."""

    source_run_root: str
    output_root: str
    slice_count: int
    slice_index: int
    remaining_train_row_count: int
    selected_row_count: int
    excluded_completed_row_count: int
    excluded_reserved_row_count: int
    excluded_explicit_row_count: int
    total_excluded_key_count: int


@dataclass(frozen=True)
class DedupedSelectedSourceSummary:
    """Stable summary for one deduplicated selected-source manifest."""

    input_selected_source_records_path: str
    output_selected_source_records_path: str
    input_row_count: int
    output_row_count: int
    excluded_completed_row_count: int
    excluded_reserved_row_count: int
    excluded_explicit_row_count: int
    total_excluded_key_count: int


@dataclass(frozen=True)
class SliceExclusionSummary:
    """Summarize how many row keys came from each exclusion source."""

    completed_run_root_count: int
    reserved_selected_source_count: int
    explicit_row_key_count: int
    total_excluded_key_count: int
    excluded_keys: frozenset[RowKey]


# --- Path Helpers ---


def source_selection_dir(output_root: Path) -> Path:
    """Return the canonical source-selection artifact directory."""
    return output_root / "source_selection"


def selected_source_records_path(output_root: Path) -> Path:
    """Return the path for the persisted bounded selected-source JSONL."""
    return source_selection_dir(output_root) / "selected_source_records.jsonl"


def shard_registry_index_path(registry_root: Path) -> Path:
    """Return the registry index path."""
    return registry_root / "shard_index.json"


def shard_assignment_ledger_path(registry_root: Path) -> Path:
    """Return the assignment-ledger path."""
    return registry_root / "assignment_ledger.jsonl"


def shard_dir(registry_root: Path, shard_id: str) -> Path:
    """Return the directory for one immutable shard."""
    return registry_root / "shards" / shard_id


def portable_selected_source_records_path(output_root: Path) -> Path:
    """Return the portable selected-source JSONL path."""
    return output_root / "selected_source_records.jsonl"


# --- Row-Key Helpers ---


def row_key_for_source_record(source_record: SourceRecord) -> RowKey:
    """Return the canonical row key for one source record."""
    return (
        source_record.dataset,
        source_record.source_split,
        source_record.dataset_row_id,
    )


def row_key_from_payload(payload: object) -> RowKey:
    """Parse one canonical row key from one JSON payload."""
    if not isinstance(payload, Mapping):
        raise ValueError("Row-key payload rows must be mappings.")
    dataset = payload.get("dataset")
    source_split = payload.get("source_split")
    dataset_row_id = payload.get("dataset_row_id")
    if not isinstance(dataset, str) or not isinstance(source_split, str) or not isinstance(dataset_row_id, str):
        raise ValueError("Malformed row-key fields in payload.")
    return (dataset, source_split, dataset_row_id)


def load_row_key_records(path: Path) -> set[RowKey]:
    """Load one deduplicated canonical row-key set from a JSONL artifact."""
    return {row_key_from_payload(payload) for payload in iter_jsonl_objects(path)}


def write_row_key_records(path: Path, row_keys: Sequence[RowKey]) -> None:
    """Write one deterministic JSONL artifact for ordered canonical row keys."""
    rows = [{"dataset": k[0], "source_split": k[1], "dataset_row_id": k[2]} for k in row_keys]
    write_jsonl(path, rows)


# --- Core Logic ---


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
        completed_keys, _ = load_completed_row_keys(run_root)
        excluded_keys.update(completed_keys)
        completed_run_root_count += len(completed_keys)

    for source_records_path in exclude_selected_source_records_paths:
        reserved_keys = {
            row_key_for_source_record(_source_record_from_payload(payload))
            for payload in iter_jsonl_objects(source_records_path)
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


def _source_record_from_payload(payload: dict[str, object]) -> SourceRecord:
    """Internal helper to hydrate one SourceRecord from payload (replaces deprecated models helper)."""
    # This matches the SourceRecord dataclass fields
    from scripts.sir_convert_a_lot.ml.qwen.common.models import audio_locator_from_payload
    return SourceRecord(
        dataset=str(payload["dataset"]),
        source_split=str(payload["source_split"]),
        dataset_row_id=str(payload["dataset_row_id"]),
        speaker_id=str(payload["speaker_id"]),
        speaker_name=str(payload["speaker_name"]),
        speaker_from_id=bool(payload["speaker_from_id"]),
        source_audio_path=str(payload["source_audio_path"]),
        text_raw=str(payload["text_raw"]),
        language=str(payload["language"]),
        speaker_total_hours=float(payload["speaker_total_hours"]) if payload.get("speaker_total_hours") is not None else None,
        has_label_files=bool(payload["has_label_files"]),
        speaker_audio_meta_ok=bool(payload["speaker_audio_meta_ok"]),
        source_audio_locator=audio_locator_from_payload(payload.get("source_audio_locator")),
        reference_audio_locator=audio_locator_from_payload(payload.get("reference_audio_locator")),
        source_sample_rate_hz=int(payload["source_sample_rate_hz"]) if payload.get("source_sample_rate_hz") is not None else None,
        duration_seconds=float(payload["duration_seconds"]) if payload.get("duration_seconds") is not None else None,
        boilerplate_group=payload.get("boilerplate_group"), # type: ignore
        notes=payload.get("notes"), # type: ignore
    )


def _utc_now_rfc3339() -> str:
    """Render the current UTC timestamp in RFC3339 form."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
