"""Projection helpers for exam-authoring correction source state.

Purpose:
    Build sanitized correction source-state DTOs from producer-owned exam
    authoring runtime models so downstream consumers can request signed
    correction bindings without posting browser-local state for signing.

Relationships:
    - Consumes DigiExam migration IR after the parser/effective-overlay path.
    - Emits `ExamAuthoringCorrectionSourceStateV1` for the source-state issuer.
    - Shares canonical digest semantics with the correction apply route.
"""

from __future__ import annotations

from typing import Literal

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringChoiceAnswerKeyV1,
    ExamAuthoringChoiceInteractionV1,
    ExamAuthoringChoiceOptionV1,
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringCorrectionSourceStateV1,
    ExamAuthoringGapAcceptedValueV1,
    ExamAuthoringGapAnswerKeyV1,
    ExamAuthoringGapOpenClozeInteractionV1,
    ExamAuthoringGapPromptBindingV1,
    ExamAuthoringGapV1,
    ExamAuthoringSourceEvidenceV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_integrity import (
    source_state_content_digest,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAlternative,
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_exam_authoring_adapter import (
    build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import source_item_fingerprint
from scripts.sir_convert_a_lot.domain.exam_authoring_gap_contracts import (
    ExamAuthoringGapOpenClozeInteraction,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringSourceEvidence,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
)

_ChoiceInteractionKind = Literal["single_choice", "multiple_choice", "multiple_response"]


def digiexam_exam_to_correction_source_state(
    exam: DigiExamIntermediateExam,
) -> ExamAuthoringCorrectionSourceStateV1:
    """Project a DigiExam migration exam into sanitized correction source state."""

    gap_interactions_by_item = {
        interaction.interaction_id: interaction
        for interaction in build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir(exam)
    }
    source_state = ExamAuthoringCorrectionSourceStateV1(
        source_authoring_schema_version=EXAM_AUTHORING_IR_SCHEMA_VERSION,
        source_state_sha256="sha256:pending",
        items=tuple(
            ExamAuthoringCorrectionSourceItemV1(
                item_id=item.item_id,
                sequence=item.sequence,
                item_type=item.item_type.value,
                source_item_fingerprint=source_item_fingerprint(item),
                title=_non_blank_or_none(item.title),
                prompt_html=_non_blank_or_none(item.prompt_html),
                prompt_lines=tuple(line for line in item.prompt_lines if line.strip()),
                max_score=item.max_score,
                choice_interactions=tuple(_choice_interactions(item)),
                gap_open_cloze_interactions=_gap_interactions_for_item(
                    item=item,
                    gap_interactions_by_item=gap_interactions_by_item,
                ),
                matching_interactions=(),
            )
            for item in exam.items
        ),
    )
    return source_state.model_copy(
        update={"source_state_sha256": source_state_content_digest(source_state)}
    )


def _choice_interactions(item: DigiExamIrItem) -> tuple[ExamAuthoringChoiceInteractionV1, ...]:
    if item.item_type not in {
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        return ()
    correct_choice_ids = tuple(
        _choice_id(alternative_id) for alternative_id in item.answer_key.correct_alternative_ids
    )
    return (
        ExamAuthoringChoiceInteractionV1(
            interaction_id=f"choice-{item.item_id}",
            interaction_kind=_choice_interaction_kind(item.item_type),
            choices=tuple(
                ExamAuthoringChoiceOptionV1(
                    choice_id=_choice_id(alternative.id),
                    source_id=str(alternative.id),
                    order=index,
                    text=_choice_text(alternative),
                )
                for index, alternative in enumerate(item.alternatives, start=1)
            ),
            min_correct_choices=1 if item.item_type == DigiExamItemType.SINGLE_CHOICE else 0,
            max_correct_choices=(
                1 if item.item_type == DigiExamItemType.SINGLE_CHOICE else len(item.alternatives)
            ),
            answer_key=ExamAuthoringChoiceAnswerKeyV1(
                provenance=_answer_key_provenance(item.answer_key.provenance).value,
                correct_choice_ids=correct_choice_ids,
            ),
            evidence=(
                ExamAuthoringSourceEvidenceV1(
                    source_family="digiexam_dxe",
                    source_id=item.item_id,
                    locator=f"items[{item.sequence - 1}].alternatives",
                ),
            ),
        ),
    )


def _gap_interactions_for_item(
    *,
    item: DigiExamIrItem,
    gap_interactions_by_item: dict[str, ExamAuthoringGapOpenClozeInteraction],
) -> tuple[ExamAuthoringGapOpenClozeInteractionV1, ...]:
    interaction = gap_interactions_by_item.get(item.item_id)
    if interaction is None:
        return ()
    return (_gap_interaction(interaction),)


def _gap_interaction(
    interaction: ExamAuthoringGapOpenClozeInteraction,
) -> ExamAuthoringGapOpenClozeInteractionV1:
    return ExamAuthoringGapOpenClozeInteractionV1(
        interaction_id=f"gap-{interaction.interaction_id}",
        gaps=tuple(
            ExamAuthoringGapV1(
                gap_id=gap.gap_id,
                display_order=gap.display_order,
                prompt_binding=ExamAuthoringGapPromptBindingV1(
                    kind=gap.prompt_binding.kind.value,
                    locator=gap.prompt_binding.locator,
                ),
                required_for_auto_evaluation=gap.required_for_auto_evaluation,
                evidence=tuple(_source_evidence(evidence) for evidence in gap.evidence),
            )
            for gap in interaction.gaps
        ),
        normalization_profile=interaction.normalization_profile.value,
        answer_key=ExamAuthoringGapAnswerKeyV1(
            provenance=interaction.answer_key.provenance.value,
            accepted_values=tuple(
                ExamAuthoringGapAcceptedValueV1(
                    gap_id=accepted_value.gap_id,
                    value=accepted_value.value,
                    provenance=accepted_value.provenance.value,
                    evidence=tuple(
                        _source_evidence(evidence) for evidence in accepted_value.evidence
                    ),
                )
                for accepted_value in interaction.answer_key.accepted_values
            ),
        ),
        evidence=tuple(_source_evidence(evidence) for evidence in interaction.evidence),
    )


def _source_evidence(evidence: ExamAuthoringSourceEvidence) -> ExamAuthoringSourceEvidenceV1:
    return ExamAuthoringSourceEvidenceV1(
        source_family=evidence.source_family,
        source_id=evidence.source_id,
        locator=evidence.locator,
    )


def _answer_key_provenance(
    provenance: DigiExamAnswerKeyProvenance,
) -> ExamAuthoringAnswerKeyProvenance:
    if provenance in {
        DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY,
        DigiExamAnswerKeyProvenance.GRADED_RESULT_PDF_CORRECT_LABELS,
    }:
        return ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED
    if provenance == DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY:
        return ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED
    return ExamAuthoringAnswerKeyProvenance.ABSENT


def _choice_interaction_kind(item_type: DigiExamItemType) -> _ChoiceInteractionKind:
    if item_type == DigiExamItemType.SINGLE_CHOICE:
        return "single_choice"
    if item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return "multiple_response"
    return "multiple_choice"


def _choice_id(alternative_id: int) -> str:
    return f"choice-{alternative_id:03d}"


def _choice_text(alternative: DigiExamAlternative) -> str:
    title = alternative.title.strip()
    about = alternative.about.strip()
    if title and about:
        return f"{title}\n{about}"
    if title:
        return title
    if about:
        return about
    return f"Choice {alternative.id}"


def _non_blank_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    return normalized
