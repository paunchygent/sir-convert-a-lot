"""Filesystem-backed idempotency store for Sir Convert-a-Lot job admission.

Purpose:
    Persist create-job idempotency records for service API job admission so
    replay and service-owned reattempt semantics survive service restarts.

Relationships:
    - Used by v1 and v2 runtime engines to store/retrieve per-scope
      idempotency records.
    - V2 create-job admission records active attempts and superseded failed
      attempt lineage while preserving legacy single-`job_id` records.
    - Record keys are derived from the HTTP scope key, hashed for stable file names.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Iterator
from contextlib import contextmanager
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
class IdempotencyAttemptRecord:
    """One superseded idempotency attempt retained for audit lineage."""

    job_id: str
    status: str | None
    failure_retryable: bool | None
    superseded_at: datetime | None


@dataclass(frozen=True)
class IdempotencyRecord:
    """Durable idempotency record for create-job replay and collision behavior."""

    fingerprint: str
    active_job_id: str
    created_at: datetime
    attempt_count: int
    previous_attempts: tuple[IdempotencyAttemptRecord, ...]

    @property
    def job_id(self) -> str:
        """Return the active job id for legacy v1/v2 call sites."""
        return self.active_job_id


class IdempotencyStore:
    """Filesystem-backed idempotency store."""

    def __init__(self, *, data_root: Path, ttl_seconds: int) -> None:
        self.dir = data_root / "idempotency"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(seconds=ttl_seconds)
        self._locks_guard = threading.Lock()
        self._scope_locks: dict[str, threading.RLock] = {}

    def _path_for_scope(self, scope_key: str) -> Path:
        digest = hashlib.sha256(scope_key.encode("utf-8")).hexdigest()
        return self.dir / f"{digest}.json"

    @contextmanager
    def scoped_lock(self, scope_key: str) -> Iterator[None]:
        """Serialize admission decisions for one idempotency scope in this process."""
        with self._locks_guard:
            lock = self._scope_locks.get(scope_key)
            if lock is None:
                lock = threading.RLock()
                self._scope_locks[scope_key] = lock
        with lock:
            yield

    def get(self, scope_key: str) -> IdempotencyRecord | None:
        path = self._path_for_scope(scope_key)
        if not path.exists():
            return None
        payload = read_json(path)
        fingerprint = payload.get("fingerprint")
        active_job_id = payload.get("active_job_id")
        if not isinstance(active_job_id, str):
            active_job_id = payload.get("job_id")
        created_at = dt_from_rfc3339(payload.get("created_at"))
        if (
            not isinstance(fingerprint, str)
            or not isinstance(active_job_id, str)
            or created_at is None
        ):
            return None
        if utc_now() - created_at > self.ttl:
            path.unlink(missing_ok=True)
            return None
        previous_attempts = _parse_previous_attempts(payload.get("previous_attempts"))
        attempt_count_obj = payload.get("attempt_count")
        attempt_count = (
            attempt_count_obj
            if isinstance(attempt_count_obj, int) and not isinstance(attempt_count_obj, bool)
            else len(previous_attempts) + 1
        )
        return IdempotencyRecord(
            fingerprint=fingerprint,
            active_job_id=active_job_id,
            created_at=created_at,
            attempt_count=max(1, attempt_count),
            previous_attempts=previous_attempts,
        )

    def put(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        payload: dict[str, object] = {
            "fingerprint": fingerprint,
            "job_id": job_id,
            "active_job_id": job_id,
            "attempt_count": 1,
            "previous_attempts": [],
            "created_at": dt_to_rfc3339(utc_now()),
        }
        atomic_write_json(self._path_for_scope(scope_key), payload)

    def put_reattempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
        previous_attempt: IdempotencyAttemptRecord,
        created_at: datetime,
        existing_previous_attempts: tuple[IdempotencyAttemptRecord, ...],
    ) -> None:
        """Point a scope at a fresh active attempt while retaining failed lineage."""
        previous_attempts = [*_attempt_payloads(existing_previous_attempts)]
        previous_attempts.append(_attempt_payload(previous_attempt))
        payload: dict[str, object] = {
            "fingerprint": fingerprint,
            "job_id": active_job_id,
            "active_job_id": active_job_id,
            "attempt_count": len(previous_attempts) + 1,
            "previous_attempts": previous_attempts,
            "created_at": dt_to_rfc3339(created_at),
        }
        atomic_write_json(self._path_for_scope(scope_key), payload)


def _parse_previous_attempts(value: object) -> tuple[IdempotencyAttemptRecord, ...]:
    if not isinstance(value, list):
        return ()
    attempts: list[IdempotencyAttemptRecord] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        job_id = item.get("job_id")
        if not isinstance(job_id, str):
            continue
        status_obj = item.get("status")
        status = status_obj if isinstance(status_obj, str) else None
        retryable_obj = item.get("failure_retryable")
        failure_retryable = retryable_obj if isinstance(retryable_obj, bool) else None
        attempts.append(
            IdempotencyAttemptRecord(
                job_id=job_id,
                status=status,
                failure_retryable=failure_retryable,
                superseded_at=dt_from_rfc3339(item.get("superseded_at")),
            )
        )
    return tuple(attempts)


def _attempt_payloads(
    attempts: tuple[IdempotencyAttemptRecord, ...],
) -> list[dict[str, object]]:
    return [_attempt_payload(attempt) for attempt in attempts]


def _attempt_payload(attempt: IdempotencyAttemptRecord) -> dict[str, object]:
    return {
        "job_id": attempt.job_id,
        "status": attempt.status,
        "failure_retryable": attempt.failure_retryable,
        "superseded_at": dt_to_rfc3339(attempt.superseded_at),
    }
