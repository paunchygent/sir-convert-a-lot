"""Tests for DeepSeek answer-key model profile manifests.

Purpose:
    Prove the DeepSeek v4 flash provider is represented as a guarded JSON
    Output profile with thinking disabled for advisory answer-key completion.

Relationships:
    - Exercises `infrastructure.answer_key_deepseek_model_profiles`.
    - Complements structured-provider payload tests by locking the DeepSeek
      JSON-object request shape consumed by hot routing and eval probes.
"""

from __future__ import annotations

import json

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMRequest,
    StructuredLLMThinkingMode,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_deepseek_model_profiles import (
    DEEPSEEK_ANSWER_KEY_MAX_OUTPUT_TOKENS,
    DEEPSEEK_API_KEY_ENV,
    DEEPSEEK_CONTEXT_WINDOW_TOKENS,
    AnswerKeyDeepSeekProviderProfileName,
    answer_key_deepseek_defaults_for_provider_profile,
    answer_key_deepseek_provider_json_for_profile,
    answer_key_deepseek_provider_profile_values,
    build_answer_key_deepseek_provider_profile,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    STRUCTURED_LLM_ENABLED_ENV,
    STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV,
    STRUCTURED_LLM_PROVIDERS_JSON_ENV,
    STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV,
    STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV,
    structured_llm_runtime_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_chat_completions_payload,
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


def test_deepseek_model_manifest_contains_v4_flash_non_thinking_profile() -> None:
    assert answer_key_deepseek_provider_profile_values() == ("deepseek-v4-flash-non-thinking",)


def test_deepseek_v4_flash_profile_uses_json_object_without_schema_capability() -> None:
    defaults = answer_key_deepseek_defaults_for_provider_profile("deepseek-v4-flash-non-thinking")
    profile = build_answer_key_deepseek_provider_profile(defaults)

    assert profile.provider_id == "deepseek-v4-flash-non-thinking"
    assert profile.model == "deepseek-v4-flash"
    assert profile.endpoint_kind == StructuredLLMEndpointKind.CHAT_COMPLETIONS
    assert profile.output_mode == StructuredLLMOutputMode.JSON_OBJECT
    assert profile.is_remote is True
    assert profile.context_window_tokens == DEEPSEEK_CONTEXT_WINDOW_TOKENS
    assert profile.max_output_tokens == DEEPSEEK_ANSWER_KEY_MAX_OUTPUT_TOKENS
    assert profile.thinking_mode == StructuredLLMThinkingMode.DISABLED
    assert profile.capabilities.supports_json_schema is False
    assert profile.capabilities.supports_json_object is True
    assert profile.capabilities.supports_multimodal_vision is False


def test_deepseek_provider_json_uses_secret_indirection_without_raw_key() -> None:
    providers_json = answer_key_deepseek_provider_json_for_profile(
        AnswerKeyDeepSeekProviderProfileName.V4_FLASH_NON_THINKING
    )
    decoded = json.loads(providers_json)
    assert isinstance(decoded, dict)
    payload = decoded["deepseek-v4-flash-non-thinking"]
    assert isinstance(payload, dict)

    assert payload["model"] == "deepseek-v4-flash"
    assert payload["endpoint_kind"] == "chat_completions"
    assert payload["output_mode"] == "json_object"
    assert payload["thinking_mode"] == "disabled"
    assert payload["base_url"] == "https://api.deepseek.com"
    assert payload["api_key_env"] == DEEPSEEK_API_KEY_ENV
    assert payload["capabilities"] == {
        "supports_gbnf": False,
        "supports_json_object": True,
        "supports_json_schema": False,
        "supports_multimodal_vision": False,
        "supports_vllm_structured_choice": False,
    }
    assert "api_key" not in payload
    assert "secret" not in providers_json.lower()


def test_deepseek_chat_payload_uses_json_object_and_disables_thinking() -> None:
    defaults = answer_key_deepseek_defaults_for_provider_profile("deepseek-v4-flash-non-thinking")
    profile = build_answer_key_deepseek_provider_profile(defaults)

    payload = build_chat_completions_payload(profile=profile, request=_request())

    assert payload["model"] == "deepseek-v4-flash"
    assert payload["max_tokens"] == 128
    assert payload["temperature"] == 0.0
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["thinking"] == {"type": "disabled"}
    assert "json_schema" not in json.dumps(payload, sort_keys=True)


def test_structured_config_loads_deepseek_manifest_with_sanctioned_secret() -> None:
    providers_json = answer_key_deepseek_provider_json_for_profile(
        AnswerKeyDeepSeekProviderProfileName.V4_FLASH_NON_THINKING
    )

    config = structured_llm_runtime_config_from_env(
        {
            STRUCTURED_LLM_ENABLED_ENV: "true",
            STRUCTURED_LLM_PROVIDERS_JSON_ENV: providers_json,
            STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV: "deepseek-v4-flash-non-thinking",
            STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV: "true",
            STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV: "true",
            DEEPSEEK_API_KEY_ENV: "test-deepseek-token",
        }
    )

    assert config.provider_set is not None
    profile = config.provider_set.primary
    assert profile.model == "deepseek-v4-flash"
    assert profile.output_mode == StructuredLLMOutputMode.JSON_OBJECT
    assert profile.thinking_mode == StructuredLLMThinkingMode.DISABLED
    assert config.connections["deepseek-v4-flash-non-thinking"].api_key == ("test-deepseek-token")


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-001",
        item_id="item-001",
        item_type="single_choice",
        prompt_template_version="answer_key_choice_prompt_v1",
        system_prompt="Return JSON only for one answer-key decision.",
        user_payload='{"output":{"json_shape":"Return one JSON object."}}',
        output_spec=StructuredOutputSpec(
            schema_name="choice_decision",
            schema_version="choice_decision_v1",
            json_schema=CHOICE_DECISION_SCHEMA,
        ),
        estimated_input_tokens=64,
        max_output_tokens=128,
        allow_remote_fallback=None,
    )
