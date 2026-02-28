"""Lifecycle-event helpers for Sir Convert-a-Lot service API v2.

Purpose:
    Provide typed event records, ULID/cursor primitives, and deterministic
    replay-window helpers used by the v2 job-store and SSE routes.

Relationships:
    - Used by `infrastructure.job_store_v2_core` for event emission and replay reads.
    - Used by `interfaces.http_routes_job_events_v2` for resume handling and
      `cursor_expired` semantics.
"""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    dt_from_rfc3339,
    dt_to_rfc3339,
)

JobEventTypeV2 = Literal[
    "job.queued",
    "job.running",
    "job.succeeded",
    "job.failed",
    "job.canceled",
]

_STATUS_TO_EVENT_TYPE: dict[JobStatus, JobEventTypeV2] = {
    JobStatus.QUEUED: "job.queued",
    JobStatus.RUNNING: "job.running",
    JobStatus.SUCCEEDED: "job.succeeded",
    JobStatus.FAILED: "job.failed",
    JobStatus.CANCELED: "job.canceled",
}
_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


@dataclass(frozen=True)
class JobLifecycleEventRecordV2:
    """One durable v2 lifecycle event record."""

    event_id: str
    event_type: JobEventTypeV2
    sequence: int
    occurred_at: datetime
    job_id: str
    status: JobStatus
    source_format: SourceFormatV2
    target_format: OutputFormatV2
    stage: str
    last_heartbeat_at: datetime | None


@dataclass
class CursorExpiredErrorV2(Exception):
    """Raised when a replay pointer is outside the retained replay horizon."""

    job_id: str
    latest_cursor: str
    replay_horizon_hours: int


@dataclass
class CursorValidationErrorV2(Exception):
    """Raised when an SSE replay cursor payload is malformed."""

    message: str


def status_to_event_type(status: JobStatus) -> JobEventTypeV2:
    """Return canonical event type for a job status."""
    return _STATUS_TO_EVENT_TYPE[status]


