"""HTTP adapter for Service API v2 create-job idempotency decisions.

Purpose:
    Map protocol-first application replay decisions into Service API v2 HTTP
    response metadata and errors.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2` before dispatching v2 jobs.
    - Delegates replay branching to
      `application.idempotency_replay_service_v2`.
    - Adapts filesystem/runtime details through infrastructure replay ports.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    IdempotencyAttemptMetadataV2,
    IdempotencyMetadataV2,
)
from scripts.sir_convert_a_lot.application.idempotency_replay_service_v2 import (
    IdempotencyReplayActiveJobMissingV2,
    IdempotencyReplayConflictV2,
    IdempotencyReplayRecordMissingAfterReattemptV2,
    IdempotencyReplayServiceV2,
)
from scripts.sir_convert_a_lot.domain.idempotency_replay_policy_v2 import (
    IdempotencyAttemptSnapshotV2,
    IdempotencyReplayDecisionV2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.idempotency_replay_adapters_v2 import (
    FreshAttemptAdmissionAdapterV2,
    IdempotencyStoreRecordAdapterV2,
    RuntimeJobLookupAdapterV2,
)
from scripts.sir_convert_a_lot.infrastructure.idempotency_store import (
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
    fresh_admission = FreshAttemptAdmissionAdapterV2(create_job=create_job)
    service = IdempotencyReplayServiceV2(
        records=IdempotencyStoreRecordAdapterV2(store),
        jobs=RuntimeJobLookupAdapterV2(get_job),
    )
    try:
        decision = service.resolve_create_job_replay(
            scope_key=scope_key,
            request_fingerprint=request_fingerprint,
            fresh_admission=fresh_admission,
        )
    except IdempotencyReplayConflictV2 as exc:
        raise ServiceError(
            status_code=409,
            code="idempotency_key_reused_with_different_payload",
            message=(
                "Idempotency-Key was already used with a different request payload "
                "within the idempotency window."
            ),
            retryable=False,
        ) from exc
    except IdempotencyReplayActiveJobMissingV2 as exc:
        raise ServiceError(
            status_code=404,
            code="job_not_found",
            message="Idempotent job no longer exists.",
            retryable=False,
        ) from exc
    except IdempotencyReplayRecordMissingAfterReattemptV2 as exc:
        raise ServiceError(
            status_code=500,
            code="idempotency_record_missing_after_reattempt",
            message="Idempotency record disappeared after reattempt admission.",
            retryable=True,
        ) from exc

    job = _returned_job_for_decision(
        decision=decision,
        admitted_job=fresh_admission.admitted_job,
        get_job=get_job,
    )
    return CreateJobIdempotencyDecisionV2(
        job=job,
        metadata=_metadata_for_decision(decision),
        idempotent_replay_header=decision.idempotent_replay,
    )


def idempotency_metadata_with_current_job_v2(
    *,
    metadata: IdempotencyMetadataV2,
    current_job: StoredJobV2,
) -> IdempotencyMetadataV2:
    """Return metadata updated to the job state used in the response body."""
    return metadata.model_copy(update={"current_attempt": _attempt_metadata_for_job(current_job)})


def _returned_job_for_decision(
    *,
    decision: IdempotencyReplayDecisionV2,
    admitted_job: StoredJobV2 | None,
    get_job: Callable[[str], StoredJobV2 | None],
) -> StoredJobV2:
    if admitted_job is not None and admitted_job.job_id == decision.returned_job_id:
        return admitted_job
    job = get_job(decision.returned_job_id)
    if job is None:
        raise ServiceError(
            status_code=404,
            code="job_not_found",
            message="Idempotent job no longer exists.",
            retryable=False,
        )
    return job


def _metadata_for_decision(decision: IdempotencyReplayDecisionV2) -> IdempotencyMetadataV2:
    return IdempotencyMetadataV2(
        state=decision.action.value,
        idempotent_replay=decision.idempotent_replay,
        active_job_id=decision.active_job_id,
        attempt_count=decision.attempt_count,
        current_attempt=_attempt_metadata_for_snapshot(decision.current_attempt),
        previous_attempts=[
            _attempt_metadata_for_snapshot(attempt) for attempt in decision.previous_attempts
        ],
        replayed_job_id=decision.replayed_job_id,
        reattempt_of_job_id=decision.reattempt_of_job_id,
        reason=decision.reason,
    )


def _attempt_metadata_for_job(job: StoredJobV2) -> IdempotencyAttemptMetadataV2:
    failure_retryable = job.failure_retryable if job.status == JobStatus.FAILED else None
    return IdempotencyAttemptMetadataV2(
        job_id=job.job_id,
        status=job.status,
        failure_retryable=failure_retryable,
    )


def _attempt_metadata_for_snapshot(
    attempt: IdempotencyAttemptSnapshotV2,
) -> IdempotencyAttemptMetadataV2:
    return IdempotencyAttemptMetadataV2(
        job_id=attempt.job_id,
        status=attempt.status,
        failure_retryable=attempt.failure_retryable,
    )
