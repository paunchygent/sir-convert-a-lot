"""Tests for structured LLM provider HTTP execution.

Purpose:
    Prove the Task 296 provider adapter executes configured
    OpenAI-compatible endpoints, parses structured responses, and maps
    provider failures without exposing raw prompts or upstream payloads.

Relationships:
    - Exercises `infrastructure.structured_llm_provider` and
      `infrastructure.structured_llm_responses`.
    - Extends the pure harness tests without wiring provider calls into
      DigiExam parsers, renderers, or HTTP artifact routes.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
    StructuredLLMProviderConnection,
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
SIMPLE_CHOICE_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {"choice": {"type": "string"}},
    "required": ["choice"],
    "additionalProperties": False,
}


def test_http_provider_executes_chat_completions_and_parses_json_content() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "selected_choice_ids": ["choice-b"],
                                    "manual_follow_up_required": False,
                                }
                            )
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 7,
                    "total_tokens": 27,
                },
            },
        )

    response = asyncio.run(
        _complete_with_transport(
            handler=handler,
            profile=_profile(),
            request=_request(),
            connection=StructuredLLMProviderConnection(
                provider_id="local-provider",
                base_url="http://provider.local",
                api_key="token",
                extra_headers={"X-Test": "1"},
            ),
        )
    )

    assert response.content == {
        "selected_choice_ids": ["choice-b"],
        "manual_follow_up_required": False,
    }
    assert response.finish_reason == "stop"
    assert response.usage.prompt_tokens == 20
    assert response.usage.total_tokens == 27
    assert str(captured_requests[0].url) == "http://provider.local/v1/chat/completions"
    assert captured_requests[0].headers["Authorization"] == "Bearer token"
    assert captured_requests[0].headers["X-Test"] == "1"


def test_http_provider_executes_responses_endpoint_and_parses_output_object() -> None:
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["text"]["format"]["name"] == "choice_decision"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": {
                    "selected_choice_ids": ["choice-c"],
                    "manual_follow_up_required": False,
                },
            },
        )

    response = asyncio.run(
        _complete_with_transport(
            handler=handler,
            profile=_profile(
                endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
                is_remote=True,
            ),
            request=_request(),
            connection=StructuredLLMProviderConnection(
                provider_id="local-provider",
                base_url="https://api.example.test/v1",
            ),
        )
    )

    assert response.content["selected_choice_ids"] == ["choice-c"]
    assert response.finish_reason == "completed"
    assert captured_urls == ["https://api.example.test/v1/responses"]


def test_http_provider_parses_vllm_structured_choice_as_bounded_object() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["structured_outputs"] == {"choice": ["A", "B", "C"]}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "B"},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    response = asyncio.run(
        _complete_with_transport(
            handler=handler,
            profile=_profile(
                endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
                output_mode=StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE,
                capabilities=StructuredLLMProviderCapabilities(
                    supports_json_schema=True,
                    supports_gbnf=False,
                    supports_vllm_structured_choice=True,
                ),
            ),
            request=_request(
                output_spec=StructuredOutputSpec(
                    schema_name="simple_choice",
                    schema_version="simple_choice_v1",
                    json_schema=SIMPLE_CHOICE_SCHEMA,
                    choice_values=("A", "B", "C"),
                )
            ),
        )
    )

    assert response.content == {"choice": "B"}


def test_http_provider_maps_missing_connection_before_request() -> None:
    async def run_provider() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(_unexpected_handler)) as client:
            provider = HttpStructuredChatProvider(client=client, connections={})
            await provider.complete_structured_chat(request=_request(), profile=_profile())

    with pytest.raises(StructuredLLMProviderError) as exc_info:
        asyncio.run(run_provider())

    assert exc_info.value.failure_code == StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING
    assert exc_info.value.provider_id == "local-provider"


def test_http_provider_maps_http_status_without_raw_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "secret upstream raw body"})

    with pytest.raises(StructuredLLMProviderError) as exc_info:
        asyncio.run(
            _complete_with_transport(handler=handler, profile=_profile(), request=_request())
        )

    assert exc_info.value.failure_code == StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR
    assert exc_info.value.status_code == 503
    assert "secret upstream raw body" not in str(exc_info.value)


def test_http_provider_maps_request_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(StructuredLLMProviderError) as exc_info:
        asyncio.run(
            _complete_with_transport(handler=handler, profile=_profile(), request=_request())
        )

    assert exc_info.value.failure_code == StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED


def test_http_provider_maps_invalid_response_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    with pytest.raises(StructuredLLMProviderError) as exc_info:
        asyncio.run(
            _complete_with_transport(handler=handler, profile=_profile(), request=_request())
        )

    assert exc_info.value.failure_code == StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON


def test_http_provider_maps_non_json_model_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not-json"}, "finish_reason": "stop"}]},
        )

    with pytest.raises(StructuredLLMProviderError) as exc_info:
        asyncio.run(
            _complete_with_transport(handler=handler, profile=_profile(), request=_request())
        )

    assert exc_info.value.failure_code == StructuredLLMBackendFailureCode.PROVIDER_CONTENT_NOT_JSON


@pytest.mark.parametrize(
    "content",
    (
        {"selected_choice_ids": ["choice-a"]},
        {
            "selected_choice_ids": ["choice-a"],
            "manual_follow_up_required": False,
            "extra": "forbidden",
        },
        {"selected_choice_ids": ["choice-a"], "manual_follow_up_required": "false"},
    ),
)
def test_http_provider_maps_schema_mismatch(content: dict[str, JsonValue]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": json.dumps(content)},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    with pytest.raises(StructuredLLMProviderError) as exc_info:
        asyncio.run(
            _complete_with_transport(handler=handler, profile=_profile(), request=_request())
        )

    assert exc_info.value.failure_code == StructuredLLMBackendFailureCode.PROVIDER_SCHEMA_MISMATCH


async def _complete_with_transport(
    *,
    handler: Callable[[httpx.Request], httpx.Response],
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
    connection: StructuredLLMProviderConnection | None = None,
) -> StructuredLLMResponse:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = HttpStructuredChatProvider(
            client=client,
            connections={
                "local-provider": connection
                or StructuredLLMProviderConnection(
                    provider_id="local-provider",
                    base_url="http://provider.local",
                )
            },
        )
        return await provider.complete_structured_chat(request=request, profile=profile)


def _request(
    *,
    output_spec: StructuredOutputSpec | None = None,
) -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-001",
        item_id="item-001",
        item_type="single_choice",
        prompt_template_version="answer_key_choice_prompt_v1",
        system_prompt="Return a bounded answer-key decision.",
        user_payload='{"item_id":"item-001","choices":["A","B","C"]}',
        output_spec=output_spec
        or StructuredOutputSpec(
            schema_name="choice_decision",
            schema_version=CHOICE_DECISION_SCHEMA_VERSION,
            json_schema=CHOICE_DECISION_SCHEMA,
        ),
        estimated_input_tokens=64,
        max_output_tokens=128,
        allow_remote_fallback=None,
    )


def _profile(
    *,
    endpoint_kind: StructuredLLMEndpointKind = StructuredLLMEndpointKind.CHAT_COMPLETIONS,
    output_mode: StructuredLLMOutputMode = StructuredLLMOutputMode.JSON_SCHEMA,
    is_remote: bool = False,
    capabilities: StructuredLLMProviderCapabilities | None = None,
) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="local-provider",
        model="local-model",
        endpoint_kind=endpoint_kind,
        output_mode=output_mode,
        is_remote=is_remote,
        context_window_tokens=4096,
        max_output_tokens=512,
        capabilities=capabilities
        or StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
    )


def _unexpected_handler(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"Unexpected structured provider request: {request.url}")
