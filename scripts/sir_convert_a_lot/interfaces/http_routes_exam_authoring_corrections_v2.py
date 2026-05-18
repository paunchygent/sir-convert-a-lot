"""Source-neutral exam authoring correction HTTP routes for service API v2.

Purpose:
    Expose the unified producer-owned correction route that applies
    source-bound teacher corrections to exam authoring state and returns
    effective state plus readiness for consumers.

Relationships:
    - Included by `interfaces.http_api` alongside the v2 job lifecycle routers.
    - Delegates correction application to
      `application.exam_authoring_corrections_apply_contracts`.
    - Delegates source-state bundle issuance to
      `application.exam_authoring_correction_source_state_issuer`.
    - Replaces the superseded Task 324 matching-specific apply route.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_issuer import (
    ExamAuthoringCorrectionSourceStateIssueError,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_issuer import (
    issue_exam_authoring_correction_source_state as issue_source_state_bundle,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceStateIssueRequestV1,
    ExamAuthoringCorrectionSourceStateIssueResultV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_contracts import (
    ExamAuthoringCorrectionsApplyError,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionsApplyResultV1,
    apply_exam_authoring_corrections_request,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import (
    auth_context_for_job_access_v2,
    require_api_key_v2,
    require_job_access_v2,
)


def build_exam_authoring_corrections_router_v2(
    *,
    service_started_at: str,
    source_state_signature_secret: str | None,
) -> APIRouter:
    """Build the unified source-neutral correction apply router."""

    router = APIRouter()

    @router.post(
        "/v2/exam-authoring/corrections/source-state/issue",
        response_model=ExamAuthoringCorrectionSourceStateIssueResultV1,
    )
    async def issue_exam_authoring_correction_source_state(
        request: Request,
        request_body: ExamAuthoringCorrectionSourceStateIssueRequestV1,
    ) -> JSONResponse:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(request_body.job_id)
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
            access_denied_code="exam_authoring_source_state_access_denied",
        )
        try:
            response = issue_source_state_bundle(
                request_body,
                job=job,
                source_state_signature_secret=source_state_signature_secret,
            )
        except ExamAuthoringCorrectionSourceStateIssueError as exc:
            raise ServiceError(
                status_code=exc.status_code,
                code=exc.code,
                message=str(exc),
                retryable=False,
                details=exc.details,
            ) from exc
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))

    @router.post(
        "/v2/exam-authoring/corrections/apply",
        response_model=ExamAuthoringCorrectionsApplyResultV1,
    )
    async def apply_exam_authoring_corrections(
        request: Request,
        request_body: ExamAuthoringCorrectionsApplyRequestV1,
    ) -> JSONResponse:
        require_api_key_v2(request, service_started_at=service_started_at)
        try:
            response = apply_exam_authoring_corrections_request(
                request_body,
                source_state_signature_secret=source_state_signature_secret,
            )
        except ExamAuthoringCorrectionsApplyError as exc:
            raise ServiceError(
                status_code=422,
                code=exc.code,
                message=str(exc),
                retryable=False,
                details=exc.details,
            ) from exc
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))

    return router
