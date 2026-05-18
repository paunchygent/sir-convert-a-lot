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

import json
from dataclasses import dataclass, replace
from typing import Protocol

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS,
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_gbnf import (
    choice_answer_key_decision_gbnf,
    numbered_gap_fill_answer_key_gbnf,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_model_projection import (
    choice_answer_key_model_payload,
    gap_fill_answer_key_model_payload,
    system_prompt_for_answer_key_item,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_output_specs import (
    choice_decision_output_spec,
    decode_choice_value,
    numbered_gap_fill_output_spec,
    valid_alternative_ids,
    vllm_choice_output_spec,
    vllm_choice_values,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_payloads import (
    answer_payload_from_model_content,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem
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
    if (
        profile is not None
        and profile.endpoint_kind == StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS
    ):
        return LlamaCppAnswerKeyCandidatePlanner()
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

        if not _provider_eligible_for_profile(item=item, profile=profile):
            return None
        if item.item_type in _CHOICE_TYPES:
            if not valid_alternative_ids(item):
                return None
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
                output_spec=choice_decision_output_spec(),
                user_payload=choice_answer_key_model_payload(
                    item,
                    provider_output_mode=_provider_output_mode_label(_json_schema_profile(profile)),
                ),
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

    max_multiple_response_choice_values: int = 512

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build one vLLM interaction using choice rows where possible."""

        if not _provider_eligible_for_profile(item=item, profile=profile):
            return None
        if item.item_type in _CHOICE_TYPES:
            values = vllm_choice_values(
                item,
                max_values=self.max_multiple_response_choice_values,
            )
            if not values:
                return None
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
                output_spec=vllm_choice_output_spec(values),
                user_payload=choice_answer_key_model_payload(
                    item,
                    provider_output_mode="vllm_structured_choice",
                ),
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


@dataclass(frozen=True)
class LlamaCppAnswerKeyCandidatePlanner:
    """llama.cpp planner restricted to JSON Schema or GBNF-constrained JSON."""

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build one llama.cpp interaction using constrained JSON output only."""

        llama_profile = _llama_cpp_profile(profile)
        if not _provider_eligible_for_profile(item=item, profile=llama_profile):
            return None
        if item.item_type in _CHOICE_TYPES:
            if not valid_alternative_ids(item):
                return None
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
                output_spec=_with_llama_cpp_grammar(
                    choice_decision_output_spec(),
                    profile=llama_profile,
                    gbnf_grammar=choice_answer_key_decision_gbnf(),
                ),
                user_payload=choice_answer_key_model_payload(
                    item,
                    provider_output_mode=_provider_output_mode_label(llama_profile),
                ),
                profile=llama_profile,
            )
            return DigiExamCompletionCandidatePlan(
                item=item,
                request=request,
                provider_profile=llama_profile,
                decoder=_JsonSchemaAnswerKeyResponseDecoder(),
            )
        if item.item_type == DigiExamItemType.GAP_FILL:
            return _gap_fill_plan(job_id=job_id, item=item, profile=llama_profile)
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
        ids = decode_choice_value(selected_value.strip())
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
    return _provider_eligible_for_profile(item=item, profile=None)


def _provider_eligible_for_profile(
    *,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile | None,
) -> bool:
    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        return False
    if item.warnings and any(warning.blocking for warning in item.warnings):
        return False
    if not (item.embedded_asset_references or item.embedded_assets):
        return True
    return profile is not None and profile.capabilities.supports_multimodal_vision


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
        output_spec=_with_llama_cpp_grammar(
            numbered_gap_fill_output_spec(len(item.gaps)),
            profile=profile,
            gbnf_grammar=numbered_gap_fill_answer_key_gbnf(len(item.gaps)),
        ),
        user_payload=gap_fill_answer_key_model_payload(
            item,
            provider_output_mode=_provider_output_mode_label(profile),
        ),
        profile=profile,
    )
    return DigiExamCompletionCandidatePlan(
        item=item,
        request=request,
        provider_profile=profile,
        decoder=_JsonSchemaAnswerKeyResponseDecoder(),
    )


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
    system_prompt = system_prompt_for_answer_key_item(item.item_type)
    max_output_tokens = (
        profile.max_output_tokens
        if profile is not None
        else ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS
    )
    return StructuredLLMRequest(
        job_id=job_id,
        item_id=item.item_id,
        item_type=item.item_type.value,
        prompt_template_version=prompt_template_version,
        system_prompt=system_prompt,
        user_payload=user_payload_text,
        output_spec=output_spec,
        estimated_input_tokens=(
            _estimate_tokens(system_prompt) + _estimate_tokens(user_payload_text)
        ),
        max_output_tokens=max_output_tokens,
        allow_remote_fallback=False,
    )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _json_schema_profile(
    profile: StructuredLLMProviderProfile | None,
) -> StructuredLLMProviderProfile | None:
    if profile is None or profile.output_mode == StructuredLLMOutputMode.JSON_SCHEMA:
        return profile
    if profile.output_mode == StructuredLLMOutputMode.JSON_OBJECT:
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


def _llama_cpp_profile(
    profile: StructuredLLMProviderProfile | None,
) -> StructuredLLMProviderProfile | None:
    if profile is None:
        return None
    if profile.output_mode in {
        StructuredLLMOutputMode.JSON_SCHEMA,
        StructuredLLMOutputMode.GBNF,
    }:
        return profile
    return replace(profile, output_mode=StructuredLLMOutputMode.JSON_SCHEMA)


def _with_llama_cpp_grammar(
    output_spec: StructuredOutputSpec,
    *,
    profile: StructuredLLMProviderProfile | None,
    gbnf_grammar: str,
) -> StructuredOutputSpec:
    if (
        profile is not None
        and profile.endpoint_kind == StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS
        and profile.output_mode == StructuredLLMOutputMode.GBNF
    ):
        return replace(output_spec, gbnf_grammar=gbnf_grammar)
    return output_spec


def _provider_output_mode_label(profile: StructuredLLMProviderProfile | None) -> str:
    if profile is None:
        return "json_schema"
    if profile.endpoint_kind == StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS:
        return profile.output_mode.value
    if (
        profile.endpoint_kind == StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS
        and profile.output_mode == StructuredLLMOutputMode.GBNF
    ):
        return "llama_cpp_gbnf_json"
    if profile.endpoint_kind == StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS:
        return "llama_cpp_json_schema"
    return profile.output_mode.value


_CHOICE_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
