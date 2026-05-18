"""Tests for structured LLM provider configuration and composition.

Purpose:
    Prove Task 296 service settings and Dishka composition are opt-in,
    constant-backed, and provider-agnostic before advisory answer-key reports
    start using the harness.

Relationships:
    - Exercises `infrastructure.structured_llm_config` and
      `infrastructure.structured_llm_di`.
    - Complements provider payload/execution tests without calling HTTP
      artifact routes.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    STRUCTURED_LLM_CAPABILITY_GBNF_KEY,
    STRUCTURED_LLM_CAPABILITY_JSON_SCHEMA_KEY,
    STRUCTURED_LLM_CAPABILITY_MULTIMODAL_VISION_KEY,
    STRUCTURED_LLM_CAPABILITY_VLLM_CHOICE_KEY,
    STRUCTURED_LLM_ENABLED_ENV,
    STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV,
    STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV,
    STRUCTURED_LLM_PROVIDER_API_KEY_ENV_KEY,
    STRUCTURED_LLM_PROVIDER_BASE_URL_KEY,
    STRUCTURED_LLM_PROVIDER_CAPABILITIES_KEY,
    STRUCTURED_LLM_PROVIDER_CONTEXT_WINDOW_TOKENS_KEY,
    STRUCTURED_LLM_PROVIDER_ENDPOINT_KIND_KEY,
    STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY,
    STRUCTURED_LLM_PROVIDER_IS_REMOTE_KEY,
    STRUCTURED_LLM_PROVIDER_MAX_OUTPUT_TOKENS_KEY,
    STRUCTURED_LLM_PROVIDER_MODEL_KEY,
    STRUCTURED_LLM_PROVIDER_OUTPUT_MODE_KEY,
    STRUCTURED_LLM_PROVIDER_REASONING_EFFORT_KEY,
    STRUCTURED_LLM_PROVIDER_TEMPERATURE_KEY,
    STRUCTURED_LLM_PROVIDER_TEXT_VERBOSITY_KEY,
    STRUCTURED_LLM_PROVIDER_TIMEOUT_SECONDS_KEY,
    STRUCTURED_LLM_PROVIDERS_JSON_ENV,
    STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV,
    STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV,
    STRUCTURED_LLM_VISION_MEDIA_PATH_ENV,
    structured_llm_runtime_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_di import (
    create_structured_llm_async_container,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
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


def test_structured_llm_service_config_defaults_disabled() -> None:
    config = structured_llm_runtime_config_from_env({})

    assert config.enabled is False
    assert config.provider_set is None
    assert dict(config.connections) == {}
    assert config.route_policy(allow_remote_fallback=True).remote_providers_enabled is False
    assert (
        config.route_policy(allow_remote_fallback=True).remote_fallback_policy_authorized is False
    )


def test_structured_llm_service_config_loads_provider_set_from_constants() -> None:
    env = _provider_env()

    config = structured_llm_runtime_config_from_env(env)

    assert config.enabled is True
    assert config.provider_set is not None
    assert config.provider_set.primary.provider_id == "granite-local"
    assert config.provider_set.primary.model == "ibm-granite/granite-4.1-8b-fp8"
    assert (
        config.provider_set.primary.endpoint_kind == StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS
    )
    assert config.provider_set.primary.output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE
    assert config.provider_set.primary.temperature == 0.15
    assert config.provider_set.fallback is not None
    assert config.provider_set.fallback.is_remote is True
    assert config.provider_set.fallback.reasoning_effort == "none"
    assert config.provider_set.fallback.text_verbosity == "low"
    assert config.connections["granite-local"].normalized_base_url == "http://127.0.0.1:8123/v1"
    assert config.connections["remote-openai"].api_key == "remote-secret"
    assert config.connections["remote-openai"].extra_headers == {"X-Provider": "test"}
    policy = config.route_policy(allow_remote_fallback=False)
    assert policy.allow_remote_fallback is False
    assert policy.remote_providers_enabled is True
    assert policy.remote_fallback_policy_authorized is True


def test_structured_llm_service_config_loads_multimodal_vision_capability() -> None:
    env = _provider_env()

    config = structured_llm_runtime_config_from_env(env)

    assert config.provider_set is not None
    assert config.provider_set.primary.capabilities.supports_multimodal_vision is True
    assert config.provider_set.fallback is not None
    assert config.provider_set.fallback.capabilities.supports_multimodal_vision is False
    assert config.vision_media_path is not None
    assert config.vision_media_path.as_posix() == "/srv/scratch/sir-convert-a-lot/vision-media"


def test_structured_llm_service_config_requires_media_path_for_vision_primary() -> None:
    env = _provider_env()
    env.pop(STRUCTURED_LLM_VISION_MEDIA_PATH_ENV)

    with pytest.raises(ValueError, match=STRUCTURED_LLM_VISION_MEDIA_PATH_ENV):
        structured_llm_runtime_config_from_env(env)


def test_structured_llm_service_config_requires_remote_primary_authorization() -> None:
    env = _provider_env(primary_provider_id="remote-openai")
    env[STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV] = "false"

    with pytest.raises(ValueError, match=STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV):
        structured_llm_runtime_config_from_env(env)


def test_structured_llm_service_config_allows_authorized_remote_primary() -> None:
    env = _provider_env(primary_provider_id="remote-openai", fallback_provider_id=None)

    config = structured_llm_runtime_config_from_env(env)

    assert config.provider_set is not None
    assert config.provider_set.primary.provider_id == "remote-openai"
    assert config.provider_set.primary.is_remote is True
    assert config.remote_providers_enabled is True
    assert config.remote_fallback_policy_authorized is True


def test_structured_llm_service_config_rejects_missing_api_key_env() -> None:
    env = _provider_env()
    env.pop("REMOTE_STRUCTURED_LLM_API_KEY")

    with pytest.raises(ValueError, match=STRUCTURED_LLM_PROVIDER_API_KEY_ENV_KEY):
        structured_llm_runtime_config_from_env(env)


def test_structured_llm_dishka_container_injects_http_provider() -> None:
    async def run_container() -> None:
        captured_urls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_urls.append(str(request.url))
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"content": "choice-a"},
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        config = structured_llm_runtime_config_from_env(_provider_env(fallback_provider_id=None))
        assert config.provider_set is not None
        container = create_structured_llm_async_container(config=config, client=client)
        try:
            provider = await container.get(HttpStructuredChatProvider)
            response = await provider.complete_structured_chat(
                request=_vllm_choice_request(),
                profile=config.provider_set.primary,
            )
        finally:
            await container.close()
            await client.aclose()

        assert captured_urls == ["http://127.0.0.1:8123/v1/chat/completions"]
        assert response.content == {"choice": "choice-a"}

    asyncio.run(run_container())


def _provider_env(
    *,
    primary_provider_id: str = "granite-local",
    fallback_provider_id: str | None = "remote-openai",
) -> dict[str, str]:
    providers = {
        "granite-local": _provider_payload(
            model="ibm-granite/granite-4.1-8b-fp8",
            endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
            output_mode=StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE,
            is_remote=False,
            base_url="http://127.0.0.1:8123",
            capabilities=StructuredLLMProviderCapabilities(
                supports_json_schema=True,
                supports_gbnf=False,
                supports_vllm_structured_choice=True,
                supports_multimodal_vision=True,
            ),
        ),
        "remote-openai": _provider_payload(
            model="gpt-4.1-mini",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
            is_remote=True,
            base_url="https://api.openai.example",
            capabilities=StructuredLLMProviderCapabilities(
                supports_json_schema=True,
                supports_gbnf=False,
                supports_vllm_structured_choice=False,
            ),
            api_key_env="REMOTE_STRUCTURED_LLM_API_KEY",
            extra_headers={"X-Provider": "test"},
            timeout_seconds=45.0,
        ),
    }
    env = {
        STRUCTURED_LLM_ENABLED_ENV: "true",
        STRUCTURED_LLM_PROVIDERS_JSON_ENV: json.dumps(providers),
        STRUCTURED_LLM_PRIMARY_PROVIDER_ID_ENV: primary_provider_id,
        STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED_ENV: "true",
        STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED_ENV: "true",
        STRUCTURED_LLM_VISION_MEDIA_PATH_ENV: "/srv/scratch/sir-convert-a-lot/vision-media",
        "REMOTE_STRUCTURED_LLM_API_KEY": "remote-secret",
    }
    if fallback_provider_id is not None:
        env[STRUCTURED_LLM_FALLBACK_PROVIDER_ID_ENV] = fallback_provider_id
    return env


def _provider_payload(
    *,
    model: str,
    endpoint_kind: StructuredLLMEndpointKind,
    output_mode: StructuredLLMOutputMode,
    is_remote: bool,
    base_url: str,
    capabilities: StructuredLLMProviderCapabilities,
    api_key_env: str | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    payload: dict[str, object] = {
        STRUCTURED_LLM_PROVIDER_MODEL_KEY: model,
        STRUCTURED_LLM_PROVIDER_ENDPOINT_KIND_KEY: endpoint_kind.value,
        STRUCTURED_LLM_PROVIDER_OUTPUT_MODE_KEY: output_mode.value,
        STRUCTURED_LLM_PROVIDER_IS_REMOTE_KEY: is_remote,
        STRUCTURED_LLM_PROVIDER_CONTEXT_WINDOW_TOKENS_KEY: 32768,
        STRUCTURED_LLM_PROVIDER_MAX_OUTPUT_TOKENS_KEY: 4096,
        STRUCTURED_LLM_PROVIDER_TEMPERATURE_KEY: 0.15,
        STRUCTURED_LLM_PROVIDER_BASE_URL_KEY: base_url,
        STRUCTURED_LLM_PROVIDER_TIMEOUT_SECONDS_KEY: timeout_seconds,
        STRUCTURED_LLM_PROVIDER_CAPABILITIES_KEY: {
            STRUCTURED_LLM_CAPABILITY_JSON_SCHEMA_KEY: capabilities.supports_json_schema,
            STRUCTURED_LLM_CAPABILITY_GBNF_KEY: capabilities.supports_gbnf,
            STRUCTURED_LLM_CAPABILITY_VLLM_CHOICE_KEY: (
                capabilities.supports_vllm_structured_choice
            ),
            STRUCTURED_LLM_CAPABILITY_MULTIMODAL_VISION_KEY: (
                capabilities.supports_multimodal_vision
            ),
        },
    }
    if api_key_env is not None:
        payload[STRUCTURED_LLM_PROVIDER_API_KEY_ENV_KEY] = api_key_env
        payload[STRUCTURED_LLM_PROVIDER_REASONING_EFFORT_KEY] = "none"
        payload[STRUCTURED_LLM_PROVIDER_TEXT_VERBOSITY_KEY] = "low"
    if extra_headers is not None:
        payload[STRUCTURED_LLM_PROVIDER_EXTRA_HEADERS_KEY] = extra_headers
    return payload


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
            schema_version=CHOICE_DECISION_SCHEMA_VERSION,
            json_schema=CHOICE_DECISION_SCHEMA,
            choice_values=("choice-a", "choice-b"),
        ),
        estimated_input_tokens=64,
        max_output_tokens=128,
        allow_remote_fallback=None,
    )


def _vllm_choice_request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-001",
        item_id="item-001",
        item_type="single_choice",
        prompt_template_version="answer_key_choice_prompt_v1",
        system_prompt="Return one bounded choice.",
        user_payload='{"item_id":"item-001","choices":["choice-a","choice-b"]}',
        output_spec=StructuredOutputSpec(
            schema_name="simple_choice",
            schema_version="simple_choice_v1",
            json_schema=SIMPLE_CHOICE_SCHEMA,
            choice_values=("choice-a", "choice-b"),
        ),
        estimated_input_tokens=64,
        max_output_tokens=128,
        allow_remote_fallback=None,
    )
