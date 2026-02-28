"""Webhook onboarding HTTP routes for service API v2.

Purpose:
    Provide owner-scoped v2 webhook subscription onboarding endpoints with
    deterministic CRUD and secret lifecycle semantics.

Relationships:
    - Included by `interfaces.http_api`.
    - Uses runtime state from `interfaces.http_app_state`.
    - Delegates persistence to `infrastructure.runtime_engine_v2` webhook APIs.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    WebhookSecretOverlapV2,
    WebhookSecretRevealV2,
    WebhookSecretRevokeRequestV2,
    WebhookSecretRevokeResponseV2,
    WebhookSecretRotateRequestV2,
    WebhookSecretRotateResponseV2,
    WebhookSubscriptionCreateRequestV2,
    WebhookSubscriptionCreateResponseV2,
    WebhookSubscriptionDataV2,
    WebhookSubscriptionGetResponseV2,
    WebhookSubscriptionListResponseV2,
    WebhookSubscriptionUpdateRequestV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request


def _require_api_key(request: Request, *, service_started_at: str) -> str:
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    api_key = request.headers.get("X-API-Key")
    if api_key != runtime.config.api_key:
        raise ServiceError(
            status_code=401,
            code="auth_invalid_api_key",
            message="Missing or invalid X-API-Key.",
            retryable=False,
        )
    return api_key


def _require_onboarding_enabled(runtime: ServiceRuntimeV2) -> None:
    if runtime.config.enable_webhook_onboarding:
        return
    raise ServiceError(
        status_code=503,
        code="push_disabled",
        message="Webhook onboarding is disabled by runtime feature flag.",
        retryable=False,
        details={"surface": "webhook_onboarding"},
    )


def _require_capability(
    runtime: ServiceRuntimeV2,
    *,
    required: str,
) -> None:
    if required in runtime.config.api_capabilities:
        return
    raise ServiceError(
        status_code=403,
        code="insufficient_scope",
        message="API key lacks required capability.",
        retryable=False,
        details={"required_capability": required, "surface": "webhook_onboarding"},
    )


def _subscription_data(record) -> WebhookSubscriptionDataV2:
    return WebhookSubscriptionDataV2(
        subscription_id=record.subscription_id,
        callback_url=record.callback_url,
        event_types=list(record.event_types),
        enabled=record.enabled,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _overlap_payload(runtime: ServiceRuntimeV2, record) -> WebhookSecretOverlapV2:
    overlap_hours = max(1, runtime.config.webhook_secret_overlap_seconds // 3600)
    active_and_next_valid = record.next_secret_present and record.overlap_expires_at is not None
    return WebhookSecretOverlapV2(
        active_and_next_valid=active_and_next_valid,
        overlap_expires_at=record.overlap_expires_at,
        overlap_hours=overlap_hours,
    )


def build_webhook_onboarding_router_v2(*, service_started_at: str) -> APIRouter:
    """Build v2 webhook onboarding router with stable app-state wiring."""

    router = APIRouter()

    @router.post("/v2/push/webhooks/subscriptions")
    async def create_subscription(
        request: Request,
        body: WebhookSubscriptionCreateRequestV2,
    ) -> JSONResponse:
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:write")

        record, secret_value = runtime.create_webhook_subscription(
            api_key=api_key,
            callback_url=body.callback_url,
            event_types=list(body.event_types),
            enabled=body.enabled,
        )
        payload = WebhookSubscriptionCreateResponseV2(
            subscription=_subscription_data(record),
            secret=WebhookSecretRevealV2(version="active", value=secret_value),
        )
        return JSONResponse(status_code=201, content=payload.model_dump(mode="json"))

    @router.get("/v2/push/webhooks/subscriptions")
    async def list_subscriptions(request: Request) -> JSONResponse:
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:read")

        records = runtime.list_webhook_subscriptions(api_key=api_key)
        payload = WebhookSubscriptionListResponseV2(
            subscriptions=[_subscription_data(record) for record in records]
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.get("/v2/push/webhooks/subscriptions/{subscription_id}")
    async def get_subscription(subscription_id: str, request: Request) -> JSONResponse:
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:read")

        record = runtime.get_webhook_subscription(
            api_key=api_key,
            subscription_id=subscription_id,
        )
        payload = WebhookSubscriptionGetResponseV2(subscription=_subscription_data(record))
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.patch("/v2/push/webhooks/subscriptions/{subscription_id}")
    async def update_subscription(
        subscription_id: str,
        request: Request,
        body: WebhookSubscriptionUpdateRequestV2,
    ) -> JSONResponse:
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:write")

        record = runtime.update_webhook_subscription(
            api_key=api_key,
            subscription_id=subscription_id,
            callback_url=body.callback_url,
            event_types=list(body.event_types) if body.event_types is not None else None,
            enabled=body.enabled,
        )
        payload = WebhookSubscriptionGetResponseV2(subscription=_subscription_data(record))
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.post("/v2/push/webhooks/subscriptions/{subscription_id}/rotate-secret")
    async def rotate_secret(
        subscription_id: str,
        request: Request,
        body: WebhookSecretRotateRequestV2 | None = None,
    ) -> JSONResponse:
        del body
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:write")

        record, revealed_secret = runtime.rotate_webhook_secret(
            api_key=api_key,
            subscription_id=subscription_id,
        )
        payload = WebhookSecretRotateResponseV2(
            subscription_id=record.subscription_id,
            secret=WebhookSecretRevealV2(version="next", value=revealed_secret),
            overlap=_overlap_payload(runtime, record),
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.post("/v2/push/webhooks/subscriptions/{subscription_id}/revoke-secret")
    async def revoke_secret(
        subscription_id: str,
        request: Request,
        body: WebhookSecretRevokeRequestV2 | None = None,
    ) -> JSONResponse:
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:write")

        requested_version = None if body is None else body.version
        record, revoked_version = runtime.revoke_webhook_secret(
            api_key=api_key,
            subscription_id=subscription_id,
            version=requested_version,
        )
        payload = WebhookSecretRevokeResponseV2(
            subscription_id=record.subscription_id,
            revoked_version=revoked_version,
            overlap=_overlap_payload(runtime, record),
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.delete("/v2/push/webhooks/subscriptions/{subscription_id}")
    async def delete_subscription(subscription_id: str, request: Request) -> Response:
        api_key = _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        _require_onboarding_enabled(runtime)
        _require_capability(runtime, required="push:write")
        runtime.delete_webhook_subscription(
            api_key=api_key,
            subscription_id=subscription_id,
        )
        return Response(status_code=204)

    return router
