"""Tests for OpenAI vision request shaping in answer-key completion runtime.

Purpose:
    Keep the service runtime's OpenAI Responses image inputs aligned with the
    provider contract without adding more coverage to the broad DigiExam API
    route test module.

Relationships:
    - Exercises `infrastructure.digiexam_answer_key_completion_runtime`.
    - Guards the Task 325 OpenAI provider path that feeds advisory answer-key
      reports for DigiExam migration jobs.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    report_to_json_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import DigiExamAnswerKeyCompletionModeV2
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
    StructuredLLMImageURLContentPart,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMTextVerbosity,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_answer_key_completion_runtime import (
    run_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
    StructuredLLMProviderConnection,
)

_ITEM_013_DXE = Path(
    "inputs/examples/digiexam-dxe-fixtures/"
    "2026-05-12-onedrive-pure-dxe/"
    "1811577114-ekologiprov-v-49-25d-e.dxe"
)


def test_openai_vision_completion_runtime_uses_data_url_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI Responses must not receive local file URLs for embedded images."""

    provider_image_urls: list[str] = []

    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        assert profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES
        content_parts = request.user_content_parts
        assert len(content_parts) == 2
        image_part = content_parts[1]
        assert isinstance(image_part, StructuredLLMImageURLContentPart)
        provider_image_urls.append(image_part.url)
        return StructuredLLMResponse(
            content={
                "1": "ekosystem",
                "2": "population",
                "3": "näringskedja",
                "4": "producent",
                "5": "konsument",
            },
            finish_reason="stop",
        )

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        advisory_provider_call,
    )
    exam = build_digiexam_intermediate_exam(DigiExamDxeParser().parse_file(_ITEM_013_DXE))
    exam = replace(exam, items=tuple(item for item in exam.items if item.item_id == "item-013"))
    assert len(exam.items) == 1
    report = run_digiexam_answer_key_completion_report(
        job_id="job-openai-vision",
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED.value
        ),
        exam=exam,
        config=ServiceConfig(
            api_key="test-key",
            data_root=tmp_path / "service-data",
            structured_llm=_openai_vision_structured_llm_config(
                vision_media_path=tmp_path / "provider-media",
            ),
        ),
    )
    payload = report_to_json_payload(report)
    rendered_report = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert provider_image_urls == [provider_image_urls[0]]
    assert provider_image_urls[0].startswith("data:image/png;base64,")
    assert "file://" not in provider_image_urls[0]
    assert report.items[0].decision_state.value == "suggested"
    assert report.items[0].provider_error_diagnostic is None
    assert "content_base64" not in rendered_report
    assert "iVBORw0KGgo" not in rendered_report


def _openai_vision_structured_llm_config(
    *,
    vision_media_path: Path,
) -> StructuredLLMRuntimeConfig:
    profile = StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.4-mini-2026-03-17",
        model="gpt-5.4-mini-2026-03-17",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=400000,
        max_output_tokens=4096,
        temperature=0.0,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=True,
        ),
        reasoning_effort=StructuredLLMReasoningEffort.NONE,
        text_verbosity=StructuredLLMTextVerbosity.LOW,
    )
    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(primary=profile),
        connections={
            profile.provider_id: StructuredLLMProviderConnection(
                provider_id=profile.provider_id,
                base_url="https://api.openai.com",
                api_key="test-token",
            )
        },
        remote_providers_enabled=True,
        remote_fallback_policy_authorized=True,
        vision_media_path=vision_media_path,
    )
