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

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    DigiExamAnswerKeyCandidatePlannerProtocol,
    DigiExamCompletionCandidatePlan,
    answer_key_candidate_planner_for_profile,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    ANSWER_KEY_COMPLETION_SAFETY_MARGIN_TOKENS,
    DigiExamAnswerKeyCompletionDecisionState,
    DigiExamAnswerKeyCompletionFailureCode,
    DigiExamAnswerKeyCompletionReport,
    DigiExamAnswerKeyCompletionReportItem,
    DigiExamAnswerKeyCompletionValidationState,
    answer_key_candidate_payload_digest,
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
    candidate_planner: DigiExamAnswerKeyCandidatePlannerProtocol | None = None,
) -> DigiExamAnswerKeyCompletionReport:
    """Build advisory answer-key candidates for one effective DigiExam exam."""

    route_decision = _route_decision(provider_set=provider_set, route_policy=route_policy)
    rows: list[DigiExamAnswerKeyCompletionReportItem] = []
    for item in exam.items:
        profile = _selected_profile(provider_set=provider_set, route_decision=route_decision)
        planner = candidate_planner or answer_key_candidate_planner_for_profile(profile)
        candidate = planner.plan_candidate(job_id=job_id, item=item, profile=profile)
        if candidate is None:
            rows.append(_non_provider_entry(item, profile=profile))
            continue
        provider_profile = candidate.provider_profile
        if provider_profile is None or provider is None:
            rows.append(
                _manual_entry(
                    item=item,
                    request=candidate.request,
                    profile=provider_profile,
                    failure_code=DigiExamAnswerKeyCompletionFailureCode.PROVIDER_CONFIG_MISSING,
                )
            )
            continue
        if route_decision.blocked:
            rows.append(
                _manual_entry(
                    item=item,
                    request=candidate.request,
                    profile=provider_profile,
                    failure_code=DigiExamAnswerKeyCompletionFailureCode.PROVIDER_ROUTE_BLOCKED,
                    backend_status=route_decision.reason.value,
                )
            )
            continue
        rows.append(await _provider_entry(candidate, provider))

    return completion_report(
        job_id=job_id,
        completion_mode=completion_mode,
        items=tuple(rows),
    )


async def _provider_entry(
    candidate: DigiExamCompletionCandidatePlan,
    provider: StructuredChatProviderProtocol,
) -> DigiExamAnswerKeyCompletionReportItem:
    request = candidate.request
    item = candidate.item
    profile = candidate.provider_profile
    if profile is None:
        return _manual_entry(
            item=item,
            request=request,
            profile=profile,
            failure_code=DigiExamAnswerKeyCompletionFailureCode.PROVIDER_CONFIG_MISSING,
        )
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
    return _response_entry(candidate=candidate, profile=profile, response=response)


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
    candidate: DigiExamCompletionCandidatePlan,
    profile: StructuredLLMProviderProfile,
    response: StructuredLLMResponse,
) -> DigiExamAnswerKeyCompletionReportItem:
    item = candidate.item
    request = candidate.request
    answer_payload = candidate.decoder.decode(item=item, response=response)
    if answer_payload is None:
        return _manual_entry(
            item=item,
            request=request,
            profile=profile,
            failure_code=DigiExamAnswerKeyCompletionFailureCode.LLM_OUTPUT_INVALID,
        )
    digest = answer_key_candidate_payload_digest(answer_payload)
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
