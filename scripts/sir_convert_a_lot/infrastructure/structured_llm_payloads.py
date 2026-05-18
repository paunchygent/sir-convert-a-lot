"""Structured LLM provider payload builders.

Purpose:
    Translate source-neutral structured-output requests into provider-specific
    JSON payloads for OpenAI-compatible Chat Completions, Responses, llama.cpp,
    and vLLM endpoints.

Relationships:
    - Consumes `domain.structured_llm_contracts` without depending on DigiExam
      parser DTOs, renderer inputs, or answer-key completion item schemas.
    - Provides pure payload construction for Task 296 provider adapters and
      tests before any network client is introduced.
"""

from __future__ import annotations

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMImageURLContentPart,
    StructuredLLMOutputMode,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMTextContentPart,
    StructuredOutputSpec,
)

StructuredLLMPayload = dict[str, JsonValue]


def build_structured_llm_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> StructuredLLMPayload:
    """Build the provider request payload selected by the profile endpoint."""

    if profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES:
        return build_responses_payload(profile=profile, request=request)
    if profile.endpoint_kind == StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS:
        return build_llama_cpp_chat_completions_payload(profile=profile, request=request)
    if profile.endpoint_kind == StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS:
        return build_vllm_chat_completions_payload(profile=profile, request=request)
    return build_chat_completions_payload(profile=profile, request=request)


def build_chat_completions_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> StructuredLLMPayload:
    """Build a Chat Completions payload using `response_format.json_schema`."""

    _require_output_mode(
        profile=profile,
        allowed=(
            StructuredLLMOutputMode.JSON_SCHEMA,
            StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
        ),
    )
    _require_text_only(request=request, provider_id=profile.provider_id)
    payload: StructuredLLMPayload = {
        "model": profile.model,
        "messages": _chat_messages(request),
        "stream": False,
        "max_tokens": request.max_output_tokens,
        "temperature": profile.temperature,
        "response_format": build_chat_completions_response_format(request.output_spec),
    }
    return payload


def build_responses_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> StructuredLLMPayload:
    """Build a Responses payload using `text.format.json_schema`."""

    _require_output_mode(profile=profile, allowed=(StructuredLLMOutputMode.JSON_SCHEMA,))
    text_config: dict[str, JsonValue] = {"format": build_responses_text_format(request.output_spec)}
    if profile.text_verbosity is not None:
        text_config["verbosity"] = profile.text_verbosity.value
    payload: StructuredLLMPayload = {
        "model": profile.model,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": _responses_user_content(request),
            }
        ],
        "instructions": request.system_prompt,
        "stream": False,
        "max_output_tokens": request.max_output_tokens,
        "store": False,
        "text": text_config,
    }
    if profile.reasoning_effort is not None:
        payload["reasoning"] = {"effort": profile.reasoning_effort.value}
    return payload


def build_llama_cpp_chat_completions_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> StructuredLLMPayload:
    """Build a llama.cpp OpenAI-compatible constrained chat payload."""

    payload: StructuredLLMPayload = {
        "model": profile.model,
        "messages": _chat_messages(request),
        "stream": False,
        "max_tokens": request.max_output_tokens,
        "temperature": profile.temperature,
    }
    if profile.output_mode == StructuredLLMOutputMode.GBNF:
        if request.output_spec.gbnf_grammar is None:
            raise ValueError("GBNF output mode requires output_spec.gbnf_grammar.")
        payload["grammar"] = request.output_spec.gbnf_grammar
        return payload
    _require_output_mode(profile=profile, allowed=(StructuredLLMOutputMode.JSON_SCHEMA,))
    payload["response_format"] = build_llama_cpp_response_format(request.output_spec)
    return payload


def build_vllm_chat_completions_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> StructuredLLMPayload:
    """Build a vLLM OpenAI-compatible structured-output chat payload."""

    payload: StructuredLLMPayload = {
        "model": profile.model,
        "messages": _chat_messages(request),
        "stream": False,
        "max_tokens": request.max_output_tokens,
        "temperature": profile.temperature,
    }
    _require_text_only(request=request, provider_id=profile.provider_id)
    if profile.output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE:
        if not request.output_spec.choice_values:
            raise ValueError("vLLM structured choice mode requires output_spec.choice_values.")
        payload["structured_outputs"] = {"choice": list(request.output_spec.choice_values)}
        return payload
    _require_output_mode(profile=profile, allowed=(StructuredLLMOutputMode.VLLM_JSON_SCHEMA,))
    payload["response_format"] = build_chat_completions_response_format(request.output_spec)
    return payload


def build_chat_completions_response_format(spec: StructuredOutputSpec) -> dict[str, JsonValue]:
    """Build OpenAI Chat Completions `response_format` for JSON Schema."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": spec.schema_name,
            "strict": spec.strict,
            "schema": spec.json_schema,
        },
    }


def build_responses_text_format(spec: StructuredOutputSpec) -> dict[str, JsonValue]:
    """Build OpenAI Responses `text.format` for JSON Schema."""

    return {
        "type": "json_schema",
        "name": spec.schema_name,
        "strict": spec.strict,
        "schema": spec.json_schema,
    }


def build_llama_cpp_response_format(spec: StructuredOutputSpec) -> dict[str, JsonValue]:
    """Build llama.cpp `response_format` for JSON Schema constrained output."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": spec.schema_name,
            "schema": spec.json_schema,
        },
    }


def _chat_messages(request: StructuredLLMRequest) -> list[JsonValue]:
    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": _user_content(request)},
    ]


def _user_content(request: StructuredLLMRequest) -> JsonValue:
    if not request.user_content_parts:
        return request.user_payload
    parts: list[JsonValue] = []
    for part in request.user_content_parts:
        if isinstance(part, StructuredLLMTextContentPart):
            parts.append({"type": "text", "text": part.text})
        elif isinstance(part, StructuredLLMImageURLContentPart):
            parts.append({"type": "image_url", "image_url": {"url": part.url}})
        else:
            raise TypeError(f"Unsupported structured LLM content part: {type(part).__name__}")
    return parts


def _responses_user_content(request: StructuredLLMRequest) -> list[JsonValue]:
    if not request.user_content_parts:
        return [{"type": "input_text", "text": request.user_payload}]
    parts: list[JsonValue] = []
    for part in request.user_content_parts:
        if isinstance(part, StructuredLLMTextContentPart):
            parts.append({"type": "input_text", "text": part.text})
        elif isinstance(part, StructuredLLMImageURLContentPart):
            parts.append({"type": "input_image", "image_url": part.url})
        else:
            raise TypeError(f"Unsupported structured LLM content part: {type(part).__name__}")
    return parts


def _require_output_mode(
    *,
    profile: StructuredLLMProviderProfile,
    allowed: tuple[StructuredLLMOutputMode, ...],
) -> None:
    if profile.output_mode not in allowed:
        allowed_values = ", ".join(output_mode.value for output_mode in allowed)
        raise ValueError(
            f"Provider {profile.provider_id} output mode {profile.output_mode.value} "
            f"is not supported here; expected one of {allowed_values}."
        )


def _require_text_only(*, request: StructuredLLMRequest, provider_id: str) -> None:
    if request.user_content_parts:
        raise ValueError(
            f"Provider {provider_id} does not support multimodal structured user content."
        )
