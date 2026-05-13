"""DigiExam IR adapter for Exam.net QTI package generation.

Purpose:
    Convert renderer-neutral DigiExam exam items into the generic Exam.net QTI
    item contract without changing parser, IR, or service-route semantics.

Relationships:
    - Consumes `domain.digiexam_ir_contracts` after parser/IR construction.
    - Emits `domain.examnet_qti_contracts` items for the reusable QTI package
      planner.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from html.parser import HTMLParser

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamEmbeddedAsset,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUp,
    ExamNetQtiManualFollowUpReason,
)


@dataclass(frozen=True)
class DigiExamExamNetQtiAdapterResult:
    """QTI items plus target-specific follow-up from DigiExam IR conversion."""

    items: tuple[ExamNetQtiItem, ...]
    manual_follow_ups: tuple[ExamNetQtiManualFollowUp, ...]


def build_examnet_qti_items_from_digiexam_ir(
    exam: DigiExamIntermediateExam,
) -> DigiExamExamNetQtiAdapterResult:
    """Convert supported DigiExam IR items to reusable Exam.net QTI items."""

    qti_items: list[ExamNetQtiItem] = []
    follow_ups: list[ExamNetQtiManualFollowUp] = []
    for item in exam.items:
        qti_item = _qti_item(item)
        if qti_item is None:
            follow_ups.append(_not_supported_follow_up(item))
        else:
            qti_items.append(qti_item)
    return DigiExamExamNetQtiAdapterResult(
        items=tuple(qti_items), manual_follow_ups=tuple(follow_ups)
    )


def _qti_item(item: DigiExamIrItem) -> ExamNetQtiItem | None:
    if item.item_type == DigiExamItemType.OPEN_ENDED:
        return _base_qti_item(item, ExamNetQtiInteractionType.FREE_TEXT)
    if item.item_type in {DigiExamItemType.SINGLE_CHOICE, DigiExamItemType.MULTIPLE_CHOICE}:
        return _choice_item(item, ExamNetQtiInteractionType.SINGLE_CHOICE)
    if item.item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return _choice_item(item, ExamNetQtiInteractionType.MULTIPLE_RESPONSE)
    return None


def _choice_item(
    item: DigiExamIrItem,
    interaction_type: ExamNetQtiInteractionType,
) -> ExamNetQtiItem:
    base_item = _base_qti_item(item, interaction_type)
    correct_ids: tuple[str, ...] = ()
    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        correct_ids = tuple(
            _choice_identifier(value) for value in item.answer_key.correct_alternative_ids
        )
    return ExamNetQtiItem(
        item_id=base_item.item_id,
        sequence=base_item.sequence,
        title=base_item.title,
        interaction_type=interaction_type,
        prompt_lines=base_item.prompt_lines,
        max_score=base_item.max_score,
        choices=tuple(
            ExamNetQtiChoice(
                identifier=_choice_identifier(alternative.id),
                text=" ".join(alternative.title.split()),
            )
            for alternative in item.alternatives
            if alternative.title.strip()
        ),
        correct_choice_identifiers=correct_ids,
        image_resources=base_item.image_resources,
    )


def _base_qti_item(
    item: DigiExamIrItem,
    interaction_type: ExamNetQtiInteractionType,
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=_safe_item_identifier(item.item_id),
        sequence=item.sequence,
        title=item.title,
        interaction_type=interaction_type,
        prompt_lines=_prompt_lines(item),
        max_score=item.max_score,
        image_resources=tuple(
            _image_resource(item, index, asset)
            for index, asset in enumerate(item.embedded_assets, start=1)
        ),
    )


def _image_resource(
    item: DigiExamIrItem,
    index: int,
    asset: DigiExamEmbeddedAsset,
) -> ExamNetQtiImageResource:
    payload = base64.b64decode(asset.content_base64, validate=True)
    return ExamNetQtiImageResource(
        asset_id=f"image_{index:03d}",
        filename=f"{item.item_id}-image-{index:03d}.png",
        media_type=asset.media_type,
        payload=payload,
        alt_text=f"Bild {index} till {item.title}",
        source_reference=asset.asset_id,
    )


def _not_supported_follow_up(item: DigiExamIrItem) -> ExamNetQtiManualFollowUp:
    return ExamNetQtiManualFollowUp(
        item_id=item.item_id,
        sequence=item.sequence,
        title=item.title,
        reason_code=ExamNetQtiManualFollowUpReason.NOT_SUPPORTED_BY_EXAMNET,
        message="Frågetypen kräver ett senare QTI-bevis innan den kan användas i Exam.net.",
        affected_targets=("qti_package",),
    )


def _prompt_lines(item: DigiExamIrItem) -> tuple[str, ...]:
    lines = tuple(line.strip() for line in item.prompt_lines if line.strip())
    if lines:
        return lines
    if item.prompt_html is None:
        return ()
    parser = _TextExtractor()
    parser.feed(item.prompt_html)
    return tuple(line for line in (" ".join(parser.parts).strip(),) if line)


def _safe_item_identifier(value: str) -> str:
    return value.replace("-", "_")


def _choice_identifier(value: int) -> str:
    return f"choice_{value:03d}"


class _TextExtractor(HTMLParser):
    """Small HTML text extractor for prompt fallback."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)
