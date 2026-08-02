"""Tests for terminal PDF checkpoint metadata aggregation.

Purpose:
    Prove terminal v2 PDF metadata preserves chunk-level formula-authority
    decisions as user-visible page-window evidence.

Relationships:
    - Exercises `infrastructure.pdf_checkpoint_metadata_v2`.
    - Uses `infrastructure.pdf_checkpoints_v2` chunk records as persisted input.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoint_metadata_v2 import (
    aggregate_pdf_checkpoint_terminal_metadata,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfChunkRecordV2,
    build_initial_pdf_checkpoint,
)


def _chunk_record(
    *,
    chunk_index: int,
    start_page: int,
    end_page: int,
    action: str,
    source_evidence_state: str,
    reason: str,
) -> PdfChunkRecordV2:
    now = dt_to_rfc3339(utc_now())
    return PdfChunkRecordV2(
        chunk_index=chunk_index,
        start_page=start_page,
        end_page=end_page,
        status="succeeded",
        started_at=now,
        completed_at=now,
        artifact_relpath=f"checkpoints/chunks/chunk_{chunk_index:04d}.md",
        sha256="sha256:" + ("a" * 64),
        size_bytes=17,
        backend_used="docling",
        acceleration_used="cuda",
        ocr_enabled=False,
        ocr_engine_used=None,
        ocr_languages_used=[],
        warnings=[],
        phase_timings_ms={"ocr_layout_extract_ms": 1},
        formula_authority={
            "action": action,
            "source_evidence_state": source_evidence_state,
            "reason": reason,
        },
    )


def test_terminal_metadata_preserves_formula_authority_page_windows() -> None:
    checkpoint = build_initial_pdf_checkpoint(
        job_id="jobv2_formula_authority",
        chunk_size_pages=1,
        total_pages=4,
    )
    checkpoint.chunks.extend(
        [
            _chunk_record(
                chunk_index=0,
                start_page=1,
                end_page=1,
                action="skipped",
                source_evidence_state="usable",
                reason="source_layer_authoritative_formula_vlm_skipped",
            ),
            _chunk_record(
                chunk_index=1,
                start_page=2,
                end_page=2,
                action="accepted",
                source_evidence_state="absent",
                reason="generated_formula_output_allowed",
            ),
            _chunk_record(
                chunk_index=2,
                start_page=3,
                end_page=3,
                action="fallback",
                source_evidence_state="partial_or_unusable",
                reason="formula_vlm_runtime_unavailable",
            ),
            _chunk_record(
                chunk_index=3,
                start_page=4,
                end_page=4,
                action="rejected",
                source_evidence_state="usable",
                reason="source_layer_authoritative_and_generated_formula_quality_defect",
            ),
        ]
    )

    metadata = aggregate_pdf_checkpoint_terminal_metadata(checkpoint)

    assert metadata.formula_authority["scope"] == "document"
    page_windows = metadata.formula_authority["page_windows"]
    assert isinstance(page_windows, list)
    assert [
        (
            window["start_page"],
            window["end_page"],
            window["action"],
            window["source_evidence_state"],
            window["reason"],
        )
        for window in page_windows
    ] == [
        (1, 1, "skipped", "usable", "source_layer_authoritative_formula_vlm_skipped"),
        (2, 2, "accepted", "absent", "generated_formula_output_allowed"),
        (3, 3, "fallback", "partial_or_unusable", "formula_vlm_runtime_unavailable"),
        (
            4,
            4,
            "rejected",
            "usable",
            "source_layer_authoritative_and_generated_formula_quality_defect",
        ),
    ]
