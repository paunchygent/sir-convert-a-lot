"""Tests for the Task 296 structured LLM provider harness.

Purpose:
    Prove the first provider-harness slice is source-neutral, local-first, and
    metadata-only before advisory answer-key completion starts using it.

Relationships:
    - Exercises `domain.structured_llm_contracts` and
      `infrastructure.structured_llm_payloads`.
    - Keeps provider payload construction separate from DigiExam parser,
      renderer, and target-exporter code.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMCaptureStatus,
    StructuredLLMEndpointKind,
    StructuredLLMImageURLContentPart,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredLLMRoutePolicy,
    StructuredLLMRouteReason,
    StructuredLLMTextContentPart,
    StructuredLLMTextVerbosity,
    StructuredLLMThinkingMode,
    StructuredOutputSpec,
    build_structured_llm_capture_metadata,
    decide_structured_llm_route,
    preflight_structured_llm_prompt,
    resolve_structured_llm_token_budget,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_chat_completions_payload,
    build_llama_cpp_chat_completions_payload,
    build_responses_payload,
    build_vllm_chat_completions_payload,
)

CHOICE_DECISION_SCHEMA_VERSION = "choice_decision_v1"
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


def test_chat_completions_payload_uses_response_format_json_schema() -> None:
    request = _request()
    profile = _profile(endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS)

    payload = build_chat_completions_payload(profile=profile, request=request)

    assert payload["model"] == "local-model"
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    assert json_schema["name"] == "choice_decision"
    assert json_schema["strict"] is True
    assert json_schema["schema"] == CHOICE_DECISION_SCHEMA


def test_chat_completions_payload_can_use_json_object_without_schema_format() -> None:
    request = _request(system_prompt="Return JSON only.")
    profile = _profile(
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_OBJECT,
        is_remote=True,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=False,
            supports_json_object=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
        thinking_mode=StructuredLLMThinkingMode.DISABLED,
    )

    payload = build_chat_completions_payload(profile=profile, request=request)

    assert payload["response_format"] == {"type": "json_object"}
    assert payload["thinking"] == {"type": "disabled"}
    assert "json_schema" not in payload


def test_responses_payload_uses_text_format_json_schema() -> None:
    request = _request()
    profile = _profile(endpoint_kind=StructuredLLMEndpointKind.RESPONSES, is_remote=True)

    payload = build_responses_payload(profile=profile, request=request)

    assert payload["store"] is False
    text = payload["text"]
    assert isinstance(text, dict)
    text_format = text["format"]
    assert isinstance(text_format, dict)
    assert text_format == {
        "type": "json_schema",
        "name": "choice_decision",
        "strict": True,
        "schema": CHOICE_DECISION_SCHEMA,
    }
    assert "response_format" not in payload


def test_responses_payload_emits_manifest_controlled_behavior_settings() -> None:
    request = _request()
    profile = _profile(
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        reasoning_effort=StructuredLLMReasoningEffort.NONE,
        text_verbosity=StructuredLLMTextVerbosity.LOW,
    )

    payload = build_responses_payload(profile=profile, request=request)

    assert payload["reasoning"] == {"effort": "none"}
    text = payload["text"]
    assert isinstance(text, dict)
    assert text["verbosity"] == "low"


def test_llama_cpp_payload_uses_gbnf_when_profile_requires_grammar() -> None:
    request = _request(output_spec=_output_spec(gbnf_grammar='root ::= "A" | "B" | "C"'))
    profile = _profile(
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.GBNF,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
        ),
    )

    payload = build_llama_cpp_chat_completions_payload(profile=profile, request=request)

    assert payload["grammar"] == 'root ::= "A" | "B" | "C"'
    assert "response_format" not in payload


def test_llama_cpp_payload_uses_json_schema_when_capability_selects_schema() -> None:
    request = _request()
    profile = _profile(endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS)

    payload = build_llama_cpp_chat_completions_payload(profile=profile, request=request)

    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    assert json_schema == {
        "name": "choice_decision",
        "schema": CHOICE_DECISION_SCHEMA,
    }


def test_llama_cpp_payload_can_use_multimodal_content_parts() -> None:
    request = _request(
        user_content_parts=(
            StructuredLLMTextContentPart('{"item_id":"item-asset"}'),
            StructuredLLMImageURLContentPart("file://source/item-asset/assets/item-asset-001.png"),
        )
    )
    profile = _profile(
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=True,
        ),
    )

    payload = build_llama_cpp_chat_completions_payload(profile=profile, request=request)
    messages = payload["messages"]
    assert isinstance(messages, list)
    user_message = messages[1]
    assert isinstance(user_message, dict)
    content = user_message["content"]
    assert isinstance(content, list)

    assert content == [
        {"type": "text", "text": '{"item_id":"item-asset"}'},
        {
            "type": "image_url",
            "image_url": {"url": "file://source/item-asset/assets/item-asset-001.png"},
        },
    ]


def test_vllm_payload_rejects_multimodal_content_parts() -> None:
    request = _request(
        user_content_parts=(
            StructuredLLMTextContentPart('{"item_id":"item-asset"}'),
            StructuredLLMImageURLContentPart("file://source/item-asset/assets/item-asset-001.png"),
        )
    )
    profile = _profile(
        endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=True,
        ),
    )

    with pytest.raises(ValueError, match="does not support multimodal"):
        build_vllm_chat_completions_payload(profile=profile, request=request)


def test_vllm_payload_uses_structured_outputs_choice_for_interim_runtime() -> None:
    request = _request(output_spec=_output_spec(choice_values=("A", "B", "C")))
    profile = _profile(
        endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=True,
        ),
    )

    payload = build_vllm_chat_completions_payload(profile=profile, request=request)

    assert payload["structured_outputs"] == {"choice": ["A", "B", "C"]}
    assert "response_format" not in payload


def test_route_policy_keeps_primary_local_first() -> None:
    provider_set = StructuredChatProviderSet(primary=_profile())

    decision = decide_structured_llm_route(
        provider_set=provider_set,
        policy=_policy(allow_remote_fallback=None),
        primary_available=True,
        fallback_available=False,
    )

    assert decision.provider_slot == "primary"
    assert decision.provider_id == "local-provider"
    assert decision.reason == StructuredLLMRouteReason.PRIMARY_AVAILABLE
    assert decision.blocked is False


def test_route_policy_allows_local_fallback_without_remote_consent() -> None:
    provider_set = StructuredChatProviderSet(
        primary=_profile(),
        fallback=_profile(provider_id="local-fallback"),
    )

    decision = decide_structured_llm_route(
        provider_set=provider_set,
        policy=_policy(allow_remote_fallback=False),
        primary_available=False,
        fallback_available=True,
    )

    assert decision.provider_slot == "fallback"
    assert decision.provider_id == "local-fallback"
    assert decision.reason == StructuredLLMRouteReason.LOCAL_FALLBACK_AVAILABLE


@pytest.mark.parametrize(
    (
        "allow_remote_fallback",
        "remote_providers_enabled",
        "remote_fallback_policy_authorized",
        "expected_reason",
    ),
    (
        (
            True,
            False,
            True,
            StructuredLLMRouteReason.REMOTE_POLICY_FORBIDDEN,
        ),
        (
            True,
            True,
            False,
            StructuredLLMRouteReason.REMOTE_POLICY_FORBIDDEN,
        ),
        (
            False,
            True,
            True,
            StructuredLLMRouteReason.REMOTE_EXPLICITLY_DENIED,
        ),
        (
            None,
            True,
            True,
            StructuredLLMRouteReason.REMOTE_CONSENT_MISSING,
        ),
    ),
)
def test_route_policy_blocks_remote_fallback_without_all_required_consent(
    allow_remote_fallback: bool | None,
    remote_providers_enabled: bool,
    remote_fallback_policy_authorized: bool,
    expected_reason: StructuredLLMRouteReason,
) -> None:
    provider_set = StructuredChatProviderSet(
        primary=_profile(),
        fallback=_profile(provider_id="remote-fallback", is_remote=True),
    )

    decision = decide_structured_llm_route(
        provider_set=provider_set,
        policy=_policy(
            allow_remote_fallback=allow_remote_fallback,
            remote_providers_enabled=remote_providers_enabled,
            remote_fallback_policy_authorized=remote_fallback_policy_authorized,
        ),
        primary_available=False,
        fallback_available=True,
    )

    assert decision.provider_slot is None
    assert decision.provider_id is None
    assert decision.reason == expected_reason
    assert decision.blocked is True


def test_route_policy_allows_remote_fallback_only_with_signed_authorized_consent() -> None:
    provider_set = StructuredChatProviderSet(
        primary=_profile(),
        fallback=_profile(provider_id="remote-fallback", is_remote=True),
    )

    decision = decide_structured_llm_route(
        provider_set=provider_set,
        policy=_policy(allow_remote_fallback=True),
        primary_available=False,
        fallback_available=True,
    )

    assert decision.provider_slot == "fallback"
    assert decision.provider_id == "remote-fallback"
    assert decision.reason == StructuredLLMRouteReason.REMOTE_FALLBACK_ALLOWED


def test_budget_preflight_blocks_over_budget_before_provider_call() -> None:
    profile = _profile(context_window_tokens=200, max_output_tokens=40)
    request = _request(estimated_input_tokens=151, max_output_tokens=30)
    budget = resolve_structured_llm_token_budget(
        profile=profile,
        requested_max_output_tokens=request.max_output_tokens,
        safety_margin_tokens=20,
    )

    result = preflight_structured_llm_prompt(request=request, budget=budget)

    assert budget.available_input_tokens == 150
    assert result.fits is False
    assert result.failure_code is not None
    assert result.failure_code.value == "over_budget"


def test_capture_metadata_excludes_prompt_payload_and_raw_response_content() -> None:
    request = _request(
        system_prompt="SYSTEM PROMPT WITH SOURCE TEXT",
        user_payload='{"raw_item_text":"student-visible prompt"}',
    )
    metadata = build_structured_llm_capture_metadata(
        request=request,
        profile=_profile(),
        status=StructuredLLMCaptureStatus.MANUAL_FOLLOW_UP_REQUIRED,
        backend_failure_code="over_budget",
    )
    payload = asdict(metadata)

    assert payload == {
        "job_id": "job-001",
        "item_id": "item-001",
        "item_type": "single_choice",
        "provider_profile_id": "local-provider",
        "remote_used": False,
        "schema_name": "choice_decision",
        "schema_version": CHOICE_DECISION_SCHEMA_VERSION,
        "prompt_template_version": "answer_key_choice_prompt_v1",
        "status": StructuredLLMCaptureStatus.MANUAL_FOLLOW_UP_REQUIRED,
        "backend_failure_code": "over_budget",
    }
    assert "SOURCE TEXT" not in repr(payload)
    assert "student-visible prompt" not in repr(payload)


def test_strict_output_spec_rejects_unbounded_json_schema() -> None:
    schema_without_extra_forbid: dict[str, JsonValue] = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }

    with pytest.raises(ValueError, match="additionalProperties=false"):
        StructuredOutputSpec(
            schema_name="bad_schema",
            schema_version="bad_schema_v1",
            json_schema=schema_without_extra_forbid,
        )


def _request(
    *,
    output_spec: StructuredOutputSpec | None = None,
    system_prompt: str = "Return a bounded answer-key decision.",
    user_payload: str = '{"item_id":"item-001","choices":["A","B","C"]}',
    user_content_parts: tuple[
        StructuredLLMTextContentPart | StructuredLLMImageURLContentPart,
        ...,
    ] = (),
    estimated_input_tokens: int = 64,
    max_output_tokens: int = 128,
) -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-001",
        item_id="item-001",
        item_type="single_choice",
        prompt_template_version="answer_key_choice_prompt_v1",
        system_prompt=system_prompt,
        user_payload=user_payload,
        output_spec=output_spec or _output_spec(),
        estimated_input_tokens=estimated_input_tokens,
        max_output_tokens=max_output_tokens,
        allow_remote_fallback=None,
        user_content_parts=user_content_parts,
    )


def _output_spec(
    *,
    gbnf_grammar: str | None = None,
    choice_values: tuple[str, ...] = (),
) -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name="choice_decision",
        schema_version=CHOICE_DECISION_SCHEMA_VERSION,
        json_schema=CHOICE_DECISION_SCHEMA,
        gbnf_grammar=gbnf_grammar,
        choice_values=choice_values,
    )


def _profile(
    *,
    provider_id: str = "local-provider",
    endpoint_kind: StructuredLLMEndpointKind = StructuredLLMEndpointKind.CHAT_COMPLETIONS,
    output_mode: StructuredLLMOutputMode = StructuredLLMOutputMode.JSON_SCHEMA,
    is_remote: bool = False,
    context_window_tokens: int = 4096,
    max_output_tokens: int = 512,
    capabilities: StructuredLLMProviderCapabilities | None = None,
    reasoning_effort: StructuredLLMReasoningEffort | None = None,
    text_verbosity: StructuredLLMTextVerbosity | None = None,
    thinking_mode: StructuredLLMThinkingMode | None = None,
) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id=provider_id,
        model="local-model",
        endpoint_kind=endpoint_kind,
        output_mode=output_mode,
        is_remote=is_remote,
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        capabilities=capabilities
        or StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
        reasoning_effort=reasoning_effort,
        text_verbosity=text_verbosity,
        thinking_mode=thinking_mode,
    )


def _policy(
    *,
    allow_remote_fallback: bool | None,
    remote_providers_enabled: bool = True,
    remote_fallback_policy_authorized: bool = True,
) -> StructuredLLMRoutePolicy:
    return StructuredLLMRoutePolicy(
        remote_providers_enabled=remote_providers_enabled,
        remote_fallback_policy_authorized=remote_fallback_policy_authorized,
        allow_remote_fallback=allow_remote_fallback,
    )
