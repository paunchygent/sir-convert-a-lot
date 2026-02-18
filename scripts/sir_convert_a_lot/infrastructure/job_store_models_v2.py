"""Typed job-store models and exceptions for Sir Convert-a-Lot service API v2.

Purpose:
    Define durable v2 job record data structures and explicit job-store
    exception types used by the filesystem-backed v2 job store.

Relationships:
    - Used by `infrastructure.job_store_v2` as the persistent model contract.
    - Used by `infrastructure.runtime_engine_v2` via job-store APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2


@dataclass(frozen=True)
class StoredJobRecordV2:
    """Durable v2 job record loaded from the filesystem journal."""

    job_id: str
    spec: JobSpecV2
    source_filename: str
    source_format: SourceFormatV2
    output_format: OutputFormatV2
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    raw_expires_at: datetime
    artifact_expires_at: datetime
    pinned: bool
    progress_stage: str
    last_heartbeat_at: datetime | None
    current_phase_started_at: datetime | None
    phase_timings_ms: dict[str, int]
    warnings: list[str]
    upload_path: Path
    resources_zip_path: Path | None
    reference_docx_path: Path | None
    artifact_path: Path
    artifact_sha256: str | None
    artifact_size_bytes: int | None
    pipeline_used: str | None
    backend_used: str | None
    acceleration_used: str | None
    options_fingerprint: str | None
    failure_code: str | None
    failure_message: str | None
    failure_retryable: bool
    failure_details: dict[str, object] | None

    @property
    def expires_at(self) -> datetime | None:
        return None if self.pinned else self.artifact_expires_at


@dataclass(frozen=True)
class JobMissingV2(Exception):
    """Raised when a v2 job id does not exist in active or expired state."""

    job_id: str


@dataclass(frozen=True)
class JobExpiredV2(Exception):
    """Raised when a v2 job id was known but has passed retention visibility."""

    job_id: str


@dataclass
class JobStateConflictV2(Exception):
    """Raised when a v2 state transition is invalid for the current job status."""

    job_id: str
    expected_statuses: tuple[JobStatus, ...]
    actual_status: JobStatus
