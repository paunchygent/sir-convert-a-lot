"""DigiExam parser domain result contracts.

Purpose:
    Define the typed value objects emitted by DigiExam source parsers, including
    item structure, source evidence, readiness status, answer-key provenance,
    and warning provenance.

Relationships:
    - Used by `domain.digiexam_parser` for legacy PDF fallback parser output.
    - Used by `domain.digiexam_dxe_parser` for canonical `.dxe` parser output.
    - Used by `infrastructure.digiexam_pdf_text` for source-line and metadata
      handoff from PyMuPDF extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DigiExamItemType(StrEnum):
    """Item types observed in DigiExam parser fixture corpora."""

    OPEN_ENDED = "open_ended"
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_RESPONSE = "multiple_response"
    GAP_FILL = "gap_fill"
    MATCHING = "matching"
    UNKNOWN = "unknown"


class DigiExamParseStatus(StrEnum):
    """Machine-checkable parser readiness state."""

    SUCCESS = "success"
    BLOCKED = "blocked"


class DigiExamWarningCode(StrEnum):
    """Typed parser warning categories required by DigiExam parser tasks."""

    MISSING_ANSWER_KEY_PROVENANCE = "missing_answer_key_provenance"
    MISSING_REQUIRED_ANCHOR = "missing_required_anchor"
    LOSSY_SWEDISH_TEXT_EXTRACTION = "lossy_swedish_text_extraction"
    MALFORMED_SOURCE = "malformed_source"
    UNKNOWN_SOURCE_SHAPE = "unknown_source_shape"
    UNSUPPORTED_STRUCTURE = "unsupported_structure"
    INVALID_EMBEDDED_ASSET_BASE64 = "invalid_embedded_asset_base64"
    UNSUPPORTED_EMBEDDED_ASSET_MEDIA = "unsupported_embedded_asset_media"
    MISSING_EMBEDDED_ASSET_REFERENCE = "missing_embedded_asset_reference"
    UNUSED_EMBEDDED_ASSET_PAYLOAD = "unused_embedded_asset_payload"
    AMBIGUOUS_EMBEDDED_ASSET_BINDING = "ambiguous_embedded_asset_binding"


class DigiExamAnswerKeyProvenance(StrEnum):
    """Answer-key provenance states for parser output."""

    ABSENT = "absent"
    DXE_POPULATED_KEY = "dxe_populated_key"
    GRADED_RESULT_PDF_CORRECT_LABELS = "graded_result_pdf_correct_labels"
    MANUAL_TEACHER_KEY = "manual_teacher_key"
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
class DigiExamAlternative:
    """One ordered DigiExam alternative with source answer-key flags preserved."""

    id: int
    title: str
    about: str
    right: bool


@dataclass(frozen=True)
class DigiExamGap:
    """One DigiExam gap-fill blank with source validations preserved."""

    guid: str
    validations: tuple[str, ...]


@dataclass(frozen=True)
class DigiExamGapAnswer:
    """One correct gap-fill value bound to the corresponding DigiExam blank."""

    guid: str
    value: str


@dataclass(frozen=True)
class DigiExamGradingPolicy:
    """Observed DigiExam grading-policy fields for machine-marked items."""

    grading_type: int | None
    is_alternative_choice_limit_enabled: bool | None
    alternative_choice_limit: int | None


@dataclass(frozen=True)
class DigiExamEmbeddedAsset:
    """One decoded DigiExam embedded asset bound to a source item."""

    asset_id: str
    item_sequence: int
    source_image_index: int
    sha256: str
    media_type: str
    content_base64: str
    byte_length: int
    width_px: int
    height_px: int


@dataclass(frozen=True)
class DigiExamEmbeddedAssetReference:
    """One ordered bodyHTML reference to a decoded embedded asset."""

    asset_id: str
    source_image_index: int
    reference_order: int


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
    question_id: int | None = None
    digiexam_type_code: int | None = None
    prompt_html: str | None = None
    max_score: int | None = None
    alternatives: tuple[DigiExamAlternative, ...] = ()
    gaps: tuple[DigiExamGap, ...] = ()
    grading_policy: DigiExamGradingPolicy | None = None
    correct_alternative_ids: tuple[int, ...] = ()
    correct_gap_values: tuple[str, ...] = ()
    correct_gap_answers: tuple[DigiExamGapAnswer, ...] = ()
    embedded_assets: tuple[DigiExamEmbeddedAsset, ...] = ()
    embedded_asset_references: tuple[DigiExamEmbeddedAssetReference, ...] = ()


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
