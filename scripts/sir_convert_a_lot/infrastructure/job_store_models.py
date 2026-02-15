"""Typed job-store models and exceptions for Sir Convert-a-Lot.

Purpose:
    Define durable job record data structures and explicit job-store exception
    types used by the filesystem-backed job store.

Relationships:
    - Used by `infrastructure.job_store` as the persistent model contract.
    - Used by `infrastructure.runtime_engine` via job-store APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus


@dataclass(frozen=True)
class StoredJobRecord:
    """Durable job record loaded from the filesystem journal."""

    job_id: str
    spec: JobSpec
    source_filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    raw_expires_at: datetime
    artifact_expires_at: datetime
    pinned: bool
    progress_stage: str
    pages_total: int | None
    pages_processed: int | None
    warnings: list[str]
    artifact_path: Path
    upload_path: Path
    artifact_sha256: str | None
    artifact_size_bytes: int | None
    backend_used: str | None
    acceleration_used: str | None
    ocr_enabled: bool | None
    options_fingerprint: str | None
    failure_code: str | None
    failure_message: str | None
    failure_retryable: bool
    failure_details: dict[str, object] | None

    @property
    def expires_at(self) -> datetime | None:
        return None if self.pinned else self.artifact_expires_at


@dataclass(frozen=True)
class JobMissing(Exception):
    """Raised when a job id does not exist in active or expired state."""

    job_id: str


@dataclass(frozen=True)
class JobExpired(Exception):
    """Raised when a job id was known but has passed retention visibility."""

    job_id: str


@dataclass
class JobStateConflict(Exception):
    """Raised when a state transition is invalid for the current job status."""

    job_id: str
    expected_statuses: tuple[JobStatus, ...]
    actual_status: JobStatus
