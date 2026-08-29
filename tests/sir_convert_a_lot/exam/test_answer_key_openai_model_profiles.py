"""Tests for OpenAI answer-key model profile manifests.

Purpose:
    Prove HTML to PDF route5's first OpenAI provider profiles are pinned, Responses-based,
    and secret-indirected before the hot routing implementation consumes them.

Relationships:
    - Exercises `infrastructure.answer_key_openai_model_profiles`.
    - Complements structured-provider payload tests by locking the OpenAI model
      manifest surface used by OpenAI answer-key evaluation evaluation.
"""

from __future__ import annotations

import json

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_openai_model_profiles import (
    OPENAI_ANSWER_KEY_MAX_OUTPUT_TOKENS,
    OPENAI_ANSWER_KEY_REASONING_EFFORT,
    OPENAI_ANSWER_KEY_TEXT_VERBOSITY,
    OPENAI_API_KEY_ENV,
    OPENAI_CONTEXT_WINDOW_TOKENS,
    AnswerKeyOpenAIProviderProfileName,
    answer_key_openai_defaults_for_provider_profile,
    answer_key_openai_provider_json_for_profile,
    answer_key_openai_provider_profile_values,
    build_answer_key_openai_provider_profile,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    STRUCTURED_LLM_ENABLED_ENV,
    STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV,
    STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV,
    STRUCTURED_LLM_PROVIDERS_JSON_ENV,
    STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV,
    STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV,
    structured_llm_runtime_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_responses_payload,
)

CHOICE_DECISION_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {
        "selected_choice_ids": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "manual_follow_up_required": {"type": "boolean"},
    },
    "required": ["selected_choice_ids", "manual_follow_up_required"],
    "additionalProperties": False,
}


def test_openai_model_manifest_contains_pinned_answer_key_profiles() -> None:
    assert answer_key_openai_provider_profile_values() == (
        "openai-gpt-5.6-luna",
        "openai-gpt-5.4-mini-2026-03-17",
        "openai-gpt-5.4-nano-2026-03-17",
    )


def test_openai_mini_profile_uses_responses_json_schema_and_snapshot_model() -> None:
    defaults = answer_key_openai_defaults_for_provider_profile("openai-gpt-5.4-mini-2026-03-17")
    profile = build_answer_key_openai_provider_profile(defaults)

    assert profile.provider_id == "openai-gpt-5.4-mini-2026-03-17"
    assert profile.model == "gpt-5.4-mini-2026-03-17"
    assert profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES
    assert profile.output_mode == StructuredLLMOutputMode.JSON_SCHEMA
    assert profile.is_remote is True
    assert profile.context_window_tokens == OPENAI_CONTEXT_WINDOW_TOKENS
    assert profile.max_output_tokens == OPENAI_ANSWER_KEY_MAX_OUTPUT_TOKENS
    assert profile.reasoning_effort == OPENAI_ANSWER_KEY_REASONING_EFFORT
    assert profile.text_verbosity == OPENAI_ANSWER_KEY_TEXT_VERBOSITY
    assert profile.capabilities.supports_json_schema is True
    assert profile.capabilities.supports_multimodal_vision is True


def test_openai_luna_profile_uses_low_effort_responses_json_schema() -> None:
    defaults = answer_key_openai_defaults_for_provider_profile("openai-gpt-5.6-luna")
    profile = build_answer_key_openai_provider_profile(defaults)
    payload = build_responses_payload(profile=profile, request=_request())

    assert profile.provider_id == "openai-gpt-5.6-luna"
    assert profile.model == "gpt-5.6-luna"
    assert profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES
    assert profile.output_mode == StructuredLLMOutputMode.JSON_SCHEMA
    assert profile.max_output_tokens == OPENAI_ANSWER_KEY_MAX_OUTPUT_TOKENS
    assert profile.reasoning_effort == StructuredLLMReasoningEffort.LOW
    assert profile.text_verbosity == OPENAI_ANSWER_KEY_TEXT_VERBOSITY
    assert payload["model"] == "gpt-5.6-luna"
    assert payload["store"] is False
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["text"] == {
        "verbosity": "low",
        "format": {
            "type": "json_schema",
            "name": "choice_decision",
            "strict": True,
            "schema": CHOICE_DECISION_SCHEMA,
        },
    }


