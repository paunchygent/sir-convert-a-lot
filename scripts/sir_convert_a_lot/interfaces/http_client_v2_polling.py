"""Polling helpers for the Sir Convert-a-Lot service API v2 client.

Purpose:
    Keep polling timeout classification logic modular and shared, so the main v2
    HTTP client stays below the 500 LoC guardrail while enforcing ADR-0005
    semantics (poll-window exceeded vs stall timeout).

Relationships:
    - Called by `scripts.sir_convert_a_lot.interfaces.http_client_v2`.
    - Uses activity inference helpers in `interfaces.http_client_activity`.
    - Raises `ClientErrorV2` from `interfaces.http_client_v2_models`.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client_activity import most_recent_activity_at
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ClientErrorV2,
    SubmittedJobV2,
)


class JobPollerV2(Protocol):
    """Minimal protocol required to poll and classify v2 job status timeouts."""

    def get_job_status(self, job_id: str, *, correlation_id: str | None = None) -> JobStatus: ...

    def get_job_payload(
        self, job_id: str, *, correlation_id: str | None = None
    ) -> dict[str, object]: ...

    def _read_job_status(self, payload: object) -> SubmittedJobV2: ...


def wait_for_terminal_status_v2(
    *,
    poller: JobPollerV2,
    job_id: str,
    timeout_seconds: float,
    stall_timeout_seconds: float,
    poll_interval_seconds: float,
    correlation_id: str | None,
) -> JobStatus:
    """Poll v2 job status until terminal status or classified timeout."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = poller.get_job_status(job_id, correlation_id=correlation_id)
        if status in TERMINAL_JOB_STATUSES:
            return status
        time.sleep(poll_interval_seconds)

    payload = poller.get_job_payload(job_id, correlation_id=correlation_id)
    status = poller._read_job_status(payload).status
    if status in TERMINAL_JOB_STATUSES:
        return status

    activity_at = most_recent_activity_at(payload)
    if activity_at is None:
        raise ClientErrorV2(
            code="job_poll_window_exceeded",
            message=(
                "Max poll window exceeded while job is still running "
                "(activity timestamp unavailable in payload)."
            ),
            retryable=True,
            status_code=202,
            job_id=job_id,
            details={"timeout_seconds": timeout_seconds},
        )

    now = datetime.now(UTC)
    seconds_since_activity = max(0.0, (now - activity_at).total_seconds())
    if seconds_since_activity <= stall_timeout_seconds:
        raise ClientErrorV2(
            code="job_poll_window_exceeded",
            message=(
                "Max poll window exceeded while job is still running "
                "(heartbeat/progress remains fresh)."
            ),
            retryable=True,
            status_code=202,
            job_id=job_id,
            details={
                "timeout_seconds": timeout_seconds,
                "stall_timeout_seconds": stall_timeout_seconds,
                "seconds_since_activity": seconds_since_activity,
            },
        )

    raise ClientErrorV2(
        code="job_timeout",
        message=(
            "Timed out waiting for conversion job to reach a terminal state "
            "and job activity appears stale (likely stalled)."
        ),
        retryable=True,
        status_code=408,
        job_id=job_id,
        details={
            "timeout_seconds": timeout_seconds,
            "stall_timeout_seconds": stall_timeout_seconds,
            "seconds_since_activity": seconds_since_activity,
        },
    )
