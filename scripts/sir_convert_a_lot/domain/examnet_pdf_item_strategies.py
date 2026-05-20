"""Exam.net PDF item rendering target-profile strategies.

Purpose:
    Own Exam.net-oriented PDF target policy for mapping immutable,
    source-neutral PDF item semantics into PDF item sections, warnings, and
    manual follow-up signals.

Relationships:
    - Consumes `domain.exam_pdf_item_semantics` values without source-adapter
      imports or mutations.
    - Produces item render contracts from `domain.digiexam_examnet_pdf_contracts`
      for the PDF item coordinator.
    - Keeps Exam.net-specific layout labels and target shaping out of parser
      IR, effective IR, bundle, QTI, and service layers.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from typing import Protocol

from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
)
from scripts.sir_convert_a_lot.domain.exam_pdf_item_semantics import (
    PdfExamItemKind,
    PdfExamItemSemantics,
)

_LABELLED_OPTION_PATTERN = re.compile(r"^(?:[A-Za-z]|\d+)[.)]\s+")


@dataclass(frozen=True)
class ExamNetPdfItemLabelPolicy:
    """Localized target labels owned by the Exam.net PDF target profile."""

    free_text_type_label: str = "Fritext"
    choice_type_label: str = "Multiple choice"
    multiple_response_type_label: str = "Multiple response"
    gap_open_cloze_type_label: str = "Lucktext"
    source_item_type_marker: str = "Typ"
    target_item_type_marker: str = "Type"
    point_label: str = "Poängvärde"
    single_answer_key_label: str = "Correct answer"
    multiple_answer_key_label: str = "Correct answers"
    gap_label: str = "Lucka"


@dataclass(frozen=True)
class ExamNetPdfTargetProfileContext:
    """Read-only target-profile context passed to Exam.net PDF item strategies."""

    target_id: str
    profile_version: str
    label_policy: ExamNetPdfItemLabelPolicy
    allow_gap_open_cloze_alternate_layout: bool = False


@dataclass(frozen=True)
class ExamNetPdfItemStrategyResult:
    """Rendered target item section plus warnings emitted by one strategy."""

    item: DigiExamExamNetPdfItemRender | None
    warnings: tuple[DigiExamExamNetPdfWarning, ...] = ()


class ExamNetPdfItemRenderingStrategy(Protocol):
    """Strategy protocol for one neutral item family in an Exam.net PDF target."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        """Render one immutable neutral PDF item into an Exam.net section."""
        ...


@dataclass(frozen=True)
class ExamNetPdfItemRenderingPolicyRegistry:
    """Registry that selects a target item strategy without widening callers."""

    strategies_by_item_kind: Mapping[PdfExamItemKind, ExamNetPdfItemRenderingStrategy]
    unsupported_strategy: ExamNetPdfItemRenderingStrategy

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        """Render one item with the registered strategy for its neutral kind."""

        strategy = self.strategies_by_item_kind.get(item.kind, self.unsupported_strategy)
        return strategy.render(item=item, context=context)


@dataclass(frozen=True)
class OpenEndedExamNetPdfItemStrategy:
    """Render open-response items as Exam.net PDF free-text sections."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        labels = context.label_policy
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=_item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.free_text_type_label,
                    instruction="",
                    body_html="",
                    item_type_marker=labels.source_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class SingleChoiceExamNetPdfItemStrategy:
    """Render keyed single-answer choice items for the Exam.net PDF target."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        option_text_by_id, warnings = _option_text_by_id(item)
        if warnings:
            return ExamNetPdfItemStrategyResult(item=None, warnings=warnings)
        if not option_text_by_id or not item.answer_key.available:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(_missing_answer_key(item),))
        if len(item.answer_key.correct_option_ids) != 1:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(_answer_key_mismatch(item, "single-answer choice needs one key"),),
            )

        correct_answer = option_text_by_id.get(item.answer_key.correct_option_ids[0])
        if correct_answer is None:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(_answer_key_mismatch(item, "correct id is not present in options"),),
            )

        labels = context.label_policy
        body_html = _options_html(tuple(option_text_by_id.values()))
        body_html += (
            f'<p class="answer-key">{escape(labels.single_answer_key_label)}: '
            f"{escape(correct_answer)}</p>"
        )
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=_item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.choice_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.target_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class MultipleResponseExamNetPdfItemStrategy:
    """Render keyed multiple-response items for the Exam.net PDF target."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        option_text_by_id, warnings = _option_text_by_id(item)
        if warnings:
            return ExamNetPdfItemStrategyResult(item=None, warnings=warnings)
        if not option_text_by_id or not item.answer_key.available:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(_missing_answer_key(item),))
        if not item.answer_key.correct_option_ids:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(_answer_key_mismatch(item, "multiple response needs a key"),),
            )

        correct_answers: list[str] = []
        for correct_id in item.answer_key.correct_option_ids:
            correct_answer = option_text_by_id.get(correct_id)
            if correct_answer is None:
                return ExamNetPdfItemStrategyResult(
                    item=None,
                    warnings=(_answer_key_mismatch(item, "correct id is not present in options"),),
                )
            correct_answers.append(correct_answer)

        labels = context.label_policy
        body_html = _options_html(tuple(option_text_by_id.values()))
        body_html += (
            f'<p class="answer-key">{escape(labels.multiple_answer_key_label)}: '
            f"{escape('; '.join(correct_answers))}</p>"
        )
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=_item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.multiple_response_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.target_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class GapOpenClozeExamNetPdfItemStrategy:
    """Render keyed gap/open-cloze items without relabeling them as free text."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        if not item.answer_key.correct_gap_answers:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(_missing_answer_key(item),))
        missing_key_labels = _missing_gap_key_labels(item, context.label_policy)
        if missing_key_labels:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(
                    _answer_key_mismatch(
                        item,
                        f"missing accepted values for {missing_key_labels}",
                    ),
                ),
            )

        labels = context.label_policy
        body_html = _gap_answer_key_html(item, labels)
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=_item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.gap_open_cloze_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.source_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class UnsupportedExamNetPdfItemStrategy:
    """Fail closed for neutral item kinds without a governed PDF target shape."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        _ = context
        if item.source_item_type_label:
            message = (
                f"Item type {item.source_item_type_label} has no governed Exam.net "
                "PDF-converter target shape yet."
            )
        else:
            message = (
                f"Item kind {item.kind.value} has no governed Exam.net "
                "PDF-converter target shape yet."
            )
        return ExamNetPdfItemStrategyResult(
            item=None,
            warnings=(
                DigiExamExamNetPdfWarning(
                    code=DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE,
                    message=message,
                    item_id=item.item_id,
                ),
            ),
        )


DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT = ExamNetPdfTargetProfileContext(
    target_id="examnet_pdf",
    profile_version="examnet-pdf-swedish-v1",
    label_policy=ExamNetPdfItemLabelPolicy(),
)

DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY = ExamNetPdfItemRenderingPolicyRegistry(
    strategies_by_item_kind={
        PdfExamItemKind.OPEN_RESPONSE: OpenEndedExamNetPdfItemStrategy(),
        PdfExamItemKind.SINGLE_CHOICE: SingleChoiceExamNetPdfItemStrategy(),
        PdfExamItemKind.MULTIPLE_RESPONSE: MultipleResponseExamNetPdfItemStrategy(),
        PdfExamItemKind.GAP_OPEN_CLOZE: GapOpenClozeExamNetPdfItemStrategy(),
    },
    unsupported_strategy=UnsupportedExamNetPdfItemStrategy(),
)


def _option_text_by_id(
    item: PdfExamItemSemantics,
) -> tuple[dict[int, str], tuple[DigiExamExamNetPdfWarning, ...]]:
    option_text_by_id: dict[int, str] = {}
    warnings: list[DigiExamExamNetPdfWarning] = []
    for option in item.options:
        option_text = " ".join(option.text.split())
        if option_text == "":
            continue
        if _LABELLED_OPTION_PATTERN.match(option_text):
            warnings.append(
                DigiExamExamNetPdfWarning(
                    code=DigiExamExamNetPdfWarningCode.OPTION_TEXT_LOOKS_LABELLED,
                    message=f"Option text for item {item.item_id} looks source-labelled.",
                    item_id=item.item_id,
                )
            )
        option_text_by_id[option.option_id] = option_text

    if len(set(option_text_by_id.values())) != len(option_text_by_id):
        return {}, (_answer_key_mismatch(item, "duplicate option text is unsafe"),)
    return option_text_by_id, tuple(warnings)


