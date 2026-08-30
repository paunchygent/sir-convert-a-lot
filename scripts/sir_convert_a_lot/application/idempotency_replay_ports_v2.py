"""Protocol ports for Service API v2 idempotent replay orchestration.

Purpose:
    Define application-layer ports for idempotency records, job lookup, fresh
    admission and route terminal-artifact compatibility.

Relationships:
    - Implemented by infrastructure adapters over filesystem idempotency state
      and v2 runtime jobs.
    - Consumed by `application.idempotency_replay_service_v2` to keep replay
      branching out of HTTP route helpers.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from scripts.sir_convert_a_lot.domain.idempotency_replay_policy_v2 import (
    IdempotencyAttemptSnapshotV2,
    IdempotencyJobSnapshotV2,
    IdempotencyRecordSnapshotV2,
    RouteArtifactCompatibilityDecisionV2,
    RouteArtifactCompatibilityStatusV2,
)


class IdempotencyRecordPortV2(Protocol):
    """Port for durable idempotency records and per-scope admission locks."""

    def scoped_lock(self, scope_key: str) -> AbstractContextManager[None]:
        """Return a lock context for one idempotency scope."""
        ...

    def get_record(self, scope_key: str) -> IdempotencyRecordSnapshotV2 | None:
        """Return current idempotency record for scope when present."""
        ...

    def record_fresh_attempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
    ) -> None:
        """Persist first admission for an idempotency scope."""
        ...

    def record_service_reattempt(
        self,
        scope_key: str,
        *,
        fingerprint: str,
        active_job_id: str,
        previous_attempt: IdempotencyAttemptSnapshotV2,
        existing_record: IdempotencyRecordSnapshotV2,
    ) -> None:
        """Point a scope at a fresh service-owned reattempt."""
        ...


class IdempotencyJobLookupPortV2(Protocol):
    """Port for resolving application-safe job snapshots."""

    def get_job_snapshot(self, job_id: str) -> IdempotencyJobSnapshotV2 | None:
        """Return a replay-policy snapshot for a stored job."""
        ...


class FreshAttemptAdmissionPortV2(Protocol):
    """Port for admitting a fresh Service API v2 job attempt."""

    def admit_fresh_attempt(self) -> IdempotencyJobSnapshotV2:
        """Create and return a fresh job snapshot."""
        ...


class RouteArtifactCompatibilityPortV2(Protocol):
    """Port for current-route terminal artifact compatibility checks."""

    def evaluate_terminal_artifact_compatibility(
        self, job: IdempotencyJobSnapshotV2
    ) -> RouteArtifactCompatibilityDecisionV2:
        """Return whether a terminal job is compatible for strict replay."""
        ...


class CompatibleRouteArtifactCompatibilityPortV2:
    """Neutral Task 375 route compatibility adapter."""

    def evaluate_terminal_artifact_compatibility(
        self, job: IdempotencyJobSnapshotV2
    ) -> RouteArtifactCompatibilityDecisionV2:
        """Treat every route/job as compatible until route contracts opt in."""

        del job
        return RouteArtifactCompatibilityDecisionV2(
            status=RouteArtifactCompatibilityStatusV2.COMPATIBLE,
            reason=None,
        )
