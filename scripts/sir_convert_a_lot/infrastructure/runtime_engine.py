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
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    JobSpec,
    JobStatus,
)
from scripts.sir_convert_a_lot.infrastructure.job_store import (
    IdempotencyStore,
    JobExpired,
    JobMissing,
    JobStore,
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
    max_workers: int = 1
    supervisor_poll_seconds: float = 0.2
    enable_supervisor: bool = True
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
        self.job_store = JobStore(
            data_root=config.data_root,
            raw_ttl_seconds=config.upload_ttl_seconds,
            artifact_ttl_seconds=config.result_ttl_seconds,
        )
        self.idempotency_store = IdempotencyStore(
            data_root=config.data_root,
            ttl_seconds=config.idempotency_ttl_seconds,
        )
        self._lock = threading.Lock()
        self._active_job_ids: set[str] = set()

        self.job_store.sweep_expired()
        self.job_store.recover_running_jobs_to_queued(active_job_ids=self._active_job_ids)

        if self.config.enable_supervisor:
            thread = threading.Thread(target=self._supervisor_loop, daemon=True)
            thread.start()

    def _supervisor_loop(self) -> None:
        """Background supervisor that runs queued jobs and re-runs recovered jobs."""
        while True:
            try:
                self.job_store.sweep_expired()
                self.job_store.recover_running_jobs_to_queued(active_job_ids=self._active_job_ids)

                with self._lock:
                    active_count = len(self._active_job_ids)
                    max_workers = max(1, self.config.max_workers)
                if active_count < max_workers:
                    for job_id in self.job_store.list_job_ids():
                        with self._lock:
                            if len(self._active_job_ids) >= max_workers:
                                break
                            if job_id in self._active_job_ids:
                                continue
                        try:
                            record = self.job_store.get_job(job_id)
                        except (JobMissing, JobExpired):
                            continue
                        if record.status != JobStatus.QUEUED:
                            continue
                        self.run_job_async(job_id)
            except Exception:
                # Defensive: keep supervisor alive.
                pass

            time.sleep(max(0.05, self.config.supervisor_poll_seconds))

    def _new_job_id(self) -> str:
        return f"job_{uuid4().hex[:26]}"

    def get_job(self, job_id: str) -> StoredJob | None:
        self.job_store.sweep_expired()
        try:
            record = self.job_store.get_job(job_id)
        except JobExpired as exc:
            raise ServiceError(
                status_code=404,
                code="job_expired",
                message="Job has expired and is no longer available.",
                retryable=False,
                details={"job_id": exc.job_id},
            ) from exc
        except JobMissing:
            return None

        return StoredJob(
            job_id=record.job_id,
            spec=record.spec,
            source_filename=record.source_filename,
            upload_path=record.upload_path,
            artifact_path=record.artifact_path,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            expires_at=record.expires_at,
            progress_stage=record.progress_stage,
            pages_total=record.pages_total,
            pages_processed=record.pages_processed,
            warnings=list(record.warnings),
            artifact_sha256=record.artifact_sha256,
            artifact_size_bytes=record.artifact_size_bytes,
            backend_used=record.backend_used,
            acceleration_used=record.acceleration_used,
            options_fingerprint=record.options_fingerprint,
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            failure_retryable=record.failure_retryable,
            failure_details=record.failure_details,
        )

    def get_idempotency(self, scope_key: str):
        return self.idempotency_store.get(scope_key)

    def put_idempotency(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        self.idempotency_store.put(scope_key, fingerprint, job_id)

    def create_job(self, spec: JobSpec, upload_bytes: bytes, source_filename: str) -> StoredJob:
        job_id = self._new_job_id()
        record = self.job_store.create_job(
            job_id=job_id,
            spec=spec,
            source_filename=source_filename,
            upload_bytes=upload_bytes,
        )
        stored = self.get_job(record.job_id)
        if stored is None:
            raise RuntimeError("created job must be loadable immediately")
        return stored

    def _set_job_status(
        self,
        job_id: str,
        status: JobStatus,
        stage: str,
        *,
        pages_processed: int | None = None,
        pages_total: int | None = None,
    ) -> StoredJob | None:
        try:
            record = self.job_store.update_progress(
                job_id,
                status=status,
                stage=stage,
                pages_processed=pages_processed,
                pages_total=pages_total,
            )
        except (JobMissing, JobExpired):
            return None
        return self.get_job(record.job_id)

    def cancel_job(
        self, job_id: str
    ) -> Literal["missing", "accepted", "already_canceled", "conflict"]:
        job = self.get_job(job_id)
        if job is None:
            return "missing"
        if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
            try:
                self.job_store.mark_canceled(job_id)
            except (JobMissing, JobExpired):
                return "missing"
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
        with self._lock:
            self._active_job_ids.add(job_id)
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()

    def _run_job(self, job_id: str) -> None:
        try:
            job = self._set_job_status(job_id, JobStatus.RUNNING, "starting")
            if job is None:
                return
        finally:
            # Ensure we always clear "active" even if early failures occur.
            pass

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
            self.job_store.mark_succeeded(
                job_id,
                markdown_bytes=artifact_bytes,
                backend_used=metadata.backend_used,
                acceleration_used=metadata.acceleration_used,
                options_fingerprint=metadata.options_fingerprint,
                warnings=warnings,
            )
        except ServiceError as exc:
            try:
                self.job_store.mark_failed(
                    job_id,
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                    details=exc.details,
                )
            except (JobMissing, JobExpired):
                return
        except Exception as exc:  # pragma: no cover - defensive fallback
            try:
                self.job_store.mark_failed(
                    job_id,
                    code="conversion_internal_error",
                    message=f"Unexpected conversion error: {exc}",
                    retryable=True,
                    details=None,
                )
            except (JobMissing, JobExpired):
                return
        finally:
            with self._lock:
                self._active_job_ids.discard(job_id)


def fingerprint_for_request(spec_payload: dict[str, object], file_sha256: str) -> str:
    """Create deterministic idempotency fingerprint for a create-job request."""
    normalized = json.dumps(spec_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{normalized}:{file_sha256}".encode("utf-8")).hexdigest()


def service_config_from_env() -> ServiceConfig:
    """Load service configuration from environment variables."""
    api_key = os.getenv("SIR_CONVERT_A_LOT_API_KEY", "dev-only-key")
    data_root = Path(
        os.getenv("CONVERTER_STORAGE_ROOT")
        or os.getenv("SIR_CONVERT_A_LOT_DATA_DIR")
        or "build/sir_convert_a_lot"
    )
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
