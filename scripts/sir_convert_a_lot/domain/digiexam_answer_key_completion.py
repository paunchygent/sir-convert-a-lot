"""DigiExam advisory answer-key completion orchestration.

Purpose:
    Run item-local structured LLM answer-key suggestions for missing DigiExam
    machine-marked keys and validate them into an advisory completion report
    without mutating source IR, effective IR, PDF, or QTI output.

Relationships:
    - Consumes candidate requests from
      `domain.digiexam_answer_key_completion_candidates`.
    - Uses Task 296 provider contracts from `domain.structured_llm_contracts`.
    - Emits report contracts from
      `domain.digiexam_answer_key_completion_contracts` for later teacher
      review and Task 306 application.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    candidate_request_for_item,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    ANSWER_KEY_COMPLETION_SAFETY_MARGIN_TOKENS,
    DigiExamAnswerKeyCompletionDecisionState,
    DigiExamAnswerKeyCompletionFailureCode,
    DigiExamAnswerKeyCompletionReport,
    DigiExamAnswerKeyCompletionReportItem,
    DigiExamAnswerKeyCompletionValidationState,
    completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderProtocol,
    StructuredChatProviderSet,
    StructuredLLMBackendFailureCode,
    StructuredLLMCaptureStatus,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMRouteDecision,
    StructuredLLMRoutePolicy,
    StructuredLLMRouteReason,
    decide_structured_llm_route,
    preflight_structured_llm_prompt,
    resolve_structured_llm_token_budget,
)


async def build_digiexam_answer_key_completion_report(
    *,
    job_id: str,
    completion_mode: str,
    exam: DigiExamIntermediateExam,
    provider_set: StructuredChatProviderSet | None,
    route_policy: StructuredLLMRoutePolicy,
    provider: StructuredChatProviderProtocol | None,
) -> DigiExamAnswerKeyCompletionReport:
    """Build advisory answer-key candidates for one effective DigiExam exam."""

    route_decision = _route_decision(provider_set=provider_set, route_policy=route_policy)
    rows: list[DigiExamAnswerKeyCompletionReportItem] = []
    for item in exam.items:
        profile = _selected_profile(provider_set=provider_set, route_decision=route_decision)
        candidate = candidate_request_for_item(job_id=job_id, item=item, profile=profile)
        if candidate is None:
            rows.append(_non_provider_entry(item, profile=profile))
            continue
        if profile is None or provider is None:
            rows.append(
                _manual_entry(
                    item=item,
                    request=candidate.request,
                    profile=profile,
                    failure_code=DigiExamAnswerKeyCompletionFailureCode.PROVIDER_CONFIG_MISSING,
                )
            )
            continue
        if route_decision.blocked:
            rows.append(
                _manual_entry(
                    item=item,
                    request=candidate.request,
                    profile=profile,
                    failure_code=DigiExamAnswerKeyCompletionFailureCode.PROVIDER_ROUTE_BLOCKED,
                    backend_status=route_decision.reason.value,
                )
            )
            continue
        rows.append(await _provider_entry(candidate.request, item, profile, provider))

    return completion_report(
        job_id=job_id,
        completion_mode=completion_mode,
        items=tuple(rows),
    )


async def _provider_entry(
    request: StructuredLLMRequest,
    item: DigiExamIrItem,
    profile: StructuredLLMProviderProfile,
    provider: StructuredChatProviderProtocol,
) -> DigiExamAnswerKeyCompletionReportItem:
    budget = resolve_structured_llm_token_budget(
        profile=profile,
        requested_max_output_tokens=request.max_output_tokens,
        safety_margin_tokens=ANSWER_KEY_COMPLETION_SAFETY_MARGIN_TOKENS,
    )
    preflight = preflight_structured_llm_prompt(request=request, budget=budget)
    if not preflight.fits:
        return _manual_entry(
            item=item,
            request=request,
            profile=profile,
            failure_code=DigiExamAnswerKeyCompletionFailureCode.OVER_BUDGET,
        )
    try:
        response = await provider.complete_structured_chat(request=request, profile=profile)
    except StructuredLLMProviderError as exc:
        return _manual_entry(
            item=item,
            request=request,
            profile=profile,
            failure_code=exc.failure_code,
        )
    return _response_entry(item=item, request=request, profile=profile, response=response)


def _route_decision(
    *,
    provider_set: StructuredChatProviderSet | None,
    route_policy: StructuredLLMRoutePolicy,
) -> StructuredLLMRouteDecision:
    if provider_set is None:
        return StructuredLLMRouteDecision(
            provider_slot=None,
            provider_id=None,
            reason=StructuredLLMRouteReason.NO_FALLBACK_CONFIGURED,
        )
    return decide_structured_llm_route(
        provider_set=provider_set,
        policy=route_policy,
        primary_available=True,
        fallback_available=provider_set.fallback is not None,
    )


def _selected_profile(
    *,
    provider_set: StructuredChatProviderSet | None,
    route_decision: StructuredLLMRouteDecision,
) -> StructuredLLMProviderProfile | None:
    if provider_set is None:
        return None
    if route_decision.provider_slot == "fallback":
        return provider_set.fallback
    return provider_set.primary


def _response_entry(
    *,
    item: DigiExamIrItem,
    request: StructuredLLMRequest,
    profile: StructuredLLMProviderProfile,
    response: StructuredLLMResponse,
) -> DigiExamAnswerKeyCompletionReportItem:
    answer_payload = _validated_answer_payload(item=item, content=response.content)
    if answer_payload is None:
        return _manual_entry(
            item=item,
            request=request,
            profile=profile,
            failure_code=DigiExamAnswerKeyCompletionFailureCode.LLM_OUTPUT_INVALID,
        )
    digest = _digest_payload(answer_payload)
    return DigiExamAnswerKeyCompletionReportItem(
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type.value,
        decision_state=DigiExamAnswerKeyCompletionDecisionState.SUGGESTED,
        validation_state=DigiExamAnswerKeyCompletionValidationState.VALID,
        candidate_id=f"{item.item_id}:{digest.removeprefix('sha256:')[:16]}",
        candidate_payload_digest=digest,
        answer_payload=answer_payload,
        provider_profile_id=profile.provider_id,
        model_profile=profile.model,
        schema_name=request.output_spec.schema_name,
        schema_version=request.output_spec.schema_version,
        prompt_template_version=request.prompt_template_version,
        backend_status=StructuredLLMCaptureStatus.SUCCESS.value,
        backend_failure_code=None,
    )


def _validated_answer_payload(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    decision_state = _string(content.get("decision_state"))
    manual_code = _string(content.get("manual_follow_up_code"))
    if decision_state != "answered" or manual_code is not None:
        return None
    if item.item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        return _validated_choice_payload(item=item, content=content)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return _validated_gap_payload(item=item, content=content)
    return None


def _validated_choice_payload(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    ids = _int_tuple(content.get("correct_alternative_ids"))
    if not ids or len(set(ids)) != len(ids):
        return None
    valid_ids = {alternative.id for alternative in item.alternatives}
    if any(alternative_id not in valid_ids for alternative_id in ids):
        return None
    if item.item_type != DigiExamItemType.MULTIPLE_RESPONSE and len(ids) != 1:
        return None
    return {"kind": "choice", "correct_alternative_ids": list(ids)}


def _validated_gap_payload(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    raw_gap_answers = content.get("gap_answers")
    if not isinstance(raw_gap_answers, list) or not raw_gap_answers:
        return None
    valid_gap_ids = {gap.guid for gap in item.gaps}
    seen_gap_ids: set[str] = set()
    gap_answers: list[JsonValue] = []
    for raw_answer in raw_gap_answers:
        if not isinstance(raw_answer, dict):
            return None
        gap_id = _string(raw_answer.get("gap_id"))
        accepted_values = _string_tuple(raw_answer.get("accepted_values"))
        if gap_id is None or gap_id not in valid_gap_ids or gap_id in seen_gap_ids:
            return None
        normalized_values = tuple(value.strip() for value in accepted_values)
        if not normalized_values or any(not value for value in normalized_values):
            return None
        if len(set(normalized_values)) != len(normalized_values):
            return None
        seen_gap_ids.add(gap_id)
        gap_answers.append({"gap_id": gap_id, "accepted_values": list(normalized_values)})
    if seen_gap_ids != valid_gap_ids:
        return None
    return {"kind": "gap_fill", "gap_answers": gap_answers}


def _manual_entry(
    *,
    item: DigiExamIrItem,
    request: StructuredLLMRequest,
    profile: StructuredLLMProviderProfile | None,
    failure_code: DigiExamAnswerKeyCompletionFailureCode | StructuredLLMBackendFailureCode,
    backend_status: str = StructuredLLMCaptureStatus.MANUAL_FOLLOW_UP_REQUIRED.value,
) -> DigiExamAnswerKeyCompletionReportItem:
    return DigiExamAnswerKeyCompletionReportItem(
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type.value,
        decision_state=DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED,
        validation_state=DigiExamAnswerKeyCompletionValidationState.MANUAL_FOLLOW_UP_REQUIRED,
        candidate_id=None,
        candidate_payload_digest=None,
        answer_payload=None,
        provider_profile_id=profile.provider_id if profile is not None else None,
        model_profile=profile.model if profile is not None else None,
        schema_name=request.output_spec.schema_name,
        schema_version=request.output_spec.schema_version,
        prompt_template_version=request.prompt_template_version,
        backend_status=backend_status,
        backend_failure_code=failure_code.value,
    )


def _non_provider_entry(
    item: DigiExamIrItem,
    *,
    profile: StructuredLLMProviderProfile | None,
) -> DigiExamAnswerKeyCompletionReportItem:
    failure_code = _non_provider_failure_code(item)
    state = (
        DigiExamAnswerKeyCompletionDecisionState.SKIPPED
        if failure_code == DigiExamAnswerKeyCompletionFailureCode.SOURCE_BOUND_ANSWER_KEY_EXISTS
        else DigiExamAnswerKeyCompletionDecisionState.MANUAL_FOLLOW_UP_REQUIRED
    )
    validation = (
        DigiExamAnswerKeyCompletionValidationState.SKIPPED
        if state == DigiExamAnswerKeyCompletionDecisionState.SKIPPED
        else DigiExamAnswerKeyCompletionValidationState.MANUAL_FOLLOW_UP_REQUIRED
    )
    return DigiExamAnswerKeyCompletionReportItem(
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type.value,
        decision_state=state,
        validation_state=validation,
        candidate_id=None,
        candidate_payload_digest=None,
        answer_payload=None,
        provider_profile_id=profile.provider_id if profile is not None else None,
        model_profile=profile.model if profile is not None else None,
        schema_name=None,
        schema_version=None,
        prompt_template_version=None,
        backend_status=state.value,
        backend_failure_code=failure_code.value,
    )


def _non_provider_failure_code(item: DigiExamIrItem) -> DigiExamAnswerKeyCompletionFailureCode:
    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        return DigiExamAnswerKeyCompletionFailureCode.SOURCE_BOUND_ANSWER_KEY_EXISTS
    if item.warnings and any(warning.blocking for warning in item.warnings):
        return DigiExamAnswerKeyCompletionFailureCode.UNRELIABLE_STRUCTURE
    if item.embedded_asset_references or item.embedded_assets:
        return DigiExamAnswerKeyCompletionFailureCode.UNSUPPORTED_ASSETS
    if item.item_type not in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    }:
        return DigiExamAnswerKeyCompletionFailureCode.UNSUPPORTED_ITEM_TYPE
    return DigiExamAnswerKeyCompletionFailureCode.MISSING_CANDIDATE_STRUCTURE


def _digest_payload(payload: dict[str, JsonValue]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: JsonValue) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    integers: list[int] = []
    for entry in value:
        if not isinstance(entry, int) or isinstance(entry, bool):
            return ()
        integers.append(entry)
    return tuple(integers)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    strings: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            return ()
        strings.append(entry)
    return tuple(strings)
