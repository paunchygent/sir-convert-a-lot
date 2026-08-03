"""Structured LLM admission routing tests.

Purpose:
    Prove HTML to PDF route5-B resolves provider routing once at job admission and keeps
    public remote-provider use fail-closed before execution begins.

Relationships:
    - Exercises `infrastructure.structured_llm_admission` with the
      hot-settings domain store.
    - Complements route-level DigiExam advisory completion tests that prove the
      persisted snapshot drives provider execution and report lineage.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import (
    ConversionSpecV2,
    DigiExamAnswerKeyCompletionModeV2,
    DigiExamMigrationOptionsV2,
    JobSpecV2,
    OutputFormatV2,
    RetentionSpecV2,
    SourceFormatV2,
    SourceKindV2,
    SourceSpecV2,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMTextVerbosity,
)
from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMHotSettingsStore,
    StructuredLLMInternalRouteClass,
    StructuredLLMProviderRoutingSettings,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_admission import (
    StructuredLLMAdmissionError,
    StructuredLLMAdmissionFailureCode,
    provider_set_for_admitted_route,
    resolve_structured_llm_admission_snapshot,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)


def test_admission_snapshot_pins_openai_behavior_metadata_for_internal_request() -> None:
    config = _structured_config()
    store = _store(active_provider_profile_id=_OPENAI_PROVIDER_ID)

    snapshot = resolve_structured_llm_admission_snapshot(
        spec=_advisory_spec(),
        structured_config=config,
        hot_settings_store=store,
        public_grant_request=False,
    )

    assert snapshot is not None
    assert snapshot.provider_family == "openai_responses"
    assert snapshot.provider_profile_id == _OPENAI_PROVIDER_ID
    assert snapshot.model == "gpt-5.4-mini-2026-03-17"
    assert snapshot.endpoint_kind == StructuredLLMEndpointKind.RESPONSES
    assert snapshot.output_mode == StructuredLLMOutputMode.JSON_SCHEMA
    assert snapshot.reasoning_effort == StructuredLLMReasoningEffort.NONE
    assert snapshot.text_verbosity == StructuredLLMTextVerbosity.LOW
    assert snapshot.settings_version == 2
    assert snapshot.route_class == StructuredLLMInternalRouteClass.OPERATOR_API_ONLY
    assert snapshot.remote_provider_authorized is True

    provider_set = provider_set_for_admitted_route(
        structured_config=config,
        admitted_route=snapshot,
    )
    assert provider_set is not None
    assert provider_set.primary.provider_id == _OPENAI_PROVIDER_ID
    assert provider_set.fallback is None


def test_admission_rejects_public_grant_remote_provider_route() -> None:
    with pytest.raises(StructuredLLMAdmissionError) as exc_info:
        resolve_structured_llm_admission_snapshot(
            spec=_advisory_spec(),
            structured_config=_structured_config(),
            hot_settings_store=_store(active_provider_profile_id=_OPENAI_PROVIDER_ID),
            public_grant_request=True,
        )

    assert (
        exc_info.value.failure_code
        == StructuredLLMAdmissionFailureCode.PUBLIC_REMOTE_PROVIDER_FORBIDDEN
    )


def test_admission_returns_none_for_source_evidence_mode() -> None:
    snapshot = resolve_structured_llm_admission_snapshot(
        spec=_source_evidence_spec(),
        structured_config=_structured_config(),
        hot_settings_store=_store(active_provider_profile_id=_LOCAL_PROVIDER_ID),
        public_grant_request=False,
    )

    assert snapshot is None


_LOCAL_PROVIDER_ID = "qwen36-llama-cpp-mtp"
_OPENAI_PROVIDER_ID = "openai-gpt-5.4-mini-2026-03-17"


def _structured_config() -> StructuredLLMRuntimeConfig:
    local_profile = StructuredLLMProviderProfile(
        provider_id=_LOCAL_PROVIDER_ID,
        model="qwen3.6-27b-q6k-mtp",
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=32768,
        max_output_tokens=4096,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
        ),
    )
    openai_profile = StructuredLLMProviderProfile(
        provider_id=_OPENAI_PROVIDER_ID,
        model="gpt-5.4-mini-2026-03-17",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=400000,
        max_output_tokens=4096,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
        reasoning_effort=StructuredLLMReasoningEffort.NONE,
        text_verbosity=StructuredLLMTextVerbosity.LOW,
    )
    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(primary=local_profile, fallback=openai_profile),
        connections={
            _LOCAL_PROVIDER_ID: StructuredLLMProviderConnection(
                provider_id=_LOCAL_PROVIDER_ID,
                base_url="http://sir_convert_qwen_answer_key:8082",
            ),
            _OPENAI_PROVIDER_ID: StructuredLLMProviderConnection(
                provider_id=_OPENAI_PROVIDER_ID,
                base_url="https://api.openai.com",
                api_key="test-token",
            ),
        },
        remote_providers_enabled=True,
        remote_fallback_policy_authorized=True,
    )


def _store(*, active_provider_profile_id: str) -> StructuredLLMHotSettingsStore:
    return StructuredLLMHotSettingsStore(
        initial_settings=StructuredLLMProviderRoutingSettings(
            version=2,
            active_provider_profile_id=active_provider_profile_id,
            allowed_internal_route_classes=(
                frozenset({StructuredLLMInternalRouteClass.OPERATOR_API_ONLY})
                if active_provider_profile_id == _OPENAI_PROVIDER_ID
                else frozenset({StructuredLLMInternalRouteClass.OPERATOR_LOCAL_ONLY})
            ),
            remote_provider_authorized=active_provider_profile_id == _OPENAI_PROVIDER_ID,
            rollout_label="test-route",
        ),
        known_provider_profile_ids=frozenset({_LOCAL_PROVIDER_ID, _OPENAI_PROVIDER_ID}),
        remote_provider_profile_ids=frozenset({_OPENAI_PROVIDER_ID}),
    )


def _advisory_spec() -> JobSpecV2:
    return _spec(
        completion_mode=DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
    )


def _source_evidence_spec() -> JobSpecV2:
    return _spec(completion_mode=DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY)


def _spec(*, completion_mode: DigiExamAnswerKeyCompletionModeV2) -> JobSpecV2:
    return JobSpecV2(
        api_version="v2",
        source=SourceSpecV2(
            kind=SourceKindV2.UPLOAD,
            filename="exam.dxe",
            format=SourceFormatV2.DIGIEXAM_DXE,
        ),
        conversion=ConversionSpecV2(output_format=OutputFormatV2.EXAMNET_MIGRATION_BUNDLE),
        digiexam_migration_options=DigiExamMigrationOptionsV2(completion_mode=completion_mode),
        retention=RetentionSpecV2(pin=False),
    )
