"""Answer-key provider runtime configuration rendering.

Purpose:
    Render governed structured-provider environment values for advisory
    answer-key completion across OpenAI and local Qwen provider profiles for
    local host, local Compose, and Hemma production Compose lanes.

Relationships:
    - Used by `structured_llm_config` to load named provider profiles without
      raw production JSON hand-editing.
    - Used by DevOps helpers to stamp the canonical Hemma `.env` values.
    - Keeps production provider URLs on Docker service DNS while preserving the
      host-local loopback lane used by local evaluation.
"""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

from scripts.sir_convert_a_lot.infrastructure.answer_key_deepseek_model_profiles import (
    AnswerKeyDeepSeekProviderProfileName,
    answer_key_deepseek_provider_json_for_profile,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_local_model_profiles import (
    LLAMA_CPP_PROVIDER_ID,
    QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS,
    QWEN36_LLAMA_CPP_MAX_OUTPUT_TOKENS,
    QWEN36_LLAMA_CPP_MODEL,
    QWEN36_LLAMA_CPP_MTP_MODEL,
    QWEN36_LLAMA_CPP_TEMPERATURE,
    AnswerKeyProviderProfileName,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_openai_model_profiles import (
    AnswerKeyOpenAIProviderProfileName,
    answer_key_openai_provider_json_for_profile,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_openrouter_model_profiles import (
    AnswerKeyOpenRouterProviderProfileName,
    answer_key_openrouter_provider_json,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)

STRUCTURED_LLM_PROVIDER_PROFILE_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDER_PROFILE"
STRUCTURED_LLM_RUNTIME_LANE_ENV = "SIR_CONVERT_A_LOT_STRUCTURED_LLM_RUNTIME_LANE"

QWEN36_LLAMA_CPP_LOCAL_HOST_URL = "http://127.0.0.1:8082"
QWEN36_LLAMA_CPP_LOCAL_COMPOSE_URL = "http://host.docker.internal:8082"
QWEN36_LLAMA_CPP_HEMMA_PROD_COMPOSE_URL = "http://sir_convert_qwen_answer_key:8082"
QWEN36_LLAMA_CPP_PRODUCTION_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/answer-key-qwen-provider"
)
QWEN36_LLAMA_CPP_PRODUCTION_VISION_MEDIA_PATH = (
    QWEN36_LLAMA_CPP_PRODUCTION_OUTPUT_ROOT / "vision-assets"
)
QWEN36_LLAMA_CPP_PRODUCTION_VISION_MEDIA_HOST_PATH = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/build/verification/answer-key-qwen-provider/vision-assets"
)

_PROD_FORBIDDEN_PROVIDER_HOSTS = frozenset({"127.0.0.1", "localhost", "host.docker.internal"})
AnswerKeyRuntimeProviderProfileName = (
    AnswerKeyProviderProfileName
    | AnswerKeyOpenAIProviderProfileName
    | AnswerKeyDeepSeekProviderProfileName
)


class AnswerKeyProviderRuntimeLane(StrEnum):
    """Container reachability lanes for structured answer-key providers."""

    LOCAL_HOST = "local-host"
    LOCAL_COMPOSE = "local-compose"
    HEMMA_PROD_COMPOSE = "hemma-prod-compose"


def render_answer_key_provider_environment(
    *,
    lane: AnswerKeyProviderRuntimeLane,
    profile_name: AnswerKeyRuntimeProviderProfileName = (
        AnswerKeyOpenAIProviderProfileName.GPT56_LUNA
    ),
) -> dict[str, str]:
    """Render canonical env keys for one answer-key provider profile."""

    providers_json = answer_key_provider_json_for_profile(lane=lane, profile_name=profile_name)
    is_api_profile = isinstance(
        profile_name,
        AnswerKeyOpenAIProviderProfileName | AnswerKeyDeepSeekProviderProfileName,
    )
    primary_provider_id = profile_name.value if is_api_profile else LLAMA_CPP_PROVIDER_ID
    remote_enabled = "1" if is_api_profile else "0"
    fallback_provider_id = ""
    if profile_name == AnswerKeyOpenAIProviderProfileName.GPT56_LUNA:
        fallback_provider_id = AnswerKeyOpenRouterProviderProfileName.GLM53_FLASH.value
    return {
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_ENABLED": "1",
        STRUCTURED_LLM_PROVIDER_PROFILE_ENV: profile_name.value,
        STRUCTURED_LLM_RUNTIME_LANE_ENV: lane.value,
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDERS_JSON": providers_json,
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_PRIMARY_PROVIDER_ID": primary_provider_id,
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_FALLBACK_PROVIDER_ID": fallback_provider_id,
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED": remote_enabled,
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED": remote_enabled,
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_PATH": (
            QWEN36_LLAMA_CPP_PRODUCTION_VISION_MEDIA_PATH.as_posix()
        ),
        "SIR_CONVERT_A_LOT_STRUCTURED_LLM_VISION_MEDIA_HOST_PATH": (
            QWEN36_LLAMA_CPP_PRODUCTION_VISION_MEDIA_HOST_PATH.as_posix()
        ),
    }


