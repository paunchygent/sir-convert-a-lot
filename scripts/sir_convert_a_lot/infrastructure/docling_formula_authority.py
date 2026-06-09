"""Source-backed formula authority for Docling PDF conversion.

Purpose:
    Represent coordinate-backed PDF source-layer evidence and decide when
    generated Docling formula output is allowed to become the conversion
    artifact for born-digital PDFs.

Relationships:
    - Used by `infrastructure.docling_formula_fallback` at the formula VLM
      acceptance boundary.
    - Complements `infrastructure.docling_formula_quality`, which detects
      malformed generated formula output but does not decide source authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

FORMULA_SOURCE_BACKED_VLM_REJECTED_WARNING = "docling_formula_source_backed_vlm_rejected"


class SourceFormulaEvidenceState(StrEnum):
    """Source-layer authority state for formula-bearing PDF conversion."""

    USABLE = "usable"
    PARTIAL_OR_UNUSABLE = "partial_or_unusable"
    ABSENT = "absent"


@dataclass(frozen=True)
class SourceLayerFormulaEvidence:
    """Coordinate-backed source-layer extraction summary for one PDF."""

    state: SourceFormulaEvidenceState
    method: str
    page_count: int
    word_count: int
    raw_character_count: int
    text_character_count: int
    pages_with_words: int
    pages_with_raw_characters: int
    reason: str

    @property
    def is_authoritative(self) -> bool:
        """Return whether generated formula output must pass a source-backed gate."""
        return self.state is SourceFormulaEvidenceState.USABLE


@dataclass(frozen=True)
class FormulaAuthorityDecision:
    """Decision made at the generated-formula acceptance boundary."""

    use_generated_output: bool
    warning_codes: tuple[str, ...]
    reason: str


def decide_formula_authority(
    *,
    source_evidence: SourceLayerFormulaEvidence,
    generated_output_has_quality_defect: bool,
) -> FormulaAuthorityDecision:
    """Decide whether a generated formula candidate can be committed."""
    if source_evidence.is_authoritative and generated_output_has_quality_defect:
        return FormulaAuthorityDecision(
            use_generated_output=False,
            warning_codes=(FORMULA_SOURCE_BACKED_VLM_REJECTED_WARNING,),
            reason="source_layer_authoritative_and_generated_formula_quality_defect",
        )
    return FormulaAuthorityDecision(
        use_generated_output=True,
        warning_codes=(),
        reason="generated_formula_output_allowed",
    )


def collect_source_layer_formula_evidence(source_bytes: bytes) -> SourceLayerFormulaEvidence:
    """Collect coordinate-backed text evidence from a PDF source layer."""
    try:
        import pymupdf
    except Exception:
        return _empty_evidence(
            state=SourceFormulaEvidenceState.PARTIAL_OR_UNUSABLE,
            reason="pymupdf_unavailable",
        )

    try:
        with pymupdf.open(stream=source_bytes, filetype="pdf") as document:
            page_count = len(document)
            word_count = 0
            raw_character_count = 0
            text_character_count = 0
            pages_with_words = 0
            pages_with_raw_characters = 0

            for page in document:
                page_words = _extract_coordinate_word_count(page.get_text("words", sort=True))
                page_raw_characters = _extract_raw_character_count(page.get_text("rawdict"))
                page_text = page.get_text("text", sort=True)
                word_count += page_words
                raw_character_count += page_raw_characters
                text_character_count += len(page_text.strip())
                if page_words > 0:
                    pages_with_words += 1
                if page_raw_characters > 0:
                    pages_with_raw_characters += 1
    except Exception:
        return _empty_evidence(
            state=SourceFormulaEvidenceState.PARTIAL_OR_UNUSABLE,
            reason="source_layer_extraction_failed",
        )

    if page_count == 0:
        state = SourceFormulaEvidenceState.ABSENT
        reason = "pdf_has_no_pages"
    elif word_count > 0 and raw_character_count > 0 and text_character_count > 0:
        state = SourceFormulaEvidenceState.USABLE
        reason = "coordinate_words_and_raw_characters_present"
    elif word_count == 0 and raw_character_count == 0 and text_character_count == 0:
        state = SourceFormulaEvidenceState.ABSENT
        reason = "no_source_layer_text_detected"
    else:
        state = SourceFormulaEvidenceState.PARTIAL_OR_UNUSABLE
        reason = "source_layer_text_incomplete"

    return SourceLayerFormulaEvidence(
        state=state,
        method="pymupdf.get_text(words/rawdict/text)",
        page_count=page_count,
        word_count=word_count,
        raw_character_count=raw_character_count,
        text_character_count=text_character_count,
        pages_with_words=pages_with_words,
        pages_with_raw_characters=pages_with_raw_characters,
        reason=reason,
    )


def _empty_evidence(
    *,
    state: SourceFormulaEvidenceState,
    reason: str,
) -> SourceLayerFormulaEvidence:
    return SourceLayerFormulaEvidence(
        state=state,
        method="pymupdf.get_text(words/rawdict/text)",
        page_count=0,
        word_count=0,
        raw_character_count=0,
        text_character_count=0,
        pages_with_words=0,
        pages_with_raw_characters=0,
        reason=reason,
    )


def _extract_coordinate_word_count(words_payload: object) -> int:
    if not isinstance(words_payload, Sequence):
        return 0
    word_count = 0
    for item in words_payload:
        if _is_coordinate_word(item):
            word_count += 1
    return word_count


def _is_coordinate_word(item: object) -> bool:
    if not isinstance(item, Sequence) or isinstance(item, str | bytes):
        return False
    if len(item) < 5:
        return False
    return (
        _is_number(item[0])
        and _is_number(item[1])
        and _is_number(item[2])
        and _is_number(item[3])
        and isinstance(item[4], str)
        and item[4].strip() != ""
    )


def _extract_raw_character_count(rawdict_payload: object) -> int:
    if not isinstance(rawdict_payload, Mapping):
        return 0
    return _count_rawdict_characters(rawdict_payload)


def _count_rawdict_characters(node: object) -> int:
    if isinstance(node, Mapping):
        character = node.get("c")
        count = 1 if isinstance(character, str) and character != "" else 0
        for value in node.values():
            count += _count_rawdict_characters(value)
        return count
    if isinstance(node, Sequence) and not isinstance(node, str | bytes):
        return sum(_count_rawdict_characters(value) for value in node)
    return 0


def _is_number(value: object) -> bool:
    return isinstance(value, int | float)
