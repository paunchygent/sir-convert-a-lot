"""Answer-key review projection adapter for correction apply results.

Purpose:
    Translate source-neutral correction apply state, reports, and readiness
    rows into the compact DigiExam answer-key review-state projection.

Relationships:
    - Keeps `exam_authoring_corrections_apply_contracts` focused on correction
      application flow.
    - Reuses `digiexam_answer_key_review_state` so correction apply and
      first-pass bundle generation share one producer projection builder.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state import (
    build_digiexam_answer_key_review_state,
)
from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state_models import (
    DigiExamAnswerKeyReviewAdvisoryCandidateInput,
    DigiExamAnswerKeyReviewCorrectionOutcomeInput,
    DigiExamAnswerKeyReviewStateV1,
    DigiExamAnswerKeyReviewSubmissionOriginV1,
    DigiExamAnswerKeyReviewTargetReadinessInput,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringCorrectionSourceStateV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionAcceptedEntryV1,
    ExamAuthoringCorrectionRejectedEntryV1,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringEffectiveStateV1,
    ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
)


def build_answer_key_review_state_for_apply_result(
    *,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    effective_state: ExamAuthoringEffectiveStateV1,
    effective_items: tuple[ExamAuthoringCorrectionSourceItemV1, ...],
    accepted_entries: tuple[ExamAuthoringCorrectionAcceptedEntryV1, ...],
    rejected_entries: tuple[ExamAuthoringCorrectionRejectedEntryV1, ...],
    readiness_rows: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...],
) -> DigiExamAnswerKeyReviewStateV1:
    """Build compact answer-key review state for one apply result."""

    return build_digiexam_answer_key_review_state(
        source_state=ExamAuthoringCorrectionSourceStateV1(
            source_authoring_schema_version=(
                request_body.source_authoring_state.source_authoring_schema_version
            ),
            source_state_sha256=effective_state.effective_state_sha256,
            items=effective_items,
        ),
        correction_outcomes=_correction_outcomes(
            request_body=request_body,
            accepted_entries=accepted_entries,
            rejected_entries=rejected_entries,
        ),
        advisory_candidates=_advisory_candidates(request_body.source_authoring_state),
        target_readiness=_target_readiness(readiness_rows),
        include_advisory_provenance_detail=True,
    )


def _correction_outcomes(
    *,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    accepted_entries: tuple[ExamAuthoringCorrectionAcceptedEntryV1, ...],
    rejected_entries: tuple[ExamAuthoringCorrectionRejectedEntryV1, ...],
) -> tuple[DigiExamAnswerKeyReviewCorrectionOutcomeInput, ...]:
    accepted_answer_key_entries = {
        entry.entry_id for entry in accepted_entries if "answer_key" in entry.applied_fields
    }
    outcomes: list[DigiExamAnswerKeyReviewCorrectionOutcomeInput] = []
    for correction in request_body.corrections:
        if not isinstance(
            correction,
            (
                ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
                ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
                ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
            ),
        ):
            continue
        if correction.entry_id in accepted_answer_key_entries:
            outcomes.append(
                DigiExamAnswerKeyReviewCorrectionOutcomeInput(
                    item_id=correction.item_id,
                    sequence=correction.sequence,
                    accepted=True,
                    submission_origin=_submission_origin(correction.submission_origin),
                )
            )
    outcomes.extend(
        DigiExamAnswerKeyReviewCorrectionOutcomeInput(
            item_id=entry.item_id,
            sequence=entry.sequence,
            accepted=False,
        )
        for entry in rejected_entries
    )
    return tuple(outcomes)


def _submission_origin(origin: str) -> DigiExamAnswerKeyReviewSubmissionOriginV1:
    if origin == "accepted_advisory_candidate":
        return "accepted_advisory_candidate"
    if origin == "teacher_edited_advisory_candidate":
        return "teacher_edited_advisory_candidate"
    return "teacher_authored"


def _target_readiness(
    rows: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...],
) -> tuple[DigiExamAnswerKeyReviewTargetReadinessInput, ...]:
    return tuple(
        DigiExamAnswerKeyReviewTargetReadinessInput(
            target=row.target,
            export_enabled=row.export_enabled,
            reason_code=row.reason_code,
            item_id=row.item_id,
            sequence=row.sequence,
            artifact_key=row.artifact_key,
        )
        for row in rows
    )


def _advisory_candidates(
    source_state: ExamAuthoringCorrectionSourceStateV1,
) -> tuple[DigiExamAnswerKeyReviewAdvisoryCandidateInput, ...]:
    return tuple(
        DigiExamAnswerKeyReviewAdvisoryCandidateInput(
            item_id=candidate.item_id,
            sequence=candidate.sequence,
            candidate_id=candidate.candidate_id,
            candidate_payload_digest=candidate.candidate_payload_digest,
            provider_profile_id=candidate.provider_profile_id,
            schema_name=candidate.schema_name,
            schema_version=candidate.schema_version,
            prompt_template_version=candidate.prompt_template_version,
            validation_state=candidate.validation_state,
        )
        for candidate in source_state.advisory_answer_key_candidates
    )
