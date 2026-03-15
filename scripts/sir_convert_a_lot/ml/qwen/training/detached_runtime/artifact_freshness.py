"""Stale-artifact filtering for resumed detached Qwen launches.

Purpose:
    Hide reused run-root artifacts that predate the current resumed container
    so detached inspection stays truthful after resume.

Relationships:
    - Used by detached inspection services.
    - Consumes `DetachedLaunch` metadata to decide whether filtering applies.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch


def load_optional_json(path: Path) -> dict[str, object] | None:
    """Load one optional JSON artifact, returning `None` when it is absent or malformed."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def filter_stale_resumed_run_artifacts(
    launch: DetachedLaunch,
    *,
    state: dict[str, object],
    pilot_status: dict[str, object] | None,
    pilot_report: dict[str, object] | None,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """Hide stale run-root artifacts that predate the current resumed container."""
    if launch.resumed_from_checkpoint_path is None:
        return pilot_status, pilot_report
    container_started_at = parse_rfc3339_utc(str(state.get("StartedAt", "")))
    if container_started_at is None:
        return pilot_status, pilot_report
    filtered_status = pilot_status
    filtered_report = pilot_report
    if artifact_timestamp_before_container_start(
        pilot_status,
        timestamp_key="updated_at",
        container_started_at=container_started_at,
    ):
        filtered_status = None
    if artifact_timestamp_before_container_start(
        pilot_report,
        timestamp_key="generated_at",
        container_started_at=container_started_at,
    ):
        filtered_report = None
    return filtered_status, filtered_report


def artifact_timestamp_before_container_start(
    payload: dict[str, object] | None,
    *,
    timestamp_key: str,
    container_started_at: datetime,
) -> bool:
    """Return whether one artifact timestamp predates the current resumed container."""
    if payload is None:
        return False
    raw_timestamp = payload.get(timestamp_key)
    if not isinstance(raw_timestamp, str):
        return False
    parsed_timestamp = parse_rfc3339_utc(raw_timestamp)
    if parsed_timestamp is None:
        return False
    return parsed_timestamp < container_started_at


def phase_history_from_status(
    pilot_status: Mapping[str, object] | None,
) -> list[Mapping[str, object]] | None:
    """Extract a normalized phase history from one optional status payload."""
    if pilot_status is None:
        return None
    raw_phase_history = pilot_status.get("phase_history")
    if not isinstance(raw_phase_history, list):
        return None
    parsed_phase_history: list[Mapping[str, object]] = []
    for event in raw_phase_history:
        if isinstance(event, Mapping):
            parsed_phase_history.append(event)
    return parsed_phase_history


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_rfc3339_utc(raw_timestamp: str) -> datetime | None:
    """Parse one RFC3339 timestamp into UTC, tolerating nanosecond precision."""
    normalized = raw_timestamp.strip()
    if normalized == "":
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    if "." not in normalized:
        try:
            return datetime.fromisoformat(normalized).astimezone(UTC)
        except ValueError:
            return None
    prefix, suffix = normalized.split(".", maxsplit=1)
    timezone_index = suffix.find("+")
    if timezone_index == -1:
        timezone_index = suffix.find("-")
    if timezone_index == -1:
        fractional_seconds = suffix
        timezone_suffix = ""
    else:
        fractional_seconds = suffix[:timezone_index]
        timezone_suffix = suffix[timezone_index:]
    normalized = f"{prefix}.{fractional_seconds[:6]}{timezone_suffix}"
    try:
        return datetime.fromisoformat(normalized).astimezone(UTC)
    except ValueError:
        return None
