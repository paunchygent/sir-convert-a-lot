"""Job lifecycle HTTP routes for Sir Convert-a-Lot service API v2.

Purpose:
    Provide v2 job create/status/result/artifact/cancel endpoints as an isolated
    router for the unified conversion API surface, enabling multi-format
    conversions (pdf/md/html -> md/pdf/docx).

Relationships:
    - Included by `interfaces.http_api` app factory.
    - Uses app-state runtime helpers from `interfaces.http_app_state`.
    - Targets v2 runtime behavior in `infrastructure.runtime_engine_v2`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    JobCreateResponseV2,
    JobLinksV2,
    JobProgressV2,
    JobRecordDataV2,
    JobRecordResponseV2,
)
from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    normalized_fingerprint_payload_for_spec_v2,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES
from scripts.sir_convert_a_lot.domain.specs_v2 import (
    JobSpecV2,
    SourceFormatV2,
    normalized_exam_migration_targets_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_config_v2 import fingerprint_for_request_v2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import (
    auth_context_for_job_access_v2,
    require_api_key_v2,
    require_internal_identity_auth_context_v2,
    require_job_access_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    CreateJobCompanionPartsV2,
    build_create_job_route_registry_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_public_exam_converter_access_v2 import (
    is_public_job_v2,
    issue_public_artifact_read_lease_fragment_v2,
    public_bundle_manifest_artifact_key_v2,
    public_conversion_grant_header_present_v2,
    require_public_create_access_v2,
    require_public_job_access_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_routes_job_artifacts_v2 import (
    register_job_artifact_routes_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_routes_job_resume_v2 import (
    register_job_resume_routes_v2,
)


def _make_job_links(job_id: str) -> JobLinksV2:
    return JobLinksV2(
        self=f"/v2/convert/jobs/{job_id}",
        result=f"/v2/convert/jobs/{job_id}/result",
        artifact=f"/v2/convert/jobs/{job_id}/artifact",
        cancel=f"/v2/convert/jobs/{job_id}/cancel",
    )


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
                total_pages=job.total_pages,
                processed_pages=job.processed_pages,
                failed_pages=job.failed_pages,
                percent_complete=job.percent_complete,
                pages_per_minute=job.pages_per_minute,
                eta_seconds=job.eta_seconds,
            ),
            links=_make_job_links(job.job_id),
        )
    )


def _infer_format_from_filename(filename: str) -> SourceFormatV2 | None:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return SourceFormatV2.PDF
    if suffix in {".md", ".markdown"}:
        return SourceFormatV2.MD
    if suffix in {".html", ".htm"}:
        return SourceFormatV2.HTML
    if suffix == ".docx":
        return SourceFormatV2.DOCX
    if suffix == ".dxe":
        return SourceFormatV2.DIGIEXAM_DXE
    return None


def build_job_router_v2(*, service_started_at: str) -> APIRouter:
    """Build v2 job router with stable app-state wiring."""
    router = APIRouter()
    route_registry = build_create_job_route_registry_v2()
    register_job_artifact_routes_v2(router=router, service_started_at=service_started_at)
    register_job_resume_routes_v2(router=router, service_started_at=service_started_at)

    @router.post(
        "/v2/convert/jobs",
        response_model=JobCreateResponseV2,
        responses={202: {"model": JobCreateResponseV2}},
    )
    async def create_job(
        request: Request,
        file: UploadFile = File(...),
        job_spec: str = Form(...),
        resources: UploadFile | None = File(None),
        reference_docx: UploadFile | None = File(None),
        graded_result_pdf: UploadFile | None = File(None),
        parity_pdf: UploadFile | None = File(None),
        digiexam_ingestion_overlay: UploadFile | None = File(None),
        wait_seconds: int = Query(default=0, ge=0, le=20),
    ) -> JSONResponse:
        auth_context = require_api_key_v2(request, service_started_at=service_started_at)
        owner_scope = auth_context.owner_api_key_scope
        public_grant_access = None
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
                details={"errors": exc.errors(include_context=False)},
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

        route_handler = route_registry.require_handler_for_spec(spec)
        if route_handler.policy.create_required_grant is not None:
            if public_conversion_grant_header_present_v2(request):
                public_grant_access = require_public_create_access_v2(
                    request=request,
                    service_started_at=service_started_at,
                    requested_targets=frozenset(
                        target.value for target in normalized_exam_migration_targets_v2(spec)
                    ),
                )
                owner_scope = public_grant_access.owner_scope
            else:
                auth_context = require_internal_identity_auth_context_v2(
                    request,
                    service_started_at=service_started_at,
                    required_grant=route_handler.policy.create_required_grant,
                )
                owner_scope = auth_context.owner_api_key_scope
        form = await request.form()
        prepared_route = await route_handler.prepare(
            spec=spec,
            config=runtime.config,
            primary_payload_size=len(payload_bytes),
            parts=CreateJobCompanionPartsV2(
                resources=resources,
                reference_docx=reference_docx,
                graded_result_pdf=graded_result_pdf,
                parity_pdf=parity_pdf,
                digiexam_ingestion_overlay=digiexam_ingestion_overlay,
                form_part_names=frozenset(str(key) for key in form.keys()),
            ),
        )

        scope_key = f"{owner_scope}:POST:/v2/convert/jobs:{idempotency_key}"
        file_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        request_fingerprint = fingerprint_for_request_v2(
            spec_payload=normalized_fingerprint_payload_for_spec_v2(
                raw_payload=raw_spec,
                spec=spec,
            ),
            file_sha256=file_sha256,
            resources_sha256=prepared_route.resources_sha256,
            reference_docx_sha256=prepared_route.reference_docx_sha256,
            graded_result_pdf_sha256=prepared_route.graded_result_pdf_sha256,
            parity_pdf_sha256=prepared_route.parity_pdf_sha256,
            digiexam_ingestion_overlay_sha256=(prepared_route.digiexam_ingestion_overlay_sha256),
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
            if public_grant_access is not None:
                body["public_artifact_read_lease"] = issue_public_artifact_read_lease_fragment_v2(
                    request=request,
                    service_started_at=service_started_at,
                    verified_grant=public_grant_access,
                    job=existing_job,
                    artifact_key=public_bundle_manifest_artifact_key_v2(),
                )
            replay_status_code = 200 if existing_job.status in TERMINAL_JOB_STATUSES else 202
            response = JSONResponse(status_code=replay_status_code, content=body)
            response.headers["X-Idempotent-Replay"] = "true"
            return response

        job = runtime.create_job(
            spec=spec,
            owner_api_key_scope=owner_scope,
            upload_bytes=payload_bytes,
            resources_zip_bytes=prepared_route.resources_zip_bytes,
            reference_docx_bytes=prepared_route.reference_docx_bytes,
            graded_result_pdf_bytes=prepared_route.graded_result_pdf_bytes,
            parity_pdf_bytes=prepared_route.parity_pdf_bytes,
            digiexam_ingestion_overlay_bytes=(prepared_route.digiexam_ingestion_overlay_bytes),
        )
        runtime.put_idempotency(scope_key, request_fingerprint, job.job_id)
        if runtime.config.run_jobs_on_submit:
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
        if public_grant_access is not None:
            payload["public_artifact_read_lease"] = issue_public_artifact_read_lease_fragment_v2(
                request=request,
                service_started_at=service_started_at,
                verified_grant=public_grant_access,
                job=current,
                artifact_key=public_bundle_manifest_artifact_key_v2(),
            )
        return JSONResponse(status_code=response_status, content=payload)

    @router.get("/v2/convert/jobs/{job_id}", response_model=JobRecordResponseV2)
    async def get_job(job_id: str, request: Request) -> JSONResponse:
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
            payload = _job_record_response(job).model_dump(mode="json")
            return JSONResponse(status_code=200, content=payload)
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
        payload = _job_record_response(job).model_dump(mode="json")
        return JSONResponse(status_code=200, content=payload)

    @router.post(
        "/v2/convert/jobs/{job_id}/cancel",
        response_model=JobRecordResponseV2,
        responses={202: {"model": JobRecordResponseV2}},
    )
    async def cancel_job(job_id: str, request: Request) -> JSONResponse:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        auth_context = auth_context_for_job_access_v2(
            request,
            service_started_at=service_started_at,
            job=job,
            required_grant="sir-convert:jobs:cancel-own",
        )
        require_job_access_v2(
            auth_context=auth_context,
            job=job,
            required_grant="sir-convert:jobs:cancel-own",
        )
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
