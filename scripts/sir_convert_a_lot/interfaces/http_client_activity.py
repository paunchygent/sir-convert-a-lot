"""Shared activity timestamp helpers for HTTP clients.

Purpose:
    Provide a single, best-effort implementation for extracting RFC3339
    timestamps and computing the "most recent activity" time from v2 job
    payloads, used by polling timeout classification.

Relationships:
    - Used by `interfaces.http_client_v2` to classify job activity freshness.
"""

from __future__ import annotations

from datetime import UTC, datetime


def dt_from_rfc3339(value: object) -> datetime | None:
    """Parse RFC3339 string into UTC datetime or return None."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).astimezone(UTC)
    except ValueError:
        return None


def most_recent_activity_at(job_payload: object) -> datetime | None:
    """Best-effort activity timestamp for v2 job payloads.

    Preference order:
      1) progress.last_heartbeat_at
      2) job.updated_at (when present)
      3) job.created_at (when present)
    """
    if not isinstance(job_payload, dict):
        return None
    job_obj = job_payload.get("job")
    if not isinstance(job_obj, dict):
        return None

    candidates: list[datetime] = []

    progress_obj = job_obj.get("progress")
    if isinstance(progress_obj, dict):
        heartbeat = dt_from_rfc3339(progress_obj.get("last_heartbeat_at"))
        if heartbeat is not None:
            candidates.append(heartbeat)

    updated_at = dt_from_rfc3339(job_obj.get("updated_at"))
    if updated_at is not None:
        candidates.append(updated_at)

    created_at = dt_from_rfc3339(job_obj.get("created_at"))
    if created_at is not None:
        candidates.append(created_at)

    if not candidates:
        return None
    return max(candidates)
