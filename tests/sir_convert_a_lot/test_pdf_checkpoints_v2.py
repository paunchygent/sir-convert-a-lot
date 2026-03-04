"""Unit tests for v2 PDF checkpoint and partial artifact helpers.

Purpose:
    Ensure chunk persistence and partial artifact assembly are deterministic and
    ordered by page range regardless of write order.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
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
