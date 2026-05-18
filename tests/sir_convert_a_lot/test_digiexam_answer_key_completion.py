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
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    build_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    answer_key_candidate_planner_for_profile,
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
    StructuredLLMImageURLContentPart,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMRoutePolicy,
)
from scripts.sir_convert_a_lot.domain.structured_llm_provider_diagnostics import (
    StructuredLLMProviderErrorDiagnostic,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_answer_key_vision_assets import (
    DigiExamVisionCandidatePlanner,
    export_digiexam_answer_key_vision_assets,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_structured_llm_payload,
)

_EMBEDDED_IMAGE_DXE = Path(
    "inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/sanitized-embedded-image.dxe"
)


def test_choice_completion_report_uses_candidate_lineage_not_prompt_text() -> None:
    provider = _FakeProvider(
        {
            "correct_alternative_ids": [2],
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


def test_granite_vllm_choice_rows_use_bounded_choice_values() -> None:
    provider = _FakeProvider({"choice": "2"})
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_vllm_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.profiles[0].output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE
    assert provider.requests[0].output_spec.choice_values == ("1", "2")
    assert provider.requests[0].output_spec.json_schema["required"] == ["choice"]
    request_payload = json.loads(provider.requests[0].user_payload)
    assert request_payload["task"]["name"] == "select_teacher_intended_choice_answer_key"
    assert request_payload["task"]["instruction"].startswith("Read the item")
    assert request_payload["item"]["stem"] == "Choose the Greek letter."
    assert request_payload["choices"] == [
        {"alternative_id": 1, "choice_value": "1", "text": "Alpha"},
        {"alternative_id": 2, "choice_value": "2", "text": "Beta"},
    ]
    assert request_payload["output"]["provider_output_mode"] == "vllm_structured_choice"
    assert "For choice items" in provider.requests[0].system_prompt
    assert report.items[0].answer_payload == {"kind": "choice", "correct_alternative_ids": [2]}


def test_granite_vllm_multiple_response_rows_use_bounded_subset_values() -> None:
    provider = _FakeProvider({"choice": "1,3"})
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_multiple_response_payload()),
            provider_set=StructuredChatProviderSet(primary=_vllm_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.profiles[0].output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE
    assert provider.requests[0].output_spec.choice_values == (
        "1",
        "2",
        "3",
        "1,2",
        "1,3",
        "2,3",
        "1,2,3",
    )
    assert report.items[0].answer_payload == {"kind": "choice", "correct_alternative_ids": [1, 3]}


def test_granite_vllm_gap_rows_use_json_schema_object_mode() -> None:
    provider = _FakeProvider(
        {
            "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_gap_payload()),
            provider_set=StructuredChatProviderSet(primary=_vllm_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.profiles[0].output_mode == StructuredLLMOutputMode.VLLM_JSON_SCHEMA
    assert provider.requests[0].output_spec.choice_values == ()
    assert provider.requests[0].output_spec.json_schema["required"] == ["1"]
    request_payload = json.loads(provider.requests[0].user_payload)
    assert request_payload["task"]["name"] == "complete_teacher_intended_gap_fill_answer_key"
    assert request_payload["task"]["instruction"].startswith("Read the cloze item")
    assert request_payload["item"]["cloze_text"] == "Växter använder [1]."
    assert request_payload["gaps"][0]["gap_number"] == 1
    assert "string keys" in request_payload["output"]["json_shape"]
    assert request_payload["output"]["provider_output_mode"] == "vllm_json_schema"
    assert "For gap-fill items" in provider.requests[0].system_prompt
    assert report.items[0].answer_payload == {
        "kind": "gap_fill",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
    }


def test_llama_cpp_choice_rows_use_json_schema_object_mode() -> None:
    provider = _FakeProvider(
        {
            "correct_alternative_ids": [2],
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_llama_cpp_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert (
        provider.profiles[0].endpoint_kind == StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS
    )
    assert provider.profiles[0].output_mode == StructuredLLMOutputMode.JSON_SCHEMA
    assert provider.requests[0].output_spec.choice_values == ()
    request_payload = json.loads(provider.requests[0].user_payload)
    assert request_payload["output"]["provider_output_mode"] == "llama_cpp_json_schema"
    provider_payload = build_structured_llm_payload(
        profile=provider.profiles[0],
        request=provider.requests[0],
    )
    assert provider_payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "digiexam_choice_answer_key_decision_v1",
            "schema": provider.requests[0].output_spec.json_schema,
        },
    }
    assert "structured_outputs" not in provider_payload
    assert "grammar" not in provider_payload
    assert report.items[0].answer_payload == {"kind": "choice", "correct_alternative_ids": [2]}


def test_llama_cpp_choice_rows_can_use_gbnf_constrained_json() -> None:
    provider = _FakeProvider(
        {
            "correct_alternative_ids": [2],
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_llama_cpp_gbnf_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.profiles[0].output_mode == StructuredLLMOutputMode.GBNF
    assert provider.requests[0].output_spec.gbnf_grammar is not None
    assert "choice_decision" in provider.requests[0].output_spec.gbnf_grammar
    request_payload = json.loads(provider.requests[0].user_payload)
    assert request_payload["output"]["provider_output_mode"] == "llama_cpp_gbnf_json"
    provider_payload = build_structured_llm_payload(
        profile=provider.profiles[0],
        request=provider.requests[0],
    )
    assert provider_payload["grammar"] == provider.requests[0].output_spec.gbnf_grammar
    assert "response_format" not in provider_payload
    assert "structured_outputs" not in provider_payload
    assert report.items[0].answer_payload == {"kind": "choice", "correct_alternative_ids": [2]}


def test_llama_cpp_gap_rows_can_use_gbnf_constrained_json() -> None:
    provider = _FakeProvider(
        {
            "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_gap_payload()),
            provider_set=StructuredChatProviderSet(primary=_llama_cpp_gbnf_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.profiles[0].output_mode == StructuredLLMOutputMode.GBNF
    assert provider.requests[0].output_spec.gbnf_grammar is not None
    assert "gap_fill_numbered" in provider.requests[0].output_spec.gbnf_grammar
    request_payload = json.loads(provider.requests[0].user_payload)
    assert request_payload["output"]["provider_output_mode"] == "llama_cpp_gbnf_json"
    provider_payload = build_structured_llm_payload(
        profile=provider.profiles[0],
        request=provider.requests[0],
    )
    assert provider_payload["grammar"] == provider.requests[0].output_spec.gbnf_grammar
    assert "response_format" not in provider_payload
    assert "structured_outputs" not in provider_payload
    assert report.items[0].answer_payload == {
        "kind": "gap_fill",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
    }


def test_invalid_granite_vllm_choice_value_becomes_manual_follow_up() -> None:
    provider = _FakeProvider({"choice": "999"})
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_exam(_choice_payload()),
            provider_set=StructuredChatProviderSet(primary=_vllm_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    item = report.items[0]

    assert item.decision_state == DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    assert (
        item.backend_failure_code == DigiExamAnswerKeyCompletionFailureCode.LLM_OUTPUT_INVALID.value
    )
    assert item.answer_payload is None


def test_invalid_choice_output_becomes_manual_follow_up_without_candidate_digest() -> None:
    provider = _FakeProvider(
        {
            "correct_alternative_ids": [999],
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
            "correct_alternative_ids": [2, 2],
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
            "gap_answers": [
                {
                    "gap_id": "gap-1",
                    "accepted_values": ["fotosyntes"],
                }
            ],
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
            "gap_answers": [
                {
                    "gap_id": "gap-1",
                    "accepted_values": ["fotosyntes"],
                }
            ],
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
            "correct_alternative_ids": [1],
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
    assert item.provider_error_diagnostic is not None
    assert item.provider_error_diagnostic.status_code == 500
    items = payload["items"]
    assert isinstance(items, list)
    first_item = items[0]
    assert isinstance(first_item, dict)
    assert first_item["provider_error_diagnostic"] == {
        "status_code": 500,
        "request_id": "req_failure",
        "error_type": "server_error",
        "error_code": "upstream_failed",
        "error_param": None,
        "message_sha256": "sha256:test",
    }
    assert item.candidate_payload_digest is None
    assert "Choose the Greek letter" not in rendered_report
    assert "Alpha" not in rendered_report
    assert "Beta" not in rendered_report
    assert "raw provider body" not in rendered_report


def test_image_item_stays_manual_follow_up_without_vision_provider() -> None:
    provider = _FakeProvider(
        {
            "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild"]}],
        }
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=_embedded_image_gap_exam(),
            provider_set=StructuredChatProviderSet(primary=_llama_cpp_profile()),
            route_policy=_route_policy(),
            provider=provider,
        )
    )

    assert provider.requests == []
    assert report.items[0].decision_state == (
        DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    )
    assert (
        report.items[0].backend_failure_code
        == DigiExamAnswerKeyCompletionFailureCode.UNSUPPORTED_ASSETS.value
    )


def test_image_item_uses_multimodal_request_when_vision_provider_is_enabled(
    tmp_path: Path,
) -> None:
    provider = _FakeProvider(
        {
            "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild"]}],
        }
    )
    profile = _llama_cpp_vision_profile()
    exam = _embedded_image_gap_exam()
    item_assets = export_digiexam_answer_key_vision_assets(
        exam=exam,
        media_path=tmp_path / "answer-key-vision-assets",
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=exam,
            provider_set=StructuredChatProviderSet(primary=profile),
            route_policy=_route_policy(),
            provider=provider,
            candidate_planner=DigiExamVisionCandidatePlanner(
                base_planner=answer_key_candidate_planner_for_profile(profile),
                item_assets_by_id=item_assets,
            ),
        )
    )
    request = provider.requests[0]
    payload = report_to_json_payload(report)
    rendered_report = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert request.max_output_tokens == 4096
    assert len(request.user_content_parts) == 2
    image_part = request.user_content_parts[1]
    assert isinstance(image_part, StructuredLLMImageURLContentPart)
    assert image_part.url.startswith("file://item-001/assets/")
    assert (tmp_path / "answer-key-vision-assets" / "item-001" / "assets").is_dir()
    assert report.items[0].answer_payload == {
        "kind": "gap_fill",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild"]}],
    }
    assert "content_base64" not in rendered_report
    assert "iVBORw0KGgo" not in rendered_report
    assert "Look at the embedded prompt image" not in rendered_report


def test_vision_asset_export_can_scope_paths_by_job_id(tmp_path: Path) -> None:
    item_assets = export_digiexam_answer_key_vision_assets(
        exam=_embedded_image_gap_exam(),
        media_path=tmp_path / "provider-media",
        relative_path_prefix="job-001",
    )

    image_url = item_assets["item-001"].image_urls[0]

    assert image_url.startswith("file://job-001/item-001/assets/")
    assert (tmp_path / "provider-media" / image_url.removeprefix("file://")).is_file()


def test_invalid_image_asset_does_not_call_vision_provider(tmp_path: Path) -> None:
    provider = _FakeProvider(
        {
            "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild"]}],
        }
    )
    profile = _llama_cpp_vision_profile()
    exam = _embedded_image_gap_exam(image_payload="not-base64")
    item_assets = export_digiexam_answer_key_vision_assets(
        exam=exam,
        media_path=tmp_path / "answer-key-vision-assets",
    )
    report = asyncio.run(
        build_digiexam_answer_key_completion_report(
            job_id="job-1",
            completion_mode="local_llm_suggest_missing_machine_marked",
            exam=exam,
            provider_set=StructuredChatProviderSet(primary=profile),
            route_policy=_route_policy(),
            provider=provider,
            candidate_planner=DigiExamVisionCandidatePlanner(
                base_planner=answer_key_candidate_planner_for_profile(profile),
                item_assets_by_id=item_assets,
            ),
        )
    )

    assert provider.requests == []
    assert item_assets == {}
    assert (
        report.items[0].backend_failure_code
        == DigiExamAnswerKeyCompletionFailureCode.UNRELIABLE_STRUCTURE.value
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "unsupported_media",
        "missing_payload",
        "invalid_base64",
        "sha_mismatch",
        "broken_reference",
    ),
)
def test_vision_asset_export_rejects_unsupported_or_inconsistent_images(
    tmp_path: Path,
    mutation: str,
) -> None:
    exam = _mutated_embedded_image_exam(mutation)

    item_assets = export_digiexam_answer_key_vision_assets(
        exam=exam,
        media_path=tmp_path / "answer-key-vision-assets",
    )

    assert item_assets == {}
    assert not (tmp_path / "answer-key-vision-assets").exists()


class _FakeProvider:
    """Fake structured provider returning one response for every request."""

    def __init__(self, content: dict[str, JsonValue]) -> None:
        self._content = content
        self.requests: list[StructuredLLMRequest] = []
        self.profiles: list[StructuredLLMProviderProfile] = []

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        self.profiles.append(profile)
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
            diagnostic=StructuredLLMProviderErrorDiagnostic(
                status_code=500,
                request_id="req_failure",
                error_type="server_error",
                error_code="upstream_failed",
                error_param=None,
                message_sha256="sha256:test",
            ),
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


def _vllm_profile(*, context_window_tokens: int = 4096) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="local-granite-vllm",
        model="ibm-granite/granite-4.1-8b-fp8",
        endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=context_window_tokens,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=True,
        ),
    )


