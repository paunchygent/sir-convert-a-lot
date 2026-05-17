"""Exam.net PDF renderer item section assembly.

Purpose:
    Convert supported DigiExam IR items into the promoted Exam.net
    PDF-converter text shape, with target warnings for unsafe items.

Relationships:
    - Uses prompt sanitation from `domain.digiexam_examnet_pdf_prompt`.
    - Produces item render contracts consumed by
      `domain.digiexam_examnet_pdf_html`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from html import escape

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    AssetReferenceKey,
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfItemRenderResult,
    DigiExamExamNetPdfRenderPolicy,
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

_LABELLED_OPTION_PATTERN = re.compile(r"^(?:[A-Za-z]|\d+)[.)]\s+")


def render_examnet_pdf_items(
    *,
    exam: DigiExamIntermediateExam,
    asset_paths_by_reference: Mapping[AssetReferenceKey, str],
    render_policy: DigiExamExamNetPdfRenderPolicy | None = None,
) -> DigiExamExamNetPdfItemRenderResult:
    """Render all supported IR items into Exam.net PDF sections."""

    resolved_policy = render_policy or DigiExamExamNetPdfRenderPolicy()
    items: list[DigiExamExamNetPdfItemRender] = []
    warnings: list[DigiExamExamNetPdfWarning] = []
    for item in exam.items:
        item_render, item_warnings = _render_item(
            item=item,
            asset_paths_by_reference=asset_paths_by_reference,
            accepted_current_state=resolved_policy.accepts_current_state(item.item_id),
        )
        warnings.extend(item_warnings)
        if item_render is not None:
            items.append(item_render)

    return DigiExamExamNetPdfItemRenderResult(items=tuple(items), warnings=tuple(warnings))


def _render_item(
    *,
    item: DigiExamIrItem,
    asset_paths_by_reference: Mapping[AssetReferenceKey, str],
    accepted_current_state: bool,
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

    if item.item_type == DigiExamItemType.OPEN_ENDED:
        return _open_ended_item(item, points, prompt_render.html), ()
    if item.item_type in {DigiExamItemType.MULTIPLE_CHOICE, DigiExamItemType.SINGLE_CHOICE}:
        return _single_choice_item(
            item,
            points,
            prompt_render.html,
            accepted_current_state=accepted_current_state,
        )
    if item.item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return _multiple_response_item(
            item,
            points,
            prompt_render.html,
            accepted_current_state=accepted_current_state,
        )
    if item.item_type == DigiExamItemType.GAP_FILL:
        return _short_answer_item(
            item,
            points,
            prompt_render.html,
            accepted_current_state=accepted_current_state,
        )

    return None, (
        DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE,
            message=(
                f"Item type {item.item_type.value} has no governed Exam.net "
                "PDF-converter target shape yet."
            ),
            item_id=item.item_id,
        ),
    )


def _points(item: DigiExamIrItem) -> int | DigiExamExamNetPdfWarning:
    if item.max_score is None:
        return DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.MISSING_POINT_VALUE,
            message=f"Item {item.item_id} has no point value.",
            item_id=item.item_id,
        )
    return item.max_score


def _open_ended_item(
    item: DigiExamIrItem, points: int, prompt_html: str
) -> DigiExamExamNetPdfItemRender:
    return DigiExamExamNetPdfItemRender(
        html=_item_shell(
            item=item,
            points=points,
            item_type_label="Fritext",
            instruction="Skriv ditt svar i Exam.net.",
            prompt_html=prompt_html,
            body_html="",
            item_type_marker="Typ",
        )
    )


def _single_choice_item(
    item: DigiExamIrItem,
    points: int,
    prompt_html: str,
    *,
    accepted_current_state: bool,
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    if item.answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT and accepted_current_state:
        return _manual_unkeyed_choice_item(
            item,
            points,
            prompt_html,
            source_type_label="flervalsfråga med ett svar",
        )

    option_text_by_id, warnings = _option_text_by_id(item)
    if warnings:
        return None, warnings
    if not option_text_by_id or item.answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT:
        return None, (_missing_answer_key(item),)
    if len(item.answer_key.correct_alternative_ids) != 1:
        return None, (_answer_key_mismatch(item, "single-answer choice needs one key"),)

    correct_answer = option_text_by_id.get(item.answer_key.correct_alternative_ids[0])
    if correct_answer is None:
        return None, (_answer_key_mismatch(item, "correct id is not present in options"),)

    body_html = _options_html(tuple(option_text_by_id.values()))
    body_html += f'<p class="answer-key">Correct answer: {escape(correct_answer)}</p>'
    return (
        DigiExamExamNetPdfItemRender(
            html=_item_shell(
                item=item,
                points=points,
                item_type_label="Multiple choice",
                instruction="Choose one answer",
                prompt_html=prompt_html,
                body_html=body_html,
            )
        ),
        (),
    )


def _multiple_response_item(
    item: DigiExamIrItem,
    points: int,
    prompt_html: str,
    *,
    accepted_current_state: bool,
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    if item.answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT and accepted_current_state:
        return _manual_unkeyed_choice_item(
            item,
            points,
            prompt_html,
            source_type_label="flervalsfråga med flera svar",
        )

    option_text_by_id, warnings = _option_text_by_id(item)
    if warnings:
        return None, warnings
    if not option_text_by_id or item.answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT:
        return None, (_missing_answer_key(item),)
    if not item.answer_key.correct_alternative_ids:
        return None, (_answer_key_mismatch(item, "multiple response needs a key"),)

    correct_answers: list[str] = []
    for correct_id in item.answer_key.correct_alternative_ids:
        correct_answer = option_text_by_id.get(correct_id)
        if correct_answer is None:
            return None, (_answer_key_mismatch(item, "correct id is not present in options"),)
        correct_answers.append(correct_answer)

    body_html = _options_html(tuple(option_text_by_id.values()))
    body_html += f'<p class="answer-key">Correct answers: {escape("; ".join(correct_answers))}</p>'
    return (
        DigiExamExamNetPdfItemRender(
            html=_item_shell(
                item=item,
                points=points,
                item_type_label="Multiple response",
                instruction="Choose all correct answers",
                prompt_html=prompt_html,
                body_html=body_html,
            )
        ),
        (),
    )


def _short_answer_item(
    item: DigiExamIrItem,
    points: int,
    prompt_html: str,
    *,
    accepted_current_state: bool,
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    if not item.answer_key.correct_gap_answers and accepted_current_state:
        return _manual_unkeyed_gap_item(item, points, prompt_html)

    if not item.answer_key.correct_gap_answers:
        return None, (_missing_answer_key(item),)
    missing_key_labels = _missing_gap_key_labels(item)
    if missing_key_labels:
        return None, (
            _answer_key_mismatch(item, f"missing accepted values for {missing_key_labels}"),
        )

    body_html = _gap_answer_key_html(item)
    return (
        DigiExamExamNetPdfItemRender(
            html=_item_shell(
                item=item,
                points=points,
                item_type_label="Fritext",
                instruction="",
                prompt_html=prompt_html,
                body_html=body_html,
                item_type_marker="Typ",
            )
        ),
        (),
    )


def _manual_unkeyed_choice_item(
    item: DigiExamIrItem,
    points: int,
    prompt_html: str,
    *,
    source_type_label: str,
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    option_texts = _manual_option_texts(item)
    if not option_texts:
        return None, (_answer_key_mismatch(item, "manual choice rendering needs options"),)
    return (
        DigiExamExamNetPdfItemRender(
            html=_item_shell(
                item=item,
                points=points,
                item_type_label="Fritext",
                instruction=f"Ursprunglig {source_type_label}. Bedöms manuellt efter import.",
                prompt_html=prompt_html,
                body_html=_options_html(option_texts),
                item_type_marker="Typ",
            )
        ),
        (
            DigiExamExamNetPdfWarning(
                code=DigiExamExamNetPdfWarningCode.MANUAL_UNKEYED_CHOICE_RENDERED,
                message=(
                    f"Item {item.item_id} rendered as manual/unkeyed PDF because "
                    "accepted-current-state was requested without trusted choice key data."
                ),
                item_id=item.item_id,
                blocking=False,
            ),
        ),
    )


def _manual_unkeyed_gap_item(
    item: DigiExamIrItem,
    points: int,
    prompt_html: str,
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    warnings = [
        DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.MANUAL_UNKEYED_GAP_OPEN_CLOZE_RENDERED,
            message=(
                f"Item {item.item_id} rendered as manual/unkeyed PDF because "
                "accepted-current-state was requested without trusted gap accepted values."
            ),
            item_id=item.item_id,
            blocking=False,
        ),
        DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.EXAMNET_PDF_GAP_OPEN_CLOZE_NATIVE_SUPPORT_UNPROVEN,
            message=(
                f"Item {item.item_id} uses degraded manual/free-text PDF rendering because "
                "native Exam.net gap/open-cloze PDF import is unproven."
            ),
            item_id=item.item_id,
            blocking=False,
        ),
    ]
    if len(item.gaps) != 1:
        warnings.append(
            DigiExamExamNetPdfWarning(
                code=DigiExamExamNetPdfWarningCode.EXAMNET_PDF_MULTI_GAP_OPEN_CLOZE_DEGRADED,
                message=(
                    f"Item {item.item_id} has {len(item.gaps)} gaps and was rendered through "
                    "the degraded manual/free-text PDF profile."
                ),
                item_id=item.item_id,
                blocking=False,
            )
        )
    return (
        DigiExamExamNetPdfItemRender(
            html=_item_shell(
                item=item,
                points=points,
                item_type_label="Fritext",
                instruction="Ursprunglig lucktext. Bedöms manuellt efter import.",
                prompt_html=prompt_html,
                body_html=_gap_order_html(item),
                item_type_marker="Typ",
            )
        ),
        tuple(warnings),
    )


def _option_text_by_id(
    item: DigiExamIrItem,
) -> tuple[dict[int, str], tuple[DigiExamExamNetPdfWarning, ...]]:
    option_text_by_id: dict[int, str] = {}
    warnings: list[DigiExamExamNetPdfWarning] = []
    for alternative in item.alternatives:
        option_text = " ".join(alternative.title.split())
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
        option_text_by_id[alternative.id] = option_text

    if len(set(option_text_by_id.values())) != len(option_text_by_id):
        return {}, (_answer_key_mismatch(item, "duplicate option text is unsafe"),)
    return option_text_by_id, tuple(warnings)


def _manual_option_texts(item: DigiExamIrItem) -> tuple[str, ...]:
    return tuple(
        option_text
        for option_text in (
            " ".join(alternative.title.split()) for alternative in item.alternatives
        )
        if option_text
    )


def _missing_answer_key(item: DigiExamIrItem) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED,
        message=f"Item {item.item_id} needs source-proven answer-key data before PDF render.",
        item_id=item.item_id,
    )


def _answer_key_mismatch(item: DigiExamIrItem, reason: str) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH,
        message=f"Item {item.item_id} cannot render safely: {reason}.",
        item_id=item.item_id,
    )


def _options_html(options: tuple[str, ...]) -> str:
    options_html = "".join(f"<p>{escape(option)}</p>" for option in options)
    return f'<div class="options">{options_html}</div>'


def _gap_order_html(item: DigiExamIrItem) -> str:
    if not item.gaps:
        return '<div class="gap-list"><p>Lucktextfrågan bedöms manuellt efter import.</p></div>'
    gap_rows = "".join(f"<p>Lucka {index}</p>" for index, _gap in enumerate(item.gaps, start=1))
    return f'<div class="gap-list">{gap_rows}</div>'


def _missing_gap_key_labels(item: DigiExamIrItem) -> str:
    values_by_gap_id = _gap_values_by_gap_id(item)
    missing_labels = tuple(
        f"Lucka {index}"
        for index, gap in enumerate(item.gaps, start=1)
        if not values_by_gap_id.get(gap.guid)
    )
    return ", ".join(missing_labels)


def _gap_answer_key_html(item: DigiExamIrItem) -> str:
    values_by_gap_id = _gap_values_by_gap_id(item)
    if len(item.gaps) == 1:
        values = values_by_gap_id.get(item.gaps[0].guid, ())
        return f'<p class="answer-key">Correct answers: {escape("; ".join(values))}</p>'
    rows = "".join(
        f"<p>Lucka {index}: {escape('; '.join(values_by_gap_id.get(gap.guid, ())))}</p>"
        for index, gap in enumerate(item.gaps, start=1)
    )
    return f'<div class="answer-key"><p>Correct answers:</p>{rows}</div>'


def _gap_values_by_gap_id(item: DigiExamIrItem) -> dict[str, tuple[str, ...]]:
    values_by_gap_id: dict[str, list[str]] = {gap.guid: [] for gap in item.gaps}
    for answer in item.answer_key.correct_gap_answers:
        value = answer.value.strip()
        if value and answer.guid in values_by_gap_id:
            values_by_gap_id[answer.guid].append(value)
    return {gap_id: tuple(values) for gap_id, values in values_by_gap_id.items()}


def _item_shell(
    *,
    item: DigiExamIrItem,
    points: int,
    item_type_label: str,
    instruction: str,
    prompt_html: str,
    body_html: str,
    item_type_marker: str = "Type",
) -> str:
    instruction_html = f"<p>{escape(instruction)}</p>" if instruction else ""
    return (
        '<section class="exam-item">'
        f"<h2>Fråga {item.sequence}</h2>"
        f'<p class="points">Poängvärde: {points}</p>'
        f'<p class="item-type">{escape(item_type_marker)}: {escape(item_type_label)}</p>'
        f"{instruction_html}"
        f'<div class="prompt">{prompt_html}</div>'
        f"{body_html}"
        "</section>"
    )
