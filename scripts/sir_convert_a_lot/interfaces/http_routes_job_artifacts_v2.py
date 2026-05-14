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
    DigiExamMigrationConversionMetadataV2,
    JobPendingResultResponseV2,
    JobResultResponseV2,
    ResultPayloadV2,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_artifacts import (
    load_digiexam_migration_result_metadata,
    resolve_digiexam_migration_artifact,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    load_pdf_checkpoint,
    partial_artifact_path_for_job_upload,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import (
    auth_context_for_job_access_v2,
    require_job_access_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_public_exam_converter_access_v2 import (
    is_public_job_v2,
    public_bundle_manifest_artifact_key_v2,
    require_public_artifact_read_lease_v2,
    require_public_job_access_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_public_exam_converter_artifacts_v2 import (
    load_public_bundle_manifest_v2,
)


def _content_type_for_output(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.MD:
        return "text/markdown"
    if output_format == OutputFormatV2.PDF:
        return "application/pdf"
    if output_format == OutputFormatV2.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if output_format == OutputFormatV2.EXAMNET_MIGRATION_BUNDLE:
        return "application/json"
    raise AssertionError(f"Unsupported output_format: {output_format}")


def register_job_artifact_routes_v2(*, router: APIRouter, service_started_at: str) -> None:
    @router.get("/v2/convert/jobs/{job_id}/result")
    async def get_result(job_id: str, request: Request) -> JSONResponse:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if is_public_job_v2(job):
            if job is None:
                raise ServiceError(
                    status_code=404,
                    code="job_not_found",
                    message="Job not found or expired.",
                    retryable=False,
                )
            require_public_job_access_v2(
                request=request,
                service_started_at=service_started_at,
                job=job,
            )
        else:
            auth_context = auth_context_for_job_access_v2(
                request,
                service_started_at=service_started_at,
                job=job,
                required_grant="sir-convert:jobs:read-own",
            )
            job = require_job_access_v2(
                auth_context=auth_context,
                job=job,
                required_grant="sir-convert:jobs:read-own",
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
                conversion_metadata=_conversion_metadata_for_job(job),
                warnings=job.warnings,
            ),
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.get("/v2/convert/jobs/{job_id}/artifact")
    async def get_artifact(job_id: str, request: Request) -> Response:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        auth_context = auth_context_for_job_access_v2(
            request,
            service_started_at=service_started_at,
            job=job,
            required_grant="sir-convert:artifacts:read-own",
        )
        job = require_job_access_v2(
            auth_context=auth_context,
            job=job,
            required_grant="sir-convert:artifacts:read-own",
            access_denied_code="artifact_access_denied",
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

    @router.get("/v2/convert/jobs/{job_id}/artifacts")
    async def get_artifact_bundle_manifest(job_id: str, request: Request) -> Response:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        public_grant = None
        if is_public_job_v2(job):
            if job is None:
                raise ServiceError(
                    status_code=404,
                    code="job_not_found",
                    message="Job not found or expired.",
                    retryable=False,
                )
            public_grant = require_public_job_access_v2(
                request=request,
                service_started_at=service_started_at,
                job=job,
            )
            require_public_artifact_read_lease_v2(
                request=request,
                service_started_at=service_started_at,
                verified_grant=public_grant,
                job=job,
                artifact_key=public_bundle_manifest_artifact_key_v2(),
            )
        else:
            auth_context = auth_context_for_job_access_v2(
                request,
                service_started_at=service_started_at,
                job=job,
                required_grant="sir-convert:artifacts:read-own",
            )
            job = require_job_access_v2(
                auth_context=auth_context,
                job=job,
                required_grant="sir-convert:artifacts:read-own",
                access_denied_code="artifact_access_denied",
            )
        _require_digiexam_bundle_job(job)
        pending = _pending_or_unsuccessful_response(job)
        if pending is not None:
            return pending
        if public_grant is not None:
            manifest = load_public_bundle_manifest_v2(
                request=request,
                service_started_at=service_started_at,
                job=job,
                verified_grant=public_grant,
            )
            return JSONResponse(status_code=200, content=manifest)
        return FileResponse(
            path=job.artifact_path.as_posix(),
            media_type="application/json",
            filename=job.artifact_path.name,
        )

    @router.get("/v2/convert/jobs/{job_id}/artifacts/{artifact_key}")
    async def get_named_artifact(job_id: str, artifact_key: str, request: Request) -> Response:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if is_public_job_v2(job):
            if job is None:
                raise ServiceError(
                    status_code=404,
                    code="job_not_found",
                    message="Job not found or expired.",
                    retryable=False,
                )
            public_grant = require_public_job_access_v2(
                request=request,
                service_started_at=service_started_at,
                job=job,
            )
            require_public_artifact_read_lease_v2(
                request=request,
                service_started_at=service_started_at,
                verified_grant=public_grant,
                job=job,
                artifact_key=artifact_key,
            )
        else:
            auth_context = auth_context_for_job_access_v2(
                request,
                service_started_at=service_started_at,
                job=job,
                required_grant="sir-convert:artifacts:read-own",
            )
            job = require_job_access_v2(
                auth_context=auth_context,
                job=job,
                required_grant="sir-convert:artifacts:read-own",
                access_denied_code="artifact_access_denied",
            )
        _require_digiexam_bundle_job(job)
        pending = _pending_or_unsuccessful_response(job)
        if pending is not None:
            return pending
        resolved = resolve_digiexam_migration_artifact(job=job, artifact_key=artifact_key)
        return FileResponse(
            path=resolved.path.as_posix(),
            media_type=resolved.content_type,
            filename=resolved.filename,
        )

    @router.get("/v2/convert/jobs/{job_id}/artifact/partial")
    async def get_partial_artifact(job_id: str, request: Request) -> Response:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        auth_context = auth_context_for_job_access_v2(
            request,
            service_started_at=service_started_at,
            job=job,
            required_grant="sir-convert:artifacts:read-own",
        )
        job = require_job_access_v2(
            auth_context=auth_context,
            job=job,
            required_grant="sir-convert:artifacts:read-own",
            access_denied_code="artifact_access_denied",
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
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        auth_context = auth_context_for_job_access_v2(
            request,
            service_started_at=service_started_at,
            job=job,
            required_grant="sir-convert:jobs:read-own",
        )
        job = require_job_access_v2(
            auth_context=auth_context,
            job=job,
            required_grant="sir-convert:jobs:read-own",
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


def _require_digiexam_bundle_job(job: StoredJobV2) -> None:
    if job.output_format == OutputFormatV2.EXAMNET_MIGRATION_BUNDLE:
        return
    raise ServiceError(
        status_code=409,
        code="artifact_bundle_not_supported",
        message="Named artifact bundle routes are only supported for bundle outputs.",
        retryable=False,
        details={"output_format": job.output_format.value},
    )


def _pending_or_unsuccessful_response(job: StoredJobV2) -> Response | None:
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
    return None


def _conversion_metadata_for_job(
    job: StoredJobV2,
) -> ConversionMetadataV2 | DigiExamMigrationConversionMetadataV2:
    if job.output_format == OutputFormatV2.EXAMNET_MIGRATION_BUNDLE:
        bundle_metadata = load_digiexam_migration_result_metadata(job=job)
        return DigiExamMigrationConversionMetadataV2(
            pipeline_used=_required_pipeline_used(job),
            backend_used=job.backend_used,
            acceleration_used=job.acceleration_used,
            ocr_enabled=job.ocr_enabled,
            ocr_engine_used=job.ocr_engine_used,
            ocr_languages_used=job.ocr_languages_used,
            acceleration_policy_requested=job.acceleration_policy_requested,
            gpu_runtime_kind=job.gpu_runtime_kind,
            gpu_device_count=job.gpu_device_count,
            gpu_busy_percent=job.gpu_busy_percent,
            gpu_memory_used_percent=job.gpu_memory_used_percent,
            options_fingerprint=_required_options_fingerprint(job),
            template_id=job.template_id,
            template_version=job.template_version,
            template_artifact_sha256=job.template_artifact_sha256,
            parallel_enabled=job.parallel_enabled,
            max_chunk_workers=job.max_chunk_workers,
            chunk_size_pages=job.chunk_size_pages,
            effective_gpu_stage_limit=job.effective_gpu_stage_limit,
            scheduling_mode=job.scheduling_mode,
            route_key="digiexam_dxe_to_examnet_migration_bundle",
            bundle_schema_version="digiexam_migration_bundle_v1",
            bundle_status=bundle_metadata.bundle_status,
            source_sha256=bundle_metadata.source_sha256,
            target_availability=bundle_metadata.target_availability,
            manual_follow_up_required=bundle_metadata.manual_follow_up_required,
            warning_count=bundle_metadata.warning_count,
            artifact_count=bundle_metadata.artifact_count,
        )
    return ConversionMetadataV2(
        pipeline_used=_required_pipeline_used(job),
        backend_used=job.backend_used,
        acceleration_used=job.acceleration_used,
        ocr_enabled=job.ocr_enabled,
        ocr_engine_used=job.ocr_engine_used,
        ocr_languages_used=job.ocr_languages_used,
        acceleration_policy_requested=job.acceleration_policy_requested,
        gpu_runtime_kind=job.gpu_runtime_kind,
        gpu_device_count=job.gpu_device_count,
        gpu_busy_percent=job.gpu_busy_percent,
        gpu_memory_used_percent=job.gpu_memory_used_percent,
        options_fingerprint=_required_options_fingerprint(job),
        template_id=job.template_id,
        template_version=job.template_version,
        template_artifact_sha256=job.template_artifact_sha256,
        parallel_enabled=job.parallel_enabled,
        max_chunk_workers=job.max_chunk_workers,
        chunk_size_pages=job.chunk_size_pages,
        effective_gpu_stage_limit=job.effective_gpu_stage_limit,
        scheduling_mode=job.scheduling_mode,
    )


def _required_pipeline_used(job: StoredJobV2) -> str:
    if job.pipeline_used is None:
        raise ServiceError(
            status_code=500,
            code="result_missing_metadata",
            message="Successful job is missing conversion metadata.",
            retryable=False,
        )
    return job.pipeline_used


def _required_options_fingerprint(job: StoredJobV2) -> str:
    if job.options_fingerprint is None:
        raise ServiceError(
            status_code=500,
            code="result_missing_metadata",
            message="Successful job is missing conversion metadata.",
            retryable=False,
        )
    return job.options_fingerprint
