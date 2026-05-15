"""DigiExam advisory answer-key completion candidate planners.

Purpose:
    Plan provider-specific, item-local answer-key completion interactions while
    keeping response decoding bound to the same provider contract that shaped
    each request.

Relationships:
    - Consumes `domain.digiexam_ir_contracts` item structures.
    - Uses `domain.structured_llm_contracts.StructuredLLMRequest` as the
      provider boundary from Task 296.
    - Feeds `domain.digiexam_answer_key_completion` orchestration and
      validation without coupling orchestration to vLLM, Granite, or JSON
      Schema implementation details.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, replace
from typing import Protocol

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS,
    ANSWER_KEY_COMPLETION_SYSTEM_PROMPT,
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_payloads import (
    answer_payload_from_model_content,
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
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredOutputSpec,
)


@dataclass(frozen=True)
class DigiExamCompletionCandidatePlan:
    """One item-local provider interaction and response decoder."""

    item: DigiExamIrItem
    request: StructuredLLMRequest
    provider_profile: StructuredLLMProviderProfile | None
    decoder: "DigiExamAnswerKeyResponseDecoderProtocol"


class DigiExamAnswerKeyResponseDecoderProtocol(Protocol):
    """Decode provider-native content into stable advisory answer payload."""

    def decode(
        self,
        *,
        item: DigiExamIrItem,
        response: StructuredLLMResponse,
    ) -> dict[str, JsonValue] | None: ...


class DigiExamAnswerKeyCandidatePlannerProtocol(Protocol):
    """Plan one item-local provider request for an answer-key candidate."""

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None: ...


def answer_key_candidate_planner_for_profile(
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamAnswerKeyCandidatePlannerProtocol:
    """Return the default answer-key planner for the selected provider profile."""

    if (
        profile is not None
        and profile.endpoint_kind == StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS
        and profile.capabilities.supports_vllm_structured_choice
        and profile.capabilities.supports_json_schema
    ):
        return GraniteVllmAnswerKeyCandidatePlanner()
    return JsonSchemaAnswerKeyCandidatePlanner()


@dataclass(frozen=True)
class JsonSchemaAnswerKeyCandidatePlanner:
    """Generic JSON Schema planner for provider-neutral answer-key completion."""

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build one JSON Schema-backed provider interaction when eligible."""

        if not _provider_eligible(item):
            return None
        if item.item_type in _CHOICE_TYPES:
            if not _alternative_ids(item):
                return None
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
                output_spec=_choice_decision_output_spec(),
                user_payload=_choice_payload(item),
                profile=profile,
            )
            return DigiExamCompletionCandidatePlan(
                item=item,
                request=request,
                provider_profile=_json_schema_profile(profile),
                decoder=_JsonSchemaAnswerKeyResponseDecoder(),
            )
        if item.item_type == DigiExamItemType.GAP_FILL:
            return _gap_fill_plan(job_id=job_id, item=item, profile=_json_schema_profile(profile))
        return None