def _missing_answer_key(item: PdfExamItemSemantics) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED,
        message=f"Item {item.item_id} needs source-proven answer-key data before PDF render.",
        item_id=item.item_id,
    )


def _answer_key_mismatch(
    item: PdfExamItemSemantics,
    reason: str,
) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH,
        message=f"Item {item.item_id} cannot render safely: {reason}.",
        item_id=item.item_id,
    )


def _options_html(options: tuple[str, ...]) -> str:
    options_html = "".join(f"<p>{escape(option)}</p>" for option in options)
    return f'<div class="options">{options_html}</div>'


def _missing_gap_key_labels(
    item: PdfExamItemSemantics,
    labels: ExamNetPdfItemLabelPolicy,
) -> str:
    values_by_gap_id = _gap_values_by_gap_id(item)
    missing_labels = tuple(
        f"{labels.gap_label} {index}"
        for index, gap in enumerate(item.gaps, start=1)
        if not values_by_gap_id.get(gap.gap_id)
    )
    return ", ".join(missing_labels)


def _gap_answer_key_html(
    item: PdfExamItemSemantics,
    labels: ExamNetPdfItemLabelPolicy,
) -> str:
    values_by_gap_id = _gap_values_by_gap_id(item)
    if len(item.gaps) == 1:
        values = values_by_gap_id.get(item.gaps[0].gap_id, ())
        return (
            f'<p class="answer-key">{escape(labels.multiple_answer_key_label)}: '
            f"{escape('; '.join(values))}</p>"
        )
    rows = "".join(
        f"<p>{escape(labels.gap_label)} {index}: "
        f"{escape('; '.join(values_by_gap_id.get(gap.gap_id, ())))}</p>"
        for index, gap in enumerate(item.gaps, start=1)
    )
    return f'<div class="answer-key"><p>{escape(labels.multiple_answer_key_label)}:</p>{rows}</div>'


def _gap_values_by_gap_id(item: PdfExamItemSemantics) -> dict[str, tuple[str, ...]]:
    values_by_gap_id: dict[str, list[str]] = {gap.gap_id: [] for gap in item.gaps}
    for answer in item.answer_key.correct_gap_answers:
        value = answer.value.strip()
        if value and answer.gap_id in values_by_gap_id:
            values_by_gap_id[answer.gap_id].append(value)
    return {gap_id: tuple(values) for gap_id, values in values_by_gap_id.items()}


def _item_shell(
    *,
    item: PdfExamItemSemantics,
    labels: ExamNetPdfItemLabelPolicy,
    item_type_label: str,
    instruction: str,
    body_html: str,
    item_type_marker: str,
) -> str:
    instruction_html = f"<p>{escape(instruction)}</p>" if instruction else ""
    return (
        '<section class="exam-item">'
        f"<h2>Fråga {item.sequence}</h2>"
        f'<p class="points">{escape(labels.point_label)}: {item.points}</p>'
        f'<p class="item-type">{escape(item_type_marker)}: {escape(item_type_label)}</p>'
        f"{instruction_html}"
        f'<div class="prompt">{item.prompt_html}</div>'
        f"{body_html}"
        "</section>"
    )
