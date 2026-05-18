"""Non-matching exam-authoring correction application.

Purpose:
    Apply DigiExam-backed point, visible-text, choice-key, and gap/open-cloze
    corrections against the unified producer-issued source-state surface.

Relationships:
    - Used by `application.exam_authoring_corrections_apply_contracts` as the
      Task 333 non-matching runtime delegate.
    - Consumes source-state DTOs from
      `application.exam_authoring_correction_source_state_models`.
    - Shares advisory-candidate digest semantics with the unified apply
      integrity helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringAnswerKeyProvenanceV1,
    ExamAuthoringChoiceAnswerKeyV1,
    ExamAuthoringChoiceInteractionV1,
    ExamAuthoringChoiceOptionV1,
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringGapAcceptedValueV1,
    ExamAuthoringGapAnswerKeyV1,
    ExamAuthoringGapOpenClozeInteractionV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_integrity import (
    choice_answer_key_payload_digest,
    gap_open_cloze_answer_key_payload_digest,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionAcceptedEntryV1,
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringCorrectionTargetV1,
    ExamAuthoringItemTextPatchCorrectionV1,
    ExamAuthoringItemTextPatchOperationV1,
    ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    ExamAuthoringPointCorrectionV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_non_matching_readiness import (
    non_matching_target_readiness_rows,
)

ExamAuthoringNonMatchingCorrectionV1: TypeAlias = (
    ExamAuthoringItemTextPatchCorrectionV1
    | ExamAuthoringPointCorrectionV1
    | ExamAuthoringManualChoiceAnswerKeyCorrectionV1
    | ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1
)
_AnswerKeyProvenance = Literal["teacher_provided", "reviewed"]


class ExamAuthoringNonMatchingCorrectionError(ValueError):
    """Raised when a non-matching correction cannot be applied."""

    def __init__(self, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class PreparedExamAuthoringNonMatchingCorrection:
    """Validated non-matching correction ready for batch application."""

    effective_item: ExamAuthoringCorrectionSourceItemV1
    accepted_entry: ExamAuthoringCorrectionAcceptedEntryV1
    readiness_rows: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]


def prepare_non_matching_correction(
    *,
    correction: ExamAuthoringNonMatchingCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
) -> PreparedExamAuthoringNonMatchingCorrection:
    """Validate and stage a supported non-matching correction."""

    if isinstance(correction, ExamAuthoringPointCorrectionV1):
        effective_item = _apply_point_correction(correction=correction, item=item)
        accepted = _accepted(correction=correction, applied_fields=("point_correction",))
    elif isinstance(correction, ExamAuthoringManualChoiceAnswerKeyCorrectionV1):
        effective_item = _apply_choice_answer_key(correction=correction, item=item)
        accepted = _accepted(
            correction=correction,
            applied_fields=("answer_key",),
            effective_provenance=_answer_key_provenance(correction.submission_origin),
        )
    elif isinstance(correction, ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1):
        effective_item = _apply_gap_open_cloze_answer_key(correction=correction, item=item)
        accepted = _accepted(
            correction=correction,
            applied_fields=("answer_key",),
            effective_provenance=_answer_key_provenance(correction.submission_origin),
        )
    else:
        effective_item = _apply_item_text_patch(correction=correction, item=item)
        accepted = _accepted(correction=correction, applied_fields=("item_text_patch",))
    return PreparedExamAuthoringNonMatchingCorrection(
        effective_item=effective_item,
        accepted_entry=accepted,
        readiness_rows=non_matching_target_readiness_rows(targets=targets, item=effective_item),
    )


def _apply_point_correction(
    *,
    correction: ExamAuthoringPointCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    if item.max_score is None:
        raise _error(
            correction,
            "point_correction_source_max_score_missing",
            "Point correction requires producer-owned max_score state.",
            {"item_id": correction.item_id},
        )
    return item.model_copy(update={"max_score": correction.max_score})


def _apply_choice_answer_key(
    *,
    correction: ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    _validate_choice_candidate_digest(correction)
    interaction = _choice_interaction(correction=correction, item=item)
    _validate_choice_ids(correction=correction, interaction=interaction)
    effective_interaction = interaction.model_copy(
        update={
            "answer_key": ExamAuthoringChoiceAnswerKeyV1(
                provenance=_answer_key_provenance(correction.submission_origin),
                correct_choice_ids=correction.correct_choice_ids,
            )
        }
    )
    return item.model_copy(
        update={
            "choice_interactions": tuple(
                effective_interaction
                if candidate.interaction_id == correction.interaction_id
                else candidate
                for candidate in item.choice_interactions
            )
        }
    )


def _apply_gap_open_cloze_answer_key(
    *,
    correction: ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    _validate_gap_candidate_digest(correction)
    interaction = _gap_interaction(correction=correction, item=item)
    _validate_gap_ids(correction=correction, interaction=interaction)
    effective_interaction = _replace_gap_answers(
        correction=correction,
        interaction=interaction,
        provenance=_answer_key_provenance(correction.submission_origin),
    )
    return item.model_copy(
        update={
            "gap_open_cloze_interactions": tuple(
                effective_interaction
                if candidate.interaction_id == correction.interaction_id
                else candidate
                for candidate in item.gap_open_cloze_interactions
            )
        }
    )


def _apply_item_text_patch(
    *,
    correction: ExamAuthoringItemTextPatchCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    effective_item = item
    for patch in correction.patches:
        effective_item = _apply_text_patch_operation(
            correction=correction,
            item=effective_item,
            patch=patch,
        )
    return effective_item


def _apply_text_patch_operation(
    *,
    correction: ExamAuthoringItemTextPatchCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
    patch: ExamAuthoringItemTextPatchOperationV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    if patch.field == "item_title":
        _require_present(correction, "item_title", item.title)
        return item.model_copy(update={"title": patch.value})
    if patch.field == "prompt_html":
        _require_present(correction, "prompt_html", item.prompt_html)
        return item.model_copy(update={"prompt_html": patch.value})
    if patch.field == "prompt_lines":
        if not item.prompt_lines:
            raise _patch_error(correction, "prompt_lines")
        lines = tuple(line.strip() for line in patch.value.splitlines() if line.strip())
        if not lines:
            raise _patch_error(correction, "prompt_lines")
        return item.model_copy(update={"prompt_lines": lines})
    if patch.field == "visible_option_text":
        if patch.choice_id is None:
            raise _error(
                correction,
                "visible_option_text_choice_id_missing",
                "Visible option text patch requires a producer choice ID.",
                {"entry_id": correction.entry_id},
            )
        return _replace_choice_text(correction=correction, item=item, patch=patch)
    raise _patch_error(correction, patch.field)


def _replace_choice_text(
    *,
    correction: ExamAuthoringItemTextPatchCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
    patch: ExamAuthoringItemTextPatchOperationV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    replaced = False
    interactions: list[ExamAuthoringChoiceInteractionV1] = []
    for interaction in item.choice_interactions:
        choices: list[ExamAuthoringChoiceOptionV1] = []
        for choice in interaction.choices:
            if choice.choice_id == patch.choice_id:
                choices.append(choice.model_copy(update={"text": patch.value}))
                replaced = True
            else:
                choices.append(choice)
        interactions.append(interaction.model_copy(update={"choices": tuple(choices)}))
    if not replaced:
        raise _error(
            correction,
            "unknown_visible_option_choice_id",
            "Visible option text patch references an unknown choice ID.",
            {"entry_id": correction.entry_id, "choice_id": patch.choice_id},
        )
    return item.model_copy(update={"choice_interactions": tuple(interactions)})


def _choice_interaction(
    *,
    correction: ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringChoiceInteractionV1:
    for interaction in item.choice_interactions:
        if interaction.interaction_id == correction.interaction_id:
            return interaction
    raise _error(
        correction,
        "unknown_choice_interaction_id",
        "Choice correction references an unknown interaction.",
        {"entry_id": correction.entry_id, "interaction_id": correction.interaction_id},
    )


def _gap_interaction(
    *,
    correction: ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringGapOpenClozeInteractionV1:
    for interaction in item.gap_open_cloze_interactions:
        if interaction.interaction_id == correction.interaction_id:
            return interaction
    raise _error(
        correction,
        "unknown_gap_open_cloze_interaction_id",
        "Gap/open-cloze correction references an unknown interaction.",
        {"entry_id": correction.entry_id, "interaction_id": correction.interaction_id},
    )


def _validate_choice_ids(
    *,
    correction: ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    interaction: ExamAuthoringChoiceInteractionV1,
) -> None:
    submitted_ids = correction.correct_choice_ids
    if len(set(submitted_ids)) != len(submitted_ids):
        raise _error(
            correction, "duplicate_choice_answer_id", "Choice key contains duplicates.", {}
        )
    known_choice_ids = frozenset(choice.choice_id for choice in interaction.choices)
    unknown_choice_ids = tuple(
        choice_id for choice_id in submitted_ids if choice_id not in known_choice_ids
    )
    if unknown_choice_ids:
        raise _error(
            correction,
            "unknown_choice_answer_id",
            "Choice key references unknown producer choice IDs.",
            {"choice_ids": unknown_choice_ids},
        )
    if interaction.interaction_kind == "single_choice" and len(submitted_ids) != 1:
        raise _error(
            correction,
            "single_choice_requires_exactly_one_correct_choice",
            "Single-choice corrections require exactly one correct choice.",
            {"submitted_choice_count": len(submitted_ids)},
        )
    max_choices = interaction.max_correct_choices or len(interaction.choices)
    min_choices = max(1, interaction.min_correct_choices)
    if len(submitted_ids) < min_choices or len(submitted_ids) > max_choices:
        raise _error(
            correction,
            "choice_answer_key_cardinality_invalid",
            "Choice correction violates producer cardinality bounds.",
            {"submitted_choice_count": len(submitted_ids)},
        )


def _validate_gap_ids(
    *,
    correction: ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    interaction: ExamAuthoringGapOpenClozeInteractionV1,
) -> None:
    submitted_gap_ids = tuple(answer.gap_id for answer in correction.gap_answers)
    if len(set(submitted_gap_ids)) != len(submitted_gap_ids):
        raise _error(correction, "duplicate_gap_answer_id", "Gap key contains duplicates.", {})
    known_gap_ids = frozenset(gap.gap_id for gap in interaction.gaps)
    unknown_gap_ids = tuple(gap_id for gap_id in submitted_gap_ids if gap_id not in known_gap_ids)
    if unknown_gap_ids:
        raise _error(
            correction,
            "unknown_gap_answer_id",
            "Gap/open-cloze key references unknown producer gap IDs.",
            {"gap_ids": unknown_gap_ids},
        )


def _replace_gap_answers(
    *,
    correction: ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    interaction: ExamAuthoringGapOpenClozeInteractionV1,
    provenance: ExamAuthoringAnswerKeyProvenanceV1,
) -> ExamAuthoringGapOpenClozeInteractionV1:
    replaced_gap_ids = frozenset(answer.gap_id for answer in correction.gap_answers)
    accepted_values = [
        value
        for value in interaction.answer_key.accepted_values
        if value.gap_id not in replaced_gap_ids
    ]
    for answer in correction.gap_answers:
        accepted_values.extend(
            ExamAuthoringGapAcceptedValueV1(
                gap_id=answer.gap_id,
                value=value,
                provenance=provenance,
            )
            for value in answer.accepted_values
        )
    return interaction.model_copy(
        update={
            "answer_key": ExamAuthoringGapAnswerKeyV1(
                provenance=_aggregate_gap_provenance(tuple(accepted_values)),
                accepted_values=tuple(accepted_values),
            )
        }
    )


def _validate_choice_candidate_digest(
    correction: ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
) -> None:
    if correction.submission_origin != "accepted_advisory_candidate":
        return
    if correction.candidate_lineage is None:
        raise _error(
            correction, "advisory_candidate_lineage_missing", "Candidate lineage missing.", {}
        )
    submitted_digest = choice_answer_key_payload_digest(correction)
    expected_digest = correction.candidate_lineage.candidate_payload_digest
    if submitted_digest != expected_digest:
        raise _error(
            correction,
            "advisory_candidate_payload_digest_mismatch",
            "Accepted advisory choice correction must match the candidate payload digest.",
            {
                "entry_id": correction.entry_id,
                "candidate_id": correction.candidate_lineage.candidate_id,
            },
        )


def _validate_gap_candidate_digest(
    correction: ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
) -> None:
    if correction.submission_origin != "accepted_advisory_candidate":
        return
    if correction.candidate_lineage is None:
        raise _error(
            correction, "advisory_candidate_lineage_missing", "Candidate lineage missing.", {}
        )
    submitted_digest = gap_open_cloze_answer_key_payload_digest(correction)
    expected_digest = correction.candidate_lineage.candidate_payload_digest
    if submitted_digest != expected_digest:
        raise _error(
            correction,
            "advisory_candidate_payload_digest_mismatch",
            "Accepted advisory gap correction must match the candidate payload digest.",
            {
                "entry_id": correction.entry_id,
                "candidate_id": correction.candidate_lineage.candidate_id,
            },
        )


def _answer_key_provenance(origin: str) -> _AnswerKeyProvenance:
    if origin == "accepted_advisory_candidate":
        return "reviewed"
    return "teacher_provided"


def _aggregate_gap_provenance(
    accepted_values: tuple[ExamAuthoringGapAcceptedValueV1, ...],
) -> ExamAuthoringAnswerKeyProvenanceV1:
    provenances = {value.provenance for value in accepted_values}
    if not provenances:
        return "absent"
    if len(provenances) == 1:
        return next(iter(provenances))
    return "mixed"


def _accepted(
    *,
    correction: ExamAuthoringNonMatchingCorrectionV1,
    applied_fields: tuple[str, ...],
    effective_provenance: str | None = None,
) -> ExamAuthoringCorrectionAcceptedEntryV1:
    return ExamAuthoringCorrectionAcceptedEntryV1(
        entry_id=correction.entry_id,
        kind=correction.kind,
        item_id=correction.item_id,
        sequence=correction.sequence,
        applied_fields=applied_fields,
        effective_provenance=effective_provenance,
    )


def _require_present(
    correction: ExamAuthoringItemTextPatchCorrectionV1,
    field: str,
    value: str | None,
) -> None:
    if value is None:
        raise _patch_error(correction, field)


def _patch_error(
    correction: ExamAuthoringItemTextPatchCorrectionV1,
    field: str,
) -> ExamAuthoringNonMatchingCorrectionError:
    return _error(
        correction,
        "item_text_patch_field_not_present",
        "Item text patch references a field not present in producer source state.",
        {"entry_id": correction.entry_id, "field": field},
    )


def _error(
    correction: ExamAuthoringNonMatchingCorrectionV1,
    code: str,
    message: str,
    details: dict[str, object],
) -> ExamAuthoringNonMatchingCorrectionError:
    merged_details = {"entry_id": correction.entry_id, "item_id": correction.item_id, **details}
    return ExamAuthoringNonMatchingCorrectionError(code, message, merged_details)
