"""DigiExam source adapter for ExamAuthoringIR v1 interactions.

Purpose:
    Map supported DigiExam source IR item structures into source-neutral
    ExamAuthoringIR v1 concepts without making DigiExam DTOs the shared
    authoring model.

Relationships:
    - Consumes `domain.digiexam_ir_contracts` after `.dxe` parser and
      DigiExam IR construction.
    - Emits `domain.exam_authoring_gap_contracts` gap/open-cloze interactions
      for Task 305 validation and later target/export cutover work.
    - Keeps target-specific PDF/QTI conversion outside the source adapter.
"""

from __future__ import annotations

from html.parser import HTMLParser

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_gap_contracts import (
    ExamAuthoringGap,
    ExamAuthoringGapAcceptedValue,
    ExamAuthoringGapAnswerKey,
    ExamAuthoringGapNormalizationProfile,
    ExamAuthoringGapOpenClozeInteraction,
    ExamAuthoringGapPromptBinding,
    ExamAuthoringGapPromptBindingKind,
    build_exam_authoring_gap_open_cloze_interaction,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringSourceEvidence,
)


def build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir(
    exam: DigiExamIntermediateExam,
) -> tuple[ExamAuthoringGapOpenClozeInteraction, ...]:
    """Map all DigiExam gap-fill items into source-neutral interactions."""

    return tuple(
        build_exam_authoring_gap_open_cloze_interaction_from_digiexam_item(item)
        for item in exam.items
        if item.item_type == DigiExamItemType.GAP_FILL
    )


def build_exam_authoring_gap_open_cloze_interaction_from_digiexam_item(
    item: DigiExamIrItem,
) -> ExamAuthoringGapOpenClozeInteraction:
    """Map one DigiExam gap-fill item into ExamAuthoringIR v1."""

    prompt_gap_ids = _prompt_gap_ids(item.prompt_html)
    return build_exam_authoring_gap_open_cloze_interaction(
        interaction_id=item.item_id,
        gaps=tuple(
            ExamAuthoringGap(
                gap_id=gap.guid,
                display_order=display_order,
                prompt_binding=_prompt_binding(
                    item_id=item.item_id,
                    gap_id=gap.guid,
                    display_order=display_order,
                    prompt_gap_ids=prompt_gap_ids,
                ),
                required_for_auto_evaluation=True,
                evidence=(
                    ExamAuthoringSourceEvidence(
                        source_family="digiexam_dxe",
                        source_id=item.item_id,
                        locator=f"gaps[{display_order - 1}].guid",
                    ),
                ),
            )
            for display_order, gap in enumerate(item.gaps, start=1)
        ),
        normalization_profile=ExamAuthoringGapNormalizationProfile.EXACT_TRIM_CASE_SENSITIVE,
        answer_key=ExamAuthoringGapAnswerKey(
            accepted_values=tuple(
                ExamAuthoringGapAcceptedValue(
                    gap_id=answer.guid,
                    value=answer.value,
                    provenance=_answer_key_provenance(item.answer_key.provenance),
                    evidence=(
                        ExamAuthoringSourceEvidence(
                            source_family=_answer_key_source_family(item.answer_key.provenance),
                            source_id=item.item_id,
                            locator=f"answer_key.correct_gap_answers[{index}]",
                        ),
                    ),
                )
                for index, answer in enumerate(item.answer_key.correct_gap_answers)
            ),
        ),
        evidence=(
            ExamAuthoringSourceEvidence(
                source_family="digiexam_dxe",
                source_id=item.item_id,
                locator=f"items[{item.sequence - 1}]",
            ),
        ),
    )


def _prompt_binding(
    *,
    item_id: str,
    gap_id: str,
    display_order: int,
    prompt_gap_ids: tuple[str, ...],
) -> ExamAuthoringGapPromptBinding:
    if gap_id in prompt_gap_ids:
        return ExamAuthoringGapPromptBinding(
            kind=ExamAuthoringGapPromptBindingKind.HTML_ATTRIBUTE,
            locator=f'bodyHTML:span[dx-wg-id="{gap_id}"]',
        )
    return ExamAuthoringGapPromptBinding(
        kind=ExamAuthoringGapPromptBindingKind.SOURCE_LOCATOR,
        locator=f"{item_id}:gaps[{display_order - 1}]",
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


def _answer_key_source_family(provenance: DigiExamAnswerKeyProvenance) -> str:
    if provenance == DigiExamAnswerKeyProvenance.GRADED_RESULT_PDF_CORRECT_LABELS:
        return "digiexam_result_pdf_correct_labels"
    if provenance == DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY:
        return "teacher_overlay"
    return "digiexam_dxe"


def _prompt_gap_ids(prompt_html: str | None) -> tuple[str, ...]:
    if prompt_html is None:
        return ()
    parser = _DigiExamGapBindingParser()
    parser.feed(prompt_html)
    return tuple(parser.gap_ids)


class _DigiExamGapBindingParser(HTMLParser):
    """Extract DigiExam gap IDs from bodyHTML span bindings."""

    def __init__(self) -> None:
        super().__init__()
        self.gap_ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "span":
            return
        attributes = {name: value for name, value in attrs if value is not None}
        gap_id = attributes.get("dx-wg-id")
        if gap_id is not None and gap_id.strip():
            self.gap_ids.append(gap_id)
