"""Job lifecycle HTTP routes for Sir Convert-a-Lot service API v2.

Purpose:
    Provide v2 job create/status/result/artifact/cancel endpoints as an isolated
    router, enabling multi-format conversions (md/html/pdf -> pdf/docx) while
    preserving the locked v1 PDF->MD contract.

Relationships:
    - Included by `interfaces.http_api` app factory alongside v1 routes.
    - Uses app-state runtime helpers from `interfaces.http_app_state`.
    - Targets v2 runtime behavior in `infrastructure.runtime_engine_v2`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    ArtifactMetadataV2,
    ConversionMetadataV2,
    JobLinksV2,
    JobPendingResultResponseV2,
    JobProgressV2,
    JobRecordDataV2,
    JobRecordResponseV2,
    JobResultResponseV2,
    ResultPayloadV2,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_config_v2 import fingerprint_for_request_v2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request


def _make_job_links(job_id: str) -> JobLinksV2:
    return JobLinksV2(
        self=f"/v2/convert/jobs/{job_id}",
        result=f"/v2/convert/jobs/{job_id}/result",
        artifact=f"/v2/convert/jobs/{job_id}/artifact",
        cancel=f"/v2/convert/jobs/{job_id}/cancel",
    )


def _content_type_for_output(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.PDF:
        return "application/pdf"
    if output_format == OutputFormatV2.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise AssertionError(f"Unsupported output_format: {output_format}")


def _job_record_response(job: StoredJobV2) -> JobRecordResponseV2:
    return JobRecordResponseV2(
        job=JobRecordDataV2(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
            source_filename=job.source_filename,
            source_format=job.source_format,
            output_format=job.output_format,
            progress=JobProgressV2(
                stage=job.progress_stage,
                last_heartbeat_at=job.last_heartbeat_at,
                current_phase_started_at=job.current_phase_started_at,
                phase_timings_ms=job.phase_timings_ms,
            ),
            links=_make_job_links(job.job_id),
        )
    )


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


def _infer_format_from_filename(filename: str) -> SourceFormatV2 | None:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return SourceFormatV2.PDF
    if suffix in {".md", ".markdown"}:
        return SourceFormatV2.MD
    if suffix in {".html", ".htm"}:
        return SourceFormatV2.HTML
    return None


def build_job_router_v2(*, service_started_at: str) -> APIRouter:
    """Build v2 job router with stable app-state wiring."""
    router = APIRouter()

    @router.post("/v2/convert/jobs")
    async def create_job(
        request: Request,
        file: UploadFile = File(...),
        job_spec: str = Form(...),
        resources: UploadFile | None = File(None),
        reference_docx: UploadFile | None = File(None),
        wait_seconds: int = Query(default=0, ge=0, le=20),
    ) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)

        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key is None or idempotency_key.strip() == "":
            raise ServiceError(
                status_code=400,
                code="idempotency_key_missing",
                message="Missing required Idempotency-Key header.",
                retryable=False,
            )

        if file.filename is None or file.filename.strip() == "":
            raise ServiceError(
                status_code=400,
                code="validation_error",
                message="Uploaded file must include a filename.",
                retryable=False,
                details={"field": "file.filename"},
            )

        file_name = file.filename.rsplit("/", maxsplit=1)[-1].rsplit("\\", maxsplit=1)[-1]
        inferred_format = _infer_format_from_filename(file_name)
        if inferred_format is None:
            raise ServiceError(
                status_code=415,
                code="unsupported_media_type",
                message="Unsupported upload type for v2.",
                retryable=False,
                details={"filename": file_name},
            )

        payload_bytes = await file.read()
        if len(payload_bytes) == 0:
            raise ServiceError(
                status_code=422,
                code="input_unreadable",
                message="Uploaded file is empty or unreadable.",
                retryable=False,
            )
        if len(payload_bytes) > runtime.config.max_upload_bytes:
            raise ServiceError(
                status_code=413,
                code="payload_too_large",
                message="Uploaded file exceeds configured size limit.",
                retryable=False,
            )

        resources_bytes: bytes | None = None
        resources_sha256: str | None = None
        if resources is not None:
            resources_bytes = await resources.read()
            if len(resources_bytes) > runtime.config.max_upload_bytes:
                raise ServiceError(
                    status_code=413,
                    code="payload_too_large",
                    message="Uploaded resources zip exceeds configured size limit.",
                    retryable=False,
                )
            resources_sha256 = hashlib.sha256(resources_bytes).hexdigest()

        reference_docx_bytes: bytes | None = None
        reference_docx_sha256: str | None = None
        if reference_docx is not None:
            if reference_docx.filename is None or reference_docx.filename.strip() == "":
                raise ServiceError(
                    status_code=400,
                    code="validation_error",
                    message="Uploaded reference_docx must include a filename.",
                    retryable=False,
                    details={"field": "reference_docx.filename"},
                )
            if not reference_docx.filename.lower().endswith(".docx"):
                raise ServiceError(
                    status_code=415,
                    code="unsupported_media_type",
                    message="reference_docx must be a .docx file.",
                    retryable=False,
                )
            reference_docx_bytes = await reference_docx.read()
            if len(reference_docx_bytes) > runtime.config.max_upload_bytes:
                raise ServiceError(
                    status_code=413,
                    code="payload_too_large",
                    message="Uploaded reference_docx exceeds configured size limit.",
                    retryable=False,
                )
            reference_docx_sha256 = hashlib.sha256(reference_docx_bytes).hexdigest()

        try:
            raw_spec_object = json.loads(job_spec)
        except json.JSONDecodeError as exc:
            raise ServiceError(
                status_code=400,
                code="validation_error",
                message=f"Invalid job_spec JSON: {exc.msg}",
                retryable=False,
            ) from exc

        if not isinstance(raw_spec_object, dict):
            raise ServiceError(
                status_code=400,
                code="validation_error",
                message="job_spec must decode into a JSON object.",
                retryable=False,
            )

        raw_spec: dict[str, object] = raw_spec_object

        try:
            spec = JobSpecV2.model_validate(raw_spec)
        except ValidationError as exc:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Job specification failed validation.",
                retryable=False,
                details={"errors": exc.errors()},
            ) from exc

        if spec.source.filename != file_name:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="job_spec.source.filename must match the uploaded file name.",
                retryable=False,
                details={"job_spec_filename": spec.source.filename, "upload_filename": file_name},
            )
        if spec.source.format != inferred_format:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="job_spec.source.format must match the uploaded file extension.",
                retryable=False,
                details={
                    "job_spec_format": spec.source.format.value,
                    "upload_format": inferred_format.value,
                },
            )

        api_key = request.headers.get("X-API-Key", "")
        scope_key = f"{api_key}:POST:/v2/convert/jobs:{idempotency_key}"
        file_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        request_fingerprint = fingerprint_for_request_v2(
            spec_payload=raw_spec,
            file_sha256=file_sha256,
            resources_sha256=resources_sha256,
            reference_docx_sha256=reference_docx_sha256,
        )

        existing_record = runtime.get_idempotency(scope_key)
        if existing_record is not None:
            if existing_record.fingerprint != request_fingerprint:
                raise ServiceError(
                    status_code=409,
                    code="idempotency_key_reused_with_different_payload",
                    message=(
                        "Idempotency-Key was already used with a different request payload "
                        "within the idempotency window."
                    ),
                    retryable=False,
                )
            existing_job = runtime.get_job(existing_record.job_id)
            if existing_job is None:
                raise ServiceError(
                    status_code=404,
                    code="job_not_found",
                    message="Idempotent job no longer exists.",
                    retryable=False,
                )
            body = _job_record_response(existing_job).model_dump(mode="json")
            replay_status_code = 200 if existing_job.status in TERMINAL_JOB_STATUSES else 202
            response = JSONResponse(status_code=replay_status_code, content=body)
            response.headers["X-Idempotent-Replay"] = "true"
            return response

        job = runtime.create_job(
            spec=spec,
            upload_bytes=payload_bytes,
            resources_zip_bytes=resources_bytes,
            reference_docx_bytes=reference_docx_bytes,
        )
        runtime.put_idempotency(scope_key, request_fingerprint, job.job_id)
        runtime.run_job_async(job.job_id)

        deadline = time.monotonic() + wait_seconds
        current = runtime.get_job(job.job_id)
        while (
            current is not None
            and current.status not in TERMINAL_JOB_STATUSES
            and time.monotonic() < deadline
        ):
            await asyncio.sleep(0.05)
            current = runtime.get_job(job.job_id)

        if current is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job expired or was removed before response could be returned.",
                retryable=False,
            )

        response_status = 200 if current.status in TERMINAL_JOB_STATUSES else 202
        payload = _job_record_response(current).model_dump(mode="json")
        return JSONResponse(status_code=response_status, content=payload)

    @router.get("/v2/convert/jobs/{job_id}")
    async def get_job(job_id: str, request: Request) -> JSONResponse:
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
        payload = _job_record_response(job).model_dump(mode="json")
        return JSONResponse(status_code=200, content=payload)

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
                    options_fingerprint=job.options_fingerprint,
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

    @router.post("/v2/convert/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str, request: Request) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        result = runtime.cancel_job(job_id)
        if result == "missing":
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )
        if result == "conflict":
            raise ServiceError(
                status_code=409,
                code="job_not_cancelable",
                message="Terminal jobs cannot be canceled.",
                retryable=False,
            )

        job = runtime.get_job(job_id)
        if job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )

        status_code = 202 if result == "accepted" else 200
        payload = _job_record_response(job).model_dump(mode="json")
        return JSONResponse(status_code=status_code, content=payload)

    return router
