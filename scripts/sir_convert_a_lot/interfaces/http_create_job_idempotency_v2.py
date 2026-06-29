"""Create-job idempotency policy for Service API v2.

Purpose:
    Centralize HTTP create-job idempotency admission decisions for strict
    replay, fresh admission, and service-owned reattempts after retryable
    terminal failures.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2` before dispatching v2 jobs.
    - Persists auditable attempt lineage through `infrastructure.idempotency_store`.
    - Builds public metadata models from `application.contracts_v2`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    IdempotencyAttemptMetadataV2,
    IdempotencyMetadataV2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import utc_now
from scripts.sir_convert_a_lot.infrastructure.idempotency_store import (
    IdempotencyAttemptRecord,
    IdempotencyRecord,
    IdempotencyStore,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class CreateJobIdempotencyDecisionV2:
    """Resolved create-job idempotency decision and returned job."""

    job: StoredJobV2
    metadata: IdempotencyMetadataV2
    idempotent_replay_header: bool


def admit_create_job_with_idempotency_v2(
    *,
    store: IdempotencyStore,
    scope_key: str,
    request_fingerprint: str,
    get_job: Callable[[str], StoredJobV2 | None],
    create_job: Callable[[], StoredJobV2],
) -> CreateJobIdempotencyDecisionV2:
    """Resolve one v2 create-job request under its idempotency scope lock."""
    with store.scoped_lock(scope_key):
        existing_record = store.get(scope_key)
        if existing_record is None:
            fresh_job = create_job()
            store.put(scope_key, request_fingerprint, fresh_job.job_id)
            return CreateJobIdempotencyDecisionV2(
                job=fresh_job,
                metadata=_metadata_for_fresh_admission(fresh_job),
                idempotent_replay_header=False,
            )

        if existing_record.fingerprint != request_fingerprint:
            raise ServiceError(
                status_code=409,
                code="idempotency_key_reused_with_different_payload",
                message=(
                    "Idempotency-Key was already used with a different request payload "
                    "within the idempotency window."
                ),
                retryable=False,
            )

        existing_job = get_job(existing_record.job_id)
        if existing_job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Idempotent job no longer exists.",
                retryable=False,
            )

        if _is_retryable_failed_attempt(existing_job):
            reattempt = create_job()
            store.put_reattempt(
                scope_key,
                fingerprint=request_fingerprint,
                active_job_id=reattempt.job_id,
                previous_attempt=_lineage_record_for_job(existing_job),
                created_at=existing_record.created_at,
                existing_previous_attempts=existing_record.previous_attempts,
            )
            updated_record = store.get(scope_key)
            if updated_record is None:
                raise ServiceError(
                    status_code=500,
                    code="idempotency_record_missing_after_reattempt",
                    message="Idempotency record disappeared after reattempt admission.",
                    retryable=True,
                )
            return CreateJobIdempotencyDecisionV2(
                job=reattempt,
                metadata=_metadata_for_service_reattempt(
                    record=updated_record,
                    current_job=reattempt,
                    reattempt_of_job=existing_job,
                ),
                idempotent_replay_header=False,
            )

        return CreateJobIdempotencyDecisionV2(
            job=existing_job,
            metadata=_metadata_for_strict_replay(
                record=existing_record,
                current_job=existing_job,
            ),
            idempotent_replay_header=True,
        )


def idempotency_metadata_with_current_job_v2(
    *,
    metadata: IdempotencyMetadataV2,
    current_job: StoredJobV2,
) -> IdempotencyMetadataV2:
    """Return metadata updated to the job state used in the response body."""
    return metadata.model_copy(update={"current_attempt": _attempt_metadata_for_job(current_job)})


def _is_retryable_failed_attempt(job: StoredJobV2) -> bool:
    return job.status == JobStatus.FAILED and job.failure_retryable


def _metadata_for_fresh_admission(job: StoredJobV2) -> IdempotencyMetadataV2:
    return IdempotencyMetadataV2(
        state="fresh_admission",
        idempotent_replay=False,
        active_job_id=job.job_id,
        attempt_count=1,
        current_attempt=_attempt_metadata_for_job(job),
        previous_attempts=[],
        replayed_job_id=None,
        reattempt_of_job_id=None,
    )


def _metadata_for_strict_replay(
    *,
    record: IdempotencyRecord,
    current_job: StoredJobV2,
) -> IdempotencyMetadataV2:
    return IdempotencyMetadataV2(
        state="strict_replay",
        idempotent_replay=True,
        active_job_id=current_job.job_id,
        attempt_count=record.attempt_count,
        current_attempt=_attempt_metadata_for_job(current_job),
        previous_attempts=_attempt_metadata_for_records(record.previous_attempts),
        replayed_job_id=current_job.job_id,
        reattempt_of_job_id=None,
    )


def _metadata_for_service_reattempt(
    *,
    record: IdempotencyRecord,
    current_job: StoredJobV2,
    reattempt_of_job: StoredJobV2,
) -> IdempotencyMetadataV2:
    return IdempotencyMetadataV2(
        state="service_reattempt",
        idempotent_replay=False,
        active_job_id=current_job.job_id,
        attempt_count=record.attempt_count,
        current_attempt=_attempt_metadata_for_job(current_job),
        previous_attempts=_attempt_metadata_for_records(record.previous_attempts),
        replayed_job_id=None,
        reattempt_of_job_id=reattempt_of_job.job_id,
    )


def _attempt_metadata_for_job(job: StoredJobV2) -> IdempotencyAttemptMetadataV2:
    failure_retryable = job.failure_retryable if job.status == JobStatus.FAILED else None
    return IdempotencyAttemptMetadataV2(
        job_id=job.job_id,
        status=job.status,
        failure_retryable=failure_retryable,
    )


def _attempt_metadata_for_records(
    attempts: tuple[IdempotencyAttemptRecord, ...],
) -> list[IdempotencyAttemptMetadataV2]:
    metadata: list[IdempotencyAttemptMetadataV2] = []
    for attempt in attempts:
        status = JobStatus(attempt.status) if attempt.status is not None else JobStatus.FAILED
        metadata.append(
            IdempotencyAttemptMetadataV2(
                job_id=attempt.job_id,
                status=status,
                failure_retryable=attempt.failure_retryable,
            )
        )
    return metadata


def _lineage_record_for_job(job: StoredJobV2) -> IdempotencyAttemptRecord:
    return IdempotencyAttemptRecord(
        job_id=job.job_id,
        status=job.status.value,
        failure_retryable=job.failure_retryable if job.status == JobStatus.FAILED else None,
        superseded_at=utc_now(),
    )
