"""OpenRouter answer-key structured-provider model profiles.

The GLM profile is the governed failover-only remote profile for answer-key
completion. Its configured context cap bounds this application request without
claiming an upstream model-context limit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
)

OPENROUTER_PROVIDER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY_ENV = "SIR_CONVERT_A_LOT_OPENROUTER_API_KEY"
OPENROUTER_GLM53_FLASH_MODEL = "z-ai/glm-5.3-flash"
OPENROUTER_GLM53_FLASH_CONTEXT_CAP_TOKENS = 32_768
OPENROUTER_ANSWER_KEY_MAX_OUTPUT_TOKENS = 4_096
OPENROUTER_ANSWER_KEY_TIMEOUT_SECONDS = 90.0
OPENROUTER_ANSWER_KEY_TEMPERATURE = 0.0


class AnswerKeyOpenRouterProviderProfileName(StrEnum):
    """Pinned OpenRouter failover profile for answer-key completion."""

    GLM53_FLASH = "openrouter-glm-5.3-flash"


@dataclass(frozen=True)
class AnswerKeyOpenRouterProviderDefaults:
    """Default structured-provider settings for the governed GLM failover."""

    profile_name: AnswerKeyOpenRouterProviderProfileName
    provider_id: str
    model: str
    context_window_tokens: int
    answer_key_max_output_tokens: int
    timeout_seconds: float
    temperature: float
    base_url: str = OPENROUTER_PROVIDER_BASE_URL
    api_key_env: str = OPENROUTER_API_KEY_ENV


ANSWER_KEY_OPENROUTER_PROVIDER_DEFAULTS = {
    AnswerKeyOpenRouterProviderProfileName.GLM53_FLASH: AnswerKeyOpenRouterProviderDefaults(
        profile_name=AnswerKeyOpenRouterProviderProfileName.GLM53_FLASH,
        provider_id=AnswerKeyOpenRouterProviderProfileName.GLM53_FLASH.value,
        model=OPENROUTER_GLM53_FLASH_MODEL,
        context_window_tokens=OPENROUTER_GLM53_FLASH_CONTEXT_CAP_TOKENS,
        answer_key_max_output_tokens=OPENROUTER_ANSWER_KEY_MAX_OUTPUT_TOKENS,
        timeout_seconds=OPENROUTER_ANSWER_KEY_TIMEOUT_SECONDS,
        temperature=OPENROUTER_ANSWER_KEY_TEMPERATURE,
    )
}


def answer_key_openrouter_defaults() -> AnswerKeyOpenRouterProviderDefaults:
    """Return defaults for the checked-in OpenRouter GLM failover profile."""

    return ANSWER_KEY_OPENROUTER_PROVIDER_DEFAULTS[
        AnswerKeyOpenRouterProviderProfileName.GLM53_FLASH
    ]


def build_answer_key_openrouter_provider_profile(
    defaults: AnswerKeyOpenRouterProviderDefaults,
) -> StructuredLLMProviderProfile:
    """Build the text-only Chat Completions profile for the GLM failover."""

    return StructuredLLMProviderProfile(
        provider_id=defaults.provider_id,
        model=defaults.model,
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=defaults.context_window_tokens,
        max_output_tokens=defaults.answer_key_max_output_tokens,
        temperature=defaults.temperature,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=False,
        ),
    )


def answer_key_openrouter_provider_json() -> str:
    """Render secret-indirected provider JSON for the GLM failover profile."""

    defaults = answer_key_openrouter_defaults()
    payload = {
        defaults.provider_id: {
            "model": defaults.model,
            "endpoint_kind": StructuredLLMEndpointKind.CHAT_COMPLETIONS.value,
            "output_mode": StructuredLLMOutputMode.JSON_SCHEMA.value,
            "is_remote": True,
            "context_window_tokens": defaults.context_window_tokens,
            "max_output_tokens": defaults.answer_key_max_output_tokens,
            "temperature": defaults.temperature,
            "base_url": defaults.base_url,
            "api_key_env": defaults.api_key_env,
            "timeout_seconds": defaults.timeout_seconds,
            "capabilities": {
                "supports_json_schema": True,
                "supports_gbnf": False,
                "supports_vllm_structured_choice": False,
                "supports_multimodal_vision": False,
            },
        }
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def is_answer_key_openrouter_provider_profile(profile: StructuredLLMProviderProfile) -> bool:
    """Identify the one profile that requires OpenRouter parameter routing."""

    return profile.provider_id == AnswerKeyOpenRouterProviderProfileName.GLM53_FLASH.value
