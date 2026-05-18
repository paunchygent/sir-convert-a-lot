"""HTTP routes for operator-owned structured LLM settings.

Purpose:
    Expose an internal-identity gated mutation surface for structured
    answer-key provider routing settings without adding provider selectors to
    public conversion job specs.

Relationships:
    - Consumes the hot-settings domain model from
      `domain.structured_llm_hot_settings`.
    - Uses v2 HuleEdu internal identity authentication from `http_auth_v2`.
    - Is included by the FastAPI app factory as an operator/admin route, not as
      a conversion request field.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMHotSettingsStore,
    StructuredLLMInternalRouteClass,
    StructuredLLMProviderRoutingSettings,
    StructuredLLMSettingsAuditEvent,
    StructuredLLMSettingsAuthoritySource,
    StructuredLLMSettingsMutationAuthority,
    StructuredLLMSettingsMutationError,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import (
    AuthContextV2,
    require_internal_identity_auth_context_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_structured_llm_settings_state_v2 import (
    structured_llm_hot_settings_store_for_request,
)

STRUCTURED_LLM_SETTINGS_READ_GRANT = "sir-convert:structured-llm-settings:read"
STRUCTURED_LLM_SETTINGS_WRITE_GRANT = "sir-convert:structured-llm-settings:write"


class StructuredLLMRoutingSettingsRequestV2(BaseModel):
    """Operator request body for replacing hot provider routing settings."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    active_provider_profile_id: str = Field(min_length=1)
    allowed_internal_route_classes: list[StructuredLLMInternalRouteClass] = Field(min_length=1)
    remote_provider_authorized: bool = False
    rollout_label: str = Field(min_length=1)
    operator_notes: str | None = None


class StructuredLLMRoutingSettingsResponseV2(BaseModel):
    """Current hot provider routing settings."""

    version: int
    active_provider_profile_id: str
    allowed_internal_route_classes: list[str]
    remote_provider_authorized: bool
    rollout_label: str
    operator_notes: str | None


class StructuredLLMSettingsAuditEventResponseV2(BaseModel):
    """Metadata-only audit event response for a settings mutation."""

    actor_id: str
    authority_source: str
    previous_settings_version: int
    requested_settings_version: int
    active_settings_version: int
    selected_provider_profile: str
    allowed_internal_route_classes: list[str]
    remote_provider_authorized: bool
    rollout_label: str
    timestamp: str
    correlation_id: str
    success: bool
    failure_code: str | None


class StructuredLLMRoutingSettingsMutationResponseV2(BaseModel):
    """Response body for successful hot settings replacement."""

    settings: StructuredLLMRoutingSettingsResponseV2
    audit_event: StructuredLLMSettingsAuditEventResponseV2


def build_structured_llm_settings_router_v2(*, service_started_at: str) -> APIRouter:
    """Build operator-only structured LLM settings routes."""

    router = APIRouter()

    @router.get(
        "/v2/operator/structured-llm/provider-routing",
        response_model=StructuredLLMRoutingSettingsResponseV2,
        tags=["operator"],
    )
    def get_provider_routing_settings(
        request: Request,
    ) -> StructuredLLMRoutingSettingsResponseV2:
        require_internal_identity_auth_context_v2(
            request,
            service_started_at=service_started_at,
            required_grant=STRUCTURED_LLM_SETTINGS_READ_GRANT,
        )
        store = _hot_settings_store_for_request(request, service_started_at=service_started_at)
        return _settings_response(store.active_settings)

    @router.put(
        "/v2/operator/structured-llm/provider-routing",
        response_model=StructuredLLMRoutingSettingsMutationResponseV2,
        tags=["operator"],
    )
    def replace_provider_routing_settings(
        body: StructuredLLMRoutingSettingsRequestV2,
        request: Request,
    ) -> StructuredLLMRoutingSettingsMutationResponseV2:
        auth_context = require_internal_identity_auth_context_v2(
            request,
            service_started_at=service_started_at,
            required_grant=STRUCTURED_LLM_SETTINGS_WRITE_GRANT,
        )
        store = _hot_settings_store_for_request(request, service_started_at=service_started_at)
        settings = StructuredLLMProviderRoutingSettings(
            version=body.version,
            active_provider_profile_id=body.active_provider_profile_id,
            allowed_internal_route_classes=frozenset(body.allowed_internal_route_classes),
            remote_provider_authorized=body.remote_provider_authorized,
            rollout_label=body.rollout_label,
            operator_notes=body.operator_notes,
        )
        try:
            event = store.replace_settings(
                new_settings=settings,
                authority=_mutation_authority(auth_context),
                timestamp=service_started_at,
                correlation_id=getattr(request.state, "correlation_id", ""),
            )
        except StructuredLLMSettingsMutationError as exc:
            raise ServiceError(
                status_code=409,
                code="structured_llm_settings_update_rejected",
                message="Structured LLM provider routing settings were not changed.",
                retryable=False,
                details={"failure_code": exc.failure_code.value},
            ) from exc
        return StructuredLLMRoutingSettingsMutationResponseV2(
            settings=_settings_response(store.active_settings),
            audit_event=_audit_response(event),
        )

    return router


def _hot_settings_store_for_request(
    request: Request,
    *,
    service_started_at: str,
) -> StructuredLLMHotSettingsStore:
    return structured_llm_hot_settings_store_for_request(
        request,
        service_started_at=service_started_at,
    )


def _mutation_authority(auth_context: AuthContextV2) -> StructuredLLMSettingsMutationAuthority:
    return StructuredLLMSettingsMutationAuthority(
        actor_id=auth_context.owner_api_key_scope,
        authority_source=StructuredLLMSettingsAuthoritySource.INTERNAL_IDENTITY,
        internal_identity_verified=auth_context.identity_context_verified,
    )


def _settings_response(
    settings: StructuredLLMProviderRoutingSettings,
) -> StructuredLLMRoutingSettingsResponseV2:
    return StructuredLLMRoutingSettingsResponseV2(
        version=settings.version,
        active_provider_profile_id=settings.active_provider_profile_id,
        allowed_internal_route_classes=sorted(
            route_class.value for route_class in settings.allowed_internal_route_classes
        ),
        remote_provider_authorized=settings.remote_provider_authorized,
        rollout_label=settings.rollout_label,
        operator_notes=settings.operator_notes,
    )


def _audit_response(
    event: StructuredLLMSettingsAuditEvent,
) -> StructuredLLMSettingsAuditEventResponseV2:
    return StructuredLLMSettingsAuditEventResponseV2(
        actor_id=event.actor_id,
        authority_source=event.authority_source.value,
        previous_settings_version=event.previous_settings_version,
        requested_settings_version=event.requested_settings_version,
        active_settings_version=event.active_settings_version,
        selected_provider_profile=event.selected_provider_profile,
        allowed_internal_route_classes=list(event.allowed_internal_route_classes),
        remote_provider_authorized=event.remote_provider_authorized,
        rollout_label=event.rollout_label,
        timestamp=event.timestamp,
        correlation_id=event.correlation_id,
        success=event.success,
        failure_code=event.failure_code.value if event.failure_code is not None else None,
    )
