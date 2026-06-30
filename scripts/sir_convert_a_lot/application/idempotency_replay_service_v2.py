"""Application service for Service API v2 idempotent replay policy.

Purpose:
    Orchestrate create-job idempotency replay decisions from protocol ports so
    HTTP routes no longer own business branching for strict replay, fresh
    admission, or service-owned reattempts.

Relationships:
    - Consumes pure domain decision types from
      `domain.idempotency_replay_policy_v2`.
    - Depends on protocol ports from `application.idempotency_replay_ports_v2`.
    - Used by interface/infrastructure adapters to preserve Task 368 behavior
      while exposing extension points for Tasks 376-378.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.idempotency_replay_ports_v2 import (
    CompatibleRouteArtifactCompatibilityPortV2,
    CorrectionReplayIdentityStorePortV2,
    DeferredCorrectionReplayIdentityStorePortV2,
    FreshAttemptAdmissionPortV2,
    IdempotencyJobLookupPortV2,
    IdempotencyRecordPortV2,
    RouteArtifactCompatibilityPortV2,
)
from scripts.sir_convert_a_lot.domain.idempotency_replay_policy_v2 import (
    IdempotencyAttemptSnapshotV2,
    IdempotencyJobSnapshotV2,
    IdempotencyReattemptReasonV2,
    IdempotencyRecordSnapshotV2,
    IdempotencyReplayActionV2,
    IdempotencyReplayDecisionV2,
    RouteArtifactCompatibilityStatusV2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus


class IdempotencyReplayConflictV2(Exception):
    """Raised when an idempotency key is reused with a different fingerprint."""


class IdempotencyReplayActiveJobMissingV2(Exception):
    """Raised when the idempotency record points at a missing active job."""


class IdempotencyReplayRecordMissingAfterReattemptV2(Exception):
    """Raised when reattempt admission cannot reread the updated record."""


class IdempotencyReplayServiceV2:
    """Resolve create-job replay policy through application ports."""

    def __init__(
        self,
        *,
        records: IdempotencyRecordPortV2,
        jobs: IdempotencyJobLookupPortV2,
        route_compatibility: RouteArtifactCompatibilityPortV2 | None = None,
        correction_replay_identity: CorrectionReplayIdentityStorePortV2 | None = None,
    ) -> None:
        self._records = records
        self._jobs = jobs
        self._route_compatibility = (
            route_compatibility or CompatibleRouteArtifactCompatibilityPortV2()
        )
        self._correction_replay_identity = (
            correction_replay_identity or DeferredCorrectionReplayIdentityStorePortV2()
        )

    @property
    def correction_replay_identity(self) -> CorrectionReplayIdentityStorePortV2:
        """Return the correction replay identity extension port for later tasks."""

        return self._correction_replay_identity

    def resolve_create_job_replay(
        self,
        *,
        scope_key: str,
        request_fingerprint: str,
        fresh_admission: FreshAttemptAdmissionPortV2,
    ) -> IdempotencyReplayDecisionV2:
        """Resolve the create-job idempotency decision for one request scope."""

        with self._records.scoped_lock(scope_key):
            existing_record = self._records.get_record(scope_key)
            if existing_record is None:
                fresh_job = fresh_admission.admit_fresh_attempt()
                self._records.record_fresh_attempt(
                    scope_key,
                    fingerprint=request_fingerprint,
                    active_job_id=fresh_job.job_id,
                )
                return _fresh_decision(fresh_job)

            if existing_record.fingerprint != request_fingerprint:
                raise IdempotencyReplayConflictV2

            existing_job = self._jobs.get_job_snapshot(existing_record.active_job_id)
            if existing_job is None:
                raise IdempotencyReplayActiveJobMissingV2

            if _is_retryable_failed_attempt(existing_job):
                return self._admit_service_reattempt(
                    scope_key=scope_key,
                    request_fingerprint=request_fingerprint,
                    existing_record=existing_record,
                    existing_job=existing_job,
                    fresh_admission=fresh_admission,
                    reason=IdempotencyReattemptReasonV2.RETRYABLE_FAILED_TERMINAL,
                )

            if existing_job.status == JobStatus.SUCCEEDED:
                compatibility = self._route_compatibility.evaluate_terminal_artifact_compatibility(
                    existing_job
                )
                if compatibility.status == RouteArtifactCompatibilityStatusV2.INCOMPATIBLE:
                    reason = (
                        compatibility.reason
                        or IdempotencyReattemptReasonV2.TERMINAL_ARTIFACT_CONTRACT_INCOMPATIBLE
                    )
                    return self._admit_service_reattempt(
                        scope_key=scope_key,
                        request_fingerprint=request_fingerprint,
                        existing_record=existing_record,
                        existing_job=existing_job,
                        fresh_admission=fresh_admission,
                        reason=reason,
                    )

            return _strict_replay_decision(record=existing_record, job=existing_job)

    def _admit_service_reattempt(
        self,
        *,
        scope_key: str,
        request_fingerprint: str,
        existing_record: IdempotencyRecordSnapshotV2,
        existing_job: IdempotencyJobSnapshotV2,
        fresh_admission: FreshAttemptAdmissionPortV2,
        reason: IdempotencyReattemptReasonV2,
    ) -> IdempotencyReplayDecisionV2:
        fresh_job = fresh_admission.admit_fresh_attempt()
        previous_attempt = _attempt_for_job(existing_job)
        self._records.record_service_reattempt(
            scope_key,
            fingerprint=request_fingerprint,
            active_job_id=fresh_job.job_id,
            previous_attempt=previous_attempt,
            existing_record=existing_record,
        )
        updated_record = self._records.get_record(scope_key)
        if updated_record is None:
            raise IdempotencyReplayRecordMissingAfterReattemptV2
        return _service_reattempt_decision(
            record=updated_record,
            current_job=fresh_job,
            reattempt_of_job=existing_job,
            reason=reason,
        )


def _is_retryable_failed_attempt(job: IdempotencyJobSnapshotV2) -> bool:
    return job.status == JobStatus.FAILED and job.failure_retryable is True


def _fresh_decision(job: IdempotencyJobSnapshotV2) -> IdempotencyReplayDecisionV2:
    return IdempotencyReplayDecisionV2(
        action=IdempotencyReplayActionV2.FRESH_ADMISSION,
        returned_job_id=job.job_id,
        idempotent_replay=False,
        active_job_id=job.job_id,
        attempt_count=1,
        current_attempt=_attempt_for_job(job),
        previous_attempts=(),
        replayed_job_id=None,
        reattempt_of_job_id=None,
        reason=None,
    )


def _strict_replay_decision(
    *,
    record: IdempotencyRecordSnapshotV2,
    job: IdempotencyJobSnapshotV2,
) -> IdempotencyReplayDecisionV2:
    return IdempotencyReplayDecisionV2(
        action=IdempotencyReplayActionV2.STRICT_REPLAY,
        returned_job_id=job.job_id,
        idempotent_replay=True,
        active_job_id=job.job_id,
        attempt_count=record.attempt_count,
        current_attempt=_attempt_for_job(job),
        previous_attempts=record.previous_attempts,
        replayed_job_id=job.job_id,
        reattempt_of_job_id=None,
        reason=None,
    )


def _service_reattempt_decision(
    *,
    record: IdempotencyRecordSnapshotV2,
    current_job: IdempotencyJobSnapshotV2,
    reattempt_of_job: IdempotencyJobSnapshotV2,
    reason: IdempotencyReattemptReasonV2,
) -> IdempotencyReplayDecisionV2:
    return IdempotencyReplayDecisionV2(
        action=IdempotencyReplayActionV2.SERVICE_REATTEMPT,
        returned_job_id=current_job.job_id,
        idempotent_replay=False,
        active_job_id=current_job.job_id,
        attempt_count=record.attempt_count,
        current_attempt=_attempt_for_job(current_job),
        previous_attempts=record.previous_attempts,
        replayed_job_id=None,
        reattempt_of_job_id=reattempt_of_job.job_id,
        reason=reason,
    )


def _attempt_for_job(job: IdempotencyJobSnapshotV2) -> IdempotencyAttemptSnapshotV2:
    failure_retryable = job.failure_retryable if job.status == JobStatus.FAILED else None
    return IdempotencyAttemptSnapshotV2(
        job_id=job.job_id,
        status=job.status,
        failure_retryable=failure_retryable,
    )
