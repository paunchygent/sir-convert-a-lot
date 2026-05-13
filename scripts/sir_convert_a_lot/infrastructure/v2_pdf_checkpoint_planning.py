"""PDF checkpoint chunk planning helpers for service API v2.

Purpose:
    Keep deterministic page-window planning and resume-skip decisions separate
    from PDF chunk conversion and checkpoint persistence.

Relationships:
    - Used by `infrastructure.v2_pdf_checkpointed_executor`.
    - Reads `infrastructure.pdf_checkpoints_v2.PdfCheckpointV2` chunk records.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import PdfCheckpointV2


@dataclass(frozen=True)
class PdfChunkPlanItemV2:
    """One deterministic PDF page window in a checkpointed conversion plan."""

    chunk_index: int
    start_page: int
    end_page: int

    @property
    def identity_key(self) -> tuple[int, int, int]:
        """Return the stable checkpoint identity key for this chunk."""
        return self.chunk_index, self.start_page, self.end_page


def chunk_identity_key_v2(
    *, chunk_index: int, start_page: int, end_page: int
) -> tuple[int, int, int]:
    """Return the stable checkpoint identity key for one page window."""
    return chunk_index, start_page, end_page


def succeeded_chunk_keys_v2(checkpoint: PdfCheckpointV2) -> set[tuple[int, int, int]]:
    """Return identity keys for checkpoint chunks that already succeeded."""
    keys: set[tuple[int, int, int]] = set()
    for chunk in checkpoint.chunks:
        if chunk.status != "succeeded":
            continue
        keys.add(
            chunk_identity_key_v2(
                chunk_index=chunk.chunk_index,
                start_page=chunk.start_page,
                end_page=chunk.end_page,
            )
        )
    return keys


def resolve_checkpoint_processed_pages_v2(checkpoint: PdfCheckpointV2) -> int:
    """Return processed page count from unique succeeded chunk identities."""
    processed_pages = 0
    for _chunk_index, start_page, end_page in succeeded_chunk_keys_v2(checkpoint):
        processed_pages += end_page - start_page + 1
    return processed_pages


def plan_pdf_chunks_v2(*, total_pages: int, chunk_size_pages: int) -> list[PdfChunkPlanItemV2]:
    """Return deterministic chunk windows for a document page count."""
    if total_pages <= 0:
        return []
    resolved_chunk_size = max(1, int(chunk_size_pages))
    chunks: list[PdfChunkPlanItemV2] = []
    chunk_index = 0
    start_page = 1
    while start_page <= total_pages:
        end_page = min(total_pages, start_page + resolved_chunk_size - 1)
        chunks.append(
            PdfChunkPlanItemV2(
                chunk_index=chunk_index,
                start_page=start_page,
                end_page=end_page,
            )
        )
        chunk_index += 1
        start_page = end_page + 1
    return chunks


def pending_pdf_chunks_v2(
    *,
    total_pages: int,
    chunk_size_pages: int,
    completed_chunk_keys: set[tuple[int, int, int]],
) -> list[PdfChunkPlanItemV2]:
    """Return planned chunks that are not already completed in the checkpoint."""
    pending: list[PdfChunkPlanItemV2] = []
    for chunk in plan_pdf_chunks_v2(total_pages=total_pages, chunk_size_pages=chunk_size_pages):
        if chunk.identity_key in completed_chunk_keys:
            continue
        pending.append(chunk)
    return pending
