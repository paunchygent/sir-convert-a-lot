"""Typed models for the Sir Convert-a-Lot HTTP client (service API v2).

Purpose:
    Keep the main v2 HTTP client implementation lean by isolating stable public
    dataclasses and type aliases used by callers (CLI, integration adapters,
    tests).

Relationships:
    - Imported by `interfaces.http_client_v2`.
    - Imported by CLI and integration adapters that consume v2 client outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Literal, TypeAlias

from scripts.sir_convert_a_lot.domain.specs import JobStatus

RequestFileValue: TypeAlias = tuple[str, IO[bytes] | bytes | str, str]

RetryModeV2: TypeAlias = Literal["auto", "replay_only", "new_job"]


@dataclass
class ClientErrorV2(Exception):
    """HTTP/service-level error returned by Sir Convert-a-Lot v2 endpoints."""

    code: str
    message: str
    retryable: bool
    status_code: int
    job_id: str | None = None
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class SubmittedJobV2:
    """Job state returned immediately after v2 job creation."""

    job_id: str
    status: JobStatus
    idempotent_replay: bool = False


@dataclass(frozen=True)
class ArtifactOutcomeV2:
    """Successful artifact outcome returned by v2 client operations."""

    job_id: str
    status: Literal[JobStatus.SUCCEEDED]
    artifact_bytes: bytes
    rerun_of_job_id: str | None = None
    formula_authority: dict[str, object] = field(default_factory=dict)
