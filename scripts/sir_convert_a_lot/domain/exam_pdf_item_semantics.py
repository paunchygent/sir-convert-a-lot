"""Source-neutral PDF exam item semantics.

Purpose:
    Define the immutable item semantics that PDF target profiles consume after
    source parsers and adapters have converted source-specific exam shapes.

Relationships:
    - Built by source adapters such as the DigiExam PDF item coordinator.
    - Consumed by target profiles such as Exam.net PDF item strategies.
    - Deliberately excludes parser/source IR ownership, target readiness,
      artifact availability, QTI policy, and persistence concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PdfExamItemKind(StrEnum):
    """Source-neutral item families available to PDF target profiles."""

    OPEN_RESPONSE = "open_response"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_RESPONSE = "multiple_response"
    GAP_OPEN_CLOZE = "gap_open_cloze"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class PdfExamOptionSemantics:
    """One source-neutral choice option available to PDF target profiles."""

    option_id: int
    text: str


@dataclass(frozen=True)
class PdfExamGapSemantics:
    """One source-neutral gap/open-cloze slot."""

    gap_id: str


@dataclass(frozen=True)
class PdfExamGapAnswerSemantics:
    """One accepted answer value bound to a source-neutral gap slot."""

    gap_id: str
    value: str


@dataclass(frozen=True)
class PdfExamAnswerKeySemantics:
    """Source-neutral answer-key semantics available for target rendering."""

    available: bool
    correct_option_ids: tuple[int, ...] = ()
    correct_gap_answers: tuple[PdfExamGapAnswerSemantics, ...] = ()


@dataclass(frozen=True)
class PdfExamItemSemantics:
    """One source-neutral PDF exam item after source adapter normalization."""

    item_id: str
    sequence: int
    kind: PdfExamItemKind
    points: int
    prompt_html: str
    source_item_type_label: str | None = None
    options: tuple[PdfExamOptionSemantics, ...] = ()
    gaps: tuple[PdfExamGapSemantics, ...] = ()
    answer_key: PdfExamAnswerKeySemantics = PdfExamAnswerKeySemantics(available=False)
