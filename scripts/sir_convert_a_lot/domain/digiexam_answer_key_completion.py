"""DigiExam advisory answer-key completion orchestration.

Purpose:
    Run item-local structured LLM answer-key suggestions for missing DigiExam
    machine-marked keys and validate them into an advisory completion report
    without mutating source IR, effective IR, PDF, or QTI output.

Relationships:
    - Consumes candidate requests from
      `domain.digiexam_answer_key_completion_candidates`.
    - Uses structured LLM provider harness provider contracts from
    `domain.structured_llm_contracts`.
    - Emits report contracts from
      `domain.digiexam_answer_key_completion_contracts` for later teacher
      review and Markdown to DOCX route6 application.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.answer_key_token_lease_contracts import (
    AnswerKeyTokenLeaseError,
)
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
from scripts.sir_convert_a_lot.domain.structured_llm_admission import (
    StructuredLLMAdmittedRouteSnapshot,
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
from scripts.sir_convert_a_lot.domain.structured_llm_provider_diagnostics import (
    StructuredLLMProviderErrorDiagnostic,
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
    admitted_route: StructuredLLMAdmittedRouteSnapshot | None = None,
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
        rows.append(
            await _provider_entry(
                candidate=candidate,
                provider=provider,
                provider_set=provider_set,
                route_policy=route_policy,
            )
        )

    return completion_report(
        job_id=job_id,
        completion_mode=completion_mode,
        items=tuple(rows),
        provider_lineage=admitted_route,
    )


async def _provider_entry(
    candidate: DigiExamCompletionCandidatePlan,
    provider: StructuredChatProviderProtocol,
    provider_set: StructuredChatProviderSet | None,
    route_policy: StructuredLLMRoutePolicy,
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
    preflight_failure = _preflight_failure(candidate)
    if preflight_failure is not None:
        return preflight_failure
    try:
        response = await provider.complete_structured_chat(request=request, profile=profile)
    except AnswerKeyTokenLeaseError as exc:
        return _lease_error_entry(candidate=candidate, error=exc)
    except StructuredLLMProviderError as exc:
        if not _allows_provider_failover(exc) or provider_set is None:
            return _provider_error_entry(candidate=candidate, error=exc)
        return await _fallback_entry(
            primary_failure=exc,
            primary_candidate=candidate,
            provider=provider,
            provider_set=provider_set,
            route_policy=route_policy,
        )
    return _response_entry(candidate=candidate, profile=profile, response=response)


async def _fallback_entry(
    *,
    primary_failure: StructuredLLMProviderError,
    primary_candidate: DigiExamCompletionCandidatePlan,
    provider: StructuredChatProviderProtocol,
    provider_set: StructuredChatProviderSet,
    route_policy: StructuredLLMRoutePolicy,
) -> DigiExamAnswerKeyCompletionReportItem:
    """Attempt the configured fallback once after an eligible primary outage."""

    route = decide_structured_llm_route(
        provider_set=provider_set,
        policy=route_policy,
        primary_available=False,
        fallback_available=provider_set.fallback is not None,
    )
    fallback = provider_set.fallback
    if route.provider_slot != "fallback" or fallback is None:
        return _provider_error_entry(candidate=primary_candidate, error=primary_failure)
    fallback_candidate = answer_key_candidate_planner_for_profile(fallback).plan_candidate(
        job_id=primary_candidate.request.job_id,
        item=primary_candidate.item,
        profile=fallback,
    )
    if fallback_candidate is None:
        return _provider_error_entry(candidate=primary_candidate, error=primary_failure)
    preflight_failure = _preflight_failure(fallback_candidate)
    if preflight_failure is not None:
        return preflight_failure
    try:
        response = await provider.complete_structured_chat(
            request=fallback_candidate.request,
            profile=fallback,
        )
    except AnswerKeyTokenLeaseError as exc:
        return _lease_error_entry(candidate=fallback_candidate, error=exc)
    except StructuredLLMProviderError as exc:
        return _provider_error_entry(candidate=fallback_candidate, error=exc)
    return _response_entry(candidate=fallback_candidate, profile=fallback, response=response)


def _preflight_failure(
    candidate: DigiExamCompletionCandidatePlan,
) -> DigiExamAnswerKeyCompletionReportItem | None:
    """Return a terminal report row when this profile cannot fit the request."""

    profile = candidate.provider_profile
    if profile is None:
        return _manual_entry(
            item=candidate.item,
            request=candidate.request,
            profile=profile,
            failure_code=DigiExamAnswerKeyCompletionFailureCode.PROVIDER_CONFIG_MISSING,
        )
    budget = resolve_structured_llm_token_budget(
        profile=profile,
        requested_max_output_tokens=candidate.request.max_output_tokens,
        safety_margin_tokens=ANSWER_KEY_COMPLETION_SAFETY_MARGIN_TOKENS,
    )
    preflight = preflight_structured_llm_prompt(request=candidate.request, budget=budget)
    if preflight.fits:
        return None
    return _manual_entry(
        item=candidate.item,
        request=candidate.request,
        profile=profile,
        failure_code=DigiExamAnswerKeyCompletionFailureCode.OVER_BUDGET,
    )


def _allows_provider_failover(error: StructuredLLMProviderError) -> bool:
    """Limit fallback execution to transient provider outages only."""

    if error.failure_code in {
        StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
        StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
    }:
        return True
    return (
        error.failure_code == StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR
        and error.status_code is not None
        and (error.status_code == 408 or 500 <= error.status_code <= 599)
    )


def _lease_error_entry(
    *,
    candidate: DigiExamCompletionCandidatePlan,
    error: AnswerKeyTokenLeaseError,
) -> DigiExamAnswerKeyCompletionReportItem:
    """Project a typed lease refusal without emitting storage or provider data."""

    return _manual_entry(
        item=candidate.item,
        request=candidate.request,
        profile=candidate.provider_profile,
        failure_code=DigiExamAnswerKeyCompletionFailureCode(error.failure_code.value),
    )


def _provider_error_entry(
    *,
    candidate: DigiExamCompletionCandidatePlan,
    error: StructuredLLMProviderError,
) -> DigiExamAnswerKeyCompletionReportItem:
    """Project one terminal provider failure into the advisory report."""

    return _manual_entry(
        item=candidate.item,
        request=candidate.request,
        profile=candidate.provider_profile,
        failure_code=error.failure_code,
        provider_error_diagnostic=error.diagnostic,
    )


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
        provider_error_diagnostic=None,
    )


def _manual_entry(
    *,
    item: DigiExamIrItem,
    request: StructuredLLMRequest,
    profile: StructuredLLMProviderProfile | None,
    failure_code: DigiExamAnswerKeyCompletionFailureCode | StructuredLLMBackendFailureCode,
    backend_status: str = StructuredLLMCaptureStatus.MANUAL_FOLLOW_UP_REQUIRED.value,
    provider_error_diagnostic: StructuredLLMProviderErrorDiagnostic | None = None,
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
        provider_error_diagnostic=provider_error_diagnostic,
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
        provider_error_diagnostic=None,
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
