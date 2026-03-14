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

import json
import shutil
import tarfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Collection, Literal, Mapping, Protocol, Sequence

from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    AudioLocator,
    SourceRecord,
    audio_locator_from_payload,
    audio_locator_to_payload,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    iter_jsonl_objects,
    load_completed_row_keys,
    write_json,
    write_jsonl,
)

RowKey = tuple[str, str, str]
RIXVOX_STAGING_PREFIX = Path("kblab_rixvox")


class HasSourceIdentity(Protocol):
    """Structural type for objects that define one canonical source row identity."""

    @property
    def dataset(self) -> str:
        """Return the dataset name."""

    @property
    def source_split(self) -> str:
        """Return the source split name."""

    @property
    def dataset_row_id(self) -> str:
        """Return the dataset-unique row identifier."""


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
class LocalizedSliceSummary:
    """Stable summary for one localized portable preprocessing slice."""

    slice_root: str
    localized_row_count: int
    localized_audio_file_count: int
    localized_manifest_path: str
    localized_audio_root: str


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


def source_selection_summary_path(output_root: Path) -> Path:
    """Return the deterministic source-selection summary JSON path."""
    return source_selection_dir(output_root) / "selection_summary.json"


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


def portable_required_files_path(output_root: Path) -> Path:
    """Return the portable required-files JSON path."""
    return output_root / "required_hub_files.json"


def portable_slice_summary_path(output_root: Path) -> Path:
    """Return the portable slice summary JSON path."""
    return output_root / "slice_summary.json"


def unique_allocation_summary_path(output_root: Path) -> Path:
    """Return the guarded unique-allocation summary JSON path."""
    return output_root / "unique_allocation_summary.json"


def localized_selected_source_records_path(slice_root: Path) -> Path:
    """Return the localized selected-source JSONL path."""
    return slice_root / "localized_selected_source_records.jsonl"


def localized_audio_root(slice_root: Path) -> Path:
    """Return the localized audio root for one portable slice."""
    return slice_root / "localized_audio"


def localized_slice_summary_path(slice_root: Path) -> Path:
    """Return the localized-slice summary JSON path."""
    return slice_root / "localized_slice_summary.json"


def deduped_selected_source_summary_path(output_path: Path) -> Path:
    """Return the summary JSON path for one deduped selected-source output."""
    return output_path.with_name(f"{output_path.stem}_dedupe_summary.json")


# --- Row-Key Helpers ---


def row_key_for_source_identity(record: HasSourceIdentity) -> RowKey:
    """Return the canonical row key for one source row identity."""
    return (
        record.dataset,
        record.source_split,
        record.dataset_row_id,
    )


def row_key_from_payload(payload: object) -> RowKey:
    """Parse one canonical row key from one JSON payload."""
    if not isinstance(payload, Mapping):
        raise ValueError("Row-key payload rows must be mappings.")
    dataset = payload.get("dataset")
    source_split = payload.get("source_split")
    dataset_row_id = payload.get("dataset_row_id")
    if (
        not isinstance(dataset, str)
        or not isinstance(source_split, str)
        or not isinstance(dataset_row_id, str)
    ):
        raise ValueError("Malformed row-key fields in payload.")
    return (dataset, source_split, dataset_row_id)


def load_row_key_records(path: Path) -> set[RowKey]:
    """Load one deduplicated canonical row-key set from a JSONL artifact."""
    return {row_key_from_payload(payload) for payload in iter_jsonl_objects(path)}


def write_row_key_records(path: Path, row_keys: Sequence[RowKey]) -> None:
    """Write one deterministic JSONL artifact for ordered canonical row keys."""
    rows: list[object] = [
        {"dataset": k[0], "source_split": k[1], "dataset_row_id": k[2]} for k in row_keys
    ]
    write_jsonl(path, rows)


def source_record_to_payload(source_record: SourceRecord) -> dict[str, object]:
    """Render one source record into a JSON-serializable payload."""
    return {
        "dataset": source_record.dataset,
        "source_split": source_record.source_split,
        "dataset_row_id": source_record.dataset_row_id,
        "speaker_id": source_record.speaker_id,
        "speaker_name": source_record.speaker_name,
        "speaker_from_id": source_record.speaker_from_id,
        "source_audio_path": source_record.source_audio_path,
        "text_raw": source_record.text_raw,
        "language": source_record.language,
        "speaker_total_hours": source_record.speaker_total_hours,
        "has_label_files": source_record.has_label_files,
        "speaker_audio_meta_ok": source_record.speaker_audio_meta_ok,
        "source_audio_locator": audio_locator_to_payload(source_record.source_audio_locator),
        "reference_audio_locator": audio_locator_to_payload(source_record.reference_audio_locator),
        "source_sample_rate_hz": source_record.source_sample_rate_hz,
        "duration_seconds": source_record.duration_seconds,
        "boilerplate_group": source_record.boilerplate_group,
        "notes": source_record.notes,
    }


