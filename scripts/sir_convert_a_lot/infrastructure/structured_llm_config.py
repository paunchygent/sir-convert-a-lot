"""Structured LLM runtime configuration.

Purpose:
    Load governed structured-provider settings from service environment
    variables while keeping provider configuration disabled by default.

Relationships:
    - Produces `StructuredLLMRuntimeConfig` values attached to
      `infrastructure.runtime_models.ServiceConfig`.
    - Builds source-neutral provider profiles from
      `domain.structured_llm_contracts` and HTTP connection settings from
      `infrastructure.structured_llm_provider`.
    - Feeds the Dishka composition root without wiring provider calls into
      parser, renderer, or HTTP artifact routes.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRoutePolicy,
    StructuredLLMTextVerbosity,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_provider_runtime_config import (
    provider_json_from_runtime_profile,
    runtime_lane_from_env,
    validate_structured_llm_connections_for_runtime_lane,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)

STRUCTURED_LLM_ENABLED_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_ENABLED"
STRUCTURED_LLM_PROVIDERS_JSON_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDERS_JSON"
STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_PRIMARY_PROVIDER_ID"
STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_FALLBACK_PROVIDER_ID"
STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV = (
    "SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED"
)
STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV = (
    "SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED"
)
STRUCTURED_LLM_VISION_MEDIA_PATH_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH"

STRUCTURED_LLM_PROVIDER_MODEL_KEY = "model"
STRUCTURED_LLM_PROVIDER_ENDPOINT_KIND_KEY = "endpoint_kind"
STRUCTURED_LLM_PROVIDER_OUTPUT_MODE_KEY = "output_mode"
STRUCTURED_LLM_PROVIDER_IS_REMOTE_KEY = "is_remote"
STRUCTURED_LLM_PROVIDER_CONTEXT_WINDOW_TOKENS_KEY = "context_window_tokens"
STRUCTURED_LLM_PROVIDER_MAX_OUTPUT_TOKENS_KEY = "max_output_tokens"
STRUCTURED_LLM_PROVIDER_TEMPERATURE_KEY = "temperature"
STRUCTURED_LLM_PROVIDER_REASONING_EFFORT_KEY = "reasoning_effort"
STRUCTURED_LLM_PROVIDER_TEXT_VERBOSITY_KEY = "text_verbosity"
STRUCTURED_LLM_PROVIDER_BASE_URL_KEY = "base_url"
STRUCTURED_LLM_PROVIDER_API_KEY_ENV_KEY = "api_key_env"
STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY = "extra_headers"
STRUCTURED_LLM_PROVIDER_TIMEOUT_SECONDS_KEY = "timeout_seconds"
STRUCTURED_LLM_PROVIDER_CAPABILITIES_KEY = "capabilities"
STRUCTURED_LLM_CAPABILITY_JSON_SCHEMA_KEY = "supports_json_schema"
STRUCTURED_LLM_CAPABILITY_GBNF_KEY = "supports_gbnf"
STRUCTURED_LLM_CAPABILITY_VLLM_CHOICE_KEY = "supports_vllm_structured_choice"
STRUCTURED_LLM_CAPABILITY_MULTIMODAL_VISION_KEY = "supports_multimodal_vision"

_BOOL_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_BOOL_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True)
class StructuredLLMRuntimeConfig:
    """Service-level structured-provider configuration."""

    enabled: bool = False
    provider_set: StructuredChatProviderSet | None = None
    connections: Mapping[str, StructuredLLMProviderConnection] = field(default_factory=dict)
    vision_media_path: Path | None = None
    remote_providers_enabled: bool = False
    remote_fallback_policy_authorized: bool = False

    def route_policy(self, *, allow_remote_fallback: bool | None) -> StructuredLLMRoutePolicy:
        """Return routing policy for one item-local request."""

        return StructuredLLMRoutePolicy(
            remote_providers_enabled=self.remote_providers_enabled,
            remote_fallback_policy_authorized=self.remote_fallback_policy_authorized,
            allow_remote_fallback=allow_remote_fallback,
        )


def disabled_structured_llm_runtime_config() -> StructuredLLMRuntimeConfig:
    """Return the service default that cannot call structured providers."""

    return StructuredLLMRuntimeConfig()


def structured_llm_runtime_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> StructuredLLMRuntimeConfig:
    """Load structured-provider runtime config from environment variables."""

    source = environ if environ is not None else os.environ
    enabled = _parse_bool_env(source, name=STRUCTURED_LLM_ENABLED_ENV, default=False)
    if not enabled:
        return disabled_structured_llm_runtime_config()

    providers_json = _optional_env(source, STRUCTURED_LLM_PROVIDERS_JSON_ENV)
    if providers_json is None:
        providers_json = provider_json_from_runtime_profile(source)
    profiles, connections = _provider_maps_from_json(providers_json, environ=source)
    validate_structured_llm_connections_for_runtime_lane(
        lane=runtime_lane_from_env(source),
        connections=connections,
    )
    primary_id = _required_env(source, STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV)
    fallback_id = _optional_env(source, STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV)
    primary = _profile_by_id(profiles, primary_id, env_name=STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV)
    if primary.is_remote:
        raise ValueError(
            f"{STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV} must reference a local provider profile."
        )
    vision_media_path = _vision_media_path_from_env(source, primary=primary)
    fallback = None
    if fallback_id is not None:
        fallback = _profile_by_id(
            profiles,
            fallback_id,
            env_name=STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV,
        )

    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(primary=primary, fallback=fallback),
        connections=connections,
        vision_media_path=vision_media_path,
        remote_providers_enabled=_parse_bool_env(
            source,
            name=STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV,
            default=False,
        ),
        remote_fallback_policy_authorized=_parse_bool_env(
            source,
            name=STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV,
            default=False,
        ),
    )


def _provider_maps_from_json(
    raw: str,
    *,
    environ: Mapping[str, str],
) -> tuple[
    dict[str, StructuredLLMProviderProfile],
    dict[str, StructuredLLMProviderConnection],
]:
    try:
        decoded: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV} must be valid JSON.") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV} must decode to an object.")
    profiles: dict[str, StructuredLLMProviderProfile] = {}
    connections: dict[str, StructuredLLMProviderConnection] = {}
    for raw_provider_id, raw_provider_payload in decoded.items():
        if not isinstance(raw_provider_id, str) or raw_provider_id.strip() == "":
            raise ValueError(
                f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV} provider ids must be non-empty strings."
            )
        if not isinstance(raw_provider_payload, dict):
            raise ValueError(
                f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{raw_provider_id}] must be an object."
            )
        provider_id = raw_provider_id.strip()
        profile = _provider_profile_from_payload(provider_id, raw_provider_payload)
        profiles[provider_id] = profile
        connections[provider_id] = _provider_connection_from_payload(
            provider_id,
            raw_provider_payload,
            environ=environ,
        )
    if not profiles:
        raise ValueError(f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV} must define at least one provider.")
    return profiles, connections


def _vision_media_path_from_env(
    source: Mapping[str, str],
    *,
    primary: StructuredLLMProviderProfile,
) -> Path | None:
    raw = _optional_env(source, STRUCTURED_LLM_VISION_MEDIA_PATH_ENV)
    if raw is None:
        if primary.capabilities.supports_multimodal_vision:
            raise ValueError(
                f"{STRUCTURED_LLM_VISION_MEDIA_PATH_ENV} must be configured when the "
                "primary structured provider supports multimodal vision."
            )
        return None
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError(f"{STRUCTURED_LLM_VISION_MEDIA_PATH_ENV} must be an absolute path.")
    return path


def _provider_profile_from_payload(
    provider_id: str,
    payload: Mapping[object, object],
) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id=provider_id,
        model=_required_str(payload, STRUCTURED_LLM_PROVIDER_MODEL_KEY, provider_id),
        endpoint_kind=_endpoint_kind(
            _required_str(payload, STRUCTURED_LLM_PROVIDER_ENDPOINT_KIND_KEY, provider_id),
            provider_id=provider_id,
        ),
        output_mode=_output_mode(
            _required_str(payload, STRUCTURED_LLM_PROVIDER_OUTPUT_MODE_KEY, provider_id),
            provider_id=provider_id,
        ),
        is_remote=_required_bool(payload, STRUCTURED_LLM_PROVIDER_IS_REMOTE_KEY, provider_id),
        context_window_tokens=_required_int(
            payload,
            STRUCTURED_LLM_PROVIDER_CONTEXT_WINDOW_TOKENS_KEY,
            provider_id,
        ),
        max_output_tokens=_required_int(
            payload,
            STRUCTURED_LLM_PROVIDER_MAX_OUTPUT_TOKENS_KEY,
            provider_id,
        ),
        temperature=_optional_float(
            payload,
            STRUCTURED_LLM_PROVIDER_TEMPERATURE_KEY,
            provider_id,
            default=0.0,
        ),
        reasoning_effort=_optional_reasoning_effort(payload, provider_id=provider_id),
        text_verbosity=_optional_text_verbosity(payload, provider_id=provider_id),
        capabilities=_capabilities_from_payload(
            _required_mapping(payload, STRUCTURED_LLM_PROVIDER_CAPABILITIES_KEY, provider_id),
            provider_id=provider_id,
        ),
    )


def _provider_connection_from_payload(
    provider_id: str,
    payload: Mapping[object, object],
    *,
    environ: Mapping[str, str],
) -> StructuredLLMProviderConnection:
    return StructuredLLMProviderConnection(
        provider_id=provider_id,
        base_url=_required_str(payload, STRUCTURED_LLM_PROVIDER_BASE_URL_KEY, provider_id),
        api_key=_api_key_from_payload(payload, provider_id=provider_id, environ=environ),
        extra_headers=_extra_headers_from_payload(payload, provider_id=provider_id),
        timeout_seconds=_optional_float(
            payload,
            STRUCTURED_LLM_PROVIDER_TIMEOUT_SECONDS_KEY,
            provider_id,
            default=30.0,
        ),
    )


def _capabilities_from_payload(
    payload: Mapping[object, object],
    *,
    provider_id: str,
) -> StructuredLLMProviderCapabilities:
    return StructuredLLMProviderCapabilities(
        supports_json_schema=_required_bool(
            payload,
            STRUCTURED_LLM_CAPABILITY_JSON_SCHEMA_KEY,
            provider_id,
        ),
        supports_gbnf=_required_bool(payload, STRUCTURED_LLM_CAPABILITY_GBNF_KEY, provider_id),
        supports_vllm_structured_choice=_required_bool(
            payload,
            STRUCTURED_LLM_CAPABILITY_VLLM_CHOICE_KEY,
            provider_id,
        ),
        supports_multimodal_vision=_optional_bool(
            payload,
            STRUCTURED_LLM_CAPABILITY_MULTIMODAL_VISION_KEY,
            provider_id,
            default=False,
        ),
    )


def _api_key_from_payload(
    payload: Mapping[object, object],
    *,
    provider_id: str,
    environ: Mapping[str, str],
) -> str:
    env_name = _optional_str(payload, STRUCTURED_LLM_PROVIDER_API_KEY_ENV_KEY, provider_id)
    if env_name is None:
        return ""
    raw = environ.get(env_name)
    if raw is None or raw.strip() == "":
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
            f"{STRUCTURED_LLM_PROVIDER_API_KEY_ENV_KEY} points to unset env var {env_name}."
        )
    return raw.strip()


def _extra_headers_from_payload(
    payload: Mapping[object, object],
    *,
    provider_id: str,
) -> dict[str, str]:
    raw_headers = payload.get(STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY)
    if raw_headers is None:
        return {}
    if not isinstance(raw_headers, dict):
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
            f"{STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY} must be an object."
        )
    headers: dict[str, str] = {}
    for raw_key, raw_value in raw_headers.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise ValueError(
                f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
                f"{STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY} must map strings to strings."
            )
        key = raw_key.strip()
        if key == "":
            raise ValueError(
                f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
                f"{STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY} contains a blank header name."
            )
        headers[key] = raw_value.strip()
    return headers


def _profile_by_id(
    profiles: Mapping[str, StructuredLLMProviderProfile],
    provider_id: str,
    *,
    env_name: str,
) -> StructuredLLMProviderProfile:
    profile = profiles.get(provider_id)
    if profile is None:
        raise ValueError(f"{env_name} references unknown structured provider {provider_id!r}.")
    return profile


def _endpoint_kind(raw: str, *, provider_id: str) -> StructuredLLMEndpointKind:
    try:
        return StructuredLLMEndpointKind(raw)
    except ValueError as exc:
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
            f"{STRUCTURED_LLM_PROVIDER_ENDPOINT_KIND_KEY} is unsupported: {raw!r}."
        ) from exc


def _output_mode(raw: str, *, provider_id: str) -> StructuredLLMOutputMode:
    try:
        return StructuredLLMOutputMode(raw)
    except ValueError as exc:
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
            f"{STRUCTURED_LLM_PROVIDER_OUTPUT_MODE_KEY} is unsupported: {raw!r}."
        ) from exc


def _optional_reasoning_effort(
    payload: Mapping[object, object], *, provider_id: str
) -> StructuredLLMReasoningEffort | None:
    raw = _optional_str(payload, STRUCTURED_LLM_PROVIDER_REASONING_EFFORT_KEY, provider_id)
    if raw is None:
        return None
    try:
        return StructuredLLMReasoningEffort(raw)
    except ValueError as exc:
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
            f"{STRUCTURED_LLM_PROVIDER_REASONING_EFFORT_KEY} is unsupported: {raw!r}."
        ) from exc


def _optional_text_verbosity(
    payload: Mapping[object, object], *, provider_id: str
) -> StructuredLLMTextVerbosity | None:
    raw = _optional_str(payload, STRUCTURED_LLM_PROVIDER_TEXT_VERBOSITY_KEY, provider_id)
    if raw is None:
        return None
    try:
        return StructuredLLMTextVerbosity(raw)
    except ValueError as exc:
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}]."
            f"{STRUCTURED_LLM_PROVIDER_TEXT_VERBOSITY_KEY} is unsupported: {raw!r}."
        ) from exc


def _parse_bool_env(source: Mapping[str, str], *, name: str, default: bool) -> bool:
    raw = source.get(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in _BOOL_TRUE_VALUES:
        return True
    if normalized in _BOOL_FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value for {name}: {raw!r}.")


def _required_env(source: Mapping[str, str], name: str) -> str:
    raw = source.get(name)
    if raw is None or raw.strip() == "":
        raise ValueError(f"{name} must be configured when structured LLM is enabled.")
    return raw.strip()


def _optional_env(source: Mapping[str, str], name: str) -> str | None:
    raw = source.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.strip()


def _required_str(payload: Mapping[object, object], key: str, provider_id: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be a non-empty string."
        )
    return value.strip()


def _optional_str(
    payload: Mapping[object, object],
    key: str,
    provider_id: str,
) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be a non-empty string."
        )
    return value.strip()


def _required_bool(payload: Mapping[object, object], key: str, provider_id: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be a boolean."
        )
    return value


def _optional_bool(
    payload: Mapping[object, object],
    key: str,
    provider_id: str,
    *,
    default: bool,
) -> bool:
    value = payload.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be a boolean."
        )
    return value


def _required_int(payload: Mapping[object, object], key: str, provider_id: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be an integer."
        )
    return value


def _optional_float(
    payload: Mapping[object, object],
    key: str,
    provider_id: str,
    *,
    default: float,
) -> float:
    value = payload.get(key)
    if value is None:
        return default
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be numeric."
        )
    return float(value)


def _required_mapping(
    payload: Mapping[object, object],
    key: str,
    provider_id: str,
) -> Mapping[object, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(
            f"{STRUCTURED_LLM_PROVIDERS_JSON_ENV}[{provider_id}].{key} must be an object."
        )
    return value
