"""Job artifact and checkpoint HTTP routes for Sir Convert-a-Lot service API v2.

Purpose:
    Expose owner-scoped terminal result, primary artifact, named bundle
    artifact, and long-PDF partial/checkpoint reads without mixing retrieval
    concerns into job admission, status, cancellation, or correction replay
    artifact resolution.

Relationships:
    - Registered by `interfaces.http_routes_jobs_v2.build_job_router_v2`.
    - Registers the request-scoped correction replay artifact route family,
      which owns artifact-set and content-hash guarded replay downloads.
    - Uses v2 runtime behavior in `infrastructure.runtime_engine_v2`.
    - Reads PDF checkpoint/partial artifacts produced by
      `infrastructure.v2_conversion_executor`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    ArtifactMetadataV2,
    JobPendingResultResponseV2,
    JobResultResponseV2,
    ResultPayloadV2,
)
from scripts.sir_convert_a_lot.application.openapi_contracts_v2 import (
    DigiExamMigrationBundleManifestV2,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_artifacts import (
    build_audio_transcript_artifact_manifest,
    resolve_audio_transcript_artifact,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_artifacts import (
    resolve_digiexam_migration_artifact,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    public_artifact_filename,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
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
from scripts.sir_convert_a_lot.interfaces.http_job_result_metadata_v2 import (
    conversion_metadata_for_job_v2,
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
from scripts.sir_convert_a_lot.interfaces.http_routes_correction_replay_artifacts_v2 import (
    register_correction_replay_artifact_routes_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_terminal_artifact_responses_v2 import (
    terminal_artifact_response_v2,
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
    if output_format == OutputFormatV2.TRANSCRIPT_BUNDLE:
        return "application/json"
    raise AssertionError(f"Unsupported output_format: {output_format}")


def _primary_artifact_filename(job: StoredJobV2) -> str:
    if (
        job.source_format == SourceFormatV2.TRANSCRIPT_JSON
        and job.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE
    ):
        return "transcript_replay_bundle_manifest.json"
    return job.artifact_path.name


def _terminal_without_result_details(job: StoredJobV2) -> dict[str, object]:
    details: dict[str, object] = {"status": job.status.value}
    if job.status == JobStatus.FAILED:
        details["failure_retryable"] = job.failure_retryable
    return details


def register_job_artifact_routes_v2(*, router: APIRouter, service_started_at: str) -> None:
    register_correction_replay_artifact_routes_v2(
        router=router,
        service_started_at=service_started_at,
    )

    @router.get(
        "/v2/convert/jobs/{job_id}/result",
        response_model=JobResultResponseV2,
        responses={202: {"model": JobPendingResultResponseV2}},
    )
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
                details=_terminal_without_result_details(job),
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
                    filename=_primary_artifact_filename(job),
                    format=job.output_format,
                    size_bytes=job.artifact_size_bytes,
                    sha256=job.artifact_sha256,
                    content_type=_content_type_for_output(job.output_format),
                ),
                conversion_metadata=conversion_metadata_for_job_v2(job),
                warnings=job.warnings,
            ),
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.get(
        "/v2/convert/jobs/{job_id}/artifact",
        responses={202: {"model": JobPendingResultResponseV2}},
    )
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
                details=_terminal_without_result_details(job),
            )

        content_type = _content_type_for_output(job.output_format)
        return terminal_artifact_response_v2(
            runtime=runtime,
            job=job,
            artifact_key="primary",
            filesystem_path=job.artifact_path,
            content_type=content_type,
            filename=_primary_artifact_filename(job),
        )

    @router.get(
        "/v2/convert/jobs/{job_id}/artifacts",
        responses={
            200: {"model": DigiExamMigrationBundleManifestV2},
            202: {"model": JobPendingResultResponseV2},
        },
    )
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
        _require_named_artifact_bundle_job(job)
        pending = _pending_or_unsuccessful_response(job)
        if pending is not None:
            return pending
        if job.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE:
            return JSONResponse(
                status_code=200,
                content=build_audio_transcript_artifact_manifest(job=job),
            )
        if public_grant is not None:
            manifest = load_public_bundle_manifest_v2(
                request=request,
                service_started_at=service_started_at,
                job=job,
                verified_grant=public_grant,
                object_store=runtime.terminal_artifact_store,
            )
            return JSONResponse(status_code=200, content=manifest)
        return terminal_artifact_response_v2(
            runtime=runtime,
            job=job,
            artifact_key="primary",
            filesystem_path=job.artifact_path,
            content_type="application/json",
            filename=public_artifact_filename(
                job=job,
                key=DigiExamMigrationArtifactKey.BUNDLE_MANIFEST,
            ),
        )

    @router.get(
        "/v2/convert/jobs/{job_id}/artifacts/{artifact_key}",
        responses={202: {"model": JobPendingResultResponseV2}},
    )
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
        _require_named_artifact_bundle_job(job)
        pending = _pending_or_unsuccessful_response(job)
        if pending is not None:
            return pending
        if job.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE:
            resolved_audio = resolve_audio_transcript_artifact(
                job=job,
                artifact_key=artifact_key,
            )
            return terminal_artifact_response_v2(
                runtime=runtime,
                job=job,
                artifact_key=artifact_key,
                filesystem_path=resolved_audio.path,
                content_type=resolved_audio.content_type,
                filename=resolved_audio.filename,
            )
        resolved = resolve_digiexam_migration_artifact(
            job=job,
            artifact_key=artifact_key,
            object_store=runtime.terminal_artifact_store,
        )
        return terminal_artifact_response_v2(
            runtime=runtime,
            job=job,
            artifact_key=artifact_key,
            filesystem_path=resolved.path,
            content_type=resolved.content_type,
            filename=resolved.filename,
        )

    @router.get(
        "/v2/convert/jobs/{job_id}/artifact/partial",
        responses={202: {"model": JobPendingResultResponseV2}},
    )
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
                details=_terminal_without_result_details(job),
            )

        return FileResponse(
            path=partial_path.as_posix(),
            media_type="text/markdown",
            filename=partial_path.name,
        )

    @router.get(
        "/v2/convert/jobs/{job_id}/checkpoint",
        response_model=PdfCheckpointV2,
        responses={202: {"model": JobPendingResultResponseV2}},
    )
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
                details=_terminal_without_result_details(job),
            )

        return JSONResponse(status_code=200, content=checkpoint.model_dump(mode="json"))


def _require_named_artifact_bundle_job(job: StoredJobV2) -> None:
    if job.output_format in {
        OutputFormatV2.EXAMNET_MIGRATION_BUNDLE,
        OutputFormatV2.TRANSCRIPT_BUNDLE,
    }:
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
            details=_terminal_without_result_details(job),
        )
    return None