def source_record_from_payload(payload: dict[str, object]) -> SourceRecord:
    """Hydrate one source record from a stored payload."""
    speaker_total_hours = payload.get("speaker_total_hours")
    source_sample_rate_hz = payload.get("source_sample_rate_hz")
    duration_seconds = payload.get("duration_seconds")
    boilerplate_group = payload.get("boilerplate_group")
    notes = payload.get("notes")
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
        speaker_total_hours=_to_float(speaker_total_hours),
        has_label_files=bool(payload["has_label_files"]),
        speaker_audio_meta_ok=bool(payload["speaker_audio_meta_ok"]),
        source_audio_locator=audio_locator_from_payload(payload.get("source_audio_locator")),
        reference_audio_locator=audio_locator_from_payload(payload.get("reference_audio_locator")),
        source_sample_rate_hz=_to_int(source_sample_rate_hz),
        duration_seconds=_to_float(duration_seconds),
        boilerplate_group=boilerplate_group if isinstance(boilerplate_group, str) else None,
        notes=notes if isinstance(notes, str) else None,
    )


def has_selected_source_records(output_root: Path) -> bool:
    """Return whether one run root already contains selected-source artifacts."""
    return selected_source_records_path(output_root).is_file()


def write_selected_source_records(
    output_root: Path,
    *,
    source_records: Sequence[SourceRecord],
    summary: SourceSelectionSummary,
) -> None:
    """Persist one bounded selected-source artifact set deterministically."""
    write_jsonl(
        selected_source_records_path(output_root),
        [source_record_to_payload(source_record) for source_record in source_records],
    )
    write_json(source_selection_summary_path(output_root), summary)


def load_selected_source_records(output_root: Path) -> list[SourceRecord] | None:
    """Load one previously persisted bounded selected-source artifact set."""
    path = selected_source_records_path(output_root)
    if not path.exists():
        return None
    return load_source_records_from_jsonl_path(path)


def load_source_records_from_jsonl_path(path: Path) -> list[SourceRecord]:
    """Load source records from one JSONL artifact."""
    return [source_record_from_payload(payload) for payload in iter_jsonl_objects(path)]


def load_selected_source_records_from_run_root(source_run_root: Path) -> list[SourceRecord]:
    """Load selected-source records from one run root."""
    selected_source_records = load_selected_source_records(source_run_root)
    if selected_source_records is None:
        raise FileNotFoundError(selected_source_records_path(source_run_root))
    return selected_source_records


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
            row_key_for_source_identity(source_record_from_payload(payload))
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
        if row_key_for_source_identity(source_record) not in excluded_keys
    ]


def attach_audio_locators_to_source_records(
    source_records: Sequence[SourceRecord],
    *,
    audio_locators_by_source_path: Mapping[str, AudioLocator],
    include_metadata_only_rows: bool,
) -> list[SourceRecord]:
    """Attach one bounded audio-locator mapping to preselected source records."""
    attached_source_records: list[SourceRecord] = []
    for source_record in source_records:
        source_audio_locator = audio_locators_by_source_path.get(source_record.source_audio_path)
        if source_audio_locator is None and not include_metadata_only_rows:
            continue
        attached_source_records.append(
            replace(source_record, source_audio_locator=source_audio_locator)
        )
    return attached_source_records


