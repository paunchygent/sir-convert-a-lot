"""Progress-event and status helpers for Task 101 batch finalization.

Purpose:
    Persist append-only Task 101 batch events and a rolled-up mutable status
    file so interrupted Hemma runs leave explicit, machine-readable progress
    evidence.

Relationships:
    - Consumed by Task 101 bundle orchestration and per-batch execution.
    - Builds on the batch plan/layout contracts from
      `task101_qwen_pilot_bundle_batch_contracts.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    Task101PilotBundleBatch,
    task101_pilot_bundle_batch_id,
    task101_pilot_bundle_progress_events_path,
    task101_pilot_bundle_progress_state_path,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import ManifestFamily
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import write_json

if TYPE_CHECKING:
    from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
        Task101PilotBundleBatchPlan,
    )


@dataclass(frozen=True)
class Task101PilotBundleProgressState:
    """Derived progress summary for one partially or fully built bundle."""

    output_root: str
    total_batch_count: int
    started_batch_count: int
    completed_batch_count: int
    skipped_batch_event_count: int
    last_event: str | None
    last_event_at: str | None
    last_started_family: ManifestFamily | None
    last_started_batch_index: int | None
    last_completed_family: ManifestFamily | None
    last_completed_batch_index: int | None


def record_task101_pilot_bundle_progress_event(
    *,
    output_root: Path,
    plan: "Task101PilotBundleBatchPlan",
    event: str,
    batch: Task101PilotBundleBatch | None = None,
    detail: str | None = None,
    extra_fields: dict[str, object] | None = None,
    timestamp: str | None = None,
) -> None:
    """Append one progress event, rebuild status, and emit a log line."""
    rendered_timestamp = timestamp or _utc_now_iso()
    payload: dict[str, object] = {
        "timestamp": rendered_timestamp,
        "event": event,
    }
    if batch is not None:
        payload.update(
            {
                "batch_id": task101_pilot_bundle_batch_id(batch),
                "manifest_family": batch.manifest_family,
                "batch_index": batch.batch_index,
                "batch_row_count": batch.row_count,
                "first_row_key": batch.first_row_key,
                "last_row_key": batch.last_row_key,
            }
        )
    if detail is not None:
        payload["detail"] = detail
    if extra_fields is not None:
        payload.update(extra_fields)
    events_path = task101_pilot_bundle_progress_events_path(output_root)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        handle.write("\n")
    rebuild_task101_pilot_bundle_progress_state(output_root, plan)
    print(
        "[task101-pilot-bundle] " + json.dumps(payload, sort_keys=True, ensure_ascii=False),
        flush=True,
    )


def rebuild_task101_pilot_bundle_progress_state(
    output_root: Path,
    plan: "Task101PilotBundleBatchPlan",
) -> Task101PilotBundleProgressState:
    """Recompute and persist the derived Task 101 status file."""
    started_batch_ids: set[str] = set()
    completed_batch_ids: set[str] = set()
    skipped_batch_event_count = 0
    last_event_payload: dict[str, object] | None = None
    last_started_payload: dict[str, object] | None = None
    last_completed_payload: dict[str, object] | None = None
    for payload in _iter_progress_event_payloads(
        task101_pilot_bundle_progress_events_path(output_root)
    ):
        last_event_payload = payload
        rendered_event = payload.get("event")
        if rendered_event == "batch_started":
            batch_id = payload.get("batch_id")
            if isinstance(batch_id, str):
                started_batch_ids.add(batch_id)
            last_started_payload = payload
        if rendered_event == "batch_completed":
            batch_id = payload.get("batch_id")
            if isinstance(batch_id, str):
                completed_batch_ids.add(batch_id)
            last_completed_payload = payload
        if rendered_event == "batch_skipped_existing":
            skipped_batch_event_count += 1
    progress_state = Task101PilotBundleProgressState(
        output_root=output_root.as_posix(),
        total_batch_count=len(plan.batches),
        started_batch_count=len(started_batch_ids),
        completed_batch_count=len(completed_batch_ids),
        skipped_batch_event_count=skipped_batch_event_count,
        last_event=_optional_string(last_event_payload, "event"),
        last_event_at=_optional_string(last_event_payload, "timestamp"),
        last_started_family=_optional_manifest_family(last_started_payload, "manifest_family"),
        last_started_batch_index=_optional_int(last_started_payload, "batch_index"),
        last_completed_family=_optional_manifest_family(last_completed_payload, "manifest_family"),
        last_completed_batch_index=_optional_int(last_completed_payload, "batch_index"),
    )
    write_json(task101_pilot_bundle_progress_state_path(output_root), progress_state)
    return progress_state


def _iter_progress_event_payloads(path: Path) -> list[dict[str, object]]:
    """Load valid progress-event rows while tolerating a truncated tail line."""
    if not path.exists():
        return []
    payloads: list[dict[str, object]] = []
    for raw_line in path.read_text("utf-8").splitlines():
        if raw_line.strip() == "":
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        payloads.append(payload)
    return payloads


def _optional_string(payload: dict[str, object] | None, key: str) -> str | None:
    """Return one optional string field from a JSON payload."""
    if payload is None:
        return None
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Malformed optional `{key}` in JSON payload.")
    return value


def _optional_int(payload: dict[str, object] | None, key: str) -> int | None:
    """Return one optional integer field from a JSON payload."""
    if payload is None:
        return None
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"Malformed optional `{key}` in JSON payload.")
    return value


def _optional_manifest_family(
    payload: dict[str, object] | None,
    key: str,
) -> ManifestFamily | None:
    """Return one optional manifest-family field from a JSON payload."""
    if payload is None:
        return None
    value = payload.get(key)
    if value is None:
        return None
    if value == "swedish_smoke_train":
        return "swedish_smoke_train"
    if value == "swedish_pilot_train":
        return "swedish_pilot_train"
    if value == "swedish_scaleup_train":
        return "swedish_scaleup_train"
    if value == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    if value == "swedish_final_test":
        return "swedish_final_test"
    if value == "swedish_waxholm_control":
        return "swedish_waxholm_control"
    raise ValueError(f"Malformed optional `{key}` manifest-family value: {value!r}.")


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
