"""Unit tests for v2 PDF checkpoint and partial artifact helpers.

Purpose:
    Ensure chunk persistence and partial artifact assembly are deterministic and
    ordered by page range regardless of write order.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
    PdfChunkRecordV2,
    assemble_partial_markdown_artifact,
    build_initial_pdf_checkpoint,
    partial_artifact_path_for_job_upload,
    persist_pdf_checkpoint,
    persist_pdf_chunk_markdown,
)


def test_partial_artifact_assembly_orders_chunks_by_page_range(tmp_path: Path) -> None:
    job_dir = tmp_path / "jobs_v2" / "jobv2_test"
    upload_path = job_dir / "raw" / "input.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"%PDF-1.4\n% fake\n%%EOF\n")

    checkpoint = build_initial_pdf_checkpoint(
        job_id="jobv2_test", chunk_size_pages=10, total_pages=2
    )

    rel_a, size_a, sha_a = persist_pdf_chunk_markdown(
        upload_path=upload_path,
        chunk_index=1,
        start_page=2,
        end_page=2,
        markdown_content="## Page 2\n\nSecond\n",
    )
    rel_b, size_b, sha_b = persist_pdf_chunk_markdown(
        upload_path=upload_path,
        chunk_index=0,
        start_page=1,
        end_page=1,
        markdown_content="# Page 1\n\nFirst\n",
    )
    now = dt_to_rfc3339(utc_now())
    checkpoint.chunks.extend(
        [
            PdfChunkRecordV2(
                chunk_index=1,
                start_page=2,
                end_page=2,
                status="succeeded",
                started_at=now,
                completed_at=now,
                artifact_relpath=rel_a,
                sha256=f"sha256:{sha_a}",
                size_bytes=size_a,
                backend_used="docling",
                acceleration_used="cpu",
                ocr_enabled=False,
                ocr_engine_used=None,
                ocr_languages_used=[],
                warnings=[],
                phase_timings_ms={},
            ),
            PdfChunkRecordV2(
                chunk_index=0,
                start_page=1,
                end_page=1,
                status="succeeded",
                started_at=now,
                completed_at=now,
                artifact_relpath=rel_b,
                sha256=f"sha256:{sha_b}",
                size_bytes=size_b,
                backend_used="docling",
                acceleration_used="cpu",
                ocr_enabled=False,
                ocr_engine_used=None,
                ocr_languages_used=[],
                warnings=[],
                phase_timings_ms={},
            ),
        ]
    )
    checkpoint.processed_pages = 2
    persist_pdf_checkpoint(upload_path=upload_path, checkpoint=checkpoint)

    assembled = assemble_partial_markdown_artifact(upload_path=upload_path, checkpoint=checkpoint)
    assert assembled is not None

    partial_path = partial_artifact_path_for_job_upload(upload_path=upload_path)
    text = partial_path.read_text(encoding="utf-8")
    assert text.index("# Page 1") < text.index("## Page 2")


def test_v1_checkpoint_payload_is_rejected_without_compatibility_bridge() -> None:
    payload = {
        "schema_version": "v2_pdf_checkpoint_v1",
        "job_id": "jobv2_test",
        "updated_at": "2026-04-28T12:00:00+00:00",
        "total_pages": 1,
        "chunk_size_pages": 1,
        "processed_pages": 1,
        "failed_pages": 0,
        "chunks": [],
    }

    with pytest.raises(ValidationError, match="v2_pdf_checkpoint_v2"):
        PdfCheckpointV2.model_validate(payload)


def test_succeeded_chunk_requires_terminal_metadata() -> None:
    payload = {
        "chunk_index": 0,
        "start_page": 1,
        "end_page": 1,
        "status": "succeeded",
        "artifact_relpath": "checkpoints/chunks/chunk_0000_p000001-000001.md",
        "sha256": "sha256:abc",
        "size_bytes": 10,
        "phase_timings_ms": {"chunk_total_ms": 5},
    }

    with pytest.raises(ValidationError, match="backend_used"):
        PdfChunkRecordV2.model_validate(payload)