def build_rixvox_audio_locator_index(
    archive_paths: Sequence[Path],
    *,
    required_source_paths: Collection[str] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, AudioLocator]:
    """Index staged RixVox tar members by dataset-relative filename."""
    audio_locators_by_source_path: dict[str, AudioLocator] = {}
    unresolved_required_paths = (
        None if required_source_paths is None else set(required_source_paths)
    )
    required_count = 0 if unresolved_required_paths is None else len(unresolved_required_paths)
    for archive_path in archive_paths:
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = member.name.strip()
                if not member_name.endswith(".wav"):
                    continue
                if (
                    unresolved_required_paths is not None
                    and member_name not in unresolved_required_paths
                ):
                    continue
                audio_locators_by_source_path.setdefault(
                    member_name,
                    AudioLocator(path=archive_path, archive_member=member_name),
                )
                if unresolved_required_paths is not None:
                    unresolved_required_paths.discard(member_name)
                    if progress_callback is not None:
                        progress_callback(
                            required_count - len(unresolved_required_paths),
                            required_count,
                        )
                    if not unresolved_required_paths:
                        return audio_locators_by_source_path
    if progress_callback is not None and unresolved_required_paths is not None:
        progress_callback(required_count - len(unresolved_required_paths), required_count)
    return audio_locators_by_source_path


def sort_train_source_records(source_records: Sequence[SourceRecord]) -> list[SourceRecord]:
    """Return `rixvox/train` source records in canonical allocation order."""
    return sorted(
        [
            source_record
            for source_record in source_records
            if source_record.dataset == "rixvox" and source_record.source_split == "train"
        ],
        key=lambda row: (row.dataset, row.source_split, row.speaker_id, row.dataset_row_id),
    )


def load_portable_selected_source_records(slice_root: Path) -> list[SourceRecord]:
    """Load the portable selected-source bundle for one worker slice."""
    return load_source_records_from_jsonl_path(portable_selected_source_records_path(slice_root))


def required_files_for_source_records(
    *,
    source_records: Sequence[SourceRecord],
    rixvox_revision: str | None,
) -> list[PortableSliceRequiredFile]:
    """Render the deduplicated required-file set for one portable source selection."""
    required_files_by_filename: dict[str, PortableSliceRequiredFile] = {}
    for source_record in source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None:
            raise ValueError(
                "Portable slice planning requires resolved `source_audio_locator` values."
            )
        archive_name = source_audio_locator.path.name
        if not archive_name.endswith(".tar.gz"):
            raise ValueError("Portable slice planning supports only archive-backed RixVox rows.")
        filename = f"data/{source_record.source_split}/{archive_name}"
        required_files_by_filename.setdefault(
            filename,
            PortableSliceRequiredFile(
                repo_id="KBLab/rixvox",
                repo_type="dataset",
                filename=filename,
                local_relative_path=f"{RIXVOX_STAGING_PREFIX.as_posix()}/{filename}",
                revision=rixvox_revision,
            ),
        )
    return [required_files_by_filename[key] for key in sorted(required_files_by_filename)]


def write_portable_slice_bundle(
    *,
    output_root: Path,
    source_records: Sequence[SourceRecord],
    required_files: Sequence[PortableSliceRequiredFile],
    summary: PortableSliceSummary,
) -> PortableSliceSummary:
    """Write one portable slice bundle from resolved source records."""
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
        [required_file.__dict__ for required_file in required_files],
    )
    write_json(portable_slice_summary_path(output_root), summary)
    return summary


