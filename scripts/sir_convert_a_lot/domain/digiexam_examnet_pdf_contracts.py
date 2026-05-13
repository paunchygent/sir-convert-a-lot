"""Exam.net-oriented DigiExam PDF renderer contracts.

Purpose:
    Define the small value objects shared by the target PDF renderer domain
    modules and the infrastructure materializer.

Relationships:
    - Used by Exam.net PDF asset, prompt, item, and document planners.
    - Returned to `infrastructure.digiexam_examnet_pdf_renderer` for local
      HTML, image, and PDF artifact materialization.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

AssetReferenceKey = tuple[str, int]


class DigiExamExamNetPdfStatus(StrEnum):
    """Renderer readiness state for the Exam.net-oriented PDF target."""

    SUCCESS = "success"
    BLOCKED = "blocked"


class DigiExamExamNetPdfWarningCode(StrEnum):
    """Typed target-renderer blocking warnings."""

    PARSER_RESULT_BLOCKS_RENDERING = "parser_result_blocks_rendering"
    MISSING_POINT_VALUE = "missing_point_value"
    EMPTY_PROMPT = "empty_prompt"
    MANUAL_ANSWER_KEY_REQUIRED = "manual_answer_key_required"
    UNSUPPORTED_ITEM_TYPE = "unsupported_item_type"
    ALTERNATIVE_ANSWER_KEY_MISMATCH = "alternative_answer_key_mismatch"
    OPTION_TEXT_LOOKS_LABELLED = "option_text_looks_labelled"
    EMBEDDED_ASSET_PAYLOAD_MISSING = "embedded_asset_payload_missing"
    EMBEDDED_ASSET_PAYLOAD_INVALID = "embedded_asset_payload_invalid"
    EMBEDDED_ASSET_REFERENCE_MISSING = "embedded_asset_reference_missing"


@dataclass(frozen=True)
class DigiExamExamNetPdfWarning:
    """One target-renderer warning with optional item binding."""

    code: DigiExamExamNetPdfWarningCode
    message: str
    item_id: str | None
    blocking: bool = True


@dataclass(frozen=True)
class DigiExamExamNetPdfAssetFile:
    """One image file that must be materialized beside the renderer HTML."""

    asset_id: str
    relative_path: str
    media_type: str
    payload: bytes


@dataclass(frozen=True)
class DigiExamExamNetPdfAssetPreparation:
    """Asset materialization plan plus item/image reference lookup."""

    asset_files: tuple[DigiExamExamNetPdfAssetFile, ...]
    asset_paths_by_reference: Mapping[AssetReferenceKey, str]
    warnings: tuple[DigiExamExamNetPdfWarning, ...]


@dataclass(frozen=True)
class DigiExamExamNetPdfPromptRender:
    """Sanitized prompt HTML plus target-renderer warnings."""

    html: str
    warnings: tuple[DigiExamExamNetPdfWarning, ...]


@dataclass(frozen=True)
class DigiExamExamNetPdfItemRender:
    """One rendered Exam.net PDF-converter item section."""

    html: str


@dataclass(frozen=True)
class DigiExamExamNetPdfItemRenderResult:
    """Rendered item sections plus target-renderer warnings."""

    items: tuple[DigiExamExamNetPdfItemRender, ...]
    warnings: tuple[DigiExamExamNetPdfWarning, ...]


@dataclass(frozen=True)
class DigiExamExamNetPdfDocument:
    """Filesystem-free Exam.net PDF renderer document plan."""

    status: DigiExamExamNetPdfStatus
    html: str
    asset_files: tuple[DigiExamExamNetPdfAssetFile, ...]
    warnings: tuple[DigiExamExamNetPdfWarning, ...]
