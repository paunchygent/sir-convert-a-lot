"""Typed runtime models for job orchestration.

Purpose:
    Centralize runtime dataclasses and time helpers so orchestration logic can
    stay focused on behavior rather than data-shape declarations.

Relationships:
    - Used by `infrastructure.runtime_engine` as primary runtime model types.
    - Used by `infrastructure.runtime_config` for environment-derived config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class ServiceConfig:
    """Runtime configuration values for Sir Convert-a-Lot service."""

    api_key: str
    data_root: Path
    max_upload_bytes: int = 50 * 1024 * 1024
    inline_max_bytes: int = 2 * 1024 * 1024
    idempotency_ttl_seconds: int = 24 * 3600
    upload_ttl_seconds: int = 24 * 3600
    result_ttl_seconds: int = 7 * 24 * 3600
    max_workers: int = 1
    supervisor_poll_seconds: float = 0.2
    enable_supervisor: bool = True
    gpu_available: bool = True
    allow_cpu_only: bool = False
    allow_cpu_fallback: bool = False
    processing_delay_seconds: float = 0.2
    heartbeat_interval_seconds: float = 5.0


@dataclass(frozen=True)
class ServiceRuntimeMetadata:
    """Runtime identity metadata used by liveness/readiness surfaces."""

    service_profile: str
    service_revision: str
    started_at: str
    data_root: Path


@dataclass
class ServiceError(Exception):
    """Structured service exception converted to standard error envelopes."""

    status_code: int
    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None = None


@dataclass
class StoredJob:
    """Internal mutable job state stored by the service runtime."""

    job_id: str
    spec: JobSpec
    source_filename: str
    upload_path: Path
    artifact_path: Path
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    progress_stage: str
    pages_total: int | None = None
    pages_processed: int | None = None
    last_heartbeat_at: datetime | None = None
    current_phase_started_at: datetime | None = None
    phase_timings_ms: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    artifact_sha256: str | None = None
    artifact_size_bytes: int | None = None
    backend_used: str | None = None
    acceleration_used: str | None = None
    ocr_enabled: bool | None = None
    options_fingerprint: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_retryable: bool = False
    failure_details: dict[str, object] | None = None
