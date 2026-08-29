"""Focused failover tests for advisory answer-key completion."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.answer_key_token_lease_contracts import (
    AnswerKeyTokenLeaseError,
    AnswerKeyTokenLeaseFailureCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    build_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    DigiExamAnswerKeyCompletionReport,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_admission import (
    admitted_route_snapshot_for_profile,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderProtocol,
    StructuredChatProviderSet,
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMRoutePolicy,
    StructuredLLMUsage,
)
from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMInternalRouteClass,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_token_lease import (
    FilesystemAnswerKeyTokenLeaseLedger,
)
from scripts.sir_convert_a_lot.infrastructure.leased_structured_llm_provider import (
    LeasedStructuredChatProvider,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_admission import (
    provider_set_for_admitted_route,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)


@pytest.mark.parametrize(
    ("failure_code", "status_code"),
    (
        (StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT, None),
        (StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED, None),
        (StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, 408),
        (StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, 500),
    ),
)
def test_transient_primary_failure_replans_and_calls_fallback_once(
    failure_code: StructuredLLMBackendFailureCode,
    status_code: int | None,
) -> None:
    provider = _SequenceProvider(
        responses=(
            _provider_error(failure_code=failure_code, status_code=status_code),
            StructuredLLMResponse(
                content={"correct_alternative_ids": [2]},
                finish_reason="stop",
            ),
        )
    )

    report = _run_completion(provider)

    assert [profile.provider_id for profile in provider.profiles] == [
        "primary-vllm",
        "fallback-remote",
    ]
    assert [request.output_spec.choice_values for request in provider.requests] == [
        ("1", "2"),
        (),
    ]
    assert [request.allow_remote_fallback for request in provider.requests] == [True, True]
    assert report.items[0].provider_profile_id == "fallback-remote"
    assert report.items[0].answer_payload == {
        "kind": "choice",
        "correct_alternative_ids": [2],
    }


@pytest.mark.parametrize(
    ("failure_code", "status_code"),
    (
        (StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING, None),
        (StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, 429),
        (StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, 499),
        (StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON, None),
        (StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT, None),
        (StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT, None),
        (StructuredLLMBackendFailureCode.PROVIDER_CONTENT_NOT_JSON, None),
        (StructuredLLMBackendFailureCode.PROVIDER_SCHEMA_MISMATCH, None),
        (StructuredLLMBackendFailureCode.PROVIDER_REFUSAL, None),
    ),
)
def test_non_transient_primary_failures_never_call_fallback(
    failure_code: StructuredLLMBackendFailureCode,
    status_code: int | None,
) -> None:
    provider = _SequenceProvider(
        responses=(_provider_error(failure_code=failure_code, status_code=status_code),)
    )

    report = _run_completion(provider)

    assert [profile.provider_id for profile in provider.profiles] == ["primary-vllm"]
    assert report.items[0].backend_failure_code == failure_code.value


def test_semantic_invalidity_does_not_call_fallback() -> None:
    provider = _SequenceProvider(
        responses=(
            StructuredLLMResponse(
                content={"correct_alternative_ids": [999]},
                finish_reason="stop",
            ),
        )
    )

    report = _run_completion(provider)

    assert [profile.provider_id for profile in provider.profiles] == ["primary-vllm"]
    assert report.items[0].backend_failure_code == "llm_output_invalid"


def test_lease_exhaustion_is_terminal_without_fallback() -> None:
    provider = _SequenceProvider(
        responses=(
            AnswerKeyTokenLeaseError(
                failure_code=AnswerKeyTokenLeaseFailureCode.DAILY_TOKEN_LEASE_EXHAUSTED,
                message="The daily lease is exhausted.",
                utc_day="2026-08-29",
                requested_tokens=100,
                available_tokens=0,
            ),
        )
    )

    report = _run_completion(provider)

    assert [profile.provider_id for profile in provider.profiles] == ["primary-vllm"]
    assert report.items[0].backend_failure_code == "daily_token_lease_exhausted"


def test_over_budget_primary_does_not_call_fallback() -> None:
    provider = _SequenceProvider(responses=())
    primary = replace(_primary_profile(), context_window_tokens=800)

    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(),
            provider_set=StructuredChatProviderSet(
                primary=primary,
                fallback=_fallback_profile(),
            ),
            route_policy=StructuredLLMRoutePolicy(
                remote_providers_enabled=True,
                remote_fallback_policy_authorized=True,
                allow_remote_fallback=True,
            ),
            provider=provider,
        )
    )

    assert provider.requests == []
    assert report.items[0].backend_failure_code == "over_budget"


def test_fallback_failure_is_terminal_without_recursion() -> None:
    provider = _SequenceProvider(
        responses=(
            _provider_error(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
                status_code=None,
            ),
            _provider_error(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
                status_code=None,
            ),
        )
    )

    report = _run_completion(provider)

    assert [profile.provider_id for profile in provider.profiles] == [
        "primary-vllm",
        "fallback-remote",
    ]
    assert report.items[0].backend_failure_code == "provider_request_failed"


def test_admitted_primary_preserves_configured_fallback() -> None:
    primary = _primary_profile()
    fallback = _fallback_profile()
    provider_set = provider_set_for_admitted_route(
        structured_config=StructuredLLMRuntimeConfig(
            enabled=True,
            provider_set=StructuredChatProviderSet(primary=primary, fallback=fallback),
        ),
        admitted_route=admitted_route_snapshot_for_profile(
            profile=primary,
            settings_version=1,
            route_class=StructuredLLMInternalRouteClass.OPERATOR_DEFAULT,
            remote_provider_authorized=True,
        ),
    )

    assert provider_set is not None
    assert provider_set.primary == primary
    assert provider_set.fallback == fallback


def test_transient_failover_reserves_a_second_lease_and_reconciles_success(
    tmp_path: Path,
) -> None:
    delegated_provider = _SequenceProvider(
        responses=(
            _provider_error(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
                status_code=None,
            ),
            StructuredLLMResponse(
                content={"correct_alternative_ids": [2]},
                finish_reason="stop",
                usage=StructuredLLMUsage(total_tokens=40),
            ),
        )
    )
    ledger = _lease_ledger(tmp_path=tmp_path, daily_token_limit=10_000)

    report = _run_completion(
        LeasedStructuredChatProvider(provider=delegated_provider, lease_ledger=ledger),
        provider_set=_remote_provider_set(),
    )

    snapshot = ledger.snapshot()
    assert [profile.provider_id for profile in delegated_provider.profiles] == [
        "openai-gpt-5.6-luna",
        "openrouter-glm-5.3-flash",
    ]
    assert len(snapshot.leases) == 2
    assert snapshot.uncertain_tokens > 0
    assert snapshot.consumed_tokens == 40
    assert report.items[0].provider_profile_id == "openrouter-glm-5.3-flash"


def test_second_lease_exhaustion_stops_before_fallback_provider_call(tmp_path: Path) -> None:
    delegated_provider = _SequenceProvider(
        responses=(
            _provider_error(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
                status_code=None,
            ),
        )
    )
    ledger = _lease_ledger(tmp_path=tmp_path, daily_token_limit=1_000)

    report = _run_completion(
        LeasedStructuredChatProvider(provider=delegated_provider, lease_ledger=ledger),
        provider_set=_remote_provider_set(),
    )

    assert [profile.provider_id for profile in delegated_provider.profiles] == [
        "openai-gpt-5.6-luna"
    ]
    assert report.items[0].provider_profile_id == "openrouter-glm-5.3-flash"
    assert report.items[0].backend_failure_code == "daily_token_lease_exhausted"
    assert len(ledger.snapshot().leases) == 1


def test_hard_exhaustion_makes_zero_provider_calls(tmp_path: Path) -> None:
    delegated_provider = _SequenceProvider(
        responses=(
            StructuredLLMResponse(
                content={"choice": "2"},
                finish_reason="stop",
            ),
        )
    )
    ledger = _lease_ledger(tmp_path=tmp_path, daily_token_limit=1)

    report = _run_completion(
        LeasedStructuredChatProvider(provider=delegated_provider, lease_ledger=ledger),
        provider_set=_remote_provider_set(),
    )

    assert delegated_provider.requests == []
    assert report.items[0].provider_profile_id == "openai-gpt-5.6-luna"
    assert report.items[0].backend_failure_code == "daily_token_lease_exhausted"
    assert ledger.snapshot().leases == ()


@dataclass
class _SequenceProvider:
    responses: tuple[
        StructuredLLMProviderError | AnswerKeyTokenLeaseError | StructuredLLMResponse,
        ...,
    ]
    requests: list[StructuredLLMRequest] = field(default_factory=list)
    profiles: list[StructuredLLMProviderProfile] = field(default_factory=list)

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        self.profiles.append(profile)
        response = self.responses[len(self.requests) - 1]
        if isinstance(response, Exception):
            raise response
        return response


def _run_completion(
    provider: StructuredChatProviderProtocol,
    *,
    provider_set: StructuredChatProviderSet | None = None,
) -> DigiExamAnswerKeyCompletionReport:
    return asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(),
            provider_set=provider_set
            or StructuredChatProviderSet(primary=_primary_profile(), fallback=_fallback_profile()),
            route_policy=StructuredLLMRoutePolicy(
                remote_providers_enabled=True,
                remote_fallback_policy_authorized=True,
                allow_remote_fallback=True,
            ),
            provider=provider,
        )
    )


def _lease_ledger(
    *,
    tmp_path: Path,
    daily_token_limit: int,
) -> FilesystemAnswerKeyTokenLeaseLedger:
    return FilesystemAnswerKeyTokenLeaseLedger(
        ledger_directory=tmp_path,
        daily_token_limit=daily_token_limit,
    )


def _remote_provider_set() -> StructuredChatProviderSet:
    return StructuredChatProviderSet(
        primary=replace(
            _fallback_profile(),
            provider_id="openai-gpt-5.6-luna",
            model="gpt-5.6-luna",
        ),
        fallback=replace(
            _fallback_profile(),
            provider_id="openrouter-glm-5.3-flash",
            model="z-ai/glm-5.3-flash",
            endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        ),
    )


def _provider_error(
    *,
    failure_code: StructuredLLMBackendFailureCode,
    status_code: int | None,
) -> StructuredLLMProviderError:
    return StructuredLLMProviderError(
        failure_code=failure_code,
        message="provider failure",
        provider_id="primary-vllm",
        status_code=status_code,
    )


def _primary_profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="primary-vllm",
        model="primary-model",
        endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=4096,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=True,
        ),
    )


def _fallback_profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="fallback-remote",
        model="fallback-model",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=4096,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
    )


def _exam() -> DigiExamIntermediateExam:
    payload: dict[str, JsonValue] = {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Single without key",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": False},
                        ],
                    }
                ]
            }
        ]
    }
    return build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(payload, filename="exam.dxe")
    )
