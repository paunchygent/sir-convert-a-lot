"""Focused tests for v2 PDF checkpoint planning and state helpers.

Purpose:
    Prove chunk planning and checkpoint-state mutation stay deterministic after
    extraction from the checkpointed PDF executor.

Relationships:
    - Tests `infrastructure.v2_pdf_checkpoint_planning`.
    - Tests `infrastructure.v2_pdf_checkpoint_state`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfChunkRecordV2,
    build_initial_pdf_checkpoint,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_planning import (
    pending_pdf_chunks_v2,
    plan_pdf_chunks_v2,
    resolve_checkpoint_processed_pages_v2,
    succeeded_chunk_keys_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_state import (
    upsert_checkpoint_chunk_record_v2,
)


def _chunk_record(
    *,
    chunk_index: int,
    start_page: int,
    end_page: int,
    markdown: str,
) -> PdfChunkRecordV2:
    payload = markdown.encode("utf-8")
    return PdfChunkRecordV2(
        chunk_index=chunk_index,
        start_page=start_page,
        end_page=end_page,
        status="succeeded",
        started_at=dt_to_rfc3339(utc_now()),
        completed_at=dt_to_rfc3339(utc_now()),
        artifact_relpath=f"chunks/{chunk_index}.md",
        sha256="sha256:" + ("a" * 64),
        size_bytes=len(payload),
        backend_used="docling",
        acceleration_used="cpu",
        ocr_enabled=False,
        ocr_engine_used=None,
        ocr_languages_used=[],
        warnings=[],
        phase_timings_ms={"chunk_total_ms": 1},
    )


def test_pdf_chunk_planning_skips_completed_chunk_identities() -> None:
    checkpoint = build_initial_pdf_checkpoint(
        job_id="jobv2_planning",
        chunk_size_pages=2,
        total_pages=5,
    )
    first = _chunk_record(chunk_index=0, start_page=1, end_page=2, markdown="# one\n")
    duplicate = _chunk_record(chunk_index=0, start_page=1, end_page=2, markdown="# one\n")
    checkpoint.chunks.extend([first, duplicate])

    planned = plan_pdf_chunks_v2(total_pages=5, chunk_size_pages=2)
    pending = pending_pdf_chunks_v2(
        total_pages=5,
        chunk_size_pages=2,
        completed_chunk_keys=succeeded_chunk_keys_v2(checkpoint),
    )

    assert [(item.chunk_index, item.start_page, item.end_page) for item in planned] == [
        (0, 1, 2),
        (1, 3, 4),
        (2, 5, 5),
    ]
    assert [(item.chunk_index, item.start_page, item.end_page) for item in pending] == [
        (1, 3, 4),
        (2, 5, 5),
    ]
    assert resolve_checkpoint_processed_pages_v2(checkpoint) == 2


def test_checkpoint_chunk_upsert_replaces_same_identity() -> None:
    checkpoint = build_initial_pdf_checkpoint(
        job_id="jobv2_upsert",
        chunk_size_pages=2,
        total_pages=2,
    )
    original = _chunk_record(chunk_index=0, start_page=1, end_page=2, markdown="# old\n")
    replacement = _chunk_record(
        chunk_index=0,
        start_page=1,
        end_page=2,
        markdown="# replacement\n",
    )

    upsert_checkpoint_chunk_record_v2(checkpoint=checkpoint, record=original)
    upsert_checkpoint_chunk_record_v2(checkpoint=checkpoint, record=replacement)

    assert checkpoint.chunks == [replacement]