def _llama_cpp_profile(*, context_window_tokens: int = 4096) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="local-llama-cpp",
        model="mistral-small",
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=context_window_tokens,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
        ),
    )


def _llama_cpp_vision_profile(
    *,
    context_window_tokens: int = 32768,
) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="local-llama-cpp",
        model="qwen3.6-27b-q6k",
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=context_window_tokens,
        max_output_tokens=4096,
        temperature=0.15,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=True,
        ),
    )


def _llama_cpp_gbnf_profile(*, context_window_tokens: int = 4096) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="local-llama-cpp",
        model="mistral-small",
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.GBNF,
        is_remote=False,
        context_window_tokens=context_window_tokens,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
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


def _multiple_response_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Multiple response without key",
                        "about": "",
                        "bodyHTML": "<p>Choose prime numbers.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "2", "about": "", "right": False},
                            {"id": 2, "title": "4", "about": "", "right": False},
                            {"id": 3, "title": "5", "about": "", "right": False},
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


def _embedded_image_gap_exam(
    *,
    image_payload: str | None = None,
) -> DigiExamIntermediateExam:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Embedded image fixture has no root object.")
    if image_payload is not None:
        payload["exams"][0]["questions"][0]["images"][0] = image_payload
    return _exam(payload)


def _mutated_embedded_image_exam(mutation: str) -> DigiExamIntermediateExam:
    exam = _embedded_image_gap_exam()
    item = exam.items[0]
    asset = item.embedded_assets[0]
    if mutation == "unsupported_media":
        changed_asset = replace(asset, media_type="image/gif")
        changed_item = replace(item, embedded_assets=(changed_asset,))
    elif mutation == "missing_payload":
        changed_asset = replace(asset, content_base64="")
        changed_item = replace(item, embedded_assets=(changed_asset,))
    elif mutation == "invalid_base64":
        changed_asset = replace(asset, content_base64="not-base64")
        changed_item = replace(item, embedded_assets=(changed_asset,))
    elif mutation == "sha_mismatch":
        changed_asset = replace(asset, sha256="0" * 64)
        changed_item = replace(item, embedded_assets=(changed_asset,))
    elif mutation == "broken_reference":
        changed_item = replace(item, embedded_asset_references=())
    else:
        raise RuntimeError(f"Unsupported mutation: {mutation}")
    return replace(exam, items=(changed_item,))
