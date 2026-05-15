"""DigiExam advisory answer-key completion candidate builders.

Purpose:
    Convert eligible DigiExam IR items into item-local structured LLM requests
    for advisory answer-key completion while keeping raw item text out of
    persisted report contracts.

Relationships:
    - Consumes `domain.digiexam_ir_contracts` item structures.
    - Uses `domain.structured_llm_contracts.StructuredLLMRequest` as the
      provider boundary from Task 296.
    - Feeds `domain.digiexam_answer_key_completion` orchestration and
      validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS,
    ANSWER_KEY_COMPLETION_SYSTEM_PROMPT,
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_exam_authoring_adapter import (
    build_exam_authoring_gap_open_cloze_interaction_from_digiexam_item,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredOutputSpec,
)


@dataclass(frozen=True)
class DigiExamCompletionCandidateRequest:
    """One item-local provider request and its source item."""

    item: DigiExamIrItem
    request: StructuredLLMRequest


def candidate_request_for_item(
    *,
    job_id: str,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamCompletionCandidateRequest | None:
    """Build a provider request for eligible missing-key machine-marked items."""

    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        return None
    if item.warnings and any(warning.blocking for warning in item.warnings):
        return None
    if item.embedded_asset_references or item.embedded_assets:
        return None
    if item.item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        return _choice_candidate_request(job_id=job_id, item=item, profile=profile)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return _gap_fill_candidate_request(job_id=job_id, item=item, profile=profile)
    return None


def _choice_candidate_request(
    *,
    job_id: str,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamCompletionCandidateRequest | None:
    alternative_ids = tuple(alternative.id for alternative in item.alternatives)
    if not alternative_ids or len(set(alternative_ids)) != len(alternative_ids):
        return None
    maximum_answers = (
        len(alternative_ids) if item.item_type == DigiExamItemType.MULTIPLE_RESPONSE else 1
    )
    payload = {
        "item_id": item.item_id,
        "item_type": item.item_type.value,
        "title": item.title,
        "prompt_html": item.prompt_html or "",
        "prompt_lines": list(item.prompt_lines),
        "alternatives": [
            {"alternative_id": alternative.id, "text": alternative.title}
            for alternative in item.alternatives
        ],
        "answer_cardinality": {"min": 1, "max": maximum_answers},
    }
    request = _request(
        job_id=job_id,
        item=item,
        prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
        output_spec=_choice_output_spec(),
        user_payload=payload,
        profile=profile,
    )
    return DigiExamCompletionCandidateRequest(item=item, request=request)


def _gap_fill_candidate_request(
    *,
    job_id: str,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamCompletionCandidateRequest | None:
    if not item.gaps or any(not gap.guid.strip() for gap in item.gaps):
        return None
    interaction = build_exam_authoring_gap_open_cloze_interaction_from_digiexam_item(item)
    payload = {
        "item_id": item.item_id,
        "item_type": item.item_type.value,
        "title": item.title,
        "prompt_html": item.prompt_html or "",
        "prompt_lines": list(item.prompt_lines),
        "normalization_profile": interaction.normalization_profile.value,
        "gaps": [
            {
                "gap_id": gap.gap_id,
                "display_order": gap.display_order,
                "required_for_auto_evaluation": gap.required_for_auto_evaluation,
            }
            for gap in interaction.gaps
        ],
    }
    request = _request(
        job_id=job_id,
        item=item,
        prompt_template_version=GAP_FILL_PROMPT_TEMPLATE_VERSION,
        output_spec=_gap_fill_output_spec(),
        user_payload=payload,
        profile=profile,
    )
    return DigiExamCompletionCandidateRequest(item=item, request=request)


def _request(
    *,
    job_id: str,
    item: DigiExamIrItem,
    prompt_template_version: str,
    output_spec: StructuredOutputSpec,
    user_payload: object,
    profile: StructuredLLMProviderProfile | None,
) -> StructuredLLMRequest:
    user_payload_text = _canonical_json(user_payload)
    max_output_tokens = (
        min(ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS, profile.max_output_tokens)
        if profile is not None
        else ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS
    )
    return StructuredLLMRequest(
        job_id=job_id,
        item_id=item.item_id,
        item_type=item.item_type.value,
        prompt_template_version=prompt_template_version,
        system_prompt=ANSWER_KEY_COMPLETION_SYSTEM_PROMPT,
        user_payload=user_payload_text,
        output_spec=output_spec,
        estimated_input_tokens=_estimate_tokens(ANSWER_KEY_COMPLETION_SYSTEM_PROMPT)
        + _estimate_tokens(user_payload_text),
        max_output_tokens=max_output_tokens,
        allow_remote_fallback=False,
    )


def _choice_output_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision_state": {
                    "type": "string",
                    "enum": ["answered", "manual_follow_up_required"],
                },
                "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}},
                "manual_follow_up_code": {"type": ["string", "null"]},
            },
            "required": ["decision_state", "correct_alternative_ids", "manual_follow_up_code"],
        },
    )


def _gap_fill_output_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision_state": {
                    "type": "string",
                    "enum": ["answered", "manual_follow_up_required"],
                },
                "gap_answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "gap_id": {"type": "string"},
                            "accepted_values": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["gap_id", "accepted_values"],
                    },
                },
                "manual_follow_up_code": {"type": ["string", "null"]},
            },
            "required": ["decision_state", "gap_answers", "manual_follow_up_code"],
        },
    )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)
