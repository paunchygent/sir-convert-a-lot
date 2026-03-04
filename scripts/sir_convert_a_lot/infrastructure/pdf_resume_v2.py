"""PDF resume helpers for v2 checkpointed long-running jobs.

Purpose:
    Provide deterministic, job-scoped cloning of checkpoint + chunk artifacts so a
    resume operation can create a new job id and continue conversion without
    reprocessing completed chunks/pages.

Relationships:
    - Called by v2 HTTP resume routes (service API v2).
    - Uses persistence utilities from `infrastructure.pdf_checkpoints_v2`.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
    assemble_partial_markdown_artifact,
    checkpoint_path_for_job_upload,
    chunk_dir_for_job_upload,
    load_pdf_checkpoint,
    persist_pdf_checkpoint,
)


@dataclass(frozen=True)
class PdfResumeSeedV2:
    """Metadata produced when cloning checkpoint state for a resume job."""

    checkpoint_sha256: str
    processed_pages: int
    failed_pages: int
    total_pages: int | None


class PdfResumeCheckpointMissingError(Exception):
    """Raised when a resume attempt does not have a usable checkpoint."""


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clone_pdf_checkpoint_state_for_resume(
    *,
    source_upload_path: Path,
    destination_upload_path: Path,
    destination_job_id: str,
) -> PdfResumeSeedV2:
    """Clone checkpoint + chunk artifacts into a new job directory for resume."""
    source_checkpoint = load_pdf_checkpoint(upload_path=source_upload_path)
    if source_checkpoint is None or source_checkpoint.processed_pages <= 0:
        raise PdfResumeCheckpointMissingError("Source job does not have a usable checkpoint.")

    source_chunks_dir = chunk_dir_for_job_upload(upload_path=source_upload_path)
    destination_chunks_dir = chunk_dir_for_job_upload(upload_path=destination_upload_path)
    destination_chunks_dir.mkdir(parents=True, exist_ok=True)
    if source_chunks_dir.exists():
        for entry in source_chunks_dir.iterdir():
            if entry.is_file():
                shutil.copy2(entry, destination_chunks_dir / entry.name)

    destination_checkpoint = PdfCheckpointV2.model_validate(
        source_checkpoint.model_dump(mode="json")
    )
    destination_checkpoint.job_id = destination_job_id
    destination_checkpoint.updated_at = (
        dt_to_rfc3339(utc_now()) or destination_checkpoint.updated_at
    )
    persist_pdf_checkpoint(upload_path=destination_upload_path, checkpoint=destination_checkpoint)
    assemble_partial_markdown_artifact(
        upload_path=destination_upload_path, checkpoint=destination_checkpoint
    )

    checkpoint_path = checkpoint_path_for_job_upload(upload_path=destination_upload_path)
    return PdfResumeSeedV2(
        checkpoint_sha256=f"sha256:{_sha256_hex(checkpoint_path)}",
        processed_pages=destination_checkpoint.processed_pages,
        failed_pages=destination_checkpoint.failed_pages,
        total_pages=destination_checkpoint.total_pages,
    )
