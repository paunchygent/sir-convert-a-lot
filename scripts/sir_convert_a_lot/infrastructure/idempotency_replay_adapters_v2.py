"""Infrastructure adapters for Service API v2 idempotent replay policy.

Purpose:
    Adapt filesystem idempotency records and v2 runtime job objects to the
    protocol ports consumed by the application replay service.

Relationships:
    - Wraps `infrastructure.idempotency_store.IdempotencyStore`.
    - Converts `infrastructure.runtime_models_v2.StoredJobV2` into pure domain
      snapshots for `application.idempotency_replay_service_v2`.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.idempotency_replay_policy_v2 import (
    IdempotencyAttemptSnapshotV2,
    IdempotencyJobSnapshotV2,
    IdempotencyRecordSnapshotV2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import utc_now
from scripts.sir_convert_a_lot.infrastructure.idempotency_store import (
    IdempotencyAttemptRecord,
    IdempotencyRecord,
    IdempotencyStore,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


class IdempotencyStoreRecordAdapterV2:
    """Adapt filesystem-backed idempotency records to application ports."""

    def __init__(self, store: IdempotencyStore) -> None:
        self._store = store

    def scoped_lock(self, scope_key: str) -> AbstractContextManager[None]:
        """Return a cross-process idempotency scope lock."""

        return self._store.scoped_lock(scope_key)

    def get_record(self, scope_key: str) -> IdempotencyRecordSnapshotV2 | None:
        """Return the current record snapshot for scope."""

        record = self._store.get(scope_key)
        if record is None:
            return None
        return _record_snapshot(record)

    def record_fresh_attempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
    ) -> None:
        """Persist the first active job for scope."""

        self._store.put(scope_key, fingerprint, active_job_id)

    def record_service_reattempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
        previous_attempt: IdempotencyAttemptSnapshotV2,
        existing_record: IdempotencyRecordSnapshotV2,
    ) -> None:
        """Persist a service-owned reattempt and retained lineage."""

        self._store.put_reattempt(
            scope_key,
            fingerprint=fingerprint,
            active_job_id=active_job_id,
            previous_attempt=_store_attempt(previous_attempt),
            created_at=existing_record.created_at,
            existing_previous_attempts=tuple(
                _store_attempt(attempt) for attempt in existing_record.previous_attempts
            ),
        )


class RuntimeJobLookupAdapterV2:
    """Adapt runtime job lookup to application-safe job snapshots."""

    def __init__(self, get_job: Callable[[str], StoredJobV2 | None]) -> None:
        self._get_job = get_job

    def get_job_snapshot(self, job_id: str) -> IdempotencyJobSnapshotV2 | None:
        """Return a snapshot for a runtime job when present."""

        job = self._get_job(job_id)
        if job is None:
            return None
        return job_snapshot_v2(job)


@dataclass
class FreshAttemptAdmissionAdapterV2:
    """Adapt route-owned fresh job creation to the admission port."""

    create_job: Callable[[], StoredJobV2]
    admitted_job: StoredJobV2 | None = None

    def admit_fresh_attempt(self) -> IdempotencyJobSnapshotV2:
        """Create a fresh runtime job and return its replay-policy snapshot."""

        job = self.create_job()
        self.admitted_job = job
        return job_snapshot_v2(job)


def job_snapshot_v2(job: StoredJobV2) -> IdempotencyJobSnapshotV2:
    """Return the application-safe replay snapshot for a runtime job."""

    return IdempotencyJobSnapshotV2(
        job_id=job.job_id,
        status=job.status,
        failure_retryable=job.failure_retryable if job.status == JobStatus.FAILED else None,
    )


def _record_snapshot(record: IdempotencyRecord) -> IdempotencyRecordSnapshotV2:
    return IdempotencyRecordSnapshotV2(
        fingerprint=record.fingerprint,
        active_job_id=record.active_job_id,
        created_at=record.created_at,
        attempt_count=record.attempt_count,
        previous_attempts=tuple(_attempt_snapshot(attempt) for attempt in record.previous_attempts),
    )


def _attempt_snapshot(attempt: IdempotencyAttemptRecord) -> IdempotencyAttemptSnapshotV2:
    status = JobStatus(attempt.status) if attempt.status is not None else JobStatus.FAILED
    return IdempotencyAttemptSnapshotV2(
        job_id=attempt.job_id,
        status=status,
        failure_retryable=attempt.failure_retryable,
        superseded_at=attempt.superseded_at,
    )


def _store_attempt(attempt: IdempotencyAttemptSnapshotV2) -> IdempotencyAttemptRecord:
    return IdempotencyAttemptRecord(
        job_id=attempt.job_id,
        status=attempt.status.value,
        failure_retryable=attempt.failure_retryable,
        superseded_at=attempt.superseded_at or utc_now(),
    )
