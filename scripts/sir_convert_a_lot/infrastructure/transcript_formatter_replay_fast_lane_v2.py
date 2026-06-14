"""Fast-lane execution for transcript formatter replay jobs.

Purpose:
    Run `transcript_json -> transcript_bundle` formatter replay immediately
    after Service API v2 create-job admission so deterministic replay work does
    not contend with generic PDF, STT, or document conversion workers.

Relationships:
    - Called by `interfaces.http_routes_jobs_v2` after normal job persistence.
    - Reuses `infrastructure.transcript_formatter_replay_runtime` for artifact
      rendering and `infrastructure.job_store_v2` for terminal job state.
"""

from __future__ import annotations

import logging
import time
from typing import Protocol

from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    is_transcript_formatter_replay_route_v2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    JobStateConflictV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CONVERSION_TOTAL_MS,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_capacity_telemetry_v2 import (
    RuntimeTelemetrySinkLikeV2,
    observe_failed_job_telemetry_v2,
    observe_succeeded_job_telemetry_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.runtime_webhook_service_v2 import (
    RuntimeWebhookServiceV2,
)
from scripts.sir_convert_a_lot.infrastructure.transcript_formatter_replay_runtime import (
    TRANSCRIPT_FORMATTER_REPLAY_PIPELINE,
    execute_transcript_formatter_replay_job,
)
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    fingerprint_job_options,
)

logger = logging.getLogger("uvicorn.error")

_REPLAY_ROUTE_LABEL = "transcript_json->transcript_bundle"


class TranscriptFormatterReplayFastLaneRuntimeV2(Protocol):
    """Runtime surface needed to execute one replay fast-lane job."""

    config: ServiceConfig
    job_store: JobStoreV2
    webhook_service: RuntimeWebhookServiceV2
    telemetry_sink: RuntimeTelemetrySinkLikeV2

    def get_job(self, job_id: str) -> StoredJobV2 | None:
        """Return the current job state."""
        ...


def run_transcript_formatter_replay_fast_lane_v2(
    *,
    runtime: TranscriptFormatterReplayFastLaneRuntimeV2,
    job_id: str,
    correlation_id: str,
    admission_started_at: float,
) -> StoredJobV2 | None:
    """Run one replay job through the producer-owned fast lane."""

    admission_ms = _elapsed_ms(admission_started_at)
    _observe_fast_lane_timing(
        runtime=runtime,
        phase="admission",
        status="accepted",
        duration_ms=admission_ms,
    )

    execution_started_at = time.perf_counter()
    try:
        claimed = runtime.job_store.claim_queued_job(job_id)
    except (JobMissingV2, JobExpiredV2):
        _observe_fast_lane_timing(
            runtime=runtime,
            phase="execution",
            status="skipped",
            duration_ms=_elapsed_ms(execution_started_at),
        )
        _log_fast_lane_completion(
            correlation_id=correlation_id,
            job_id=job_id,
            status="skipped",
            admission_ms=admission_ms,
            execution_ms=_elapsed_ms(execution_started_at),
        )
        return None
    if not claimed:
        current = runtime.get_job(job_id)
        _observe_fast_lane_timing(
            runtime=runtime,
            phase="execution",
            status="skipped",
            duration_ms=_elapsed_ms(execution_started_at),
        )
        _log_fast_lane_completion(
            correlation_id=correlation_id,
            job_id=job_id,
            status="skipped",
            admission_ms=admission_ms,
            execution_ms=_elapsed_ms(execution_started_at),
        )
        return current

    job = runtime.get_job(job_id)
    if job is None or not _is_replay_job(job):
        return runtime.get_job(job_id)

    try:
        runtime.job_store.update_progress(
            job_id,
            status=JobStatus.RUNNING,
            stage="transcript_replay_fast_lane",
        )
        runtime.webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
        running_job = runtime.get_job(job_id)
        if running_job is None:
            return None
        replay_result = execute_transcript_formatter_replay_job(job=running_job)
        execution_ms = _elapsed_ms(execution_started_at)
        phase_timings_ms = dict(replay_result.phase_timings_ms)
        phase_timings_ms[TIMING_KEY_CONVERSION_TOTAL_MS] = execution_ms
        runtime.job_store.mark_succeeded(
            job_id,
            artifact_bytes=replay_result.artifact_bytes,
            pipeline_used=TRANSCRIPT_FORMATTER_REPLAY_PIPELINE,
            backend_used=None,
            acceleration_used=None,
            options_fingerprint=f"sha256:{fingerprint_job_options(running_job.spec)}",
            warnings=list(replay_result.warnings),
            phase_timings_ms=phase_timings_ms,
        )
        runtime.webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
        succeeded = runtime.get_job(job_id)
        if succeeded is not None:
            observe_succeeded_job_telemetry_v2(
                enabled=runtime.config.enable_runtime_telemetry_calls,
                telemetry_sink=runtime.telemetry_sink,
                job=succeeded,
            )
        _observe_fast_lane_timing(
            runtime=runtime,
            phase="execution",
            status="succeeded",
            duration_ms=execution_ms,
        )
        _log_fast_lane_completion(
            correlation_id=correlation_id,
            job_id=job_id,
            status="succeeded",
            admission_ms=admission_ms,
            execution_ms=execution_ms,
        )
        return succeeded
    except ServiceError as exc:
        return _fail_replay_fast_lane_job(
            runtime=runtime,
            job_id=job_id,
            correlation_id=correlation_id,
            admission_ms=admission_ms,
            execution_started_at=execution_started_at,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )
    except (JobMissingV2, JobExpiredV2, JobStateConflictV2):
        return runtime.get_job(job_id)
    except Exception:
        return _fail_replay_fast_lane_job(
            runtime=runtime,
            job_id=job_id,
            correlation_id=correlation_id,
            admission_ms=admission_ms,
            execution_started_at=execution_started_at,
            code="transcript_formatter_replay_internal_error",
            message="Unexpected transcript formatter replay error.",
            retryable=True,
            details=None,
        )