def replay_horizon_hours(*, replay_horizon_seconds: int) -> int:
    """Return rounded-up replay horizon in whole hours for error payloads."""
    seconds = max(1, replay_horizon_seconds)
    return max(1, (seconds + 3599) // 3600)


def _parse_event_type(value: str) -> JobEventTypeV2 | None:
    if value == "job.queued":
        return "job.queued"
    if value == "job.running":
        return "job.running"
    if value == "job.succeeded":
        return "job.succeeded"
    if value == "job.failed":
        return "job.failed"
    if value == "job.canceled":
        return "job.canceled"
    return None


def encode_replay_cursor(*, sequence: int) -> str:
    """Encode an opaque replay cursor from a monotonic sequence number."""
    payload = json.dumps({"seq": sequence}, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(payload).decode("ascii")
    return token.rstrip("=")


def decode_replay_cursor(cursor: str) -> int:
    """Decode an opaque replay cursor into a sequence number."""
    normalized = cursor.strip()
    if normalized == "":
        raise CursorValidationErrorV2("cursor must not be empty.")
    padding = "=" * ((4 - len(normalized) % 4) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(f"{normalized}{padding}".encode("ascii"))
        payload_obj = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise CursorValidationErrorV2("cursor is malformed.") from exc
    if not isinstance(payload_obj, dict):
        raise CursorValidationErrorV2("cursor is malformed.")
    sequence_obj = payload_obj.get("seq")
    if not isinstance(sequence_obj, int) or sequence_obj < 0:
        raise CursorValidationErrorV2("cursor is malformed.")
    return sequence_obj


def _base32_encode_fixed(value: int, *, length: int) -> str:
    chars: list[str] = []
    for _ in range(length):
        chars.append(_CROCKFORD_BASE32[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def generate_event_ulid(*, now: datetime) -> str:
    """Generate a canonical 26-char ULID string for event identity."""
    timestamp_ms = int(now.timestamp() * 1000)
    randomness = int.from_bytes(secrets.token_bytes(10), byteorder="big", signed=False)
    timestamp_part = _base32_encode_fixed(timestamp_ms, length=10)
    randomness_part = _base32_encode_fixed(randomness, length=16)
    return f"{timestamp_part}{randomness_part}"


def _event_records(payload: dict[str, object]) -> list[JobLifecycleEventRecordV2]:
    events_obj = payload.get("events")
    if not isinstance(events_obj, list):
        return []

    records: list[JobLifecycleEventRecordV2] = []
    for item in events_obj:
        if not isinstance(item, dict):
            continue
        event_id = item.get("event_id")
        event_type_obj = item.get("event_type")
        sequence = item.get("sequence")
        occurred_at_obj = item.get("occurred_at")
        job_id = item.get("job_id")
        status_obj = item.get("status")
        route_obj = item.get("route")
        progress_obj = item.get("progress")
        if not isinstance(event_id, str) or not isinstance(sequence, int):
            continue
        if not isinstance(occurred_at_obj, str) or not isinstance(job_id, str):
            continue
        if not isinstance(status_obj, str) or not isinstance(route_obj, dict):
            continue
        if not isinstance(progress_obj, dict):
            continue
        if not isinstance(event_type_obj, str):
            continue
        source_format_obj = route_obj.get("source_format")
        target_format_obj = route_obj.get("target_format")
        stage_obj = progress_obj.get("stage")
        heartbeat_obj = progress_obj.get("last_heartbeat_at")
        if not isinstance(source_format_obj, str) or not isinstance(target_format_obj, str):
            continue
        if not isinstance(stage_obj, str):
            continue
        if heartbeat_obj is not None and not isinstance(heartbeat_obj, str):
            continue

        try:
            event_type = _parse_event_type(event_type_obj)
            if event_type is None:
                continue
            occurred_at = dt_from_rfc3339(occurred_at_obj)
            if occurred_at is None:
                continue
            last_heartbeat_at = dt_from_rfc3339(heartbeat_obj)
            records.append(
                JobLifecycleEventRecordV2(
                    event_id=event_id,
                    event_type=event_type,
                    sequence=sequence,
                    occurred_at=occurred_at,
                    job_id=job_id,
                    status=JobStatus(status_obj),
                    source_format=SourceFormatV2(source_format_obj),
                    target_format=OutputFormatV2(target_format_obj),
                    stage=stage_obj,
                    last_heartbeat_at=last_heartbeat_at,
                )
            )
        except (KeyError, ValueError):
            continue

    records.sort(key=lambda record: record.sequence)
    return records


def _record_to_payload(record: JobLifecycleEventRecordV2) -> dict[str, object]:
    return {
        "event_id": record.event_id,
        "event_type": record.event_type,
        "sequence": record.sequence,
        "occurred_at": dt_to_rfc3339(record.occurred_at),
        "job_id": record.job_id,
        "status": record.status.value,
        "route": {
            "source_format": record.source_format.value,
            "target_format": record.target_format.value,
        },
        "progress": {
            "stage": record.stage,
            "last_heartbeat_at": dt_to_rfc3339(record.last_heartbeat_at),
        },
    }


def append_lifecycle_event(
    *,
    payload: dict[str, object],
    status: JobStatus,
    stage: str,
    occurred_at: datetime,
) -> JobLifecycleEventRecordV2:
    """Append one lifecycle event to a manifest payload in-place."""
    source_format_obj = payload.get("source_format")
    output_format_obj = payload.get("output_format")
    job_id_obj = payload.get("job_id")
    if not isinstance(source_format_obj, str) or not isinstance(output_format_obj, str):
        raise ValueError("manifest missing source/output format for event emission.")
    if not isinstance(job_id_obj, str):
        raise ValueError("manifest missing job_id for event emission.")

    records = _event_records(payload)
    counter_obj = payload.get("event_sequence_counter")
    counter = counter_obj if isinstance(counter_obj, int) and counter_obj >= 0 else 0
    if records:
        counter = max(counter, records[-1].sequence)
    sequence = counter + 1

    diagnostics_obj = payload.get("diagnostics")
    diagnostics = diagnostics_obj if isinstance(diagnostics_obj, dict) else {}
    heartbeat_obj = diagnostics.get("last_heartbeat_at")
    last_heartbeat_at = dt_from_rfc3339(heartbeat_obj)

    record = JobLifecycleEventRecordV2(
        event_id=generate_event_ulid(now=occurred_at),
        event_type=status_to_event_type(status),
        sequence=sequence,
        occurred_at=occurred_at,
        job_id=job_id_obj,
        status=status,
        source_format=SourceFormatV2(source_format_obj),
        target_format=OutputFormatV2(output_format_obj),
        stage=stage,
        last_heartbeat_at=last_heartbeat_at,
    )

    events_obj = payload.get("events")
    events = events_obj if isinstance(events_obj, list) else []
    events.append(_record_to_payload(record))
    payload["events"] = events
    payload["event_sequence_counter"] = sequence
    return record


def prune_replay_events(
    *,
    payload: dict[str, object],
    now: datetime,
    replay_horizon_seconds: int,
) -> bool:
    """Prune events outside replay horizon; return True when payload changed."""
    records = _event_records(payload)
    cutoff = now - timedelta(seconds=max(1, replay_horizon_seconds))
    kept = [record for record in records if record.occurred_at >= cutoff]
    changed = len(kept) != len(records)
    if changed:
        payload["events"] = [_record_to_payload(record) for record in kept]
    elif "events" not in payload:
        payload["events"] = [_record_to_payload(record) for record in kept]
        changed = True
    return changed


def list_events_after_sequence(
    *,
    payload: dict[str, object],
    after_sequence: int,
) -> list[JobLifecycleEventRecordV2]:
    """Return sorted lifecycle events with sequence strictly greater than cursor."""
    records = _event_records(payload)
    return [record for record in records if record.sequence > after_sequence]


def latest_resumable_cursor(*, payload: dict[str, object]) -> str:
    """Return opaque cursor for latest retained sequence."""
    records = _event_records(payload)
    if records:
        return encode_replay_cursor(sequence=records[-1].sequence)
    counter_obj = payload.get("event_sequence_counter")
    sequence = counter_obj if isinstance(counter_obj, int) and counter_obj > 0 else 0
    return encode_replay_cursor(sequence=sequence)


def resolve_resume_sequence(
    *,
    payload: dict[str, object],
    cursor: str | None,
    last_event_id: str | None,
    replay_horizon_seconds: int,
) -> int:
    """Resolve replay pointer to sequence or raise deterministic cursor errors."""
    if cursor is not None and last_event_id is not None:
        raise CursorValidationErrorV2("cursor and last_event_id cannot be provided together.")

    records = _event_records(payload)
    counter_obj = payload.get("event_sequence_counter")
    max_sequence = counter_obj if isinstance(counter_obj, int) and counter_obj >= 0 else 0
    if records:
        max_sequence = max(max_sequence, records[-1].sequence)

    if cursor is None and last_event_id is None:
        return 0

    requested_sequence: int | None = None
    if cursor is not None:
        requested_sequence = decode_replay_cursor(cursor)
    else:
        for record in records:
            if record.event_id == last_event_id:
                requested_sequence = record.sequence
                break
        if requested_sequence is None:
            job_id_obj = payload.get("job_id")
            job_id = job_id_obj if isinstance(job_id_obj, str) else "unknown"
            raise CursorExpiredErrorV2(
                job_id=job_id,
                latest_cursor=latest_resumable_cursor(payload=payload),
                replay_horizon_hours=replay_horizon_hours(
                    replay_horizon_seconds=replay_horizon_seconds
                ),
            )

    if requested_sequence is None:
        return 0
    if requested_sequence > max_sequence:
        raise CursorValidationErrorV2("cursor points beyond known event sequence.")

    if records:
        first_sequence = records[0].sequence
        if requested_sequence < first_sequence:
            job_id_obj = payload.get("job_id")
            job_id = job_id_obj if isinstance(job_id_obj, str) else "unknown"
            raise CursorExpiredErrorV2(
                job_id=job_id,
                latest_cursor=latest_resumable_cursor(payload=payload),
                replay_horizon_hours=replay_horizon_hours(
                    replay_horizon_seconds=replay_horizon_seconds
                ),
            )
    elif requested_sequence > 0 and max_sequence > 0:
        job_id_obj = payload.get("job_id")
        job_id = job_id_obj if isinstance(job_id_obj, str) else "unknown"
        raise CursorExpiredErrorV2(
            job_id=job_id,
            latest_cursor=latest_resumable_cursor(payload=payload),
            replay_horizon_hours=replay_horizon_hours(
                replay_horizon_seconds=replay_horizon_seconds
            ),
        )
    return requested_sequence