def build_portable_slice_bundle(
    *,
    source_run_root: Path,
    output_root: Path,
    slice_count: int,
    slice_index: int,
    rixvox_revision: str | None,
) -> PortableSliceSummary:
    """Build one deterministic portable slice bundle from a selected-source run root."""
    if slice_count <= 0:
        raise ValueError("slice_count must be positive.")
    if slice_index < 0 or slice_index >= slice_count:
        raise ValueError("slice_index must satisfy 0 <= slice_index < slice_count.")
    train_source_records = sort_train_source_records(
        load_selected_source_records_from_run_root(source_run_root)
    )
    slice_source_records = [
        source_record
        for row_index, source_record in enumerate(train_source_records)
        if row_index % slice_count == slice_index
    ]
    required_files = required_files_for_source_records(
        source_records=slice_source_records,
        rixvox_revision=rixvox_revision,
    )
    return write_portable_slice_bundle(
        output_root=output_root,
        source_records=slice_source_records,
        required_files=required_files,
        summary=PortableSliceSummary(
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
    exclude_row_keys_paths: Sequence[Path],
) -> UniqueAllocationSummary:
    """Build one portable slice bundle from the remaining unallocated train rows."""
    if not exclude_completed_run_roots and not exclude_selected_source_records_paths:
        raise ValueError("Guarded unique allocation requires at least one exclusion source.")
    if slice_count <= 0:
        raise ValueError("slice_count must be positive.")
    if slice_index < 0 or slice_index >= slice_count:
        raise ValueError("slice_index must satisfy 0 <= slice_index < slice_count.")
    train_source_records = sort_train_source_records(
        load_selected_source_records_from_run_root(source_run_root)
    )
    exclusion_summary = collect_excluded_row_keys(
        exclude_completed_run_roots=exclude_completed_run_roots,
        exclude_selected_source_records_paths=exclude_selected_source_records_paths,
        exclude_row_keys_paths=exclude_row_keys_paths,
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
    slice_summary = write_portable_slice_bundle(
        output_root=output_root,
        source_records=slice_source_records,
        required_files=required_files,
        summary=PortableSliceSummary(
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
        selected_row_count=slice_summary.selected_row_count,
        excluded_completed_row_count=exclusion_summary.completed_run_root_count,
        excluded_reserved_row_count=exclusion_summary.reserved_selected_source_count,
        excluded_explicit_row_count=exclusion_summary.explicit_row_key_count,
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
    exclude_row_keys_paths: Sequence[Path],
) -> DedupedSelectedSourceSummary:
    """Write one selected-source artifact with already owned rows removed."""
    input_source_records = load_source_records_from_jsonl_path(selected_source_records_path)
    exclusion_summary = collect_excluded_row_keys(
        exclude_completed_run_roots=exclude_completed_run_roots,
        exclude_selected_source_records_paths=exclude_selected_source_records_paths,
        exclude_row_keys_paths=exclude_row_keys_paths,
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
        excluded_explicit_row_count=exclusion_summary.explicit_row_key_count,
        total_excluded_key_count=exclusion_summary.total_excluded_key_count,
    )
    write_json(deduped_selected_source_summary_path(output_path), summary)
    return summary


def stage_required_files_for_portable_slice(
    *,
    slice_root: Path,
    data_root: Path,
    cache_dir: Path | None = None,
) -> list[Path]:
    """Stage the exact Hub files required by one portable slice into local raw storage."""
    payload = json.loads(portable_required_files_path(slice_root).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Portable slice required-files payload must be a list.")
    _emit_progress(
        "[qwen-portable-slice] staging required archives "
        f"count={len(payload)} slice_root={slice_root.as_posix()}"
    )
    staged_paths: list[Path] = []
    for file_index, row in enumerate(payload, start=1):
        required_file = _required_file_from_payload(row)
        _emit_progress(
            "[qwen-portable-slice] staging archive start "
            f"index={file_index}/{len(payload)} filename={required_file.filename}"
        )
        cached_path = Path(
            hf_hub_download(
                repo_id=required_file.repo_id,
                repo_type=required_file.repo_type,
                filename=required_file.filename,
                revision=required_file.revision,
                cache_dir=None if cache_dir is None else cache_dir.as_posix(),
            )
        )
        target_path = data_root / "raw" / required_file.local_relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cached_path, target_path)
        staged_paths.append(target_path)
        _emit_progress(
            "[qwen-portable-slice] staging archive done "
            f"index={file_index}/{len(payload)} filename={required_file.filename}"
        )
    _emit_progress(
        f"[qwen-portable-slice] staging required archives done count={len(staged_paths)}"
    )
    return staged_paths


def localize_portable_slice(
    *,
    slice_root: Path,
    data_root: Path,
) -> LocalizedSliceSummary:
    """Materialize one portable slice into plain local audio files and a localized manifest."""
    from scripts.sir_convert_a_lot.ml.qwen.preprocessing.public_corpus import (
        resolve_selected_source_records_for_local_data,
    )

    portable_source_records = load_portable_selected_source_records(slice_root)
    _emit_progress(
        "[qwen-portable-slice] localize slice start "
        f"slice_root={slice_root.as_posix()} row_count={len(portable_source_records)}"
    )
    resolved_source_records = resolve_selected_source_records_for_local_data(
        data_root=data_root,
        source_records=portable_source_records,
    )
    localized_root = localized_audio_root(slice_root)
    localized_root.mkdir(parents=True, exist_ok=True)
    localized_source_records: list[SourceRecord] = []
    localized_paths_by_key: dict[tuple[Path, str], Path] = {}
    records_by_archive_path: dict[Path, list[SourceRecord]] = {}
    for source_record in resolved_source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None:
            raise ValueError("Resolved portable source records must include source_audio_locator.")
        if source_audio_locator.archive_member is None:
            localized_source_records.append(source_record)
            continue
        records_by_archive_path.setdefault(source_audio_locator.path, []).append(source_record)
    for archive_path in sorted(records_by_archive_path):
        required_members = {
            source_record.source_audio_locator.archive_member
            for source_record in records_by_archive_path[archive_path]
            if source_record.source_audio_locator is not None
            and source_record.source_audio_locator.archive_member is not None
        }
        _emit_progress(
            "[qwen-portable-slice] localize archive start "
            f"archive_path={archive_path.as_posix()} required_member_count={len(required_members)}"
        )
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile() or member.name.strip() not in required_members:
                    continue
                target_path = localized_root / member.name.strip()
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if not target_path.exists():
                    extracted_file = archive.extractfile(member)
                    if extracted_file is None:
                        raise FileNotFoundError(
                            f"Could not extract `{member.name}` from `{archive_path}`."
                        )
                    with target_path.open("wb") as handle:
                        shutil.copyfileobj(extracted_file, handle)
                localized_paths_by_key[(archive_path, member.name.strip())] = target_path
                if len(localized_paths_by_key) >= len(required_members):
                    continue
        _emit_progress(
            f"[qwen-portable-slice] localize archive done archive_path={archive_path.as_posix()}"
        )
    for source_record in resolved_source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None or source_audio_locator.archive_member is None:
            if source_audio_locator is not None and source_audio_locator.archive_member is None:
                localized_source_records.append(source_record)
            continue
        localized_path = localized_paths_by_key.get(
            (source_audio_locator.path, source_audio_locator.archive_member)
        )
        if localized_path is None:
            raise FileNotFoundError(
                "Localized portable slice is missing extracted file for "
                f"{source_audio_locator.path.as_posix()}::{source_audio_locator.archive_member}"
            )
        localized_source_records.append(
            replace(source_record, source_audio_locator=AudioLocator(path=localized_path))
        )
    write_jsonl(
        localized_selected_source_records_path(slice_root),
        [source_record_to_payload(source_record) for source_record in localized_source_records],
    )
    summary = LocalizedSliceSummary(
        slice_root=slice_root.as_posix(),
        localized_row_count=len(localized_source_records),
        localized_audio_file_count=len(
            {
                row.source_audio_locator.path
                for row in localized_source_records
                if row.source_audio_locator is not None
            }
        ),
        localized_manifest_path=localized_selected_source_records_path(slice_root).as_posix(),
        localized_audio_root=localized_root.as_posix(),
    )
    write_json(localized_slice_summary_path(slice_root), summary)
    _emit_progress(
        "[qwen-portable-slice] localize slice done "
        f"row_count={summary.localized_row_count} "
        f"localized_audio_file_count={summary.localized_audio_file_count}"
    )
    return summary


def _to_float(value: object) -> float | None:
    """Narrow one object to float when possible."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _to_int(value: object) -> int | None:
    """Narrow one object to int when possible."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _required_file_from_payload(payload: object) -> PortableSliceRequiredFile:
    """Parse one required-file payload from JSON."""
    if not isinstance(payload, Mapping):
        raise ValueError("Portable slice required-file payload must be a mapping.")
    repo_id = payload.get("repo_id")
    repo_type = payload.get("repo_type")
    filename = payload.get("filename")
    local_relative_path = payload.get("local_relative_path")
    revision = payload.get("revision")
    if not isinstance(repo_id, str):
        raise ValueError("Portable slice required-file payload is missing `repo_id`.")
    if not isinstance(repo_type, str):
        raise ValueError("Portable slice required-file payload is missing `repo_type`.")
    if not isinstance(filename, str):
        raise ValueError("Portable slice required-file payload is missing `filename`.")
    if not isinstance(local_relative_path, str):
        raise ValueError("Portable slice required-file payload is missing `local_relative_path`.")
    if revision is not None and not isinstance(revision, str):
        raise ValueError("Portable slice required-file `revision` must be a string or null.")
    return PortableSliceRequiredFile(
        repo_id=repo_id,
        repo_type=repo_type,
        filename=filename,
        local_relative_path=local_relative_path,
        revision=revision,
    )


def _emit_progress(message: str) -> None:
    """Print one operator-facing progress line for notebook-backed runs."""
    print(message, flush=True)


def _utc_now_rfc3339() -> str:
    """Render the current UTC timestamp in RFC3339 form."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