def _fail_replay_fast_lane_job(
    *,
    runtime: TranscriptFormatterReplayFastLaneRuntimeV2,
    job_id: str,
    correlation_id: str,
    admission_ms: int,
    execution_started_at: float,
    code: str,
    message: str,
    retryable: bool,
    details: dict[str, object] | None,
) -> StoredJobV2 | None:
    execution_ms = _elapsed_ms(execution_started_at)
    try:
        runtime.job_store.mark_failed(
            job_id,
            code=code,
            message=message,
            retryable=retryable,
            details=details,
            phase_timings_ms={TIMING_KEY_CONVERSION_TOTAL_MS: execution_ms},
        )
        runtime.webhook_service.enqueue_webhook_events_for_job(job_id=job_id)
    except (JobMissingV2, JobExpiredV2, JobStateConflictV2):
        return runtime.get_job(job_id)
    failed = runtime.get_job(job_id)
    if failed is not None:
        observe_failed_job_telemetry_v2(
            enabled=runtime.config.enable_runtime_telemetry_calls,
            telemetry_sink=runtime.telemetry_sink,
            job=failed,
        )
    _observe_fast_lane_timing(
        runtime=runtime,
        phase="execution",
        status="failed",
        duration_ms=execution_ms,
    )
    _log_fast_lane_completion(
        correlation_id=correlation_id,
        job_id=job_id,
        status="failed",
        admission_ms=admission_ms,
        execution_ms=execution_ms,
    )
    return failed


def _is_replay_job(job: StoredJobV2) -> bool:
    return is_transcript_formatter_replay_route_v2(
        source_format=job.source_format,
        output_format=job.output_format,
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.perf_counter() - started_at) * 1000))


def _observe_fast_lane_timing(
    *,
    runtime: TranscriptFormatterReplayFastLaneRuntimeV2,
    phase: str,
    status: str,
    duration_ms: int,
) -> None:
    if not runtime.config.enable_runtime_telemetry_calls:
        return
    try:
        runtime.telemetry_sink.observe_transcript_replay_fast_lane_timing(
            phase=phase,
            status=status,
            duration_ms=duration_ms,
        )
    except Exception:
        return


def _log_fast_lane_completion(
    *,
    correlation_id: str,
    job_id: str,
    status: str,
    admission_ms: int,
    execution_ms: int,
) -> None:
    logger.info(
        "transcript_formatter_replay_fast_lane_completed correlation_id=%s job_id=%s "
        "route=%s status=%s admission_ms=%d execution_ms=%d",
        correlation_id,
        job_id,
        _REPLAY_ROUTE_LABEL,
        status,
        admission_ms,
        execution_ms,
    )
