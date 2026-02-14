"""Filesystem-backed idempotency store for Sir Convert-a-Lot v1.

Purpose:
    Persist idempotency records for `POST /v1/convert/jobs` so create-job replay
    semantics survive service restarts.

Relationships:
    - Used by `infrastructure.runtime_engine.ServiceRuntime` to store/retrieve
      per-scope idempotency records.
    - Record keys are derived from the HTTP scope key, hashed for stable file names.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)


@dataclass(frozen=True)
class IdempotencyRecord:
    """Durable idempotency record for create-job replay and collision behavior."""

    fingerprint: str
    job_id: str
    created_at: datetime


class IdempotencyStore:
    """Filesystem-backed idempotency store."""

    def __init__(self, *, data_root: Path, ttl_seconds: int) -> None:
        self.dir = data_root / "idempotency"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(seconds=ttl_seconds)

    def _path_for_scope(self, scope_key: str) -> Path:
        digest = hashlib.sha256(scope_key.encode("utf-8")).hexdigest()
        return self.dir / f"{digest}.json"

    def get(self, scope_key: str) -> IdempotencyRecord | None:
        path = self._path_for_scope(scope_key)
        if not path.exists():
            return None
        payload = read_json(path)
        fingerprint = payload.get("fingerprint")
        job_id = payload.get("job_id")
        created_at = dt_from_rfc3339(payload.get("created_at"))
        if not isinstance(fingerprint, str) or not isinstance(job_id, str) or created_at is None:
            return None
        if utc_now() - created_at > self.ttl:
            path.unlink(missing_ok=True)
            return None
        return IdempotencyRecord(fingerprint=fingerprint, job_id=job_id, created_at=created_at)

    def put(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        payload: dict[str, object] = {
            "fingerprint": fingerprint,
            "job_id": job_id,
            "created_at": dt_to_rfc3339(utc_now()),
        }
        atomic_write_json(self._path_for_scope(scope_key), payload)
