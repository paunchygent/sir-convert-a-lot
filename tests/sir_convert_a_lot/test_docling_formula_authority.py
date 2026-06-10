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
    FORMULA_SOURCE_BACKED_VLM_SKIPPED_WARNING,
    SourceFormulaEvidenceState,
    SourceLayerFormulaEvidence,
    build_formula_authority_metadata,
    collect_source_layer_formula_evidence,
    decide_formula_authority,
    reconcile_formula_markdown_representation,
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


def test_source_backed_skip_metadata_is_safe_and_represents_page_window() -> None:
    evidence = SourceLayerFormulaEvidence(
        state=SourceFormulaEvidenceState.USABLE,
        method="pymupdf.get_text(words/rawdict/text)",
        page_count=4,
        word_count=120,
        raw_character_count=700,
        text_character_count=690,
        pages_with_words=4,
        pages_with_raw_characters=4,
        reason="coordinate_words_and_raw_characters_present",
    )

    metadata = build_formula_authority_metadata(
        source_evidence=evidence,
        action="skipped",
        representation="source_layer_markdown",
        vlm_attempted=False,
        reason="source_layer_authoritative_formula_vlm_skipped",
        warning_codes=(FORMULA_SOURCE_BACKED_VLM_SKIPPED_WARNING,),
    )

    assert metadata["scope"] == "page_window"
    assert metadata["action"] == "skipped"
    assert metadata["source_evidence_state"] == "usable"
    assert metadata["representation"] == "source_layer_markdown"
    assert metadata["vlm_attempted"] is False
    assert metadata["source_page_count"] == 4
    assert "prompt" not in metadata
    assert "crop" not in metadata


def test_reconciliation_appends_deterministic_formula_authority_marker() -> None:
    evidence = SourceLayerFormulaEvidence(
        state=SourceFormulaEvidenceState.USABLE,
        method="test",
        page_count=1,
        word_count=12,
        raw_character_count=42,
        text_character_count=42,
        pages_with_words=1,
        pages_with_raw_characters=1,
        reason="test_usable_source_layer",
    )
    metadata = build_formula_authority_metadata(
        source_evidence=evidence,
        action="skipped",
        representation="source_layer_markdown",
        vlm_attempted=False,
        reason="source_layer_authoritative_formula_vlm_skipped",
        warning_codes=(FORMULA_SOURCE_BACKED_VLM_SKIPPED_WARNING,),
    )

    reconciled = reconcile_formula_markdown_representation(
        markdown_content="accepted source markdown\n",
        metadata=metadata,
    )

    assert reconciled.startswith("accepted source markdown\n\n")
    assert "sir-convert-a-lot:formula-authority" in reconciled
    assert "action=skipped" in reconciled
    assert "source=usable" in reconciled
    assert "vlm_attempted=false" in reconciled
