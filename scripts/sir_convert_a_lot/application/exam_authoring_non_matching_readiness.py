"""Readiness projection for non-matching exam-authoring corrections.

Purpose:
    Project item-level readiness for point, visible-text, choice-key, and
    gap/open-cloze corrections after Sir Convert has applied producer-bound
    effective state.

Relationships:
    - Used by `application.exam_authoring_non_matching_corrections`.
    - Consumes source-state DTOs from
      `application.exam_authoring_correction_source_state_models`.
    - Emits unified apply route readiness DTOs for HuleEdu/Skriptoteket
      consumers.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringGapOpenClozeInteractionV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringCorrectionTargetV1,
)


def non_matching_target_readiness_rows(
    *,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
    item: ExamAuthoringCorrectionSourceItemV1,
) -> tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]:
    """Return target readiness rows for a corrected non-matching item."""

    return tuple(_target_readiness(target=target, item=item) for target in targets)


def _target_readiness(
    *,
    target: ExamAuthoringCorrectionTargetV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringCorrectionTargetReadinessRowV1:
    if _non_matching_item_ready(item):
        return ExamAuthoringCorrectionTargetReadinessRowV1(
            target=target,
            readiness="ready",
            export_enabled=True,
            reason_code="ready",
            message_key="exam_converter.target.ready",
            item_id=item.item_id,
            sequence=item.sequence,
        )
    return ExamAuthoringCorrectionTargetReadinessRowV1(
        target=target,
        readiness="target_validation_failed",
        export_enabled=False,
        reason_code="manual_answer_key_required",
        message_key="exam_converter.target.needs_teacher_answer_key",
        item_id=item.item_id,
        sequence=item.sequence,
    )


def _non_matching_item_ready(item: ExamAuthoringCorrectionSourceItemV1) -> bool:
    if item.choice_interactions:
        return all(
            interaction.answer_key.correct_choice_ids for interaction in item.choice_interactions
        )
    if item.gap_open_cloze_interactions:
        return all(
            _gap_interaction_ready(interaction) for interaction in item.gap_open_cloze_interactions
        )
    return item.item_type == "open_ended" and (
        item.title is not None or item.prompt_html is not None or bool(item.prompt_lines)
    )


def _gap_interaction_ready(interaction: ExamAuthoringGapOpenClozeInteractionV1) -> bool:
    accepted_gap_ids = frozenset(value.gap_id for value in interaction.answer_key.accepted_values)
    return all(
        not gap.required_for_auto_evaluation or gap.gap_id in accepted_gap_ids
        for gap in interaction.gaps
    )
