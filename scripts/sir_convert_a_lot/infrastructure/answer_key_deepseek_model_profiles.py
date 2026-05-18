"""DeepSeek answer-key structured-provider model profiles.

Purpose:
    Define the guarded DeepSeek JSON Output provider profile used by advisory
    answer-key completion without claiming strict JSON Schema support.

Relationships:
    - Complements OpenAI Responses and local Qwen profiles behind the same
      source-neutral structured-provider harness.
    - Produces `StructuredLLMProviderProfile` values consumed by hot routing,
      runtime config, provider payload construction, and evaluation probes.
    - Keeps raw DeepSeek secrets outside persisted configuration through
      environment-variable indirection.
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
    StructuredLLMThinkingMode,
)

DEEPSEEK_PROVIDER_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_API_KEY_ENV = "SIR_CONVERT_A_LOT_DEEPSEEK_API_KEY"
DEEPSEEK_CHAT_OUTPUT_MODE = StructuredLLMOutputMode.JSON_OBJECT
DEEPSEEK_V4_FLASH_MODEL = "deepseek-v4-flash"
DEEPSEEK_CONTEXT_WINDOW_TOKENS = 1_000_000
DEEPSEEK_MAX_OUTPUT_TOKENS = 384_000
DEEPSEEK_ANSWER_KEY_MAX_OUTPUT_TOKENS = 4_096
DEEPSEEK_ANSWER_KEY_TIMEOUT_SECONDS = 90.0
DEEPSEEK_ANSWER_KEY_TEMPERATURE = 0.0
DEEPSEEK_ANSWER_KEY_THINKING_MODE = StructuredLLMThinkingMode.DISABLED


class AnswerKeyDeepSeekProviderProfileName(StrEnum):
    """Pinned DeepSeek provider profiles for answer-key completion."""

    V4_FLASH_NON_THINKING = "deepseek-v4-flash-non-thinking"


@dataclass(frozen=True)
class AnswerKeyDeepSeekProviderDefaults:
    """Default structured-provider settings for one DeepSeek profile."""

    profile_name: AnswerKeyDeepSeekProviderProfileName
    provider_id: str
    model: str
    context_window_tokens: int
    max_output_tokens: int
    answer_key_max_output_tokens: int
    timeout_seconds: float
    temperature: float
    thinking_mode: StructuredLLMThinkingMode
    base_url: str = DEEPSEEK_PROVIDER_BASE_URL
    api_key_env: str = DEEPSEEK_API_KEY_ENV


ANSWER_KEY_DEEPSEEK_PROVIDER_DEFAULTS = {
    AnswerKeyDeepSeekProviderProfileName.V4_FLASH_NON_THINKING: (
        AnswerKeyDeepSeekProviderDefaults(
            profile_name=AnswerKeyDeepSeekProviderProfileName.V4_FLASH_NON_THINKING,
            provider_id=AnswerKeyDeepSeekProviderProfileName.V4_FLASH_NON_THINKING.value,
            model=DEEPSEEK_V4_FLASH_MODEL,
            context_window_tokens=DEEPSEEK_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=DEEPSEEK_MAX_OUTPUT_TOKENS,
            answer_key_max_output_tokens=DEEPSEEK_ANSWER_KEY_MAX_OUTPUT_TOKENS,
            timeout_seconds=DEEPSEEK_ANSWER_KEY_TIMEOUT_SECONDS,
            temperature=DEEPSEEK_ANSWER_KEY_TEMPERATURE,
            thinking_mode=DEEPSEEK_ANSWER_KEY_THINKING_MODE,
        )
    )
}


def answer_key_deepseek_provider_profile_values() -> tuple[str, ...]:
    """Return CLI-safe DeepSeek answer-key profile values."""

    return tuple(profile.value for profile in AnswerKeyDeepSeekProviderProfileName)


def parse_answer_key_deepseek_provider_profile_name(
    value: str,
) -> AnswerKeyDeepSeekProviderProfileName:
    """Parse a DeepSeek answer-key provider profile value."""

    try:
        return AnswerKeyDeepSeekProviderProfileName(value)
    except ValueError as exc:
        values = ", ".join(answer_key_deepseek_provider_profile_values())
        message = f"Unsupported DeepSeek answer-key provider profile {value!r}; expected {values}."
        raise ValueError(message) from exc


def answer_key_deepseek_defaults_for_provider_profile(
    value: str,
) -> AnswerKeyDeepSeekProviderDefaults:
    """Return defaults for a DeepSeek answer-key provider profile."""

    profile_name = parse_answer_key_deepseek_provider_profile_name(value)
    return ANSWER_KEY_DEEPSEEK_PROVIDER_DEFAULTS[profile_name]


def build_answer_key_deepseek_provider_profile(
    defaults: AnswerKeyDeepSeekProviderDefaults,
) -> StructuredLLMProviderProfile:
    """Build a source-neutral structured-provider profile for DeepSeek."""

    return StructuredLLMProviderProfile(
        provider_id=defaults.provider_id,
        model=defaults.model,
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        output_mode=DEEPSEEK_CHAT_OUTPUT_MODE,
        is_remote=True,
        context_window_tokens=defaults.context_window_tokens,
        max_output_tokens=defaults.answer_key_max_output_tokens,
        temperature=defaults.temperature,
        thinking_mode=defaults.thinking_mode,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=False,
            supports_json_object=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=False,
        ),
    )


def answer_key_deepseek_provider_json_for_profile(
    profile_name: AnswerKeyDeepSeekProviderProfileName,
    *,
    api_key_env: str = DEEPSEEK_API_KEY_ENV,
) -> str:
    """Render compact provider JSON for one DeepSeek profile."""

    defaults = ANSWER_KEY_DEEPSEEK_PROVIDER_DEFAULTS[profile_name]
    payload = {
        defaults.provider_id: {
            "model": defaults.model,
            "endpoint_kind": StructuredLLMEndpointKind.CHAT_COMPLETIONS.value,
            "output_mode": DEEPSEEK_CHAT_OUTPUT_MODE.value,
            "is_remote": True,
            "context_window_tokens": defaults.context_window_tokens,
            "max_output_tokens": defaults.answer_key_max_output_tokens,
            "temperature": defaults.temperature,
            "thinking_mode": defaults.thinking_mode.value,
            "base_url": defaults.base_url,
            "api_key_env": api_key_env,
            "timeout_seconds": defaults.timeout_seconds,
            "capabilities": {
                "supports_json_schema": False,
                "supports_json_object": True,
                "supports_gbnf": False,
                "supports_vllm_structured_choice": False,
                "supports_multimodal_vision": False,
            },
        }
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
