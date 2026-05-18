"""Source-neutral matching correction HTTP routes for service API v2.

Purpose:
    Expose the producer-owned authoring route that applies teacher-provided
    matching answer keys to `ExamAuthoringIR v1` interactions and returns
    effective state plus target readiness for consumers.

Relationships:
    - Included by `interfaces.http_api` alongside the v2 job lifecycle routers.
    - Delegates matching application to
      `application.exam_authoring_matching_apply_contracts`.
    - Keeps source-neutral matching submit separate from DigiExam ingestion
      overlays and job companions.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from scripts.sir_convert_a_lot.application.exam_authoring_matching_apply_contracts import (
    ExamAuthoringMatchingManualAnswerKeyApplyRequest,
    ExamAuthoringMatchingManualAnswerKeyApplyResponse,
    apply_matching_manual_answer_key_request,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_matching_manual_answer_key import (
    ExamAuthoringMatchingManualAnswerKeyError,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import require_api_key_v2


def build_exam_authoring_matching_router_v2(*, service_started_at: str) -> APIRouter:
    """Build the source-neutral matching apply router."""

    router = APIRouter()

    @router.post(
        "/v2/exam-authoring/matching/manual-answer-key/apply",
        response_model=ExamAuthoringMatchingManualAnswerKeyApplyResponse,
    )
    async def apply_matching_manual_answer_key(
        request: Request,
        request_body: ExamAuthoringMatchingManualAnswerKeyApplyRequest,
    ) -> JSONResponse:
        require_api_key_v2(request, service_started_at=service_started_at)
        try:
            response = apply_matching_manual_answer_key_request(request_body)
        except ExamAuthoringMatchingManualAnswerKeyError as exc:
            raise ServiceError(
                status_code=422,
                code=exc.code,
                message=str(exc),
                retryable=False,
                details=exc.details,
            ) from exc
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))

    return router
