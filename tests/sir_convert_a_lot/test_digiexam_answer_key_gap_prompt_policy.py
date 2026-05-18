"""DigiExam gap-fill answer-key prompt policy tests.

Purpose:
    Guard the teacher-intended answer-value contract for gap-fill completion
    prompts, including labeled candidate banks represented in text or images.

Relationships:
    - Exercises `domain.digiexam_answer_key_model_projection` directly for
      prompt-policy wording.
    - Exercises `domain.digiexam_answer_key_completion_candidates` to prove
      vision-capable provider plans receive the same gap-fill policy.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    candidate_request_for_item,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_model_projection import (
    GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT,
    gap_fill_answer_key_model_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
)

_ITEM_013_DXE = Path(
    "inputs/examples/digiexam-dxe-fixtures/"
    "2026-05-12-onedrive-pure-dxe/"
    "1811577114-ekologiprov-v-49-25d-e.dxe"
)


def test_gap_fill_payload_prefers_visible_candidate_labels_for_item_013() -> None:
    """Item 013 must ask for A-E labels, not expanded candidate text."""

    payload = gap_fill_answer_key_model_payload(_item_013())
    item_payload = _payload_section(payload, "item")
    output_payload = _payload_section(payload, "output")

    assert "Kretslopp = [1]" in item_payload
    assert "Näringsväv = [2]" in item_payload
    assert "Fotosyntes = [3]" in item_payload
    assert "Producent = [4]" in item_payload
    assert "Cellandning = [5]" in item_payload
    assert "candidate list" in GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT
    assert "Return the exact value a student is expected to put in the blank" in (
        GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT
    )
    assert "return only the label" in GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT
    assert "Do not paraphrase, substitute synonyms, or expand labels" in (
        GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT
    )
    assert "student is expected to place in the blank" in output_payload
    assert "A, B, C, D, E" in output_payload
    assert "return only the label, not the explanation" in output_payload


def test_gap_fill_vision_request_uses_labeled_candidate_policy() -> None:
    """Vision-capable plans keep the same label-only gap-fill rule."""

    plan = candidate_request_for_item(
        job_id="job-item-013",
        item=_item_013(),
        profile=_openai_vision_profile(),
    )

    assert plan is not None
    assert "complete_teacher_intended_gap_fill_answer_key" in plan.request.user_payload
    assert "candidate list" in plan.request.system_prompt
    assert "return only the label" in plan.request.system_prompt
    assert "not the explanation" in plan.request.user_payload


def _item_013() -> DigiExamIrItem:
    exam = build_digiexam_intermediate_exam(DigiExamDxeParser().parse_file(_ITEM_013_DXE))
    return next(item for item in exam.items if item.item_id == "item-013")


def _payload_section(payload: dict[str, object], key: str) -> str:
    return json.dumps(payload[key], ensure_ascii=False, sort_keys=True)


def _openai_vision_profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
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
    )
