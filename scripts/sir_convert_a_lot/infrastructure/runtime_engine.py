"""Sir Convert-a-Lot infrastructure runtime engine.

Purpose:
    Provide filesystem-backed job persistence, idempotency tracking, and
    asynchronous conversion execution for the conversion bounded context.

Relationships:
    - Consumed by `interfaces.http_api` as the service backend.
    - Uses `domain.specs` for domain rules and `application.contracts` metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    JobSpec,
    JobStatus,
)

CPU_UNLOCK_ENV_VARS: tuple[str, str] = (
    "SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY",
    "SIR_CONVERT_A_LOT_ALLOW_CPU_FALLBACK",
)


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
    gpu_available: bool = True
    # Test-only override for explicit CPU-only behavior checks.
    allow_cpu_only: bool = False
    # Test-only override for explicit GPU fallback behavior checks.
    allow_cpu_fallback: bool = False
    processing_delay_seconds: float = 0.2


@dataclass(frozen=True)
class ServiceError(Exception):
    """Structured service exception converted to standard error envelopes."""

    status_code: int
    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class IdempotencyRecord:
    """Idempotency map record for create-job replay and collision behavior."""

    fingerprint: str
    job_id: str
    created_at: datetime


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
    warnings: list[str] = field(default_factory=list)
    artifact_sha256: str | None = None
    artifact_size_bytes: int | None = None
    backend_used: str | None = None
    acceleration_used: str | None = None
    options_fingerprint: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_retryable: bool = False
    failure_details: dict[str, object] | None = None


class ServiceRuntime:
    """Thread-safe runtime state and execution for Sir Convert-a-Lot jobs."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.uploads_dir = config.data_root / "uploads"
        self.artifacts_dir = config.data_root / "artifacts"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self._jobs: dict[str, StoredJob] = {}
        self._idempotency: dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def _new_job_id(self) -> str:
        return f"job_{uuid4().hex[:26]}"

    def _is_expired(self, job: StoredJob, now: datetime) -> bool:
        return job.expires_at is not None and now > job.expires_at

    def get_job(self, job_id: str) -> StoredJob | None:
        now = utc_now()
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if self._is_expired(job, now):
                self._jobs.pop(job_id, None)
                return None
            return job

    def get_idempotency(self, scope_key: str) -> IdempotencyRecord | None:
        now = utc_now()
        with self._lock:
            record = self._idempotency.get(scope_key)
            if record is None:
                return None
            record_ttl = timedelta(seconds=self.config.idempotency_ttl_seconds)
            if now - record.created_at > record_ttl:
                self._idempotency.pop(scope_key, None)
                return None
            return record

    def put_idempotency(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        with self._lock:
            self._idempotency[scope_key] = IdempotencyRecord(
                fingerprint=fingerprint,
                job_id=job_id,
                created_at=utc_now(),
            )

    def create_job(self, spec: JobSpec, upload_bytes: bytes, source_filename: str) -> StoredJob:
        now = utc_now()
        job_id = self._new_job_id()
        upload_path = self.uploads_dir / f"{job_id}.pdf"
        artifact_path = self.artifacts_dir / f"{job_id}.md"
        upload_path.write_bytes(upload_bytes)

        expires_at: datetime | None
        if spec.retention.pin:
            expires_at = None
        else:
            expires_at = now + timedelta(seconds=self.config.result_ttl_seconds)

        job = StoredJob(
            job_id=job_id,
            spec=spec,
            source_filename=source_filename,
            upload_path=upload_path,
            artifact_path=artifact_path,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            progress_stage="queued",
        )

        with self._lock:
            self._jobs[job_id] = job

        return job

    def _set_job_status(
        self,
        job_id: str,
        status: JobStatus,
        stage: str,
        *,
        pages_processed: int | None = None,
        pages_total: int | None = None,
    ) -> StoredJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.status = status
            job.progress_stage = stage
            job.updated_at = utc_now()
            if pages_processed is not None:
                job.pages_processed = pages_processed
            if pages_total is not None:
                job.pages_total = pages_total
            return job

    def cancel_job(
        self, job_id: str
    ) -> Literal["missing", "accepted", "already_canceled", "conflict"]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return "missing"
            if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                job.status = JobStatus.CANCELED
                job.progress_stage = "canceled"
                job.updated_at = utc_now()
                return "accepted"
            if job.status == JobStatus.CANCELED:
                return "already_canceled"
            return "conflict"

    def validate_acceleration_policy(self, spec: JobSpec) -> None:
        """Enforce GPU-first rollout policy constraints."""
        policy = spec.execution.acceleration_policy

        if policy == AccelerationPolicy.CPU_ONLY and not self.config.allow_cpu_only:
            raise ServiceError(
                status_code=503,
                code="gpu_not_available",
                message=(
                    "CPU-only execution is disabled during GPU-first rollout. "
                    "Retry when GPU execution is available."
                ),
                retryable=True,
            )

        if self.config.gpu_available:
            return

        if policy in {AccelerationPolicy.GPU_REQUIRED, AccelerationPolicy.GPU_PREFER}:
            if not self.config.allow_cpu_fallback:
                raise ServiceError(
                    status_code=503,
                    code="gpu_not_available",
                    message="GPU execution is required and no fallback is currently allowed.",
                    retryable=True,
                )

    def _execute_conversion(self, job: StoredJob) -> tuple[str, ConversionMetadata, list[str]]:
        self.validate_acceleration_policy(job.spec)

        file_bytes = job.upload_path.read_bytes()
        if not file_bytes.startswith(b"%PDF"):
            raise ServiceError(
                status_code=422,
                code="pdf_unreadable",
                message="Uploaded file is not a readable PDF.",
                retryable=False,
            )

        backend_used = (
            "docling"
            if job.spec.conversion.backend_strategy.value == "auto"
            else job.spec.conversion.backend_strategy.value
        )
        acceleration_used = "cuda" if self.config.gpu_available else "cpu"
        options_fingerprint = hashlib.sha256(
            json.dumps(
                job.spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()

        title = Path(job.source_filename).stem.replace("_", " ").replace("-", " ").strip()
        markdown_content = (
            f"# {title or 'Document'}\n\n"
            "Converted by Sir Convert-a-Lot.\n\n"
            f"- source: {job.source_filename}\n"
            f"- backend: {backend_used}\n"
            f"- acceleration: {acceleration_used}\n"
            f"- ocr_mode: {job.spec.conversion.ocr_mode.value}\n"
            f"- table_mode: {job.spec.conversion.table_mode.value}\n"
        )

        metadata = ConversionMetadata(
            backend_used=backend_used,
            acceleration_used=acceleration_used,
            ocr_enabled=job.spec.conversion.ocr_mode.value != "off",
            table_mode=job.spec.conversion.table_mode,
            options_fingerprint=f"sha256:{options_fingerprint}",
        )
        return markdown_content, metadata, []

    def run_job_async(self, job_id: str) -> None:
        """Run a conversion job asynchronously in a background thread."""
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()

    def _run_job(self, job_id: str) -> None:
        job = self._set_job_status(job_id, JobStatus.RUNNING, "starting")
        if job is None:
            return

        time.sleep(self.config.processing_delay_seconds)

        job = self.get_job(job_id)
        if job is None:
            return
        if job.status == JobStatus.CANCELED:
            return

        self._set_job_status(
            job_id, JobStatus.RUNNING, "converting", pages_processed=1, pages_total=1
        )

        try:
            markdown_content, metadata, warnings = self._execute_conversion(job)
            artifact_bytes = markdown_content.encode("utf-8")
            job.artifact_path.write_bytes(artifact_bytes)
            artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()

            with self._lock:
                stored = self._jobs.get(job_id)
                if stored is None:
                    return
                if stored.status == JobStatus.CANCELED:
                    return
                stored.status = JobStatus.SUCCEEDED
                stored.progress_stage = "completed"
                stored.updated_at = utc_now()
                stored.backend_used = metadata.backend_used
                stored.acceleration_used = metadata.acceleration_used
                stored.options_fingerprint = metadata.options_fingerprint
                stored.artifact_sha256 = artifact_sha
                stored.artifact_size_bytes = len(artifact_bytes)
                stored.warnings = warnings
        except ServiceError as exc:
            with self._lock:
                stored = self._jobs.get(job_id)
                if stored is None:
                    return
                stored.status = JobStatus.FAILED
                stored.progress_stage = "failed"
                stored.updated_at = utc_now()
                stored.failure_code = exc.code
                stored.failure_message = exc.message
                stored.failure_retryable = exc.retryable
                stored.failure_details = exc.details
        except Exception as exc:  # pragma: no cover - defensive fallback
            with self._lock:
                stored = self._jobs.get(job_id)
                if stored is None:
                    return
                stored.status = JobStatus.FAILED
                stored.progress_stage = "failed"
                stored.updated_at = utc_now()
                stored.failure_code = "conversion_internal_error"
                stored.failure_message = f"Unexpected conversion error: {exc}"
                stored.failure_retryable = True


def fingerprint_for_request(spec_payload: dict[str, object], file_sha256: str) -> str:
    """Create deterministic idempotency fingerprint for a create-job request."""
    normalized = json.dumps(spec_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{normalized}:{file_sha256}".encode("utf-8")).hexdigest()


def service_config_from_env() -> ServiceConfig:
    """Load service configuration from environment variables."""
    api_key = os.getenv("SIR_CONVERT_A_LOT_API_KEY", "dev-only-key")
    data_root = Path(os.getenv("SIR_CONVERT_A_LOT_DATA_DIR", "build/sir_convert_a_lot"))
    gpu_available = os.getenv("SIR_CONVERT_A_LOT_GPU_AVAILABLE", "1") == "1"

    enabled_unlock_envs = [name for name in CPU_UNLOCK_ENV_VARS if os.getenv(name) == "1"]
    if enabled_unlock_envs:
        joined_names = ", ".join(enabled_unlock_envs)
        raise ValueError(
            "CPU unlock env vars are disabled during GPU-first rollout lock: "
            f"{joined_names}. Use explicit ServiceConfig test overrides instead."
        )

    return ServiceConfig(
        api_key=api_key,
        data_root=data_root,
        gpu_available=gpu_available,
    )