@dataclass(frozen=True)
class GraniteVllmAnswerKeyCandidatePlanner:
    """Granite/vLLM planner with per-item constrained-output selection."""

    max_multiple_response_choice_values: int = 256

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build one vLLM interaction using choice rows where possible."""

        if not _provider_eligible(item):
            return None
        if item.item_type in _CHOICE_TYPES:
            values = _vllm_choice_values(
                item,
                max_values=self.max_multiple_response_choice_values,
            )
            if not values:
                return None
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
                output_spec=_vllm_choice_output_spec(values),
                user_payload=_choice_payload(item),
                profile=_vllm_choice_profile(profile),
            )
            return DigiExamCompletionCandidatePlan(
                item=item,
                request=request,
                provider_profile=_vllm_choice_profile(profile),
                decoder=_VllmChoiceAnswerKeyResponseDecoder(),
            )
        if item.item_type == DigiExamItemType.GAP_FILL:
            return _gap_fill_plan(
                job_id=job_id,
                item=item,
                profile=_vllm_json_schema_profile(profile),
            )
        return None


def candidate_request_for_item(
    *,
    job_id: str,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamCompletionCandidatePlan | None:
    """Build a provider plan using the default planner for compatibility."""

    return answer_key_candidate_planner_for_profile(profile).plan_candidate(
        job_id=job_id,
        item=item,
        profile=profile,
    )


@dataclass(frozen=True)
class _JsonSchemaAnswerKeyResponseDecoder:
    def decode(
        self,
        *,
        item: DigiExamIrItem,
        response: StructuredLLMResponse,
    ) -> dict[str, JsonValue] | None:
        return answer_payload_from_model_content(item=item, content=response.content)


@dataclass(frozen=True)
class _VllmChoiceAnswerKeyResponseDecoder:
    def decode(
        self,
        *,
        item: DigiExamIrItem,
        response: StructuredLLMResponse,
    ) -> dict[str, JsonValue] | None:
        selected_value = response.content.get("choice")
        if not isinstance(selected_value, str) or not selected_value.strip():
            return None
        ids = _decode_choice_value(selected_value.strip())
        if not ids:
            return None
        valid_ids = {alternative.id for alternative in item.alternatives}
        if any(alternative_id not in valid_ids for alternative_id in ids):
            return None
        if item.item_type != DigiExamItemType.MULTIPLE_RESPONSE and len(ids) != 1:
            return None
        if len(set(ids)) != len(ids):
            return None
        return {"kind": "choice", "correct_alternative_ids": list(ids)}


def _provider_eligible(item: DigiExamIrItem) -> bool:
    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        return False
    if item.warnings and any(warning.blocking for warning in item.warnings):
        return False
    return not (item.embedded_asset_references or item.embedded_assets)


def _gap_fill_plan(
    *,
    job_id: str,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamCompletionCandidatePlan | None:
    if not item.gaps or any(not gap.guid.strip() for gap in item.gaps):
        return None
    request = _request(
        job_id=job_id,
        item=item,
        prompt_template_version=GAP_FILL_PROMPT_TEMPLATE_VERSION,
        output_spec=_gap_fill_output_spec(),
        user_payload=_gap_fill_payload(item),
        profile=profile,
    )
    return DigiExamCompletionCandidatePlan(
        item=item,
        request=request,
        provider_profile=profile,
        decoder=_JsonSchemaAnswerKeyResponseDecoder(),
    )


def _choice_payload(item: DigiExamIrItem) -> dict[str, object]:
    alternative_ids = _alternative_ids(item)
    maximum_answers = (
        len(alternative_ids) if item.item_type == DigiExamItemType.MULTIPLE_RESPONSE else 1
    )
    return {
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


def _gap_fill_payload(item: DigiExamIrItem) -> dict[str, object]:
    interaction = build_exam_authoring_gap_open_cloze_interaction_from_digiexam_item(item)
    return {
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


def _choice_decision_output_spec() -> StructuredOutputSpec:
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


def _vllm_choice_output_spec(choice_values: tuple[str, ...]) -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"choice": {"type": "string", "enum": list(choice_values)}},
            "required": ["choice"],
        },
        choice_values=choice_values,
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


def _alternative_ids(item: DigiExamIrItem) -> tuple[int, ...]:
    ids = tuple(alternative.id for alternative in item.alternatives)
    if not ids or len(set(ids)) != len(ids):
        return ()
    return ids


def _vllm_choice_values(item: DigiExamIrItem, *, max_values: int) -> tuple[str, ...]:
    alternative_ids = _alternative_ids(item)
    if item.item_type != DigiExamItemType.MULTIPLE_RESPONSE:
        return tuple(_encode_choice_value((alternative_id,)) for alternative_id in alternative_ids)
    combinations: list[str] = []
    for size in range(1, len(alternative_ids) + 1):
        for selected_ids in itertools.combinations(alternative_ids, size):
            combinations.append(_encode_choice_value(selected_ids))
            if len(combinations) > max_values:
                return ()
    return tuple(combinations)


def _encode_choice_value(alternative_ids: tuple[int, ...]) -> str:
    return ",".join(str(alternative_id) for alternative_id in alternative_ids)


def _decode_choice_value(value: str) -> tuple[int, ...]:
    ids: list[int] = []
    for part in value.split(","):
        if not part.isdecimal():
            return ()
        ids.append(int(part))
    return tuple(ids)


def _json_schema_profile(
    profile: StructuredLLMProviderProfile | None,
) -> StructuredLLMProviderProfile | None:
    if profile is None or profile.output_mode == StructuredLLMOutputMode.JSON_SCHEMA:
        return profile
    if profile.output_mode == StructuredLLMOutputMode.VLLM_JSON_SCHEMA:
        return profile
    if profile.endpoint_kind == StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS:
        return _vllm_json_schema_profile(profile)
    return replace(profile, output_mode=StructuredLLMOutputMode.JSON_SCHEMA)


def _vllm_choice_profile(
    profile: StructuredLLMProviderProfile | None,
) -> StructuredLLMProviderProfile | None:
    if profile is None:
        return None
    return replace(profile, output_mode=StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE)


def _vllm_json_schema_profile(
    profile: StructuredLLMProviderProfile | None,
) -> StructuredLLMProviderProfile | None:
    if profile is None:
        return None
    return replace(profile, output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA)


_CHOICE_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