def answer_key_provider_json_for_profile(
    *,
    lane: AnswerKeyProviderRuntimeLane,
    profile_name: AnswerKeyRuntimeProviderProfileName,
) -> str:
    """Render compact provider JSON for the selected runtime lane."""

    if isinstance(profile_name, AnswerKeyDeepSeekProviderProfileName):
        del lane
        return answer_key_deepseek_provider_json_for_profile(profile_name)
    if isinstance(profile_name, AnswerKeyOpenAIProviderProfileName):
        del lane
        if profile_name == AnswerKeyOpenAIProviderProfileName.GPT56_LUNA:
            return _luna_remote_provider_catalog()
        return answer_key_openai_provider_json_for_profile(profile_name)
    if profile_name not in {
        AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP,
        AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP,
    }:
        raise ValueError(f"Unsupported production answer-key provider profile: {profile_name}")
    payload = {
        LLAMA_CPP_PROVIDER_ID: {
            "model": _model_for_profile(profile_name),
            "endpoint_kind": "llama_cpp_chat_completions",
            "output_mode": "json_schema",
            "is_remote": False,
            "context_window_tokens": QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS,
            "max_output_tokens": QWEN36_LLAMA_CPP_MAX_OUTPUT_TOKENS,
            "temperature": QWEN36_LLAMA_CPP_TEMPERATURE,
            "base_url": _provider_url_for_lane(lane),
            "timeout_seconds": 90.0,
            "capabilities": {
                "supports_json_schema": True,
                "supports_gbnf": True,
                "supports_vllm_structured_choice": False,
                "supports_multimodal_vision": True,
            },
        }
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _luna_remote_provider_catalog() -> str:
    """Render the governed Luna primary and GLM failover provider catalog."""

    luna_payload = json.loads(
        answer_key_openai_provider_json_for_profile(AnswerKeyOpenAIProviderProfileName.GPT56_LUNA)
    )
    glm_payload = json.loads(answer_key_openrouter_provider_json())
    catalog = {**luna_payload, **glm_payload}
    return json.dumps(catalog, sort_keys=True, separators=(",", ":"))


def provider_json_from_runtime_profile(source: Mapping[str, str]) -> str:
    """Render provider JSON from profile and lane environment variables."""

    raw_profile = _required_env(source, STRUCTURED_LLM_PROVIDER_PROFILE_ENV)
    profile_name = _runtime_profile_name(raw_profile)
    return answer_key_provider_json_for_profile(
        lane=runtime_lane_from_env(source),
        profile_name=profile_name,
    )


def runtime_lane_from_env(source: Mapping[str, str]) -> AnswerKeyProviderRuntimeLane:
    """Parse configured runtime lane, defaulting to host-local development."""

    raw_lane = source.get(STRUCTURED_LLM_RUNTIME_LANE_ENV)
    if raw_lane is None or raw_lane.strip() == "":
        return AnswerKeyProviderRuntimeLane.LOCAL_HOST
    return AnswerKeyProviderRuntimeLane(raw_lane.strip())


def validate_structured_llm_connections_for_runtime_lane(
    *,
    lane: AnswerKeyProviderRuntimeLane,
    connections: Mapping[str, StructuredLLMProviderConnection],
) -> None:
    """Reject provider URLs that are invalid for the selected runtime lane."""

    if lane != AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE:
        return
    for connection in connections.values():
        _reject_production_container_host_alias(connection.base_url)


def _provider_url_for_lane(lane: AnswerKeyProviderRuntimeLane) -> str:
    if lane == AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE:
        return QWEN36_LLAMA_CPP_HEMMA_PROD_COMPOSE_URL
    if lane == AnswerKeyProviderRuntimeLane.LOCAL_COMPOSE:
        return QWEN36_LLAMA_CPP_LOCAL_COMPOSE_URL
    return QWEN36_LLAMA_CPP_LOCAL_HOST_URL


def _model_for_profile(profile_name: AnswerKeyProviderProfileName) -> str:
    if profile_name == AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP:
        return QWEN36_LLAMA_CPP_MTP_MODEL
    return QWEN36_LLAMA_CPP_MODEL


def _runtime_profile_name(raw_profile: str) -> AnswerKeyRuntimeProviderProfileName:
    try:
        return AnswerKeyDeepSeekProviderProfileName(raw_profile)
    except ValueError:
        pass
    try:
        return AnswerKeyOpenAIProviderProfileName(raw_profile)
    except ValueError:
        return AnswerKeyProviderProfileName(raw_profile)


def _reject_production_container_host_alias(raw_url: str) -> None:
    parsed = urlparse(raw_url)
    host = parsed.hostname
    if host is None or host.strip() == "":
        raise ValueError("Production structured provider URL must include a host.")
    normalized_host = host.strip().lower()
    if normalized_host in _PROD_FORBIDDEN_PROVIDER_HOSTS:
        raise ValueError(
            "Production structured provider URL must use Docker service DNS; "
            f"rejected host {host!r}."
        )
    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        return
    if address.is_loopback or address.is_unspecified:
        raise ValueError(
            "Production structured provider URL must use Docker service DNS; "
            f"rejected address {host!r}."
        )


def _required_env(source: Mapping[str, str], name: str) -> str:
    raw = source.get(name)
    if raw is None or raw.strip() == "":
        raise ValueError(f"{name} must be configured for structured answer-key provider profile.")
    return raw.strip()
