"""Tests for answer-key provider runtime config rendering.

Purpose:
    Prove governed Qwen3.6 MTP provider settings render deterministically for
    Hemma production while local development can still use host-local Qwen.

Relationships:
    - Exercises `infrastructure.answer_key_provider_runtime_config`.
    - Complements service config tests by locking the profile/lane defaults
      before `structured_llm_config` consumes the rendered provider JSON.
"""

from __future__ import annotations

import json

import pytest

from scripts.sir_convert_a_lot.infrastructure.answer_key_local_model_profiles import (
    LLAMA_CPP_PROVIDER_ID,
    AnswerKeyProviderProfileName,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_provider_runtime_config import (
    STRUCTURED_LLM_PROVIDER_PROFILE_ENV,
    STRUCTURED_LLM_RUNTIME_LANE_ENV,
    AnswerKeyProviderRuntimeLane,
    answer_key_provider_json_for_profile,
    render_answer_key_provider_environment,
    validate_structured_llm_connections_for_runtime_lane,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    structured_llm_runtime_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)


def test_rendered_prod_profile_uses_qwen36_mtp_alias_and_service_dns() -> None:
    env = render_answer_key_provider_environment(
        lane=AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE
    )
    provider_payload = _provider_payload(env["SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDERS_JSON"])

    assert env[STRUCTURED_LLM_PROVIDER_PROFILE_ENV] == "qwen36-llama-cpp-mtp"
    assert env[STRUCTURED_LLM_RUNTIME_LANE_ENV] == "hemma-prod-compose"
    assert provider_payload["model"] == "qwen3.6-27b-q6k-mtp"
    assert provider_payload["base_url"] == "http://sir_convert_qwen_answer_key:8082"
    assert provider_payload["endpoint_kind"] == "llama_cpp_chat_completions"
    assert provider_payload["output_mode"] == "json_schema"
    assert provider_payload["context_window_tokens"] == 32768
    assert provider_payload["max_output_tokens"] == 4096
    assert provider_payload["temperature"] == 0.15
    assert provider_payload["capabilities"] == {
        "supports_gbnf": True,
        "supports_json_schema": True,
        "supports_multimodal_vision": True,
        "supports_vllm_structured_choice": False,
    }


def test_structured_config_can_render_profile_when_raw_json_is_absent() -> None:
    env = render_answer_key_provider_environment(
        lane=AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE
    )
    env.pop("SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDERS_JSON")

    config = structured_llm_runtime_config_from_env(env)

    assert config.provider_set is not None
    assert config.provider_set.primary.model == "qwen3.6-27b-q6k-mtp"
    assert config.connections[LLAMA_CPP_PROVIDER_ID].base_url == (
        "http://sir_convert_qwen_answer_key:8082"
    )


@pytest.mark.parametrize("base_url", ["http://127.0.0.1:8082", "http://localhost:8082"])
def test_prod_lane_rejects_loopback_provider_urls(base_url: str) -> None:
    with pytest.raises(ValueError, match="Docker service DNS"):
        validate_structured_llm_connections_for_runtime_lane(
            lane=AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE,
            connections={
                LLAMA_CPP_PROVIDER_ID: StructuredLLMProviderConnection(
                    provider_id=LLAMA_CPP_PROVIDER_ID,
                    base_url=base_url,
                )
            },
        )


def test_prod_lane_rejects_container_host_alias() -> None:
    with pytest.raises(ValueError, match="Docker service DNS"):
        validate_structured_llm_connections_for_runtime_lane(
            lane=AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE,
            connections={
                LLAMA_CPP_PROVIDER_ID: StructuredLLMProviderConnection(
                    provider_id=LLAMA_CPP_PROVIDER_ID,
                    base_url="http://host.docker.internal:8082",
                )
            },
        )


def test_local_host_lane_allows_loopback_provider_url() -> None:
    provider_json = answer_key_provider_json_for_profile(
        lane=AnswerKeyProviderRuntimeLane.LOCAL_HOST,
        profile_name=AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP,
    )

    assert _provider_payload(provider_json)["base_url"] == "http://127.0.0.1:8082"
    validate_structured_llm_connections_for_runtime_lane(
        lane=AnswerKeyProviderRuntimeLane.LOCAL_HOST,
        connections={
            LLAMA_CPP_PROVIDER_ID: StructuredLLMProviderConnection(
                provider_id=LLAMA_CPP_PROVIDER_ID,
                base_url="http://127.0.0.1:8082",
            )
        },
    )


def _provider_payload(providers_json: str) -> dict[str, object]:
    decoded = json.loads(providers_json)
    assert isinstance(decoded, dict)
    provider_payload = decoded[LLAMA_CPP_PROVIDER_ID]
    assert isinstance(provider_payload, dict)
    return provider_payload
