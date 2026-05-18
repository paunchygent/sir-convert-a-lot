"""Structured LLM hot-settings runtime composition.

Purpose:
    Build the shared running-service hot-settings store from immutable service
    configuration so operator routes and job admission use the same provider
    catalog and remote-provider classification.

Relationships:
    - Consumes `infrastructure.structured_llm_config.StructuredLLMRuntimeConfig`
      and `domain.structured_llm_hot_settings`.
    - Used by HTTP operator settings routes and v2 job admission without
      exposing route settings through public job specs.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMHotSettingsStore,
    StructuredLLMInternalRouteClass,
    StructuredLLMProviderRoutingSettings,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)


def structured_llm_hot_settings_store_from_config(
    config: ServiceConfig,
) -> StructuredLLMHotSettingsStore:
    """Create the initial hot-settings store for a configured service."""

    structured_config = config.structured_llm
    if not structured_config.enabled or structured_config.provider_set is None:
        raise ServiceError(
            status_code=409,
            code="structured_llm_settings_unavailable",
            message="Structured LLM provider routing is not configured.",
            retryable=False,
        )
    return StructuredLLMHotSettingsStore(
        initial_settings=StructuredLLMProviderRoutingSettings(
            version=1,
            active_provider_profile_id=structured_config.provider_set.primary.provider_id,
            allowed_internal_route_classes=frozenset(
                {StructuredLLMInternalRouteClass.OPERATOR_DEFAULT}
            ),
            remote_provider_authorized=(
                structured_config.remote_providers_enabled
                and structured_config.remote_fallback_policy_authorized
            ),
            rollout_label="service-startup",
        ),
        known_provider_profile_ids=structured_llm_provider_ids(structured_config),
        remote_provider_profile_ids=structured_llm_remote_provider_ids(structured_config),
    )


def structured_llm_provider_ids(config: StructuredLLMRuntimeConfig) -> frozenset[str]:
    """Return configured structured provider profile IDs."""

    if config.provider_set is None:
        return frozenset()
    provider_ids = {config.provider_set.primary.provider_id}
    if config.provider_set.fallback is not None:
        provider_ids.add(config.provider_set.fallback.provider_id)
    return frozenset(provider_ids)


def structured_llm_remote_provider_ids(config: StructuredLLMRuntimeConfig) -> frozenset[str]:
    """Return configured remote structured provider profile IDs."""

    if config.provider_set is None:
        return frozenset()
    provider_ids: set[str] = set()
    if config.provider_set.primary.is_remote:
        provider_ids.add(config.provider_set.primary.provider_id)
    if config.provider_set.fallback is not None and config.provider_set.fallback.is_remote:
        provider_ids.add(config.provider_set.fallback.provider_id)
    return frozenset(provider_ids)
