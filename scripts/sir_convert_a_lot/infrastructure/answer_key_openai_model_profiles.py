"""OpenAI answer-key structured-provider model profiles.

Purpose:
    Define the pinned OpenAI Responses provider profiles used by advisory
    answer-key completion and the linked model-evaluation gate.

Relationships:
    - Complements local profiles from `answer_key_local_model_profiles` without
      changing local Qwen routing defaults.
    - Produces source-neutral `StructuredLLMProviderProfile` values consumed by
      the existing structured-provider harness.
    - Supplies provider JSON fragments for operator settings and Task 326 eval
      runs while keeping raw OpenAI secrets outside persisted configuration.
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
    StructuredLLMReasoningEffort,
    StructuredLLMTextVerbosity,
)

OPENAI_PROVIDER_BASE_URL = "https://api.openai.com"
OPENAI_API_KEY_ENV = "SIR_CONVERT_A_LOT_OPENAI_API_KEY"
OPENAI_RESPONSES_OUTPUT_MODE = StructuredLLMOutputMode.JSON_SCHEMA
OPENAI_CONTEXT_WINDOW_TOKENS = 400_000
OPENAI_MAX_OUTPUT_TOKENS = 128_000
OPENAI_ANSWER_KEY_MAX_OUTPUT_TOKENS = 4_096
OPENAI_ANSWER_KEY_TIMEOUT_SECONDS = 90.0
OPENAI_ANSWER_KEY_TEMPERATURE = 0.0
OPENAI_ANSWER_KEY_REASONING_EFFORT = StructuredLLMReasoningEffort.NONE
OPENAI_ANSWER_KEY_TEXT_VERBOSITY = StructuredLLMTextVerbosity.LOW


class AnswerKeyOpenAIProviderProfileName(StrEnum):
    """Pinned OpenAI provider profiles for answer-key completion."""

    GPT54_MINI_2026_03_17 = "openai-gpt-5.4-mini-2026-03-17"
    GPT54_NANO_2026_03_17 = "openai-gpt-5.4-nano-2026-03-17"


@dataclass(frozen=True)
class AnswerKeyOpenAIProviderDefaults:
    """Default structured-provider settings for one pinned OpenAI snapshot."""

    profile_name: AnswerKeyOpenAIProviderProfileName
    provider_id: str
    model: str
    context_window_tokens: int
    max_output_tokens: int
    answer_key_max_output_tokens: int
    timeout_seconds: float
    temperature: float
    reasoning_effort: StructuredLLMReasoningEffort
    text_verbosity: StructuredLLMTextVerbosity
    base_url: str = OPENAI_PROVIDER_BASE_URL
    api_key_env: str = OPENAI_API_KEY_ENV


OPENAI_GPT54_MINI_MODEL = "gpt-5.4-mini-2026-03-17"
OPENAI_GPT54_NANO_MODEL = "gpt-5.4-nano-2026-03-17"

ANSWER_KEY_OPENAI_PROVIDER_DEFAULTS = {
    AnswerKeyOpenAIProviderProfileName.GPT54_MINI_2026_03_17: (
        AnswerKeyOpenAIProviderDefaults(
            profile_name=AnswerKeyOpenAIProviderProfileName.GPT54_MINI_2026_03_17,
            provider_id=AnswerKeyOpenAIProviderProfileName.GPT54_MINI_2026_03_17.value,
            model=OPENAI_GPT54_MINI_MODEL,
            context_window_tokens=OPENAI_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
            answer_key_max_output_tokens=OPENAI_ANSWER_KEY_MAX_OUTPUT_TOKENS,
            timeout_seconds=OPENAI_ANSWER_KEY_TIMEOUT_SECONDS,
            temperature=OPENAI_ANSWER_KEY_TEMPERATURE,
            reasoning_effort=OPENAI_ANSWER_KEY_REASONING_EFFORT,
            text_verbosity=OPENAI_ANSWER_KEY_TEXT_VERBOSITY,
        )
    ),
    AnswerKeyOpenAIProviderProfileName.GPT54_NANO_2026_03_17: (
        AnswerKeyOpenAIProviderDefaults(
            profile_name=AnswerKeyOpenAIProviderProfileName.GPT54_NANO_2026_03_17,
            provider_id=AnswerKeyOpenAIProviderProfileName.GPT54_NANO_2026_03_17.value,
            model=OPENAI_GPT54_NANO_MODEL,
            context_window_tokens=OPENAI_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
            answer_key_max_output_tokens=OPENAI_ANSWER_KEY_MAX_OUTPUT_TOKENS,
            timeout_seconds=OPENAI_ANSWER_KEY_TIMEOUT_SECONDS,
            temperature=OPENAI_ANSWER_KEY_TEMPERATURE,
            reasoning_effort=OPENAI_ANSWER_KEY_REASONING_EFFORT,
            text_verbosity=OPENAI_ANSWER_KEY_TEXT_VERBOSITY,
        )
    ),
}


def answer_key_openai_provider_profile_values() -> tuple[str, ...]:
    """Return CLI-safe OpenAI answer-key profile values."""

    return tuple(profile.value for profile in AnswerKeyOpenAIProviderProfileName)


def parse_answer_key_openai_provider_profile_name(
    value: str,
) -> AnswerKeyOpenAIProviderProfileName:
    """Parse a pinned OpenAI answer-key provider profile value."""

    try:
        return AnswerKeyOpenAIProviderProfileName(value)
    except ValueError as exc:
        values = ", ".join(answer_key_openai_provider_profile_values())
        message = f"Unsupported OpenAI answer-key provider profile {value!r}; expected {values}."
        raise ValueError(message) from exc


def answer_key_openai_defaults_for_provider_profile(
    value: str,
) -> AnswerKeyOpenAIProviderDefaults:
    """Return defaults for a pinned OpenAI answer-key provider profile."""

    profile_name = parse_answer_key_openai_provider_profile_name(value)
    return ANSWER_KEY_OPENAI_PROVIDER_DEFAULTS[profile_name]


def build_answer_key_openai_provider_profile(
    defaults: AnswerKeyOpenAIProviderDefaults,
    *,
    supports_multimodal_vision: bool = True,
) -> StructuredLLMProviderProfile:
    """Build a source-neutral structured-provider profile for OpenAI Responses."""

    return StructuredLLMProviderProfile(
        provider_id=defaults.provider_id,
        model=defaults.model,
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=OPENAI_RESPONSES_OUTPUT_MODE,
        is_remote=True,
        context_window_tokens=defaults.context_window_tokens,
        max_output_tokens=defaults.answer_key_max_output_tokens,
        temperature=defaults.temperature,
        reasoning_effort=defaults.reasoning_effort,
        text_verbosity=defaults.text_verbosity,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=supports_multimodal_vision,
        ),
    )


def answer_key_openai_provider_json_for_profile(
    profile_name: AnswerKeyOpenAIProviderProfileName,
    *,
    api_key_env: str = OPENAI_API_KEY_ENV,
    supports_multimodal_vision: bool = True,
) -> str:
    """Render compact provider JSON for one pinned OpenAI profile."""

    defaults = ANSWER_KEY_OPENAI_PROVIDER_DEFAULTS[profile_name]
    payload = {
        defaults.provider_id: {
            "model": defaults.model,
            "endpoint_kind": StructuredLLMEndpointKind.RESPONSES.value,
            "output_mode": OPENAI_RESPONSES_OUTPUT_MODE.value,
            "is_remote": True,
            "context_window_tokens": defaults.context_window_tokens,
            "max_output_tokens": defaults.answer_key_max_output_tokens,
            "temperature": defaults.temperature,
            "reasoning_effort": defaults.reasoning_effort.value,
            "text_verbosity": defaults.text_verbosity.value,
            "base_url": defaults.base_url,
            "api_key_env": api_key_env,
            "timeout_seconds": defaults.timeout_seconds,
            "capabilities": {
                "supports_json_schema": True,
                "supports_gbnf": False,
                "supports_vllm_structured_choice": False,
                "supports_multimodal_vision": supports_multimodal_vision,
            },
        }
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
