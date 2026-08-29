"""Structured LLM route admission for service jobs.

Purpose:
    Resolve the active structured-provider hot settings into an immutable job
    admission snapshot before execution begins, preserving route lineage and
    fail-closed remote-provider policy.

Relationships:
    - Consumes `domain.structured_llm_admission` snapshots and
      `domain.structured_llm_hot_settings` runtime settings.
    - Used by v2 HTTP job admission before persisting a job manifest.
    - Supplies provider-set narrowing for DigiExam advisory answer-key
      completion execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from scripts.sir_convert_a_lot.domain.specs_v2 import (
    DigiExamAnswerKeyCompletionModeV2,
    JobSpecV2,
)
from scripts.sir_convert_a_lot.domain.structured_llm_admission import (
    StructuredLLMAdmittedRouteSnapshot,
    admitted_route_snapshot_for_profile,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMProviderProfile,
)
from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMHotSettingsStore,
    StructuredLLMInternalRouteClass,
    StructuredLLMProviderRoutingSettings,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)


class StructuredLLMAdmissionFailureCode(StrEnum):
    """Typed admission failures for structured provider routing."""

    ACTIVE_PROVIDER_MISSING = "active_provider_missing"
    PUBLIC_REMOTE_PROVIDER_FORBIDDEN = "public_remote_provider_forbidden"
    REMOTE_PROVIDER_POLICY_FORBIDDEN = "remote_provider_policy_forbidden"
    INCOMPATIBLE_ROUTE_CLASS = "incompatible_route_class"


@dataclass(frozen=True)
class StructuredLLMAdmissionError(Exception):
    """Structured provider admission failure before a job is persisted."""

    failure_code: StructuredLLMAdmissionFailureCode
    message: str

    def __str__(self) -> str:
        return self.message


def resolve_structured_llm_admission_snapshot(
    *,
    spec: JobSpecV2,
    structured_config: StructuredLLMRuntimeConfig,
    hot_settings_store: StructuredLLMHotSettingsStore | None,
    public_grant_request: bool,
) -> StructuredLLMAdmittedRouteSnapshot | None:
    """Resolve admitted route lineage for advisory answer-key jobs."""

    if not _requests_advisory_completion(spec):
        return None
    if not structured_config.enabled or structured_config.provider_set is None:
        return None
    if hot_settings_store is None:
        return None

    settings = hot_settings_store.active_settings
    profile = provider_profile_by_id(
        structured_config=structured_config,
        provider_profile_id=settings.active_provider_profile_id,
    )
    if profile is None:
        raise StructuredLLMAdmissionError(
            failure_code=StructuredLLMAdmissionFailureCode.ACTIVE_PROVIDER_MISSING,
            message="Structured LLM active provider profile is not configured.",
        )
    _validate_remote_policy(
        profile=profile,
        structured_config=structured_config,
        settings=settings,
        public_grant_request=public_grant_request,
    )
    route_class = _route_class_for_active_profile(settings=settings, profile=profile)
    return admitted_route_snapshot_for_profile(
        profile=profile,
        settings_version=settings.version,
        route_class=route_class,
        remote_provider_authorized=settings.remote_provider_authorized,
    )


def provider_set_for_admitted_route(
    *,
    structured_config: StructuredLLMRuntimeConfig,
    admitted_route: StructuredLLMAdmittedRouteSnapshot | None,
) -> StructuredChatProviderSet | None:
    """Return a provider set pinned to the admitted route snapshot."""

    if structured_config.provider_set is None:
        return None
    if admitted_route is None:
        return structured_config.provider_set
    profile = provider_profile_by_id(
        structured_config=structured_config,
        provider_profile_id=admitted_route.provider_profile_id,
    )
    if profile is None:
        return None
    fallback = structured_config.provider_set.fallback
    preserved_fallback = (
        fallback if fallback is not None and fallback.provider_id != profile.provider_id else None
    )
    return StructuredChatProviderSet(
        primary=profile,
        fallback=preserved_fallback,
    )


def provider_profile_by_id(
    *,
    structured_config: StructuredLLMRuntimeConfig,
    provider_profile_id: str,
) -> StructuredLLMProviderProfile | None:
    """Return a configured provider profile by ID."""

    if structured_config.provider_set is None:
        return None
    if structured_config.provider_set.primary.provider_id == provider_profile_id:
        return structured_config.provider_set.primary
    fallback = structured_config.provider_set.fallback
    if fallback is not None and fallback.provider_id == provider_profile_id:
        return fallback
    return None


def _requests_advisory_completion(spec: JobSpecV2) -> bool:
    options = spec.digiexam_migration_options
    return (
        options is not None
        and options.completion_mode
        == DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
    )


def _validate_remote_policy(
    *,
    profile: StructuredLLMProviderProfile,
    structured_config: StructuredLLMRuntimeConfig,
    settings: StructuredLLMProviderRoutingSettings,
    public_grant_request: bool,
) -> None:
    if not profile.is_remote:
        return
    if public_grant_request:
        raise StructuredLLMAdmissionError(
            failure_code=StructuredLLMAdmissionFailureCode.PUBLIC_REMOTE_PROVIDER_FORBIDDEN,
            message="Public conversion grants cannot use remote structured LLM providers.",
        )
    if (
        not settings.remote_provider_authorized
        or not structured_config.remote_providers_enabled
        or not structured_config.remote_fallback_policy_authorized
    ):
        raise StructuredLLMAdmissionError(
            failure_code=StructuredLLMAdmissionFailureCode.REMOTE_PROVIDER_POLICY_FORBIDDEN,
            message="Remote structured LLM provider use is not authorized.",
        )


def _route_class_for_active_profile(
    *,
    settings: StructuredLLMProviderRoutingSettings,
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMInternalRouteClass:
    allowed = settings.allowed_internal_route_classes
    if StructuredLLMInternalRouteClass.OPERATOR_DEFAULT in allowed:
        return StructuredLLMInternalRouteClass.OPERATOR_DEFAULT
    if profile.is_remote and StructuredLLMInternalRouteClass.OPERATOR_API_ONLY in allowed:
        return StructuredLLMInternalRouteClass.OPERATOR_API_ONLY
    if not profile.is_remote and StructuredLLMInternalRouteClass.OPERATOR_LOCAL_ONLY in allowed:
        return StructuredLLMInternalRouteClass.OPERATOR_LOCAL_ONLY
    if not profile.is_remote and StructuredLLMInternalRouteClass.OPERATOR_LOCAL_FIRST in allowed:
        return StructuredLLMInternalRouteClass.OPERATOR_LOCAL_FIRST
    raise StructuredLLMAdmissionError(
        failure_code=StructuredLLMAdmissionFailureCode.INCOMPATIBLE_ROUTE_CLASS,
        message="Structured LLM hot settings do not allow the active provider route class.",
    )
