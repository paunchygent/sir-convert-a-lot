"""Structured-LLM admission helper for Service API v2 create-job routes.

Purpose:
    Resolve structured-LLM provider admission snapshots for v2 job creation
    without making the primary jobs router own provider-routing details.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2` during fresh job admission.
    - Reads runtime config from `interfaces.http_app_state`.
    - Delegates provider policy checks to `infrastructure.structured_llm_admission`.
"""

from __future__ import annotations

from fastapi import Request

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.domain.structured_llm_admission import (
    StructuredLLMAdmittedRouteSnapshot,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.structured_llm_admission import (
    StructuredLLMAdmissionError,
    resolve_structured_llm_admission_snapshot,
)
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_structured_llm_settings_state_v2 import (
    structured_llm_hot_settings_store_for_request,
)


def structured_llm_admission_for_create_request_v2(
    *,
    spec: JobSpecV2,
    request: Request,
    service_started_at: str,
    public_grant_request: bool,
) -> StructuredLLMAdmittedRouteSnapshot | None:
    """Resolve the structured-LLM admission snapshot for one create request."""
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    hot_settings_store = None
    if (
        runtime.config.structured_llm.enabled
        and runtime.config.structured_llm.provider_set is not None
    ):
        hot_settings_store = structured_llm_hot_settings_store_for_request(
            request,
            service_started_at=service_started_at,
        )
    try:
        return resolve_structured_llm_admission_snapshot(
            spec=spec,
            structured_config=runtime.config.structured_llm,
            hot_settings_store=hot_settings_store,
            public_grant_request=public_grant_request,
        )
    except StructuredLLMAdmissionError as exc:
        raise ServiceError(
            status_code=403,
            code="structured_llm_route_admission_rejected",
            message="Structured LLM provider routing is not allowed for this job.",
            retryable=False,
            details={"failure_code": exc.failure_code.value},
        ) from exc
