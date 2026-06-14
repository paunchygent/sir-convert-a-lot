"""Single-job execution runner for service API v2 runtime workers.

Purpose:
    Execute one claimed v2 job through progress initialization, heartbeat,
    conversion, terminal persistence, webhook dispatch, and telemetry while the
    runtime engine owns only scheduling and public lifecycle methods.

Relationships:
    - Called by `infrastructure.runtime_engine_v2.ServiceRuntimeV2`.
    - Delegates conversion to `infrastructure.v2_conversion_executor`.
    - Persists lifecycle transitions through `infrastructure.job_store_v2`.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Protocol

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_runtime import (
    AudioProgressUpdateV2,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    AudioTranscriptionSidecarClient,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import ConversionBackend
from scripts.sir_convert_a_lot.infrastructure.gpu_utilization_snapshot import (
    GpuUtilizationSnapshotTimeoutError,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    JobStateConflictV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import load_pdf_checkpoint
from scripts.sir_convert_a_lot.infrastructure.pdf_metadata_v2 import best_effort_pdf_total_pages
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CONVERSION_TOTAL_MS,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_capacity_telemetry_v2 import (
    RuntimeTelemetrySinkLikeV2,
    observe_failed_job_telemetry_v2,
    observe_succeeded_job_telemetry_v2,
    resolve_requested_acceleration_policy_value_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.runtime_webhook_service_v2 import (
    RuntimeWebhookServiceV2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    V2ExecutionResult,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfCheckpointProgressUpdateV2,
    PdfConversionCanceledV2,
)

_GPU_SNAPSHOT_WARNING_CAPTURE_FAILED = "gpu_snapshot_capture_failed"
_GPU_SNAPSHOT_WARNING_CAPTURE_TIMEOUT = "gpu_snapshot_capture_timeout"


class RuntimeHeartbeatThreadV2(Protocol):
    """Thread-like heartbeat object returned by the heartbeat starter."""

    def join(self, timeout: float | None = None) -> None:
        """Join the heartbeat worker."""


class RuntimeHeartbeatStarterV2(Protocol):
    """Callable that starts conversion heartbeats for one job."""

    def __call__(
        self,
        *,
        job_store: JobStoreV2,
        job_id: str,
        heartbeat_interval_seconds: float,
    ) -> tuple[threading.Event, RuntimeHeartbeatThreadV2]:
        """Start heartbeat emission and return stop event plus worker."""


class RuntimeGpuSnapshotCollectorV2(Protocol):
    """Callable that collects terminal GPU snapshot fields."""

    def __call__(
        self,
        *,
        acceleration_used: str | None,
    ) -> tuple[str | None, int | None, int | None, int | None]:
        """Collect terminal GPU snapshot fields."""


class RuntimeConversionExecutorV2(Protocol):
    """Callable that executes one v2 job conversion."""

    def __call__(
        self,
        *,
        job: StoredJobV2,
        config: ServiceConfig,
        docling_backend: ConversionBackend,
        pymupdf_backend: ConversionBackend,
        audio_transcription_sidecar: AudioTranscriptionSidecarClient,
        progress_callback: Callable[[PdfCheckpointProgressUpdateV2 | AudioProgressUpdateV2], None]
        | None = None,
        is_cancel_requested: Callable[[], bool] | None = None,
        on_chunk_worker_start: Callable[[], None] | None = None,
        on_chunk_worker_finish: Callable[[], None] | None = None,
    ) -> V2ExecutionResult:
        """Run one conversion and return terminal artifact metadata."""


def run_runtime_job_v2(
    *,
    job_id: str,
    config: ServiceConfig,
    job_store: JobStoreV2,
    webhook_service: RuntimeWebhookServiceV2,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    audio_transcription_sidecar: AudioTranscriptionSidecarClient,
    telemetry_sink: RuntimeTelemetrySinkLikeV2,
    get_job: Callable[[str], StoredJobV2 | None],
    safe_get_job: Callable[[str], StoredJobV2 | None],
    collect_gpu_utilization_fields: RuntimeGpuSnapshotCollectorV2,
    acquire_chunk_worker_slot: Callable[[], None],
    release_chunk_worker_slot: Callable[[], None],
    execute_conversion: RuntimeConversionExecutorV2,
    start_heartbeat: RuntimeHeartbeatStarterV2,
) -> None:
    """Run one v2 job from queued claim through terminal state."""
    try:
        claimed = job_store.claim_queued_job(job_id)
    except (JobMissingV2, JobExpiredV2):
        return
    if not claimed:
        return

    job = get_job(job_id)
    if job is None:
        return

    time.sleep(config.processing_delay_seconds)

    job = get_job(job_id)
    if job is None:
        return
    if job.status == JobStatus.CANCELED:
        return

    _initialize_running_progress(job_id=job_id, job=job, job_store=job_store)
    job_store.touch_heartbeat(job_id)
    webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
    heartbeat_stop, heartbeat_thread = start_heartbeat(
        job_store=job_store,
        job_id=job_id,
        heartbeat_interval_seconds=config.heartbeat_interval_seconds,
    )

    conversion_started = time.perf_counter()
    try:
        result = _execute_conversion(
            job_id=job_id,
            job=job,
            config=config,
            docling_backend=docling_backend,
            pymupdf_backend=pymupdf_backend,
            audio_transcription_sidecar=audio_transcription_sidecar,
            job_store=job_store,
            webhook_service=webhook_service,
            get_job=get_job,
            acquire_chunk_worker_slot=acquire_chunk_worker_slot,
            release_chunk_worker_slot=release_chunk_worker_slot,
            execute_conversion=execute_conversion,
        )
        current = safe_get_job(job_id)
        if current is not None and current.status == JobStatus.CANCELED:
            _stop_heartbeat(
                heartbeat_stop=heartbeat_stop,
                heartbeat_thread=heartbeat_thread,
                heartbeat_interval_seconds=config.heartbeat_interval_seconds,
            )
            webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
            return
        phase_timings_ms = dict(result.phase_timings_ms)
        phase_timings_ms[TIMING_KEY_CONVERSION_TOTAL_MS] = max(
            0, int((time.perf_counter() - conversion_started) * 1000)
        )
        warnings = list(result.warnings)
        gpu_runtime_kind: str | None = None
        gpu_device_count: int | None = None
        gpu_busy_percent: int | None = None
        gpu_memory_used_percent: int | None = None
        if config.enable_runtime_telemetry_calls:
            try:
                (
                    gpu_runtime_kind,
                    gpu_device_count,
                    gpu_busy_percent,
                    gpu_memory_used_percent,
                ) = collect_gpu_utilization_fields(acceleration_used=result.acceleration_used)
            except GpuUtilizationSnapshotTimeoutError:
                _append_warning_once(warnings, _GPU_SNAPSHOT_WARNING_CAPTURE_TIMEOUT)
            except Exception:
                _append_warning_once(warnings, _GPU_SNAPSHOT_WARNING_CAPTURE_FAILED)

        _stop_heartbeat(
            heartbeat_stop=heartbeat_stop,
            heartbeat_thread=heartbeat_thread,
            heartbeat_interval_seconds=config.heartbeat_interval_seconds,
        )
        job_store.mark_succeeded(
            job_id,
            artifact_bytes=result.artifact_bytes,
            pipeline_used=result.pipeline_used,
            backend_used=result.backend_used,
            acceleration_used=result.acceleration_used,
            ocr_enabled=result.ocr_enabled,
            ocr_engine_used=result.ocr_engine_used,
            ocr_languages_used=result.ocr_languages_used,
            options_fingerprint=f"sha256:{result.options_fingerprint}",
            acceleration_policy_requested=resolve_requested_acceleration_policy_value_v2(job),
            gpu_runtime_kind=gpu_runtime_kind,
            gpu_device_count=gpu_device_count,
            gpu_busy_percent=gpu_busy_percent,
            gpu_memory_used_percent=gpu_memory_used_percent,
            template_id=result.template_id,
            template_version=result.template_version,
            template_artifact_sha256=result.template_artifact_sha256,
            parallel_enabled=result.parallel_enabled,
            max_chunk_workers=result.max_chunk_workers,
            chunk_size_pages=result.chunk_size_pages,
            effective_gpu_stage_limit=result.effective_gpu_stage_limit,
            scheduling_mode=result.scheduling_mode,
            formula_authority=dict(result.formula_authority),
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
        )
        webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
        succeeded = safe_get_job(job_id)
        if succeeded is not None:
            observe_succeeded_job_telemetry_v2(
                enabled=config.enable_runtime_telemetry_calls,
                telemetry_sink=telemetry_sink,
                job=succeeded,
            )
    except PdfConversionCanceledV2:
        _stop_heartbeat(
            heartbeat_stop=heartbeat_stop,
            heartbeat_thread=heartbeat_thread,
            heartbeat_interval_seconds=config.heartbeat_interval_seconds,
        )
        webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
        return
    except JobStateConflictV2:
        return
    except ServiceError as exc:
        _mark_conversion_failed(
            job_id=job_id,
            job_store=job_store,
            webhook_service=webhook_service,
            safe_get_job=safe_get_job,
            telemetry_sink=telemetry_sink,
            telemetry_enabled=config.enable_runtime_telemetry_calls,
            heartbeat_stop=heartbeat_stop,
            heartbeat_thread=heartbeat_thread,
            heartbeat_interval_seconds=config.heartbeat_interval_seconds,
            conversion_elapsed_ms=max(0, int((time.perf_counter() - conversion_started) * 1000)),
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        _mark_conversion_failed(
            job_id=job_id,
            job_store=job_store,
            webhook_service=webhook_service,
            safe_get_job=safe_get_job,
            telemetry_sink=telemetry_sink,
            telemetry_enabled=config.enable_runtime_telemetry_calls,
            heartbeat_stop=heartbeat_stop,
            heartbeat_thread=heartbeat_thread,
            heartbeat_interval_seconds=config.heartbeat_interval_seconds,
            conversion_elapsed_ms=max(0, int((time.perf_counter() - conversion_started) * 1000)),
            code="conversion_internal_error",
            message=f"Unexpected conversion error: {exc}",
            retryable=True,
            details=None,
        )


def _initialize_running_progress(
    *,
    job_id: str,
    job: StoredJobV2,
    job_store: JobStoreV2,
) -> None:
    total_pages: int | None = None
    stage = "converting"
    if job.source_format == SourceFormatV2.PDF:
        checkpoint = None
        try:
            checkpoint = load_pdf_checkpoint(upload_path=job.upload_path)
        except Exception:
            checkpoint = None
        total_pages = checkpoint.total_pages if checkpoint is not None else None
        if total_pages is None:
            total_pages = best_effort_pdf_total_pages(job.upload_path)
        processed_pages = checkpoint.processed_pages if checkpoint is not None else 0
        failed_pages = checkpoint.failed_pages if checkpoint is not None else 0
        percent_complete = (
            (processed_pages / float(total_pages)) * 100.0
            if total_pages is not None and total_pages > 0
            else None
        )
    elif job.source_format == SourceFormatV2.AUDIO:
        processed_pages = None
        failed_pages = None
        percent_complete = None
        stage = "starting"
    else:
        processed_pages = None
        failed_pages = None
        percent_complete = None
    job_store.update_progress(
        job_id,
        status=JobStatus.RUNNING,
        stage=stage,
        total_pages=total_pages,
        processed_pages=processed_pages,
        failed_pages=failed_pages,
        percent_complete=percent_complete,
    )


def _execute_conversion(
    *,
    job_id: str,
    job: StoredJobV2,
    config: ServiceConfig,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    audio_transcription_sidecar: AudioTranscriptionSidecarClient,
    job_store: JobStoreV2,
    webhook_service: RuntimeWebhookServiceV2,
    get_job: Callable[[str], StoredJobV2 | None],
    acquire_chunk_worker_slot: Callable[[], None],
    release_chunk_worker_slot: Callable[[], None],
    execute_conversion: RuntimeConversionExecutorV2,
) -> V2ExecutionResult:
    def _progress_callback(update: PdfCheckpointProgressUpdateV2 | AudioProgressUpdateV2) -> None:
        try:
            current = get_job(job_id)
            if current is not None and current.status == JobStatus.CANCELED:
                return
            if isinstance(update, AudioProgressUpdateV2):
                job_store.update_progress(
                    job_id,
                    status=JobStatus.RUNNING,
                    stage=update.stage,
                    audio_total_media_seconds=update.audio_total_media_seconds,
                    audio_processed_media_seconds=update.audio_processed_media_seconds,
                    audio_percent_complete=update.audio_percent_complete,
                    audio_current_chunk_index=update.audio_current_chunk_index,
                    audio_total_chunks=update.audio_total_chunks,
                    audio_pipeline_percent_complete=update.audio_pipeline_percent_complete,
                    audio_pipeline_eta_seconds=update.audio_pipeline_eta_seconds,
                    phase_timings_ms=update.phase_timings_ms,
                )
                webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
                return
            job_store.update_progress(
                job_id,
                status=JobStatus.RUNNING,
                stage="converting",
                total_pages=update.total_pages,
                processed_pages=update.processed_pages,
                failed_pages=update.failed_pages,
                percent_complete=update.percent_complete,
                pages_per_minute=update.pages_per_minute,
                eta_seconds=update.eta_seconds,
                phase_timings_ms=update.phase_timings_ms,
            )
            webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
        except (JobMissingV2, JobExpiredV2, JobStateConflictV2):
            return

    def _is_cancel_requested() -> bool:
        current = get_job(job_id)
        return current is not None and current.status == JobStatus.CANCELED

    return execute_conversion(
        job=job,
        config=config,
        docling_backend=docling_backend,
        pymupdf_backend=pymupdf_backend,
        audio_transcription_sidecar=audio_transcription_sidecar,
        progress_callback=_progress_callback,
        is_cancel_requested=_is_cancel_requested,
        on_chunk_worker_start=acquire_chunk_worker_slot,
        on_chunk_worker_finish=release_chunk_worker_slot,
    )


def _append_warning_once(warnings: list[str], warning: str) -> None:
    if warning not in warnings:
        warnings.append(warning)


def _stop_heartbeat(
    *,
    heartbeat_stop: threading.Event,
    heartbeat_thread: RuntimeHeartbeatThreadV2,
    heartbeat_interval_seconds: float,
) -> None:
    heartbeat_stop.set()
    heartbeat_thread.join(timeout=max(0.5, heartbeat_interval_seconds))


def _mark_conversion_failed(
    *,
    job_id: str,
    job_store: JobStoreV2,
    webhook_service: RuntimeWebhookServiceV2,
    safe_get_job: Callable[[str], StoredJobV2 | None],
    telemetry_sink: RuntimeTelemetrySinkLikeV2,
    telemetry_enabled: bool,
    heartbeat_stop: threading.Event,
    heartbeat_thread: RuntimeHeartbeatThreadV2,
    heartbeat_interval_seconds: float,
    conversion_elapsed_ms: int,
    code: str,
    message: str,
    retryable: bool,
    details: dict[str, object] | None,
) -> None:
    _stop_heartbeat(
        heartbeat_stop=heartbeat_stop,
        heartbeat_thread=heartbeat_thread,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
    )
    try:
        job_store.mark_failed(
            job_id,
            code=code,
            message=message,
            retryable=retryable,
            details=details,
            phase_timings_ms={TIMING_KEY_CONVERSION_TOTAL_MS: conversion_elapsed_ms},
        )
        webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
        failed = safe_get_job(job_id)
        if failed is not None:
            observe_failed_job_telemetry_v2(
                enabled=telemetry_enabled,
                telemetry_sink=telemetry_sink,
                job=failed,
            )
    except (JobMissingV2, JobExpiredV2, JobStateConflictV2):
        return
