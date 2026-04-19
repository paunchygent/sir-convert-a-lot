"""Resume-from-checkpoint HTTP routes for Sir Convert-a-Lot service API v2.

Purpose:
    Keep resume semantics isolated from the main jobs router to avoid exceeding
    the 500 LoC guardrail while implementing ADR-0005 `POST /resume`.

Relationships:
    - Registered by `interfaces.http_routes_jobs_v2.build_job_router_v2`.
    - Uses v2 runtime behavior in `infrastructure.runtime_engine_v2`.
    - Clones checkpoint state via `infrastructure.pdf_resume_v2`.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    JobLinksV2,
    JobProgressV2,
    JobRecordDataV2,
    JobRecordResponseV2,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    checkpoint_path_for_job_upload,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_resume_v2 import (
    PdfResumeCheckpointMissingError,
    clone_pdf_checkpoint_state_for_resume,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_config_v2 import (
    fingerprint_for_resume_request_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import (
    require_api_key_v2,
    require_job_access_v2,
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


def register_job_resume_routes_v2(*, router: APIRouter, service_started_at: str) -> None:
    @router.post("/v2/convert/jobs/{job_id}/resume")
    async def resume_job(job_id: str, request: Request) -> JSONResponse:
        auth_context = require_api_key_v2(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)

        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key is None or idempotency_key.strip() == "":
            raise ServiceError(
                status_code=400,
                code="idempotency_key_missing",
                message="Missing required Idempotency-Key header.",
                retryable=False,
            )

        source_job = runtime.get_job(job_id)
        source_job = require_job_access_v2(auth_context=auth_context, job=source_job)

        if source_job.source_format != SourceFormatV2.PDF or source_job.output_format not in {
            OutputFormatV2.MD,
            OutputFormatV2.DOCX,
        }:
            raise ServiceError(
                status_code=409,
                code="resume_not_available",
                message="Resume is only supported for long-running PDF routes.",
                retryable=False,
            )

        if source_job.status not in {JobStatus.CANCELED, JobStatus.FAILED}:
            raise ServiceError(
                status_code=409,
                code="resume_not_available",
                message="Resume is only supported for terminal canceled/failed jobs.",
                retryable=False,
                details={"status": source_job.status.value},
            )

        checkpoint_path = checkpoint_path_for_job_upload(upload_path=source_job.upload_path)
        if not checkpoint_path.exists():
            raise ServiceError(
                status_code=409,
                code="resume_checkpoint_missing",
                message="Resume requires a valid checkpoint from the source job.",
                retryable=False,
            )
        checkpoint_sha256 = f"sha256:{hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()}"

        scope_key = (
            f"{auth_context.owner_api_key_scope}:POST:/v2/convert/jobs/{job_id}/resume:"
            f"{idempotency_key}"
        )
        request_fingerprint = fingerprint_for_resume_request_v2(
            source_job_id=job_id,
            source_spec_payload=source_job.spec.model_dump(mode="json"),
            checkpoint_sha256=checkpoint_sha256,
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

        resources_zip_bytes = (
            source_job.resources_zip_path.read_bytes()
            if source_job.resources_zip_path is not None
            else None
        )
        reference_docx_bytes = (
            source_job.reference_docx_path.read_bytes()
            if source_job.reference_docx_path is not None
            else None
        )
        resumed_job = runtime.create_job(
            spec=source_job.spec,
            owner_api_key_scope=auth_context.owner_api_key_scope,
            upload_bytes=source_job.upload_path.read_bytes(),
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=reference_docx_bytes,
        )

        try:
            seed = clone_pdf_checkpoint_state_for_resume(
                source_upload_path=source_job.upload_path,
                destination_upload_path=resumed_job.upload_path,
                destination_job_id=resumed_job.job_id,
            )
        except PdfResumeCheckpointMissingError as exc:
            raise ServiceError(
                status_code=409,
                code="resume_checkpoint_missing",
                message=str(exc),
                retryable=False,
            ) from exc

        runtime.job_store.annotate_resume_metadata(
            job_id=resumed_job.job_id,
            resumed_from_job_id=job_id,
            checkpoint_sha256=seed.checkpoint_sha256,
        )
        runtime.put_idempotency(scope_key, request_fingerprint, resumed_job.job_id)
        runtime.run_job_async(resumed_job.job_id)

        payload = _job_record_response(resumed_job).model_dump(mode="json")
        return JSONResponse(status_code=202, content=payload)
