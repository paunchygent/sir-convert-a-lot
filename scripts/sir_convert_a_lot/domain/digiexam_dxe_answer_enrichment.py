"""DigiExam `.dxe` answer-key enrichment validation.

Purpose:
    Bind sanitized DigiExam result-PDF answer evidence to observed `.dxe`
    alternatives and blanks without inventing answer keys when the binding is
    ambiguous or structurally incomplete.

Relationships:
    - Used by `domain.digiexam_dxe_parser` after `.dxe` structure extraction.
    - Consumes `domain.digiexam_result_pdf_answers` evidence items.
    - Emits shared DigiExam warning and answer value objects for downstream
      renderer-neutral contracts.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAlternative,
    DigiExamGap,
    DigiExamGapAnswer,
    DigiExamSourceSpan,
    DigiExamWarning,
    DigiExamWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerItem,
    normalize_result_text,
)


@dataclass(frozen=True)
class DigiExamDxeAnswerMatch:
    """Validated answer evidence bound to the corresponding `.dxe` structure."""

    correct_alternative_ids: tuple[int, ...]
    correct_gap_answers: tuple[DigiExamGapAnswer, ...]
    warnings: tuple[DigiExamWarning, ...]


def dxe_gap_answers(gaps: tuple[DigiExamGap, ...]) -> tuple[DigiExamGapAnswer, ...]:
    """Return populated `.dxe` gap validations bound to their blank GUIDs."""

    return tuple(
        DigiExamGapAnswer(guid=gap.guid, value=value) for gap in gaps for value in gap.validations
    )


def match_result_pdf_answers(
    *,
    alternatives: tuple[DigiExamAlternative, ...],
    gaps: tuple[DigiExamGap, ...],
    evidence_item: DigiExamResultPdfAnswerItem | None,
    source_span: DigiExamSourceSpan,
) -> DigiExamDxeAnswerMatch:
    """Bind result-PDF answer evidence to `.dxe` alternatives and gaps."""

    if evidence_item is None:
        return DigiExamDxeAnswerMatch(
            correct_alternative_ids=(), correct_gap_answers=(), warnings=()
        )
    alternative_match = _alternative_match(alternatives, evidence_item, source_span)
    gap_match = _gap_match(gaps, evidence_item, source_span)
    return DigiExamDxeAnswerMatch(
        correct_alternative_ids=alternative_match.correct_alternative_ids,
        correct_gap_answers=gap_match.correct_gap_answers,
        warnings=alternative_match.warnings + gap_match.warnings,
    )


def _alternative_match(
    alternatives: tuple[DigiExamAlternative, ...],
    evidence_item: DigiExamResultPdfAnswerItem,
    source_span: DigiExamSourceSpan,
) -> DigiExamDxeAnswerMatch:
    correct_ids: list[int] = []
    warnings: list[DigiExamWarning] = []
    for label in evidence_item.correct_alternative_texts:
        normalized_label = normalize_result_text(label)
        matches = tuple(
            alternative.id
            for alternative in alternatives
            if normalize_result_text(alternative.title) == normalized_label
        )
        if len(matches) != 1:
            warnings.append(
                DigiExamWarning(
                    code=DigiExamWarningCode.UNSUPPORTED_STRUCTURE,
                    message=(
                        "Result-PDF correct alternative label does not bind to exactly "
                        f"one `.dxe` alternative for '{evidence_item.title}': {label!r}."
                    ),
                    blocking=True,
                    source_span=source_span,
                )
            )
            continue
        correct_ids.append(matches[0])
    return DigiExamDxeAnswerMatch(
        correct_alternative_ids=tuple(correct_ids) if not warnings else (),
        correct_gap_answers=(),
        warnings=tuple(warnings),
    )


def _gap_match(
    gaps: tuple[DigiExamGap, ...],
    evidence_item: DigiExamResultPdfAnswerItem,
    source_span: DigiExamSourceSpan,
) -> DigiExamDxeAnswerMatch:
    values = evidence_item.correct_gap_values
    if not values:
        return DigiExamDxeAnswerMatch(
            correct_alternative_ids=(), correct_gap_answers=(), warnings=()
        )
    if len(values) != len(gaps):
        return DigiExamDxeAnswerMatch(
            correct_alternative_ids=(),
            correct_gap_answers=(),
            warnings=(
                DigiExamWarning(
                    code=DigiExamWarningCode.UNSUPPORTED_STRUCTURE,
                    message=(
                        "Result-PDF gap answer count does not match `.dxe` blanks for "
                        f"'{evidence_item.title}': {len(values)} answers for {len(gaps)} gaps."
                    ),
                    blocking=True,
                    source_span=source_span,
                ),
            ),
        )
    return DigiExamDxeAnswerMatch(
        correct_alternative_ids=(),
        correct_gap_answers=tuple(
            DigiExamGapAnswer(guid=gap.guid, value=value)
            for gap, value in zip(gaps, values, strict=True)
        ),
        warnings=(),
    )
