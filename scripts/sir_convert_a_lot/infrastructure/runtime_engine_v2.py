"""Sir Convert-a-Lot infrastructure runtime engine for service API v2.

Purpose:
    Provide filesystem-backed v2 job persistence, idempotency tracking, and asynchronous conversion
    execution for multi-format conversion workflows executed on Hemma (dockerized runtime).

Relationships:
    - Consumed by v2 HTTP routes for service API v2 job lifecycle operations.
    - Coexists with the locked v1 runtime engine in `infrastructure.runtime_engine`.
    - Uses v1 PDF backends (Docling/PyMuPDF) for the PDF->Markdown stage where needed.
    - Uses Pandoc/WeasyPrint converter utilities for HTML/Markdown outputs.
"""

from __future__ import annotations

import threading
from typing import Literal
from uuid import uuid4

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.domain.structured_llm_admission import (
    StructuredLLMAdmittedRouteSnapshot,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    AudioTranscriptionSidecarClient,
    build_audio_transcription_sidecar_client,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_job_companion_paths_v2 import (
    graded_result_pdf_path_for_upload,
    ingestion_overlay_path_for_upload,
    parity_pdf_path_for_upload,
)
from scripts.sir_convert_a_lot.infrastructure.docling_backend import DoclingConversionBackend
from scripts.sir_convert_a_lot.infrastructure.idempotency_store import IdempotencyStore
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import JobLifecycleEventRecordV2
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    JobStateConflictV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.ocr_preflight_v2 import preflight_pdf_ocr_or_raise
from scripts.sir_convert_a_lot.infrastructure.pymupdf_backend import PyMuPdfConversionBackend
from scripts.sir_convert_a_lot.infrastructure.runtime_capacity_telemetry_v2 import (
    RuntimeCapacityTelemetryEmitterV2,
    RuntimeChunkWorkerLimiterV2,
    RuntimeGpuUtilizationFieldsV2,
    collect_gpu_utilization_fields_v2,
    observe_canceled_job_telemetry_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_heartbeat_v2 import (
    start_conversion_heartbeat_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_job_runner_v2 import run_runtime_job_v2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.runtime_supervision_v2 import (
    RuntimeSupervisorV2,
    join_supervisor_thread_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_telemetry_v2 import (
    NoopRuntimeTelemetrySinkV2,
    RuntimeTelemetrySinkV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_webhook_service_v2 import (
    RuntimeWebhookServiceV2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
)
from scripts.sir_convert_a_lot.infrastructure.webhook_delivery_v2 import WebhookDeliveryWorkerV2
from scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2_store import (
    WebhookSubscriptionStoreV2,
)


class ServiceRuntimeV2:
    """Thread-safe runtime state and execution for Sir Convert-a-Lot v2 jobs."""

    def __init__(
        self,
        config: ServiceConfig,
        *,
        telemetry_sink: RuntimeTelemetrySinkV2 | None = None,
        audio_transcription_sidecar: AudioTranscriptionSidecarClient | None = None,
    ) -> None:
        self.config = config
        self.telemetry_sink: RuntimeTelemetrySinkV2 | NoopRuntimeTelemetrySinkV2 = (
            telemetry_sink if telemetry_sink is not None else NoopRuntimeTelemetrySinkV2()
        )
        self.job_store = JobStoreV2(
            data_root=config.data_root,
            raw_ttl_seconds=config.upload_ttl_seconds,
            artifact_ttl_seconds=config.result_ttl_seconds,
            replay_horizon_seconds=config.sse_replay_horizon_seconds,
        )
        self.idempotency_store = IdempotencyStore(
            data_root=config.data_root,
            ttl_seconds=config.idempotency_ttl_seconds,
        )
        self.webhook_store = WebhookSubscriptionStoreV2(
            data_root=config.data_root,
            secret_overlap_seconds=config.webhook_secret_overlap_seconds,
        )
        self.webhook_delivery_worker: WebhookDeliveryWorkerV2 | None = None
        if self.config.enable_webhook_delivery:
            self.webhook_delivery_worker = WebhookDeliveryWorkerV2(
                data_root=config.data_root,
                subscription_store=self.webhook_store,
            )
            self.webhook_delivery_worker.start()
        self.webhook_service = RuntimeWebhookServiceV2(
            job_store=self.job_store,
            webhook_store=self.webhook_store,
            webhook_delivery_worker=self.webhook_delivery_worker,
            enable_webhook_delivery=self.config.enable_webhook_delivery,
            sse_replay_horizon_seconds=self.config.sse_replay_horizon_seconds,
        )
        self.docling_backend = DoclingConversionBackend(
            easyocr_model_storage_directory=self.config.easyocr_model_storage_directory,
            easyocr_download_enabled=False,
        )
        self.pymupdf_backend = PyMuPdfConversionBackend()
        self.audio_transcription_sidecar = (
            audio_transcription_sidecar
            if audio_transcription_sidecar is not None
            else build_audio_transcription_sidecar_client(
                base_url=self.config.audio_transcription_sidecar_base_url,
                timeout_seconds=self.config.audio_transcription_sidecar_timeout_seconds,
            )
        )
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._supervisor_thread: threading.Thread | None = None
        self._active_job_ids: set[str] = set()
        self._capacity_telemetry = RuntimeCapacityTelemetryEmitterV2(
            config=self.config,
            telemetry_sink=self.telemetry_sink,
            job_store=self.job_store,
            active_job_count=self._active_job_count,
            active_chunk_worker_count=self._active_chunk_worker_count,
        )
        self._chunk_worker_limiter = RuntimeChunkWorkerLimiterV2(
            max_concurrency=self.config.gpu_stage_max_concurrency,
            emit_capacity=self._emit_chunk_capacity_metrics,
        )
        self._supervisor = RuntimeSupervisorV2(
            config=self.config,
            job_store=self.job_store,
            active_job_ids=self._active_job_ids,
            lock=self._lock,
            shutdown_event=self._shutdown_event,
            run_job_async=self.run_job_async,
            emit_capacity=self._emit_runtime_capacity_metrics,
        )

        self.job_store.sweep_expired()
        self.job_store.recover_running_jobs_to_queued(active_job_ids=self._active_job_ids)

        self._supervisor_thread = self._supervisor.start_if_enabled()
        self._emit_runtime_capacity_metrics()
        self._emit_chunk_capacity_metrics()

    def _active_job_count(self) -> int:
        with self._lock:
            return len(self._active_job_ids)

    def _active_chunk_worker_count(self) -> int:
        return self._chunk_worker_limiter.active_workers

    def _emit_runtime_capacity_metrics(self) -> None:
        self._capacity_telemetry.emit_runtime_capacity()

    def _emit_chunk_capacity_metrics(self) -> None:
        self._capacity_telemetry.emit_chunk_capacity()

    def _acquire_chunk_worker_slot(self) -> None:
        self._chunk_worker_limiter.acquire()

    def _release_chunk_worker_slot(self) -> None:
        self._chunk_worker_limiter.release()

    @staticmethod
    def _collect_gpu_utilization_fields(
        *,
        acceleration_used: str | None,
    ) -> tuple[str | None, int | None, int | None, int | None]:
        fields: RuntimeGpuUtilizationFieldsV2 = collect_gpu_utilization_fields_v2(
            acceleration_used=acceleration_used
        )
        return (
            fields.runtime_kind,
            fields.device_count,
            fields.busy_percent,
            fields.memory_used_percent,
        )

    def shutdown(self) -> None:
        """Stop background supervisor loops and release runtime resources."""
        self._shutdown_event.set()
        if self.webhook_delivery_worker is not None:
            self.webhook_delivery_worker.stop()
        join_supervisor_thread_v2(
            thread=self._supervisor_thread,
            supervisor_poll_seconds=self.config.supervisor_poll_seconds,
        )

    def _new_job_id(self) -> str:
        return f"jobv2_{uuid4().hex[:26]}"

    def get_job(self, job_id: str) -> StoredJobV2 | None:
        self.job_store.sweep_expired()
        try:
            record = self.job_store.get_job(job_id)
        except JobExpiredV2 as exc:
            raise ServiceError(
                status_code=404,
                code="job_expired",
                message="Job has expired and is no longer available.",
                retryable=False,
                details={"job_id": exc.job_id},
            ) from exc
        except JobMissingV2:
            return None

        return StoredJobV2(
            job_id=record.job_id,
            spec=record.spec,
            owner_api_key_scope=record.owner_api_key_scope,
            source_filename=record.source_filename,
            source_format=record.source_format,
            output_format=record.output_format,
            upload_path=record.upload_path,
            resources_zip_path=record.resources_zip_path,
            reference_docx_path=record.reference_docx_path,
            artifact_path=record.artifact_path,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            expires_at=record.expires_at,
            progress_stage=record.progress_stage,
            last_heartbeat_at=record.last_heartbeat_at,
            current_phase_started_at=record.current_phase_started_at,
            phase_timings_ms=dict(record.phase_timings_ms),
            total_pages=record.total_pages,
            processed_pages=record.processed_pages,
            failed_pages=record.failed_pages,
            percent_complete=record.percent_complete,
            pages_per_minute=record.pages_per_minute,
            eta_seconds=record.eta_seconds,
            audio_total_media_seconds=record.audio_total_media_seconds,
            audio_processed_media_seconds=record.audio_processed_media_seconds,
            audio_percent_complete=record.audio_percent_complete,
            audio_current_chunk_index=record.audio_current_chunk_index,
            audio_total_chunks=record.audio_total_chunks,
            warnings=list(record.warnings),
            artifact_sha256=record.artifact_sha256,
            artifact_size_bytes=record.artifact_size_bytes,
            pipeline_used=record.pipeline_used,
            backend_used=record.backend_used,
            acceleration_used=record.acceleration_used,
            ocr_enabled=record.ocr_enabled,
            ocr_engine_used=record.ocr_engine_used,
            ocr_languages_used=(
                list(record.ocr_languages_used) if record.ocr_languages_used is not None else None
            ),
            acceleration_policy_requested=record.acceleration_policy_requested,
            gpu_runtime_kind=record.gpu_runtime_kind,
            gpu_device_count=record.gpu_device_count,
            gpu_busy_percent=record.gpu_busy_percent,
            gpu_memory_used_percent=record.gpu_memory_used_percent,
            options_fingerprint=record.options_fingerprint,
            template_id=record.template_id,
            template_version=record.template_version,
            template_artifact_sha256=record.template_artifact_sha256,
            parallel_enabled=record.parallel_enabled,
            max_chunk_workers=record.max_chunk_workers,
            chunk_size_pages=record.chunk_size_pages,
            effective_gpu_stage_limit=record.effective_gpu_stage_limit,
            scheduling_mode=record.scheduling_mode,
            formula_authority=dict(record.formula_authority),
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            failure_retryable=record.failure_retryable,
            failure_details=record.failure_details,
            structured_llm_admission=record.structured_llm_admission,
        )

    def _safe_get_job(self, job_id: str) -> StoredJobV2 | None:
        try:
            return self.get_job(job_id)
        except ServiceError:
            return None

    def get_idempotency(self, scope_key: str):
        return self.idempotency_store.get(scope_key)

    def put_idempotency(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        self.idempotency_store.put(scope_key, fingerprint, job_id)

    def resolve_sse_resume_sequence(
        self,
        *,
        job_id: str,
        cursor: str | None,
        last_event_id: str | None,
    ) -> int:
        """Resolve replay pointer sequence for SSE streaming."""
        self.job_store.sweep_expired()
        try:
            return self.job_store.resolve_events_resume_sequence(
                job_id=job_id,
                cursor=cursor,
                last_event_id=last_event_id,
                replay_horizon_seconds=self.config.sse_replay_horizon_seconds,
            )
        except JobExpiredV2 as exc:
            raise ServiceError(
                status_code=404,
                code="job_expired",
                message="Job has expired and is no longer available.",
                retryable=False,
                details={"job_id": exc.job_id},
            ) from exc
        except JobMissingV2:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            ) from None

    def get_sse_events(
        self,
        *,
        job_id: str,
        after_sequence: int,
    ) -> list[JobLifecycleEventRecordV2]:
        """Return lifecycle events newer than the supplied sequence pointer."""
        self.job_store.sweep_expired()
        try:
            return self.job_store.list_job_events_after_sequence(
                job_id=job_id,
                after_sequence=after_sequence,
                replay_horizon_seconds=self.config.sse_replay_horizon_seconds,
            )
        except JobExpiredV2 as exc:
            raise ServiceError(
                status_code=404,
                code="job_expired",
                message="Job has expired and is no longer available.",
                retryable=False,
                details={"job_id": exc.job_id},
            ) from exc
        except JobMissingV2:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            ) from None

    def create_job(
        self,
        *,
        spec: JobSpecV2,
        owner_api_key_scope: str = "service-api-key",
        upload_bytes: bytes,
        resources_zip_bytes: bytes | None,
        reference_docx_bytes: bytes | None,
        graded_result_pdf_bytes: bytes | None = None,
        parity_pdf_bytes: bytes | None = None,
        digiexam_ingestion_overlay_bytes: bytes | None = None,
        structured_llm_admission: StructuredLLMAdmittedRouteSnapshot | None = None,
    ) -> StoredJobV2:
        preflight_pdf_ocr_or_raise(
            spec=spec,
            config=self.config,
            enforce_local_gpu_runtime=(
                self.config.run_jobs_on_submit or self.config.enable_supervisor
            ),
        )
        job_id = self._new_job_id()
        record = self.job_store.create_job(
            job_id=job_id,
            spec=spec,
            owner_api_key_scope=owner_api_key_scope,
            upload_bytes=upload_bytes,
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=reference_docx_bytes,
            structured_llm_admission=structured_llm_admission,
        )
        if graded_result_pdf_bytes is not None:
            graded_result_pdf_path_for_upload(record.upload_path).write_bytes(
                graded_result_pdf_bytes
            )
        if parity_pdf_bytes is not None:
            parity_pdf_path_for_upload(record.upload_path).write_bytes(parity_pdf_bytes)
        if digiexam_ingestion_overlay_bytes is not None:
            ingestion_overlay_path_for_upload(record.upload_path).write_bytes(
                digiexam_ingestion_overlay_bytes
            )
        stored = self.get_job(record.job_id)
        if stored is None:
            raise RuntimeError("created v2 job must be loadable immediately")
        self.webhook_service.enqueue_webhook_events_for_job(job_id=record.job_id)
        self._emit_runtime_capacity_metrics()
        return stored

    def cancel_job(
        self, job_id: str
    ) -> Literal["missing", "accepted", "already_canceled", "conflict"]:
        job = self.get_job(job_id)
        if job is None:
            return "missing"
        if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
            try:
                self.job_store.mark_canceled(job_id)
            except (JobMissingV2, JobExpiredV2):
                return "missing"
            except JobStateConflictV2:
                return "conflict"
            if _uses_audio_transcription_sidecar(job):
                self.audio_transcription_sidecar.cancel(job_id)
            self.webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
            canceled = self._safe_get_job(job_id)
            if canceled is not None:
                observe_canceled_job_telemetry_v2(
                    enabled=self.config.enable_runtime_telemetry_calls,
                    telemetry_sink=self.telemetry_sink,
                    job=canceled,
                )
            self._emit_runtime_capacity_metrics()
            return "accepted"
        if job.status == JobStatus.CANCELED:
            return "already_canceled"
        return "conflict"

    def run_job_async(self, job_id: str) -> None:
        """Run a v2 conversion job asynchronously in a background thread."""
        with self._lock:
            if job_id in self._active_job_ids:
                return
            self._active_job_ids.add(job_id)
        self._emit_runtime_capacity_metrics()
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()

    def _run_job(self, job_id: str) -> None:
        try:
            run_runtime_job_v2(
                job_id=job_id,
                config=self.config,
                job_store=self.job_store,
                webhook_service=self.webhook_service,
                docling_backend=self.docling_backend,
                pymupdf_backend=self.pymupdf_backend,
                audio_transcription_sidecar=self.audio_transcription_sidecar,
                telemetry_sink=self.telemetry_sink,
                get_job=self.get_job,
                safe_get_job=self._safe_get_job,
                collect_gpu_utilization_fields=self._collect_gpu_utilization_fields,
                acquire_chunk_worker_slot=self._acquire_chunk_worker_slot,
                release_chunk_worker_slot=self._release_chunk_worker_slot,
                execute_conversion=execute_v2_job_conversion,
                start_heartbeat=start_conversion_heartbeat_v2,
            )
        finally:
            with self._lock:
                self._active_job_ids.discard(job_id)
            self._emit_runtime_capacity_metrics()


def _uses_audio_transcription_sidecar(job: StoredJobV2) -> bool:
    return (
        job.source_format == SourceFormatV2.AUDIO
        and job.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE
    )
