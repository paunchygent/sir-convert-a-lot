"""DigiExam sanitized result-PDF answer evidence extraction.

Purpose:
    Extract only correct machine-marked answer evidence from sanitized DigiExam
    result-PDF text lines while discarding wrong answers and student-result data.

Relationships:
    - Consumes `DigiExamSourceLine` values from the PDF text infrastructure.
    - Feeds optional enrichment in `domain.digiexam_dxe_parser`.
    - Intentionally does not parse `.dxe` structure or Exam.net renderer syntax.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamSourceLine


@dataclass(frozen=True)
class DigiExamResultPdfAnswerItem:
    """Correct answer evidence extracted from one sanitized result-PDF item."""

    title: str
    correct_alternative_texts: tuple[str, ...]
    correct_gap_values: tuple[str, ...]


@dataclass(frozen=True)
class DigiExamResultPdfAnswerEvidence:
    """Correct machine-marked answer evidence extracted from a result PDF."""

    items: tuple[DigiExamResultPdfAnswerItem, ...]

    def item_for_title(self, title: str) -> DigiExamResultPdfAnswerItem | None:
        """Return the result-PDF answer item whose title matches the `.dxe` item."""

        normalized_title = normalize_result_text(title)
        for item in self.items:
            if normalize_result_text(item.title) == normalized_title:
                return item
        return None


@dataclass(frozen=True)
class _AnswerBlock:
    title: str
    lines: tuple[str, ...]


_CORRECT_RESULT_LABELS = frozenset({"Korrekt svar", "Korrekt alternativ"})
_WRONG_RESULT_LABEL = "Fel svar"
_RESULT_LABEL_RE = re.compile(r"^\((?P<label>[^)]+)\)\s*(?P<text>.+)$")
_NUMBERED_GAP_ANSWER_RE = re.compile(r"^(?P<number>\d+)\.\s+(?P<value>.+)$")


class DigiExamResultPdfAnswerExtractor:
    """Extract correct machine-marked answer evidence from result-PDF text lines."""

    def __init__(self, *, student_block_delimiter: str) -> None:
        """Create an extractor for a sanitized result-PDF student delimiter."""

        normalized_delimiter = normalize_result_text(student_block_delimiter)
        if normalized_delimiter == "":
            raise ValueError("Result-PDF student block delimiter must not be empty.")
        self._student_block_delimiter = normalized_delimiter

    def extract(self, lines: tuple[DigiExamSourceLine, ...]) -> DigiExamResultPdfAnswerEvidence:
        """Extract correct labels while ignoring wrong answers and student-result data."""

        items: list[DigiExamResultPdfAnswerItem] = []
        for block in _answer_blocks(lines, self._student_block_delimiter):
            correct_alternatives: list[str] = []
            correct_gap_values: list[str] = []
            gap_answer_section = False
            for line in block.lines:
                if line.startswith("Luckorna innehåller följande ord:"):
                    gap_answer_section = True
                    continue
                label_match = _RESULT_LABEL_RE.match(line)
                if label_match is not None:
                    label = normalize_result_text(label_match.group("label"))
                    text = normalize_result_text(label_match.group("text"))
                    if label in _CORRECT_RESULT_LABELS:
                        correct_alternatives.append(text)
                    elif label == _WRONG_RESULT_LABEL:
                        continue
                gap_match = _NUMBERED_GAP_ANSWER_RE.match(line)
                if gap_answer_section and gap_match is not None:
                    correct_gap_values.append(normalize_result_text(gap_match.group("value")))
            if correct_alternatives or correct_gap_values:
                items.append(
                    DigiExamResultPdfAnswerItem(
                        title=block.title,
                        correct_alternative_texts=tuple(correct_alternatives),
                        correct_gap_values=tuple(correct_gap_values),
                    )
                )
        return DigiExamResultPdfAnswerEvidence(items=tuple(items))


def _answer_blocks(
    lines: tuple[DigiExamSourceLine, ...], student_block_delimiter: str
) -> tuple[_AnswerBlock, ...]:
    blocks: list[_AnswerBlock] = []
    title: str | None = None
    block_lines: list[str] = []
    expecting_title = False

    for source_line in lines:
        text = normalize_result_text(source_line.text)
        if text == "":
            continue
        if text == student_block_delimiter:
            if title is not None:
                blocks.append(_AnswerBlock(title=title, lines=tuple(block_lines)))
            title = None
            block_lines = []
            expecting_title = True
            continue
        if expecting_title:
            title = text
            expecting_title = False
            continue
        if title is not None:
            block_lines.append(text)

    if title is not None:
        blocks.append(_AnswerBlock(title=title, lines=tuple(block_lines)))
    return tuple(blocks)


def normalize_result_text(value: str) -> str:
    """Normalize DigiExam result-PDF text spacing without changing content."""

    normalized = " ".join(value.split())
    return re.sub(r"\s+([),.:])", r"\1", normalized)
