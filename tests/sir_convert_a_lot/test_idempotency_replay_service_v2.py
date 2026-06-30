"""Application-service tests for Service API v2 idempotent replay policy.

Purpose:
    Prove create-job idempotency replay decisions through a protocol-first
    application service rather than HTTP helper branching.

Relationships:
    - Exercises `application.idempotency_replay_service_v2` with in-memory
      ports.
    - Complements HTTP route tests that preserve the public Service API v2
      response contract.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from scripts.sir_convert_a_lot.application.idempotency_replay_service_v2 import (
    IdempotencyReplayServiceV2,
)
from scripts.sir_convert_a_lot.domain.idempotency_replay_policy_v2 import (
    IdempotencyAttemptSnapshotV2,
    IdempotencyJobSnapshotV2,
    IdempotencyReattemptReasonV2,
    IdempotencyRecordSnapshotV2,
    IdempotencyReplayActionV2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus


def test_retryable_failed_terminal_policy_admits_service_reattempt_with_reason() -> None:
    failed_job = IdempotencyJobSnapshotV2(
        job_id="jobv2_failed",
        status=JobStatus.FAILED,
        failure_retryable=True,
    )
    fresh_job = IdempotencyJobSnapshotV2(
        job_id="jobv2_fresh",
        status=JobStatus.QUEUED,
        failure_retryable=None,
    )
    records = _MemoryRecords(
        IdempotencyRecordSnapshotV2(
            fingerprint="sha256:request",
            active_job_id=failed_job.job_id,
            created_at=datetime(2026, 6, 29, tzinfo=UTC),
            attempt_count=1,
            previous_attempts=(),
        )
    )
    service = IdempotencyReplayServiceV2(records=records, jobs=_MemoryJobs(failed_job))

    decision = service.resolve_create_job_replay(
        scope_key="owner:POST:/v2/convert/jobs:key",
        request_fingerprint="sha256:request",
        fresh_admission=_FreshAdmission(fresh_job),
    )

    assert decision.action == IdempotencyReplayActionV2.SERVICE_REATTEMPT
    assert decision.reason == IdempotencyReattemptReasonV2.RETRYABLE_FAILED_TERMINAL
    assert decision.returned_job_id == fresh_job.job_id
    assert decision.reattempt_of_job_id == failed_job.job_id
    assert decision.attempt_count == 2
    assert decision.previous_attempts == (
        IdempotencyAttemptSnapshotV2(
            job_id=failed_job.job_id,
            status=JobStatus.FAILED,
            failure_retryable=True,
        ),
    )
    assert records.record is not None
    assert records.record.active_job_id == fresh_job.job_id
    assert records.record.attempt_count == 2


def test_running_terminal_compatibility_default_remains_strict_replay() -> None:
    running_job = IdempotencyJobSnapshotV2(
        job_id="jobv2_running",
        status=JobStatus.RUNNING,
        failure_retryable=None,
    )
    records = _MemoryRecords(
        IdempotencyRecordSnapshotV2(
            fingerprint="sha256:request",
            active_job_id=running_job.job_id,
            created_at=datetime(2026, 6, 29, tzinfo=UTC),
            attempt_count=1,
            previous_attempts=(),
        )
    )
    service = IdempotencyReplayServiceV2(records=records, jobs=_MemoryJobs(running_job))

    decision = service.resolve_create_job_replay(
        scope_key="owner:POST:/v2/convert/jobs:key",
        request_fingerprint="sha256:request",
        fresh_admission=_FreshAdmission(
            IdempotencyJobSnapshotV2(
                job_id="jobv2_unexpected",
                status=JobStatus.QUEUED,
                failure_retryable=None,
            )
        ),
    )

    assert decision.action == IdempotencyReplayActionV2.STRICT_REPLAY
    assert decision.reason is None
    assert decision.returned_job_id == running_job.job_id
    assert decision.replayed_job_id == running_job.job_id


@dataclass
class _MemoryRecords:
    record: IdempotencyRecordSnapshotV2 | None

    def scoped_lock(self, scope_key: str) -> AbstractContextManager[None]:
        del scope_key
        return nullcontext()

    def get_record(self, scope_key: str) -> IdempotencyRecordSnapshotV2 | None:
        del scope_key
        return self.record

    def record_fresh_attempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
    ) -> None:
        del scope_key
        self.record = IdempotencyRecordSnapshotV2(
            fingerprint=fingerprint,
            active_job_id=active_job_id,
            created_at=datetime(2026, 6, 29, tzinfo=UTC),
            attempt_count=1,
            previous_attempts=(),
        )

    def record_service_reattempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
        previous_attempt: IdempotencyAttemptSnapshotV2,
        existing_record: IdempotencyRecordSnapshotV2,
    ) -> None:
        del scope_key, fingerprint
        self.record = replace(
            existing_record,
            active_job_id=active_job_id,
            attempt_count=existing_record.attempt_count + 1,
            previous_attempts=(*existing_record.previous_attempts, previous_attempt),
        )


@dataclass(frozen=True)
class _MemoryJobs:
    job: IdempotencyJobSnapshotV2

    def get_job_snapshot(self, job_id: str) -> IdempotencyJobSnapshotV2 | None:
        if job_id == self.job.job_id:
            return self.job
        return None


@dataclass(frozen=True)
class _FreshAdmission:
    job: IdempotencyJobSnapshotV2

    def admit_fresh_attempt(self) -> IdempotencyJobSnapshotV2:
        return self.job
