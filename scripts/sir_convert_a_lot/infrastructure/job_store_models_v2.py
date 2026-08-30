"""Typed job-store models and exceptions for Sir Convert-a-Lot service API v2.

Purpose:
    Define durable v2 job record data structures and explicit job-store
    exception types used by the filesystem-backed v2 job store.

Relationships:
    - Used by `infrastructure.job_store_v2` as the persistent model contract.
    - Used by `infrastructure.runtime_engine_v2` via job-store APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    TerminalArtifactObjectRef,
)


@dataclass(frozen=True)
class StoredJobRecordV2:
    """Durable v2 job record loaded from the filesystem journal."""

    job_id: str
    spec: JobSpecV2
    owner_api_key_scope: str
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
    total_pages: int | None
    processed_pages: int | None
    failed_pages: int | None
    percent_complete: float | None
    pages_per_minute: float | None
    eta_seconds: int | None
    audio_total_media_seconds: float | None
    audio_processed_media_seconds: float | None
    audio_percent_complete: float | None
    audio_current_chunk_index: int | None
    audio_total_chunks: int | None
    audio_pipeline_percent_complete: float | None
    audio_pipeline_eta_seconds: int | None
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
    ocr_enabled: bool | None
    ocr_engine_used: str | None
    ocr_languages_used: list[str] | None
    acceleration_policy_requested: str | None
    gpu_runtime_kind: str | None
    gpu_device_count: int | None
    gpu_busy_percent: int | None
    gpu_memory_used_percent: int | None
    options_fingerprint: str | None
    template_id: str | None
    template_version: str | None
    template_artifact_sha256: str | None
    parallel_enabled: bool | None
    max_chunk_workers: int | None
    chunk_size_pages: int | None
    effective_gpu_stage_limit: int | None
    scheduling_mode: str | None
    formula_authority: dict[str, object]
    failure_code: str | None
    failure_message: str | None
    failure_retryable: bool
    failure_details: dict[str, object] | None
    terminal_artifact_object_refs: dict[str, TerminalArtifactObjectRef] = field(
        default_factory=dict
    )

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
