"""Job artifact and checkpoint HTTP routes for Sir Convert-a-Lot service API v2.

Purpose:
    Keep result/artifact retrieval and long-PDF partial/checkpoint endpoints
    isolated from the job create/status/cancel router so the primary jobs router
    stays lean and remains below the 500 LoC guardrail.

Relationships:
    - Registered by `interfaces.http_routes_jobs_v2.build_job_router_v2`.
    - Uses v2 runtime behavior in `infrastructure.runtime_engine_v2`.
    - Reads PDF checkpoint/partial artifacts produced by
      `infrastructure.v2_conversion_executor`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    ArtifactMetadataV2,
    ConversionMetadataV2,
    JobPendingResultResponseV2,
    JobResultResponseV2,
    ResultPayloadV2,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    load_pdf_checkpoint,
    partial_artifact_path_for_job_upload,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request


def _content_type_for_output(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.MD:
        return "text/markdown"
    if output_format == OutputFormatV2.PDF:
        return "application/pdf"
    if output_format == OutputFormatV2.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise AssertionError(f"Unsupported output_format: {output_format}")


def _require_api_key(request: Request, *, service_started_at: str) -> None:
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    api_key = request.headers.get("X-API-Key")
    if api_key != runtime.config.api_key:
        raise ServiceError(
            status_code=401,
            code="auth_invalid_api_key",
            message="Missing or invalid X-API-Key.",
            retryable=False,
        )


def register_job_artifact_routes_v2(*, router: APIRouter, service_started_at: str) -> None:
    @router.get("/v2/convert/jobs/{job_id}/result")
    async def get_result(job_id: str, request: Request) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )

        if job.status not in TERMINAL_JOB_STATUSES:
            pending = JobPendingResultResponseV2(job_id=job.job_id, status=job.status)
            return JSONResponse(status_code=202, content=pending.model_dump(mode="json"))

        if job.status != JobStatus.SUCCEEDED:
            raise ServiceError(
                status_code=409,
                code="job_not_succeeded",
                message="Job is terminal but has no successful conversion result.",
                retryable=False,
                details={"status": job.status.value},
            )

        if job.artifact_sha256 is None or job.artifact_size_bytes is None:
            raise ServiceError(
                status_code=500,
                code="result_missing_artifact",
                message="Successful job is missing artifact metadata.",
                retryable=False,
            )

        if job.pipeline_used is None or job.options_fingerprint is None:
            raise ServiceError(
                status_code=500,
                code="result_missing_metadata",
                message="Successful job is missing conversion metadata.",
                retryable=False,
            )

        payload = JobResultResponseV2(
            job_id=job.job_id,
            result=ResultPayloadV2(
                artifact=ArtifactMetadataV2(
                    filename=job.artifact_path.name,
                    format=job.output_format,
                    size_bytes=job.artifact_size_bytes,
                    sha256=job.artifact_sha256,
                    content_type=_content_type_for_output(job.output_format),
                ),
                conversion_metadata=ConversionMetadataV2(
                    pipeline_used=job.pipeline_used,
                    backend_used=job.backend_used,
                    acceleration_used=job.acceleration_used,
                    acceleration_policy_requested=job.acceleration_policy_requested,
                    gpu_runtime_kind=job.gpu_runtime_kind,
                    gpu_device_count=job.gpu_device_count,
                    gpu_busy_percent=job.gpu_busy_percent,
                    gpu_memory_used_percent=job.gpu_memory_used_percent,
                    options_fingerprint=job.options_fingerprint,
                    template_id=job.template_id,
                    template_version=job.template_version,
                    template_artifact_sha256=job.template_artifact_sha256,
                    parallel_enabled=job.parallel_enabled,
                    max_chunk_workers=job.max_chunk_workers,
                    chunk_size_pages=job.chunk_size_pages,
                    effective_gpu_stage_limit=job.effective_gpu_stage_limit,
                    scheduling_mode=job.scheduling_mode,
                ),
                warnings=job.warnings,
            ),
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.get("/v2/convert/jobs/{job_id}/artifact")
    async def get_artifact(job_id: str, request: Request) -> Response:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )

        if job.status not in TERMINAL_JOB_STATUSES:
            pending = JobPendingResultResponseV2(job_id=job.job_id, status=job.status)
            return JSONResponse(status_code=202, content=pending.model_dump(mode="json"))

        if job.status != JobStatus.SUCCEEDED:
            raise ServiceError(
                status_code=409,
                code="job_not_succeeded",
                message="Job is terminal but has no successful conversion result.",
                retryable=False,
                details={"status": job.status.value},
            )

        content_type = _content_type_for_output(job.output_format)
        return FileResponse(
            path=job.artifact_path.as_posix(),
            media_type=content_type,
            filename=job.artifact_path.name,
        )

    @router.get("/v2/convert/jobs/{job_id}/artifact/partial")
    async def get_partial_artifact(job_id: str, request: Request) -> Response:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )

        if job.source_format != SourceFormatV2.PDF:
            raise ServiceError(
                status_code=409,
                code="partial_artifact_not_supported",
                message="Partial artifacts are only supported for PDF routes.",
                retryable=False,
                details={"source_format": job.source_format.value},
            )

        if job.status == JobStatus.SUCCEEDED:
            raise ServiceError(
                status_code=409,
                code="job_succeeded_use_artifact",
                message="Job succeeded; use the terminal artifact endpoint instead.",
                retryable=False,
            )

        partial_path = partial_artifact_path_for_job_upload(upload_path=job.upload_path)
        if not partial_path.exists():
            if job.status in {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCELED}:
                pending = JobPendingResultResponseV2(job_id=job.job_id, status=job.status)
                return JSONResponse(status_code=202, content=pending.model_dump(mode="json"))
            raise ServiceError(
                status_code=409,
                code="partial_artifact_not_available",
                message="Job is terminal and no partial artifact is available.",
                retryable=False,
                details={"status": job.status.value},
            )

        return FileResponse(
            path=partial_path.as_posix(),
            media_type="text/markdown",
            filename=partial_path.name,
        )

    @router.get("/v2/convert/jobs/{job_id}/checkpoint")
    async def get_checkpoint(job_id: str, request: Request) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )

        if job.source_format != SourceFormatV2.PDF:
            raise ServiceError(
                status_code=409,
                code="checkpoint_not_supported",
                message="Checkpoints are only supported for PDF routes.",
                retryable=False,
                details={"source_format": job.source_format.value},
            )

        try:
            checkpoint = load_pdf_checkpoint(upload_path=job.upload_path)
        except Exception as exc:
            raise ServiceError(
                status_code=500,
                code="checkpoint_invalid",
                message=f"Checkpoint payload could not be loaded: {exc}",
                retryable=True,
            ) from exc

        if checkpoint is None:
            if job.status in {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCELED}:
                pending = JobPendingResultResponseV2(job_id=job.job_id, status=job.status)
                return JSONResponse(status_code=202, content=pending.model_dump(mode="json"))
            raise ServiceError(
                status_code=409,
                code="checkpoint_not_available",
                message="Job is terminal and no checkpoint is available.",
                retryable=False,
                details={"status": job.status.value},
            )

        return JSONResponse(status_code=200, content=checkpoint.model_dump(mode="json"))
