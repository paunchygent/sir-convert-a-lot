"""Filesystem journal helpers for Sir Convert-a-Lot infrastructure.

Purpose:
    Provide small, shared primitives for durable on-disk state in the
    infrastructure layer (atomic JSON writes and RFC3339 timestamps).

Relationships:
    - Used by `infrastructure.job_store` for durable job manifests and tombstones.
    - Used by `infrastructure.idempotency_store` for durable idempotency records.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(UTC)


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return payload


def dt_to_rfc3339(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dt_from_rfc3339(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid datetime value: {value!r}")
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)
