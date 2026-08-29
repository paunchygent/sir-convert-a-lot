"""Tests for the governed remote answer-key provider profiles."""

from __future__ import annotations

import json

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_openrouter_model_profiles import (
    OPENROUTER_API_KEY_ENV,
    answer_key_openrouter_defaults,
    answer_key_openrouter_provider_json,
    build_answer_key_openrouter_provider_profile,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_chat_completions_payload,
)

_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {"selected_choice_ids": {"type": "array", "items": {"type": "string"}}},
    "required": ["selected_choice_ids"],
    "additionalProperties": False,
}


def test_openrouter_glm_failover_profile_has_exact_model_and_secret_indirection() -> None:
    defaults = answer_key_openrouter_defaults()
    profile = build_answer_key_openrouter_provider_profile(defaults)
    catalog = json.loads(answer_key_openrouter_provider_json())

    assert profile.provider_id == "openrouter-glm-5.3-flash"
    assert profile.provider_id != profile.model
    assert profile.model == "z-ai/glm-5.3-flash"
    assert profile.endpoint_kind == StructuredLLMEndpointKind.CHAT_COMPLETIONS
    assert profile.output_mode == StructuredLLMOutputMode.JSON_SCHEMA
    assert profile.is_remote is True
    assert profile.temperature == 0.0
    assert profile.capabilities.supports_multimodal_vision is False
    assert catalog[profile.provider_id]["base_url"] == "https://openrouter.ai/api/v1"
    assert catalog[profile.provider_id]["api_key_env"] == OPENROUTER_API_KEY_ENV
    assert "api_key" not in catalog[profile.provider_id]


def test_openrouter_glm_payload_requires_supported_parameters_and_json_schema() -> None:
    profile = build_answer_key_openrouter_provider_profile(answer_key_openrouter_defaults())

    payload = build_chat_completions_payload(profile=profile, request=_request())

    assert payload["model"] == "z-ai/glm-5.3-flash"
    assert payload["max_tokens"] == 128
    assert payload["temperature"] == 0.0
    assert payload["provider"] == {"require_parameters": True}
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "choice_decision", "strict": True, "schema": _SCHEMA},
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
            json_schema=_SCHEMA,
        ),
        estimated_input_tokens=64,
        max_output_tokens=128,
        allow_remote_fallback=True,
    )
