"""DigiExam advisory answer-key completion domain tests.

Purpose:
    Prove Task 297 candidate construction, backend validation, and report
    privacy without exercising HTTP artifact routes.

Relationships:
    - Exercises `domain.digiexam_answer_key_completion` and its candidate/report
      contracts.
    - Uses the Task 296 structured LLM provider protocol with a fake provider.
    - Complements route-level bundle tests for artifact wiring.
"""

from __future__ import annotations

import asyncio
import json

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    build_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    DigiExamAnswerKeyCompletionDecisionState,
    DigiExamAnswerKeyCompletionFailureCode,
    report_to_json_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
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
)


def test_choice_completion_report_uses_candidate_lineage_not_prompt_text() -> None:
    provider = _FakeProvider(
        {
            "decision_state": "answered",
            "correct_alternative_ids": [2],
            "manual_follow_up_code": None,
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    payload = report_to_json_payload(report)
    item = report.items[0]
    rendered_report = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert provider.requests[0].user_payload.find("Choose the Greek letter") > -1
    assert item.decision_state == DigiExamAnswerKeyCompletionDecisionState.SUGGESTED
    assert item.answer_payload == {"kind": "choice", "correct_alternative_ids": [2]}
    assert item.candidate_id is not None
    assert item.candidate_payload_digest is not None
    assert item.provider_profile_id == "local-structured"
    assert "Choose the Greek letter" not in rendered_report
    assert "Alpha" not in rendered_report
    assert "Beta" not in rendered_report
    assert "source_provided" not in rendered_report
    assert "teacher_provided" not in rendered_report
    assert "reviewed" not in rendered_report


def test_invalid_choice_output_becomes_manual_follow_up_without_candidate_digest() -> None:
    provider = _FakeProvider(
        {
            "decision_state": "answered",
            "correct_alternative_ids": [999],
            "manual_follow_up_code": None,
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    item = report.items[0]

    assert item.decision_state == DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    assert (
        item.backend_failure_code == DigiExamAnswerKeyCompletionFailureCode.LLM_OUTPUT_INVALID.value
    )
    assert item.candidate_id is None
    assert item.candidate_payload_digest is None
    assert item.answer_payload is None


def test_duplicate_choice_output_becomes_manual_follow_up_without_candidate_digest() -> None:
    provider = _FakeProvider(
        {
            "decision_state": "answered",
            "correct_alternative_ids": [2, 2],
            "manual_follow_up_code": None,
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    item = report.items[0]

    assert item.decision_state == DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    assert (
        item.backend_failure_code == DigiExamAnswerKeyCompletionFailureCode.LLM_OUTPUT_INVALID.value
    )
    assert item.candidate_id is None
    assert item.candidate_payload_digest is None
    assert item.answer_payload is None


def test_gap_fill_completion_validates_exact_gap_ids() -> None:
    provider = _FakeProvider(
        {
            "decision_state": "answered",
            "gap_answers": [
                {
                    "gap_id": "gap-1",
                    "accepted_values": ["fotosyntes"],
                }
            ],
            "manual_follow_up_code": None,
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_gap_payload()),
            provider_set=StructuredChatProviderSet(primary=_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert report.items[0].answer_payload == {
        "kind": "gap_fill",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
    }


def test_gap_fill_completion_rejects_partial_gap_answers() -> None:
    provider = _FakeProvider(
        {
            "decision_state": "answered",
            "gap_answers": [
                {
                    "gap_id": "gap-1",
                    "accepted_values": ["fotosyntes"],
                }
            ],
            "manual_follow_up_code": None,
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_two_gap_payload()),
            provider_set=StructuredChatProviderSet(primary=_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    item = report.items[0]

    assert item.decision_state == DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    assert (
        item.backend_failure_code == DigiExamAnswerKeyCompletionFailureCode.LLM_OUTPUT_INVALID.value
    )
    assert item.candidate_payload_digest is None
    assert item.answer_payload is None


def test_over_budget_item_does_not_call_provider() -> None:
    provider = _FakeProvider(
        {
            "decision_state": "answered",
            "correct_alternative_ids": [1],
            "manual_follow_up_code": None,
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload(prompt_multiplier=300)),
            provider_set=StructuredChatProviderSet(primary=_profile(context_window_tokens=900)),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.requests == []
    assert (
        report.items[0].backend_failure_code
        == DigiExamAnswerKeyCompletionFailureCode.OVER_BUDGET.value
    )


def test_provider_failure_becomes_manual_follow_up_without_raw_capture() -> None:
    provider = _FailingProvider()
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    payload = report_to_json_payload(report)
    rendered_report = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    item = report.items[0]

    assert item.decision_state == DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    assert item.backend_failure_code == StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR.value
    assert item.candidate_payload_digest is None
    assert "Choose the Greek letter" not in rendered_report
    assert "Alpha" not in rendered_report
    assert "Beta" not in rendered_report


class _FakeProvider:
    """Fake structured provider returning one response for every request."""

    def __init__(self, content: dict[str, JsonValue]) -> None:
        self._content = content
        self.requests: list[StructuredLLMRequest] = []

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del profile
        self.requests.append(request)
        return StructuredLLMResponse(content=self._content, finish_reason="stop")


class _FailingProvider:
    """Fake structured provider raising a typed backend failure."""

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del request
        raise StructuredLLMProviderError(
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
            message="backend failed",
            provider_id=profile.provider_id,
            status_code=500,
        )


def _profile(*, context_window_tokens: int = 4096) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="local-structured",
        model="local-model",
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=context_window_tokens,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
    )


def _route_policy() -> StructuredLLMRoutePolicy:
    return StructuredLLMRoutePolicy(
        remote_providers_enabled=False,
        remote_fallback_policy_authorized=False,
        allow_remote_fallback=False,
    )


def _exam(payload: dict[str, object]) -> DigiExamIntermediateExam:
    return build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(payload, filename="exam.dxe")
    )


def _choice_payload(*, prompt_multiplier: int = 1) -> dict[str, object]:
    prompt = "Choose the Greek letter. " * prompt_multiplier
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Single without key",
                        "about": "",
                        "bodyHTML": f"<p>{prompt}</p>",
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


def _gap_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Gap without key",
                        "about": "",
                        "bodyHTML": '<p>Växter använder <span dx-wg-id="gap-1"></span>.</p>',
                        "images": [],
                        "maxScore": 2,
                        "type": 3,
                        "blanks": [{"guid": "gap-1", "validations": []}],
                    }
                ]
            }
        ]
    }


def _two_gap_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Two gaps without key",
                        "about": "",
                        "bodyHTML": (
                            '<p>Växter använder <span dx-wg-id="gap-1"></span> '
                            'och producerar <span dx-wg-id="gap-2"></span>.</p>'
                        ),
                        "images": [],
                        "maxScore": 2,
                        "type": 3,
                        "blanks": [
                            {"guid": "gap-1", "validations": []},
                            {"guid": "gap-2", "validations": []},
                        ],
                    }
                ]
            }
        ]
    }
