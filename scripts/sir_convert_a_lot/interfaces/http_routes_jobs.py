"""Job lifecycle HTTP routes for Sir Convert-a-Lot.

Purpose:
    Provide v1 job create/status/result/cancel endpoints as an isolated router.

Relationships:
    - Included by `interfaces.http_api` app factory.
    - Uses app-state runtime helpers from `interfaces.http_app_state`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.contracts import (
    ArtifactMetadata,
    ConversionMetadata,
    JobLinks,
    JobPendingResultResponse,
    JobProgress,
    JobRecordData,
    JobRecordResponse,
    JobResultResponse,
    ResultPayload,
)
from scripts.sir_convert_a_lot.domain.specs import (
    TERMINAL_JOB_STATUSES,
    JobSpec,
    JobStatus,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine import (
    ServiceError,
    StoredJob,
    fingerprint_for_request,
)
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_for_request


def _make_job_links(job_id: str) -> JobLinks:
    return JobLinks(
        self=f"/v1/convert/jobs/{job_id}",
        result=f"/v1/convert/jobs/{job_id}/result",
        cancel=f"/v1/convert/jobs/{job_id}/cancel",
    )


def _job_record_response(job: StoredJob) -> JobRecordResponse:
    return JobRecordResponse(
        job=JobRecordData(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
            source_filename=job.source_filename,
            progress=JobProgress(
                stage=job.progress_stage,
                pages_total=job.pages_total,
                pages_processed=job.pages_processed,
                last_heartbeat_at=job.last_heartbeat_at,
                current_phase_started_at=job.current_phase_started_at,
                phase_timings_ms=job.phase_timings_ms,
            ),
            links=_make_job_links(job.job_id),
        )
    )


def _require_api_key(request: Request, *, service_started_at: str) -> None:
    runtime = runtime_for_request(request, utc_now_iso=service_started_at)
    api_key = request.headers.get("X-API-Key")
    if api_key != runtime.config.api_key:
        raise ServiceError(
            status_code=401,
            code="auth_invalid_api_key",
            message="Missing or invalid X-API-Key.",
            retryable=False,
        )


def build_job_router(*, service_started_at: str) -> APIRouter:
    """Build job router with stable app-state wiring."""
    router = APIRouter()

    @router.post("/v1/convert/jobs")
    async def create_job(
        request: Request,
        file: UploadFile = File(...),
        job_spec: str = Form(...),
        wait_seconds: int = Query(default=0, ge=0, le=20),
    ) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_for_request(request, utc_now_iso=service_started_at)

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
        if not file_name.lower().endswith(".pdf"):
            raise ServiceError(
                status_code=415,
                code="unsupported_media_type",
                message="Only PDF uploads are supported.",
                retryable=False,
            )

        payload_bytes = await file.read()
        if len(payload_bytes) == 0:
            raise ServiceError(
                status_code=422,
                code="pdf_unreadable",
                message="Uploaded PDF is empty or unreadable.",
                retryable=False,
            )
        if len(payload_bytes) > runtime.config.max_upload_bytes:
            raise ServiceError(
                status_code=413,
                code="payload_too_large",
                message="Uploaded PDF exceeds configured size limit.",
                retryable=False,
            )

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
            spec = JobSpec.model_validate(raw_spec)
        except ValidationError as exc:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Job specification failed validation.",
                retryable=False,
                details={"errors": exc.errors()},
            ) from exc

        if spec.source.kind.value != "upload":
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="source.kind must be 'upload' in v1.",
                retryable=False,
                details={"field": "source.kind"},
            )

        runtime.validate_backend_strategy(spec)
        runtime.validate_acceleration_policy(spec)

        api_key = request.headers.get("X-API-Key", "")
        scope_key = f"{api_key}:POST:/v1/convert/jobs:{idempotency_key}"
        file_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        request_fingerprint = fingerprint_for_request(raw_spec, file_sha256)

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

        job = runtime.create_job(spec=spec, upload_bytes=payload_bytes, source_filename=file_name)
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

    @router.get("/v1/convert/jobs/{job_id}")
    async def get_job(job_id: str, request: Request) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_for_request(request, utc_now_iso=service_started_at)
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

    @router.get("/v1/convert/jobs/{job_id}/result")
    async def get_result(
        job_id: str, request: Request, inline: bool = Query(default=False)
    ) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        if job is None:
            raise ServiceError(
                status_code=404,
                code="job_not_found",
                message="Job not found or expired.",
                retryable=False,
            )

        if job.status not in TERMINAL_JOB_STATUSES:
            pending = JobPendingResultResponse(job_id=job.job_id, status=job.status)
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

        markdown_content: str | None = None
        if inline:
            if job.artifact_size_bytes > runtime.config.inline_max_bytes:
                raise ServiceError(
                    status_code=413,
                    code="result_inline_too_large",
                    message="Result artifact exceeds inline response size limit.",
                    retryable=False,
                )
            markdown_content = job.artifact_path.read_text(encoding="utf-8")

        if (
            job.backend_used is None
            or job.acceleration_used is None
            or job.ocr_enabled is None
            or job.options_fingerprint is None
        ):
            raise ServiceError(
                status_code=500,
                code="result_missing_metadata",
                message="Successful job is missing conversion metadata.",
                retryable=False,
            )

        payload = JobResultResponse(
            job_id=job.job_id,
            result=ResultPayload(
                artifact=ArtifactMetadata(
                    markdown_filename=job.artifact_path.name,
                    size_bytes=job.artifact_size_bytes,
                    sha256=job.artifact_sha256,
                ),
                conversion_metadata=ConversionMetadata(
                    backend_used=job.backend_used,
                    acceleration_used=job.acceleration_used,
                    ocr_enabled=job.ocr_enabled,
                    table_mode=job.spec.conversion.table_mode,
                    options_fingerprint=job.options_fingerprint,
                ),
                warnings=job.warnings,
                markdown_content=markdown_content,
            ),
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.post("/v1/convert/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str, request: Request) -> JSONResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_for_request(request, utc_now_iso=service_started_at)
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
