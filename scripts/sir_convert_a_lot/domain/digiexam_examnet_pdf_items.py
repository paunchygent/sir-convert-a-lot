"""Exam.net PDF renderer item section orchestration.

Purpose:
    Coordinate item-level prompt validation and target-profile strategy
    selection for Exam.net-oriented PDF rendering.

Relationships:
    - Uses prompt sanitation from `domain.digiexam_examnet_pdf_prompt`.
    - Adapts DigiExam IR items into source-neutral PDF item semantics.
    - Delegates target-specific item family policy to
      `domain.examnet_pdf_item_strategies`.
    - Produces item render contracts consumed by
      `domain.digiexam_examnet_pdf_html`.
"""

from __future__ import annotations

from collections.abc import Mapping

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    AssetReferenceKey,
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfItemRenderResult,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
    blocking_examnet_pdf_warnings,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_prompt import (
    prompt_has_renderable_content,
    render_examnet_prompt_html,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from scripts.sir_convert_a_lot.domain.exam_pdf_item_semantics import (
    PdfExamAnswerKeySemantics,
    PdfExamGapAnswerSemantics,
    PdfExamGapSemantics,
    PdfExamItemKind,
    PdfExamItemSemantics,
    PdfExamOptionSemantics,
)
from scripts.sir_convert_a_lot.domain.examnet_pdf_item_strategies import (
    DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY,
    DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT,
    ExamNetPdfItemRenderingPolicyRegistry,
    ExamNetPdfTargetProfileContext,
)


def render_examnet_pdf_items(
    *,
    exam: DigiExamIntermediateExam,
    asset_paths_by_reference: Mapping[AssetReferenceKey, str],
    target_profile_context: ExamNetPdfTargetProfileContext = (
        DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT
    ),
    strategy_registry: ExamNetPdfItemRenderingPolicyRegistry = (
        DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY
    ),
) -> DigiExamExamNetPdfItemRenderResult:
    """Render all supported IR items into Exam.net PDF sections."""

    items: list[DigiExamExamNetPdfItemRender] = []
    warnings: list[DigiExamExamNetPdfWarning] = []
    for item in exam.items:
        item_render, item_warnings = _render_item(
            item=item,
            asset_paths_by_reference=asset_paths_by_reference,
            target_profile_context=target_profile_context,
            strategy_registry=strategy_registry,
        )
        warnings.extend(item_warnings)
        if item_render is not None:
            items.append(item_render)

    return DigiExamExamNetPdfItemRenderResult(items=tuple(items), warnings=tuple(warnings))


def _render_item(
    *,
    item: DigiExamIrItem,
    asset_paths_by_reference: Mapping[AssetReferenceKey, str],
    target_profile_context: ExamNetPdfTargetProfileContext,
    strategy_registry: ExamNetPdfItemRenderingPolicyRegistry,
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    warnings: list[DigiExamExamNetPdfWarning] = []
    points = _points(item)
    if isinstance(points, DigiExamExamNetPdfWarning):
        return None, (points,)

    prompt_render = render_examnet_prompt_html(
        item=item,
        asset_paths_by_reference=asset_paths_by_reference,
    )
    warnings.extend(prompt_render.warnings)
    if not prompt_has_renderable_content(prompt_render.html):
        warnings.append(
            DigiExamExamNetPdfWarning(
                code=DigiExamExamNetPdfWarningCode.EMPTY_PROMPT,
                message=f"Item {item.item_id} has no renderable prompt.",
                item_id=item.item_id,
            )
        )
    if blocking_examnet_pdf_warnings(tuple(warnings)):
        return None, tuple(warnings)

    item_semantics = _adapt_digiexam_item_to_pdf_semantics(
        item=item,
        points=points,
        prompt_html=prompt_render.html,
    )
    strategy_result = strategy_registry.render(
        item=item_semantics,
        context=target_profile_context,
    )
    return strategy_result.item, strategy_result.warnings


def _points(item: DigiExamIrItem) -> int | DigiExamExamNetPdfWarning:
    if item.max_score is None:
        return DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.MISSING_POINT_VALUE,
            message=f"Item {item.item_id} has no point value.",
            item_id=item.item_id,
        )
    return item.max_score


def _adapt_digiexam_item_to_pdf_semantics(
    *,
    item: DigiExamIrItem,
    points: int,
    prompt_html: str,
) -> PdfExamItemSemantics:
    return PdfExamItemSemantics(
        item_id=item.item_id,
        sequence=item.sequence,
        kind=_pdf_item_kind(item.item_type),
        points=points,
        prompt_html=prompt_html,
        source_item_type_label=item.item_type.value,
        options=tuple(
            PdfExamOptionSemantics(option_id=alternative.id, text=alternative.title)
            for alternative in item.alternatives
        ),
        gaps=tuple(PdfExamGapSemantics(gap_id=gap.guid) for gap in item.gaps),
        answer_key=PdfExamAnswerKeySemantics(
            available=item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT,
            correct_option_ids=item.answer_key.correct_alternative_ids,
            correct_gap_answers=tuple(
                PdfExamGapAnswerSemantics(gap_id=answer.guid, value=answer.value)
                for answer in item.answer_key.correct_gap_answers
            ),
        ),
    )


def _pdf_item_kind(item_type: DigiExamItemType) -> PdfExamItemKind:
    if item_type == DigiExamItemType.OPEN_ENDED:
        return PdfExamItemKind.OPEN_RESPONSE
    if item_type in {DigiExamItemType.MULTIPLE_CHOICE, DigiExamItemType.SINGLE_CHOICE}:
        return PdfExamItemKind.SINGLE_CHOICE
    if item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return PdfExamItemKind.MULTIPLE_RESPONSE
    if item_type == DigiExamItemType.GAP_FILL:
        return PdfExamItemKind.GAP_OPEN_CLOZE
    return PdfExamItemKind.UNSUPPORTED
