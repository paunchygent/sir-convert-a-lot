"""Tests for source-backed Docling formula authority decisions.

Purpose:
    Prove the evidence and policy layer that prevents defective generated
    formula output from overwriting born-digital PDF source evidence.

Relationships:
    - Exercises `infrastructure.docling_formula_authority`.
    - Complements Docling backend tests that wire the policy into conversion.
"""

from __future__ import annotations

import pymupdf

from scripts.sir_convert_a_lot.infrastructure.docling_formula_authority import (
    FORMULA_SOURCE_BACKED_VLM_REJECTED_WARNING,
    SourceFormulaEvidenceState,
    collect_source_layer_formula_evidence,
    decide_formula_authority,
)


def test_born_digital_pdf_source_layer_is_usable() -> None:
    document = pymupdf.open()
    page = document.new_page()
    if page is None:
        raise RuntimeError("PyMuPDF returned no page for authority fixture.")
    page.insert_text((72, 72), "alpha + beta = gamma")
    source_bytes = document.write()

    evidence = collect_source_layer_formula_evidence(source_bytes)

    assert evidence.state is SourceFormulaEvidenceState.USABLE
    assert evidence.word_count > 0
    assert evidence.raw_character_count > 0
    assert evidence.text_character_count > 0
    assert evidence.pages_with_words == 1
    assert evidence.pages_with_raw_characters == 1


def test_blank_pdf_source_layer_is_absent() -> None:
    document = pymupdf.open()
    if document.new_page() is None:
        raise RuntimeError("PyMuPDF returned no page for blank authority fixture.")
    source_bytes = document.write()

    evidence = collect_source_layer_formula_evidence(source_bytes)

    assert evidence.state is SourceFormulaEvidenceState.ABSENT
    assert evidence.word_count == 0
    assert evidence.raw_character_count == 0
    assert evidence.text_character_count == 0


def test_authority_rejects_defective_generated_formula_with_usable_source() -> None:
    document = pymupdf.open()
    page = document.new_page()
    if page is None:
        raise RuntimeError("PyMuPDF returned no page for authority policy fixture.")
    page.insert_text((72, 72), "source-backed formula evidence")
    evidence = collect_source_layer_formula_evidence(document.write())

    decision = decide_formula_authority(
        source_evidence=evidence,
        generated_output_has_quality_defect=True,
    )

    assert decision.use_generated_output is False
    assert decision.warning_codes == (FORMULA_SOURCE_BACKED_VLM_REJECTED_WARNING,)


def test_authority_allows_generated_formula_when_source_is_absent() -> None:
    document = pymupdf.open()
    if document.new_page() is None:
        raise RuntimeError("PyMuPDF returned no page for absent policy fixture.")
    evidence = collect_source_layer_formula_evidence(document.write())

    decision = decide_formula_authority(
        source_evidence=evidence,
        generated_output_has_quality_defect=True,
    )

    assert decision.use_generated_output is True
    assert decision.warning_codes == ()
