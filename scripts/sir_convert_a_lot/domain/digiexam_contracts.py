"""DigiExam parser v1 domain result contracts.

Purpose:
    Define the typed value objects emitted by the DigiExam parser, including
    item structure, source evidence, readiness status, and warning provenance.

Relationships:
    - Used by `domain.digiexam_parser` for parser output.
    - Used by `infrastructure.digiexam_pdf_text` for source-line and metadata
      handoff from PyMuPDF extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DigiExamItemType(StrEnum):
    """Item types observed in the Task 267 fixture corpus."""

    OPEN_ENDED = "open_ended"
    MULTIPLE_CHOICE = "multiple_choice"
    MATCHING = "matching"
    UNKNOWN = "unknown"


class DigiExamParseStatus(StrEnum):
    """Machine-checkable parser readiness state."""

    SUCCESS = "success"
    BLOCKED = "blocked"


class DigiExamWarningCode(StrEnum):
    """Typed parser warning categories required by Task 267."""

    MISSING_ANSWER_KEY_PROVENANCE = "missing_answer_key_provenance"
    MISSING_REQUIRED_ANCHOR = "missing_required_anchor"
    LOSSY_SWEDISH_TEXT_EXTRACTION = "lossy_swedish_text_extraction"
    UNKNOWN_SOURCE_SHAPE = "unknown_source_shape"
    UNSUPPORTED_STRUCTURE = "unsupported_structure"


class DigiExamAnswerKeyProvenance(StrEnum):
    """Answer-key provenance states for parser output."""

    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class DigiExamSourceLine:
    """One layout-extracted source line with stable page/line evidence."""

    page_number: int
    line_number: int
    text: str


@dataclass(frozen=True)
class DigiExamSourceSpan:
    """Inclusive source evidence span for a parsed item."""

    start_page: int
    start_line: int
    end_page: int
    end_line: int


@dataclass(frozen=True)
class DigiExamPointMarker:
    """Observed point marker evidence."""

    points: int
    raw_text: str
    source_span: DigiExamSourceSpan


@dataclass(frozen=True)
class DigiExamWarning:
    """Typed parser warning with source evidence when available."""

    code: DigiExamWarningCode
    message: str
    blocking: bool
    source_span: DigiExamSourceSpan | None = None


@dataclass(frozen=True)
class DigiExamMatchingStructure:
    """Observed matching item structure from the source PDF."""

    left_prompts: tuple[str, ...]
    right_options: tuple[str, ...]
    blank_row_evidence: str | None


@dataclass(frozen=True)
class DigiExamItem:
    """Parsed DigiExam item with source evidence and provenance state."""

    header: str
    item_type: DigiExamItemType
    source_span: DigiExamSourceSpan
    prompt_lines: tuple[str, ...]
    point_marker: DigiExamPointMarker | None
    options: tuple[str, ...]
    matching: DigiExamMatchingStructure | None
    answer_key_provenance: DigiExamAnswerKeyProvenance
    warnings: tuple[DigiExamWarning, ...]


@dataclass(frozen=True)
class DigiExamDocumentMetadata:
    """Source document metadata relevant to parser validation."""

    filename: str
    page_count: int
    producer: str | None


@dataclass(frozen=True)
class DigiExamParseResult:
    """Top-level parser result boundary for downstream consumers."""

    metadata: DigiExamDocumentMetadata
    status: DigiExamParseStatus
    renderer_ready: bool
    items: tuple[DigiExamItem, ...]
    warnings: tuple[DigiExamWarning, ...]
