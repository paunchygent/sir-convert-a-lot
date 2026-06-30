"""Domain decisions for Service API v2 idempotent replay policy.

Purpose:
    Define product-neutral replay actions, attempt snapshots, lineage, typed
    reattempt reasons, and extension decisions for Service API v2 create-job
    idempotency.

Relationships:
    - Consumed by `application.idempotency_replay_service_v2` to orchestrate
      replay policy without HTTP, Pydantic, filesystem, or runtime imports.
    - Mapped by interface adapters into public Service API v2 response
      metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from scripts.sir_convert_a_lot.domain.specs import JobStatus


class IdempotencyReplayActionV2(StrEnum):
    """Create-job idempotency action selected for a request."""

    FRESH_ADMISSION = "fresh_admission"
    STRICT_REPLAY = "strict_replay"
    SERVICE_REATTEMPT = "service_reattempt"


class IdempotencyReattemptReasonV2(StrEnum):
    """Typed reason for service-owned reattempt admission."""

    RETRYABLE_FAILED_TERMINAL = "retryable_failed_terminal"
    TERMINAL_ARTIFACT_CONTRACT_INCOMPATIBLE = "terminal_artifact_contract_incompatible"


class RouteArtifactCompatibilityStatusV2(StrEnum):
    """Terminal artifact compatibility status for strict replay."""

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class IdempotencyAttemptSnapshotV2:
    """Sanitized attempt state retained in idempotency lineage."""

    job_id: str
    status: JobStatus
    failure_retryable: bool | None
    superseded_at: datetime | None = None


@dataclass(frozen=True)
class IdempotencyJobSnapshotV2:
    """Application-safe job state needed for replay decisions."""

    job_id: str
    status: JobStatus
    failure_retryable: bool | None


@dataclass(frozen=True)
class IdempotencyRecordSnapshotV2:
    """Application-safe idempotency record state for one request scope."""

    fingerprint: str
    active_job_id: str
    created_at: datetime
    attempt_count: int
    previous_attempts: tuple[IdempotencyAttemptSnapshotV2, ...]


@dataclass(frozen=True)
class RouteArtifactCompatibilityDecisionV2:
    """Compatibility decision for terminal strict replay."""

    status: RouteArtifactCompatibilityStatusV2
    reason: IdempotencyReattemptReasonV2 | None = None


@dataclass(frozen=True)
class CorrectionReplayIdentityRequestV2:
    """Neutral correction replay identity request for future artifact-set stores."""

    parent_job_id: str
    request_id: str
    source_binding_digest: str
    source_state_sha256: str
    correction_payload_digest: str
    target_set_digest: str
    replay_profile_version: str


@dataclass(frozen=True)
class CorrectionReplayIdentityReservationV2:
    """Neutral correction replay artifact-set reservation result."""

    artifact_set_id: str
    duplicate_request: bool


@dataclass(frozen=True)
class IdempotencyReplayDecisionV2:
    """Resolved create-job idempotency decision."""

    action: IdempotencyReplayActionV2
    returned_job_id: str
    idempotent_replay: bool
    active_job_id: str
    attempt_count: int
    current_attempt: IdempotencyAttemptSnapshotV2
    previous_attempts: tuple[IdempotencyAttemptSnapshotV2, ...]
    replayed_job_id: str | None
    reattempt_of_job_id: str | None
    reason: IdempotencyReattemptReasonV2 | None
