"""Health/readiness HTTP routes for Sir Convert-a-Lot.

Purpose:
    Provide liveness (`/healthz`) and fail-closed readiness (`/readyz`)
    surfaces as a dedicated router.

Relationships:
    - Included by `interfaces.http_api` app factory.
    - Uses app-state helpers from `interfaces.http_app_state`.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from scripts.sir_convert_a_lot.application.contracts import (
    ServiceHealthResponse,
    ServiceReadinessReason,
    ServiceReadinessResponse,
)
from scripts.sir_convert_a_lot.interfaces.http_app_state import (
    metadata_for_app,
    resolve_eval_root_from_env,
    resolve_prod_root_from_env,
)


def build_health_router(*, app: FastAPI, service_started_at: str) -> APIRouter:
    """Build health router bound to app-state helpers."""
    router = APIRouter()

    @router.get("/healthz")
    async def healthcheck() -> ServiceHealthResponse:
        metadata = metadata_for_app(app, utc_now_iso=service_started_at)
        return ServiceHealthResponse(
            status="ok",
            service_revision=metadata.service_revision,
            started_at=metadata.started_at,
            data_root=metadata.data_root.as_posix(),
            service_profile=metadata.service_profile,
        )

    @router.get("/readyz")
    async def readycheck() -> JSONResponse:
        metadata = metadata_for_app(app, utc_now_iso=service_started_at)
        expected_revision_obj = getattr(
            app.state, "expected_service_revision", metadata.service_revision
        )
        expected_revision = (
            expected_revision_obj
            if isinstance(expected_revision_obj, str)
            else metadata.service_revision
        )
        expected_profile_obj = getattr(
            app.state, "expected_service_profile", metadata.service_profile
        )
        expected_profile = (
            expected_profile_obj
            if isinstance(expected_profile_obj, str)
            else metadata.service_profile
        )
        prod_root = resolve_prod_root_from_env()
        eval_root = resolve_eval_root_from_env()

        reasons: list[ServiceReadinessReason] = []
        if metadata.service_revision == "unknown":
            reasons.append(
                ServiceReadinessReason(
                    code="unknown_service_revision",
                    message="Service revision is unknown; readiness cannot be guaranteed.",
                )
            )
        if expected_revision == "unknown":
            reasons.append(
                ServiceReadinessReason(
                    code="unknown_expected_revision",
                    message="Expected revision is unknown; readiness cannot be guaranteed.",
                )
            )
        elif metadata.service_revision != expected_revision:
            reasons.append(
                ServiceReadinessReason(
                    code="stale_revision",
                    message="Service revision does not match expected repository revision.",
                    details={
                        "service_revision": metadata.service_revision,
                        "expected_revision": expected_revision,
                    },
                )
            )
        if metadata.service_profile != expected_profile:
            reasons.append(
                ServiceReadinessReason(
                    code="profile_mismatch",
                    message="Service profile does not match configured entrypoint profile.",
                    details={
                        "service_profile": metadata.service_profile,
                        "expected_profile": expected_profile,
                    },
                )
            )
        if prod_root == eval_root:
            reasons.append(
                ServiceReadinessReason(
                    code="data_root_configuration_collision",
                    message="Configured prod/eval data roots collide.",
                    details={"data_root": prod_root.as_posix()},
                )
            )
        if metadata.service_profile == "prod" and metadata.data_root != prod_root:
            reasons.append(
                ServiceReadinessReason(
                    code="data_root_profile_mismatch",
                    message="Prod service data root does not match configured prod data root.",
                    details={
                        "service_data_root": metadata.data_root.as_posix(),
                        "expected_data_root": prod_root.as_posix(),
                    },
                )
            )
        if metadata.service_profile == "eval" and metadata.data_root != eval_root:
            reasons.append(
                ServiceReadinessReason(
                    code="data_root_profile_mismatch",
                    message="Eval service data root does not match configured eval data root.",
                    details={
                        "service_data_root": metadata.data_root.as_posix(),
                        "expected_data_root": eval_root.as_posix(),
                    },
                )
            )

        is_ready = len(reasons) == 0
        payload = ServiceReadinessResponse(
            status="ready" if is_ready else "not_ready",
            ready=is_ready,
            service_revision=metadata.service_revision,
            expected_revision=expected_revision,
            service_profile=metadata.service_profile,
            expected_service_profile=expected_profile,
            started_at=metadata.started_at,
            data_root=metadata.data_root.as_posix(),
            reasons=reasons,
        )
        status_code = 200 if is_ready else 503
        return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

    @router.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> PlainTextResponse:
        registry_obj = getattr(app.state, "metrics_registry", None)
        if not isinstance(registry_obj, CollectorRegistry):
            return PlainTextResponse(content="metrics registry unavailable", status_code=500)
        metrics_data = generate_latest(registry_obj)
        return PlainTextResponse(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    return router
