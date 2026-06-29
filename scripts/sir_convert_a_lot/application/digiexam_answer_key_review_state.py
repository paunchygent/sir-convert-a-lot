"""Compact DigiExam answer-key review-state projection.

Purpose:
    Build the Sir Convert-owned item review-state surface consumed by
    Skriptoteket after first-pass DigiExam migration and correction replay.

Relationships:
    - Consumes sanitized exam-authoring source/effective state DTOs instead of
      raw DigiExam, provider, correction-session, or identity payloads.
    - Shares one projection builder across migration bundle artifacts and the
      source-neutral correction apply result.
    - Keeps target export readiness separate by only copying replay artifact
      references after target rendering has actually produced replay artifacts.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state_models import (
    DigiExamAnswerKeyCorrectionAffordanceV1,
    DigiExamAnswerKeyOriginCodeV1,
    DigiExamAnswerKeyReviewAdvisoryCandidateInput,
    DigiExamAnswerKeyReviewCorrectionOutcomeInput,
    DigiExamAnswerKeyReviewProvenanceDetailV1,
    DigiExamAnswerKeyReviewReasonCodeV1,
    DigiExamAnswerKeyReviewReplayArtifactReferenceV1,
    DigiExamAnswerKeyReviewStateCodeV1,
    DigiExamAnswerKeyReviewStateItemV1,
    DigiExamAnswerKeyReviewStateV1,
    DigiExamAnswerKeyReviewSubmissionOriginV1,
    DigiExamAnswerKeyReviewTargetReadinessInput,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringAnswerKeyProvenanceV1,
    ExamAuthoringChoiceInteractionV1,
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringCorrectionSourceStateV1,
    ExamAuthoringGapOpenClozeInteractionV1,
)


def build_digiexam_answer_key_review_state(
    *,
    source_state: ExamAuthoringCorrectionSourceStateV1,
    advisory_candidates: tuple[DigiExamAnswerKeyReviewAdvisoryCandidateInput, ...] = (),
    correction_outcomes: tuple[DigiExamAnswerKeyReviewCorrectionOutcomeInput, ...] = (),
    target_readiness: tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...] = (),
    include_advisory_provenance_detail: bool = False,
) -> DigiExamAnswerKeyReviewStateV1:
    """Build the compact item review-state projection from producer-owned state."""

    advisory_by_item = {
        (candidate.item_id, candidate.sequence): candidate
        for candidate in advisory_candidates
        if candidate.validation_state == "valid"
    }
    accepted_by_item = _accepted_correction_origin_by_item(correction_outcomes)
    rejected_items = {
        (outcome.item_id, outcome.sequence)
        for outcome in correction_outcomes
        if not outcome.accepted
    }
    target_rows_by_item = _target_rows_by_item(target_readiness)
    return DigiExamAnswerKeyReviewStateV1(
        items=tuple(
            _item_projection(
                item=item,
                advisory=advisory_by_item.get((item.item_id, item.sequence)),
                accepted_origin=accepted_by_item.get((item.item_id, item.sequence)),
                has_rejected_correction=(item.item_id, item.sequence) in rejected_items,
                target_rows=target_rows_by_item.get((item.item_id, item.sequence), ()),
                include_advisory_provenance_detail=include_advisory_provenance_detail,
            )
            for item in source_state.items
        )
    )


def attach_digiexam_answer_key_review_replay_references(
    *,
    report: DigiExamAnswerKeyReviewStateV1,
    target_readiness: tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...],
) -> DigiExamAnswerKeyReviewStateV1:
    """Copy replay-scoped artifact references into an existing projection."""

    rows_by_item = _target_rows_by_item(target_readiness)
    return report.model_copy(
        update={
            "items": tuple(
                item.model_copy(
                    update={
                        "replay_artifact_references": _replay_references(
                            rows_by_item.get((item.item_id, item.sequence), ())
                        )
                    }
                )
                for item in report.items
            )
        }
    )


def _item_projection(
    *,
    item: ExamAuthoringCorrectionSourceItemV1,
    advisory: DigiExamAnswerKeyReviewAdvisoryCandidateInput | None,
    accepted_origin: DigiExamAnswerKeyReviewSubmissionOriginV1 | None,
    has_rejected_correction: bool,
    target_rows: tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...],
    include_advisory_provenance_detail: bool,
) -> DigiExamAnswerKeyReviewStateItemV1:
    origin = _current_origin(item)
    reasons = list(_base_reasons(item=item, origin=origin, advisory=advisory))
    if accepted_origin is not None:
        origin = _origin_for_accepted_correction(accepted_origin)
        reasons = [_reason_for_accepted_correction(accepted_origin)]
    if has_rejected_correction:
        _append_unique(reasons, "correction_rejected")
    for row in target_rows:
        mapped_reason = _target_reason(row)
        if mapped_reason is not None:
            if "answer_key_not_applicable" in reasons and mapped_reason == "manual_answer_key_required":
                continue
            if (
                advisory is not None
                and origin == "none"
                and mapped_reason == "manual_answer_key_required"
            ):
                continue
            _append_unique(reasons, mapped_reason)
    if not reasons:
        reasons.append("unsupported_item_type")
    review_state = _review_state(origin=origin, reasons=tuple(reasons), advisory=advisory)
    return DigiExamAnswerKeyReviewStateItemV1(
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type,
        source_item_fingerprint=item.source_item_fingerprint,
        choice_interaction_ids=tuple(
            interaction.interaction_id for interaction in item.choice_interactions
        ),
        choice_ids=tuple(
            choice.choice_id
            for interaction in item.choice_interactions
            for choice in interaction.choices
        ),
        gap_interaction_ids=tuple(
            interaction.interaction_id for interaction in item.gap_open_cloze_interactions
        ),
        gap_ids=tuple(
            gap.gap_id
            for interaction in item.gap_open_cloze_interactions
            for gap in interaction.gaps
        ),
        correction_affordances=_correction_affordances(item),
        review_state=review_state,
        current_key_origin=origin,
        reasons=tuple(reasons),
        message_key=f"exam_converter.answer_key_review.{reasons[0]}",
        provenance_detail=(
            _provenance_detail(advisory)
            if include_advisory_provenance_detail
            and advisory is not None
            and origin == "none"
            and "advisory_candidate_pending" in reasons
            else None
        ),
        replay_artifact_references=_replay_references(target_rows),
    )


def _base_reasons(
    *,
    item: ExamAuthoringCorrectionSourceItemV1,
    origin: DigiExamAnswerKeyOriginCodeV1,
    advisory: DigiExamAnswerKeyReviewAdvisoryCandidateInput | None,
) -> tuple[DigiExamAnswerKeyReviewReasonCodeV1, ...]:
    if not _answer_key_applicable(item):
        return ("answer_key_not_applicable",)
    if advisory is not None and origin == "none" and _advisory_reviewable(item):
        return ("advisory_candidate_pending",)
    if origin == "source_provided":
        return ("source_answer_key_present",)
    if origin == "reviewed_advisory":
        return ("reviewed_advisory_accepted",)
    if origin in {"teacher_authored", "mixed"}:
        return ("teacher_answer_key_present",)
    if _missing_choice_key(item):
        return ("no_correct_choice_selected",)
    if _missing_gap_values(item):
        return ("required_gap_accepted_values_missing",)
    if _answer_key_applicable(item):
        return ("manual_answer_key_required",)
    return ("answer_key_not_applicable",)


def _current_origin(item: ExamAuthoringCorrectionSourceItemV1) -> DigiExamAnswerKeyOriginCodeV1:
    origins: set[DigiExamAnswerKeyOriginCodeV1] = set()
    for choice_interaction in item.choice_interactions:
        origins.add(_origin_for_provenance(choice_interaction.answer_key.provenance))
    for gap_interaction in item.gap_open_cloze_interactions:
        origins.add(_origin_for_gap_interaction(gap_interaction))
    for matching_interaction in item.matching_interactions:
        origins.add(_origin_for_provenance(matching_interaction.answer_key.provenance))
    origins.discard("none")
    if not origins:
        return "none"
    if len(origins) == 1:
        return next(iter(origins))
    return "mixed"


def _origin_for_gap_interaction(
    interaction: ExamAuthoringGapOpenClozeInteractionV1,
) -> DigiExamAnswerKeyOriginCodeV1:
    if interaction.answer_key.provenance == "mixed":
        return "mixed"
    return _origin_for_provenance(interaction.answer_key.provenance)


def _origin_for_provenance(
    provenance: ExamAuthoringAnswerKeyProvenanceV1,
) -> DigiExamAnswerKeyOriginCodeV1:
    if provenance == "source_provided":
        return "source_provided"
    if provenance == "reviewed":
        return "reviewed_advisory"
    if provenance == "teacher_provided":
        return "teacher_authored"
    if provenance == "mixed":
        return "mixed"
    return "none"


def _origin_for_accepted_correction(
    origin: DigiExamAnswerKeyReviewSubmissionOriginV1,
) -> DigiExamAnswerKeyOriginCodeV1:
    if origin == "accepted_advisory_candidate":
        return "reviewed_advisory"
    if origin == "teacher_edited_advisory_candidate":
        return "teacher_edited_advisory"
    return "teacher_authored"


def _reason_for_accepted_correction(
    origin: DigiExamAnswerKeyReviewSubmissionOriginV1,
) -> DigiExamAnswerKeyReviewReasonCodeV1:
    if origin == "accepted_advisory_candidate":
        return "reviewed_advisory_accepted"
    if origin == "teacher_edited_advisory_candidate":
        return "teacher_edited_advisory_candidate"
    return "teacher_answer_key_present"


def _review_state(
    *,
    origin: DigiExamAnswerKeyOriginCodeV1,
    reasons: tuple[DigiExamAnswerKeyReviewReasonCodeV1, ...],
    advisory: DigiExamAnswerKeyReviewAdvisoryCandidateInput | None,
) -> DigiExamAnswerKeyReviewStateCodeV1:
    if "correction_rejected" in reasons or any(_validation_reason(reason) for reason in reasons):
        return "validation_required"
    if "answer_key_not_applicable" in reasons:
        return "review_complete"
    if advisory is not None and origin == "none":
        return "review_required"
    if origin in {"teacher_authored", "teacher_edited_advisory", "mixed"}:
        return "teacher_modified"
    if origin in {"source_provided", "reviewed_advisory"}:
        return "review_complete"
    return "validation_required"


def _answer_key_applicable(item: ExamAuthoringCorrectionSourceItemV1) -> bool:
    return bool(
        item.choice_interactions
        or item.gap_open_cloze_interactions
        or item.matching_interactions
    )


def _advisory_reviewable(item: ExamAuthoringCorrectionSourceItemV1) -> bool:
    return bool(item.choice_interactions or item.gap_open_cloze_interactions)


def _validation_reason(reason: DigiExamAnswerKeyReviewReasonCodeV1) -> bool:
    return reason in {
        "manual_answer_key_required",
        "no_correct_choice_selected",
        "required_gap_accepted_values_missing",
        "unsupported_item_type",
        "unsupported_target_shape",
        "target_validation_failed",
        "provider_unavailable",
        "stale_source_state",
        "replay_artifact_unavailable",
        "matching_source_state_unavailable",
    }


def _missing_choice_key(item: ExamAuthoringCorrectionSourceItemV1) -> bool:
    return any(
        _choice_interaction_missing_key(interaction) for interaction in item.choice_interactions
    )


def _choice_interaction_missing_key(interaction: ExamAuthoringChoiceInteractionV1) -> bool:
    return not interaction.answer_key.correct_choice_ids


def _missing_gap_values(item: ExamAuthoringCorrectionSourceItemV1) -> bool:
    return any(
        _gap_interaction_missing_values(interaction)
        for interaction in item.gap_open_cloze_interactions
    )


def _gap_interaction_missing_values(interaction: ExamAuthoringGapOpenClozeInteractionV1) -> bool:
    accepted_gap_ids = frozenset(value.gap_id for value in interaction.answer_key.accepted_values)
    return any(
        gap.required_for_auto_evaluation and gap.gap_id not in accepted_gap_ids
        for gap in interaction.gaps
    )


def _correction_affordances(
    item: ExamAuthoringCorrectionSourceItemV1,
) -> tuple[DigiExamAnswerKeyCorrectionAffordanceV1, ...]:
    affordances: list[DigiExamAnswerKeyCorrectionAffordanceV1] = []
    if item.title is not None or item.prompt_html is not None or item.prompt_lines:
        affordances.append("item_text_patch")
    if item.max_score is not None:
        affordances.append("point_correction")
    if item.choice_interactions:
        affordances.append("manual_choice_answer_key")
    if item.gap_open_cloze_interactions:
        affordances.append("manual_gap_open_cloze_answer_key")
    if item.matching_interactions:
        affordances.append("manual_matching_answer_key")
    return tuple(affordances)


def _accepted_correction_origin_by_item(
    outcomes: tuple[DigiExamAnswerKeyReviewCorrectionOutcomeInput, ...],
) -> dict[tuple[str, int], DigiExamAnswerKeyReviewSubmissionOriginV1]:
    accepted: dict[tuple[str, int], DigiExamAnswerKeyReviewSubmissionOriginV1] = {}
    for outcome in outcomes:
        if outcome.accepted and outcome.submission_origin is not None:
            accepted[(outcome.item_id, outcome.sequence)] = outcome.submission_origin
    return accepted


def _target_rows_by_item(
    rows: tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...],
) -> dict[tuple[str, int], tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...]]:
    grouped: dict[tuple[str, int], list[DigiExamAnswerKeyReviewTargetReadinessInput]] = {}
    for row in rows:
        if row.item_id is None or row.sequence is None:
            continue
        grouped.setdefault((row.item_id, row.sequence), []).append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _target_reason(
    row: DigiExamAnswerKeyReviewTargetReadinessInput,
) -> DigiExamAnswerKeyReviewReasonCodeV1 | None:
    if row.export_enabled:
        return None
    if row.reason_code == "manual_answer_key_required":
        return "manual_answer_key_required"
    if row.reason_code == "unsupported_target_shape":
        return "unsupported_target_shape"
    if row.reason_code == "provider_unavailable":
        return "provider_unavailable"
    if row.reason_code == "matching_source_state_unavailable":
        return "matching_source_state_unavailable"
    if row.reason_code == "stale_source_state":
        return "stale_source_state"
    if row.reason_code.startswith("correction_replay_"):
        return "replay_artifact_unavailable"
    if row.reason_code:
        return "target_validation_failed"
    return None


def _replay_references(
    rows: tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...],
) -> tuple[DigiExamAnswerKeyReviewReplayArtifactReferenceV1, ...]:
    references: list[DigiExamAnswerKeyReviewReplayArtifactReferenceV1] = []
    for row in rows:
        if not row.export_enabled:
            continue
        if row.target == "examnet_pdf" and row.artifact_key == "correction_replay_examnet_pdf":
            references.append(
                DigiExamAnswerKeyReviewReplayArtifactReferenceV1(
                    target="examnet_pdf",
                    artifact_key="correction_replay_examnet_pdf",
                )
            )
        if row.target == "qti_package" and row.artifact_key == "correction_replay_qti_package":
            references.append(
                DigiExamAnswerKeyReviewReplayArtifactReferenceV1(
                    target="qti_package",
                    artifact_key="correction_replay_qti_package",
                )
            )
    return tuple(references)


def _provenance_detail(
    advisory: DigiExamAnswerKeyReviewAdvisoryCandidateInput,
) -> DigiExamAnswerKeyReviewProvenanceDetailV1:
    return DigiExamAnswerKeyReviewProvenanceDetailV1(
        candidate_id=advisory.candidate_id,
        candidate_payload_digest=advisory.candidate_payload_digest,
        provider_profile_id=advisory.provider_profile_id,
        schema_name=advisory.schema_name,
        schema_version=advisory.schema_version,
        prompt_template_version=advisory.prompt_template_version,
        validation_state="valid",
    )


def _append_unique(
    reasons: list[DigiExamAnswerKeyReviewReasonCodeV1],
    reason: DigiExamAnswerKeyReviewReasonCodeV1,
) -> None:
    if reason not in reasons:
        reasons.append(reason)
