"""Shard assignment ledger and processing-unit issuance for Task 121.

Purpose:
    Reserve immutable Qwen shard ids for concrete processing units and replay
    that append-only history into one current availability state so future work
    cannot overlap silently.

Relationships:
    - Uses shard registry artifacts from `task121_qwen_shard_registry.py`.
    - Emits processing-unit roots that remain compatible with Task 121 staging
      and Task 103 selected-source processing.
    - Reuses portable required-file derivation from
      `task121_qwen_portable_slice_planning.py`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_jsonl_objects,
    write_json,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    SourceRecord,
    source_record_to_payload,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_planning import (
    required_files_for_source_records,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_shard_registry import (
    QwenShardRegistryIndex,
    load_shard_registry_index,
    load_shard_source_records,
    shard_assignment_ledger_path,
)

AssignmentEventType = Literal["assigned", "released", "completed"]
ShardStatus = Literal["available", "assigned", "completed"]


@dataclass(frozen=True)
class QwenShardAssignmentEvent:
    """One append-only shard-assignment ledger event."""

    event_type: AssignmentEventType
    event_timestamp: str
    processing_unit_id: str
    executor: str
    shard_ids: list[str]


@dataclass(frozen=True)
class QwenProcessingUnitSummary:
    """Stable summary for one shard-backed processing unit."""

    processing_unit_id: str
    registry_root: str
    processing_unit_root: str
    executor: str
    shard_ids: list[str]
    selected_row_count: int
    required_files_count: int


@dataclass(frozen=True)
class QwenShardState:
    """Current replayed availability state for one shard."""

    shard_id: str
    status: ShardStatus
    processing_unit_id: str | None


def processing_unit_summary_path(processing_unit_root: Path) -> Path:
    """Return the summary path for one processing unit."""
    return processing_unit_root / "processing_unit_summary.json"


def issue_processing_unit_from_shards(
    *,
    registry_root: Path,
    processing_unit_root: Path,
    processing_unit_id: str,
    executor: str,
    shard_ids: Sequence[str],
) -> QwenProcessingUnitSummary:
    """Reserve shard ids and emit one processing-unit root from their manifests."""
    if processing_unit_root.exists():
        raise ValueError("Processing-unit root must be a new path.")
    registry_index = load_shard_registry_index(registry_root)
    requested_shard_ids = list(shard_ids)
    if not requested_shard_ids:
        raise ValueError("At least one shard id is required.")
    _validate_requested_shards(registry_index=registry_index, shard_ids=requested_shard_ids)
    shard_states = replay_shard_assignment_ledger(registry_root)
    unavailable_shards = [
        shard_id for shard_id in requested_shard_ids if shard_states[shard_id].status != "available"
    ]
    if unavailable_shards:
        raise ValueError(
            "Cannot issue processing unit from unavailable shards: "
            + ", ".join(sorted(unavailable_shards))
        )

    selected_source_records = _load_processing_unit_source_records(
        registry_root=registry_root,
        shard_ids=requested_shard_ids,
    )
    required_files = required_files_for_source_records(
        source_records=selected_source_records,
        rixvox_revision=None,
    )
    write_jsonl(
        processing_unit_root / "selected_source_records.jsonl",
        [source_record_to_payload(source_record) for source_record in selected_source_records],
    )
    write_json(
        processing_unit_root / "required_hub_files.json",
        [asdict(required_file) for required_file in required_files],
    )
    summary = QwenProcessingUnitSummary(
        processing_unit_id=processing_unit_id,
        registry_root=registry_root.as_posix(),
        processing_unit_root=processing_unit_root.as_posix(),
        executor=executor,
        shard_ids=requested_shard_ids,
        selected_row_count=len(selected_source_records),
        required_files_count=len(required_files),
    )
    write_json(processing_unit_summary_path(processing_unit_root), summary)
    _append_assignment_event(
        registry_root=registry_root,
        event=QwenShardAssignmentEvent(
            event_type="assigned",
            event_timestamp=_utc_now_rfc3339(),
            processing_unit_id=processing_unit_id,
            executor=executor,
            shard_ids=requested_shard_ids,
        ),
    )
    return summary


def release_processing_unit(
    *,
    registry_root: Path,
    processing_unit_root: Path,
    executor: str,
) -> QwenShardAssignmentEvent:
    """Release one processing unit so its shard ids become available again."""
    summary = _load_processing_unit_summary(processing_unit_root)
    _assert_processing_unit_owns_assigned_shards(
        registry_root=registry_root,
        summary=summary,
    )
    event = QwenShardAssignmentEvent(
        event_type="released",
        event_timestamp=_utc_now_rfc3339(),
        processing_unit_id=summary.processing_unit_id,
        executor=executor,
        shard_ids=summary.shard_ids,
    )
    _append_assignment_event(registry_root=registry_root, event=event)
    return event


def complete_processing_unit(
    *,
    registry_root: Path,
    processing_unit_root: Path,
    executor: str,
) -> QwenShardAssignmentEvent:
    """Mark one processing unit completed so its shard ids cannot be reissued."""
    summary = _load_processing_unit_summary(processing_unit_root)
    _assert_processing_unit_owns_assigned_shards(
        registry_root=registry_root,
        summary=summary,
    )
    event = QwenShardAssignmentEvent(
        event_type="completed",
        event_timestamp=_utc_now_rfc3339(),
        processing_unit_id=summary.processing_unit_id,
        executor=executor,
        shard_ids=summary.shard_ids,
    )
    _append_assignment_event(registry_root=registry_root, event=event)
    return event


def replay_shard_assignment_ledger(registry_root: Path) -> dict[str, QwenShardState]:
    """Replay the shard-assignment ledger into one current-state mapping."""
    registry_index = load_shard_registry_index(registry_root)
    shard_states = {
        shard_id: QwenShardState(shard_id=shard_id, status="available", processing_unit_id=None)
        for shard_id in registry_index.shard_ids
    }
    for payload in iter_jsonl_objects(shard_assignment_ledger_path(registry_root)):
        event = _assignment_event_from_payload(payload)
        for shard_id in event.shard_ids:
            current_state = shard_states[shard_id]
            if event.event_type == "assigned":
                shard_states[shard_id] = QwenShardState(
                    shard_id=shard_id,
                    status="assigned",
                    processing_unit_id=event.processing_unit_id,
                )
                continue
            if event.event_type == "released":
                if current_state.processing_unit_id == event.processing_unit_id:
                    shard_states[shard_id] = QwenShardState(
                        shard_id=shard_id,
                        status="available",
                        processing_unit_id=None,
                    )
                continue
            if current_state.processing_unit_id == event.processing_unit_id:
                shard_states[shard_id] = QwenShardState(
                    shard_id=shard_id,
                    status="completed",
                    processing_unit_id=event.processing_unit_id,
                )
    return shard_states


def _append_assignment_event(
    *,
    registry_root: Path,
    event: QwenShardAssignmentEvent,
) -> None:
    """Append one assignment event to the append-only ledger."""
    ledger_path = shard_assignment_ledger_path(registry_root)
    existing_rows: list[object] = list(iter_jsonl_objects(ledger_path))
    existing_rows.append(asdict(event))
    write_jsonl(ledger_path, existing_rows)


def _load_processing_unit_source_records(
    *,
    registry_root: Path,
    shard_ids: Sequence[str],
) -> list[SourceRecord]:
    """Load the ordered selected-source records for one processing unit."""
    selected_source_records: list[SourceRecord] = []
    for shard_id in shard_ids:
        selected_source_records.extend(
            load_shard_source_records(registry_root=registry_root, shard_id=shard_id)
        )
    return selected_source_records


def _validate_requested_shards(
    *,
    registry_index: QwenShardRegistryIndex,
    shard_ids: Sequence[str],
) -> None:
    """Ensure every requested shard id exists in the registry."""
    unknown_shard_ids = [
        shard_id for shard_id in shard_ids if shard_id not in registry_index.shard_ids
    ]
    if unknown_shard_ids:
        raise ValueError(f"Unknown shard ids: {', '.join(sorted(unknown_shard_ids))}")


def _assert_processing_unit_owns_assigned_shards(
    *,
    registry_root: Path,
    summary: QwenProcessingUnitSummary,
) -> None:
    """Ensure one processing unit still owns every assigned shard before state change."""
    shard_states = replay_shard_assignment_ledger(registry_root)
    for shard_id in summary.shard_ids:
        shard_state = shard_states[shard_id]
        if (
            shard_state.status != "assigned"
            or shard_state.processing_unit_id != summary.processing_unit_id
        ):
            raise ValueError(
                "Cannot transition shards that are not currently assigned to this processing unit."
            )


def _load_processing_unit_summary(processing_unit_root: Path) -> QwenProcessingUnitSummary:
    """Load one processing-unit summary from disk."""
    from json import loads

    payload = loads(processing_unit_summary_path(processing_unit_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Malformed processing-unit summary.")
    shard_ids = payload.get("shard_ids")
    if not isinstance(shard_ids, list) or not all(isinstance(item, str) for item in shard_ids):
        raise ValueError("Malformed processing-unit shard ids.")
    return QwenProcessingUnitSummary(
        processing_unit_id=_required_string(payload, "processing_unit_id"),
        registry_root=_required_string(payload, "registry_root"),
        processing_unit_root=_required_string(payload, "processing_unit_root"),
        executor=_required_string(payload, "executor"),
        shard_ids=shard_ids,
        selected_row_count=_required_int(payload, "selected_row_count"),
        required_files_count=_required_int(payload, "required_files_count"),
    )


def _assignment_event_from_payload(payload: dict[str, object]) -> QwenShardAssignmentEvent:
    """Hydrate one typed assignment event from one stored payload."""
    shard_ids = payload.get("shard_ids")
    if not isinstance(shard_ids, list) or not all(isinstance(item, str) for item in shard_ids):
        raise ValueError("Malformed assignment-event shard ids.")
    return QwenShardAssignmentEvent(
        event_type=_required_event_type(payload),
        event_timestamp=_required_string(payload, "event_timestamp"),
        processing_unit_id=_required_string(payload, "processing_unit_id"),
        executor=_required_string(payload, "executor"),
        shard_ids=shard_ids,
    )


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


def _required_event_type(payload: dict[str, object]) -> AssignmentEventType:
    """Return one required typed assignment-event discriminator."""
    event_type = _required_string(payload, "event_type")
    if event_type == "assigned":
        return "assigned"
    if event_type == "released":
        return "released"
    if event_type == "completed":
        return "completed"
    raise ValueError("Malformed assignment event type.")


def _utc_now_rfc3339() -> str:
    """Render the current UTC timestamp in RFC3339 form."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