def test_openai_nano_provider_json_uses_secret_indirection_without_raw_key() -> None:
    providers_json = answer_key_openai_provider_json_for_profile(
        AnswerKeyOpenAIProviderProfileName.GPT54_NANO_2026_03_17
    )
    decoded = json.loads(providers_json)
    assert isinstance(decoded, dict)
    payload = decoded["openai-gpt-5.4-nano-2026-03-17"]
    assert isinstance(payload, dict)

    assert payload["model"] == "gpt-5.4-nano-2026-03-17"
    assert payload["endpoint_kind"] == "responses"
    assert payload["output_mode"] == "json_schema"
    assert payload["is_remote"] is True
    assert payload["reasoning_effort"] == "none"
    assert payload["text_verbosity"] == "low"
    assert payload["base_url"] == "https://api.openai.com"
    assert payload["api_key_env"] == OPENAI_API_KEY_ENV
    assert "api_key" not in payload
    assert "secret" not in providers_json.lower()


def test_openai_responses_payload_uses_pinned_model_and_text_format() -> None:
    defaults = answer_key_openai_defaults_for_provider_profile("openai-gpt-5.4-mini-2026-03-17")
    profile = build_answer_key_openai_provider_profile(defaults)

    payload = build_responses_payload(profile=profile, request=_request())

    assert payload["model"] == "gpt-5.4-mini-2026-03-17"
    assert payload["store"] is False
    assert payload["max_output_tokens"] == 128
    text = payload["text"]
    assert isinstance(text, dict)
    assert text["verbosity"] == "low"
    assert text["format"] == {
        "type": "json_schema",
        "name": "choice_decision",
        "strict": True,
        "schema": CHOICE_DECISION_SCHEMA,
    }
    assert "response_format" not in payload
    assert payload["reasoning"] == {"effort": "none"}


def test_structured_config_loads_openai_manifest_as_secret_indirected_fallback() -> None:
    openai_json = answer_key_openai_provider_json_for_profile(
        AnswerKeyOpenAIProviderProfileName.GPT54_MINI_2026_03_17
    )
    providers = {
        "local-stub": _local_provider_payload(),
        **json.loads(openai_json),
    }

    config = structured_llm_runtime_config_from_env(
        {
            STRUCTURED_LLM_ENABLED_ENV: "true",
            STRUCTURED_LLM_PROVIDERS_JSON_ENV: json.dumps(providers),
            STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV: "local-stub",
            STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV: "openai-gpt-5.4-mini-2026-03-17",
            STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV: "true",
            STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV: "true",
            OPENAI_API_KEY_ENV: "test-openai-token",
        }
    )

    assert config.provider_set is not None
    assert config.provider_set.fallback is not None
    assert config.provider_set.fallback.model == "gpt-5.4-mini-2026-03-17"
    assert config.provider_set.fallback.reasoning_effort == OPENAI_ANSWER_KEY_REASONING_EFFORT
    assert config.provider_set.fallback.text_verbosity == OPENAI_ANSWER_KEY_TEXT_VERBOSITY
    assert config.connections["openai-gpt-5.4-mini-2026-03-17"].api_key == ("test-openai-token")


def _local_provider_payload() -> dict[str, object]:
    return {
        "model": "local-stub",
        "endpoint_kind": "llama_cpp_chat_completions",
        "output_mode": "json_schema",
        "is_remote": False,
        "context_window_tokens": 4096,
        "max_output_tokens": 512,
        "temperature": 0.0,
        "base_url": "http://127.0.0.1:8082",
        "timeout_seconds": 30.0,
        "capabilities": {
            "supports_json_schema": True,
            "supports_gbnf": True,
            "supports_vllm_structured_choice": False,
            "supports_multimodal_vision": False,
        },
    }


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-001",
        item_id="item-001",
        item_type="single_choice",
        prompt_template_version="answer_key_choice_prompt_v1",
        system_prompt="Return a bounded answer-key decision.",
        user_payload='{"item_id":"item-001","choices":["A","B","C"]}',
        output_spec=StructuredOutputSpec(
            schema_name="choice_decision",
            schema_version="choice_decision_v1",
            json_schema=CHOICE_DECISION_SCHEMA,
        ),
        estimated_input_tokens=64,
        max_output_tokens=128,
        allow_remote_fallback=None,
    )
