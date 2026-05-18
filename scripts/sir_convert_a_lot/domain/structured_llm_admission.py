"""Structured LLM admission-time route lineage.

Purpose:
    Define the immutable route snapshot captured when structured answer-key
    work is admitted, so execution and reports do not drift when operators
    mutate hot provider settings later.

Relationships:
    - Consumes provider profile contracts from `domain.structured_llm_contracts`
      and hot route classes from `domain.structured_llm_hot_settings`.
    - Is persisted by the v2 job store and consumed by DigiExam advisory
      answer-key completion.
    - Serializes only provider metadata, never prompts, item text, responses,
      request payloads, API keys, owner metadata, or artifact paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMTextVerbosity,
)
from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMInternalRouteClass,
)


class StructuredLLMAdmittedRouteDecision(StrEnum):
    """Stable admission decisions for structured provider routing."""

    ACTIVE_PROVIDER_PROFILE = "active_provider_profile"


@dataclass(frozen=True)
class StructuredLLMAdmittedRouteSnapshot:
    """Immutable provider route selected for one admitted job."""

    provider_family: str
    provider_profile_id: str
    model: str
    endpoint_kind: StructuredLLMEndpointKind
    output_mode: StructuredLLMOutputMode
    reasoning_effort: StructuredLLMReasoningEffort | None
    text_verbosity: StructuredLLMTextVerbosity | None
    settings_version: int
    route_class: StructuredLLMInternalRouteClass
    route_decision: StructuredLLMAdmittedRouteDecision
    remote_provider_authorized: bool

    def __post_init__(self) -> None:
        if not self.provider_family.strip():
            raise ValueError("Structured LLM provider_family must be non-empty.")
        if not self.provider_profile_id.strip():
            raise ValueError("Structured LLM provider_profile_id must be non-empty.")
        if not self.model.strip():
            raise ValueError("Structured LLM admitted model must be non-empty.")
        if self.settings_version <= 0:
            raise ValueError("Structured LLM admitted settings_version must be positive.")


def admitted_route_snapshot_for_profile(
    *,
    profile: StructuredLLMProviderProfile,
    settings_version: int,
    route_class: StructuredLLMInternalRouteClass,
    remote_provider_authorized: bool,
) -> StructuredLLMAdmittedRouteSnapshot:
    """Build metadata-only admitted lineage for a selected provider profile."""

    return StructuredLLMAdmittedRouteSnapshot(
        provider_family=structured_llm_provider_family(profile),
        provider_profile_id=profile.provider_id,
        model=profile.model,
        endpoint_kind=profile.endpoint_kind,
        output_mode=profile.output_mode,
        reasoning_effort=profile.reasoning_effort,
        text_verbosity=profile.text_verbosity,
        settings_version=settings_version,
        route_class=route_class,
        route_decision=StructuredLLMAdmittedRouteDecision.ACTIVE_PROVIDER_PROFILE,
        remote_provider_authorized=remote_provider_authorized,
    )


def structured_llm_provider_family(profile: StructuredLLMProviderProfile) -> str:
    """Return a coarse provider family for route lineage and reporting."""

    if profile.provider_id.startswith("openai-"):
        return "openai_responses"
    if profile.provider_id.startswith("deepseek-"):
        return "deepseek_json_object"
    if profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES and profile.is_remote:
        return "api_responses"
    if profile.is_remote:
        return "api_structured_llm"
    return "local_structured_llm"


def admitted_route_snapshot_to_json(
    snapshot: StructuredLLMAdmittedRouteSnapshot,
) -> dict[str, JsonValue]:
    """Serialize an admitted route snapshot into manifest/report JSON."""

    return {
        "provider_family": snapshot.provider_family,
        "provider_profile_id": snapshot.provider_profile_id,
        "model": snapshot.model,
        "endpoint_kind": snapshot.endpoint_kind.value,
        "output_mode": snapshot.output_mode.value,
        "reasoning_effort": (
            snapshot.reasoning_effort.value if snapshot.reasoning_effort is not None else None
        ),
        "text_verbosity": (
            snapshot.text_verbosity.value if snapshot.text_verbosity is not None else None
        ),
        "settings_version": snapshot.settings_version,
        "route_class": snapshot.route_class.value,
        "route_decision": snapshot.route_decision.value,
        "remote_provider_authorized": snapshot.remote_provider_authorized,
    }


def admitted_route_snapshot_from_json(
    payload: object,
) -> StructuredLLMAdmittedRouteSnapshot | None:
    """Parse a stored admitted route snapshot from manifest JSON."""

    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError("Structured LLM admission snapshot must be an object.")
    return StructuredLLMAdmittedRouteSnapshot(
        provider_family=_required_str(payload, "provider_family"),
        provider_profile_id=_required_str(payload, "provider_profile_id"),
        model=_required_str(payload, "model"),
        endpoint_kind=StructuredLLMEndpointKind(_required_str(payload, "endpoint_kind")),
        output_mode=StructuredLLMOutputMode(_required_str(payload, "output_mode")),
        reasoning_effort=_optional_reasoning_effort(payload.get("reasoning_effort")),
        text_verbosity=_optional_text_verbosity(payload.get("text_verbosity")),
        settings_version=_required_int(payload, "settings_version"),
        route_class=StructuredLLMInternalRouteClass(_required_str(payload, "route_class")),
        route_decision=StructuredLLMAdmittedRouteDecision(_required_str(payload, "route_decision")),
        remote_provider_authorized=_required_bool(payload, "remote_provider_authorized"),
    )


def _required_str(payload: dict[object, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"Structured LLM admission snapshot needs non-empty {key}.")
    return value


def _required_int(payload: dict[object, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Structured LLM admission snapshot needs integer {key}.")
    return value


def _required_bool(payload: dict[object, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Structured LLM admission snapshot needs boolean {key}.")
    return value


def _optional_reasoning_effort(value: object) -> StructuredLLMReasoningEffort | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Structured LLM reasoning_effort must be a string when present.")
    return StructuredLLMReasoningEffort(value)


def _optional_text_verbosity(value: object) -> StructuredLLMTextVerbosity | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Structured LLM text_verbosity must be a string when present.")
    return StructuredLLMTextVerbosity(value)
