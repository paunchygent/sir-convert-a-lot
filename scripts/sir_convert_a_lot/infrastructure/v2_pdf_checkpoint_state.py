"""PDF checkpoint state and artifact integrity helpers for service API v2.

Purpose:
    Own checkpoint mutation, resume/finalization integrity checks, and
    fail-closed checkpoint metadata validation separate from page-window
    planning and chunk conversion.

Relationships:
    - Used by `infrastructure.v2_pdf_checkpointed_executor`.
    - Reads and mutates `infrastructure.pdf_checkpoints_v2` models.
    - Raises `infrastructure.runtime_models.ServiceError` for public runtime
      failure semantics.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
    PdfChunkRecordV2,
    load_pdf_checkpoint,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_planning import (
    chunk_identity_key_v2,
)


class PdfCheckpointArtifactIntegrityError(Exception):
    """Raised when checkpoint chunk artifacts cannot safely assemble final markdown."""


def upsert_checkpoint_chunk_record_v2(
    *,
    checkpoint: PdfCheckpointV2,
    record: PdfChunkRecordV2,
) -> None:
    """Replace any existing chunk entry for the same identity and append latest record."""
    key = chunk_identity_key_v2(
        chunk_index=record.chunk_index,
        start_page=record.start_page,
        end_page=record.end_page,
    )
    filtered: list[PdfChunkRecordV2] = []
    for existing in checkpoint.chunks:
        existing_key = chunk_identity_key_v2(
            chunk_index=existing.chunk_index,
            start_page=existing.start_page,
            end_page=existing.end_page,
        )
        if existing_key == key:
            continue
        filtered.append(existing)
    filtered.append(record)
    checkpoint.chunks = filtered


def load_pdf_checkpoint_or_fail_closed_v2(*, upload_path: Path) -> PdfCheckpointV2 | None:
    """Load an existing checkpoint or fail closed on invalid checkpoint payloads."""
    try:
        return load_pdf_checkpoint(upload_path=upload_path)
    except Exception as exc:
        raise ServiceError(
            status_code=500,
            code="checkpoint_invalid",
            message=("PDF checkpoint payload is incompatible with the required metadata schema."),
            retryable=False,
        ) from exc


def required_checkpoint_metadata_value_v2(*, label: str, value: str | None) -> str:
    """Return required terminal chunk metadata or fail closed."""
    if value is None or value.strip() == "":
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message=f"PDF chunk completed without {label} metadata to persist.",
            retryable=False,
        )
    return value


def observed_ocr_engine_used_for_checkpoint_record_v2(
    *,
    ocr_enabled: bool,
    ocr_engine_used: str | None,
) -> str | None:
    """Return OCR engine metadata for a checkpoint record, fail-closed when required."""
    if not ocr_enabled:
        return None
    if ocr_engine_used is None or ocr_engine_used.strip() == "":
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message="OCR chunk completed without observed OCR engine metadata to persist.",
            retryable=False,
        )
    return ocr_engine_used


def observed_ocr_languages_used_for_checkpoint_record_v2(
    *,
    ocr_enabled: bool,
    ocr_languages_used: list[str],
) -> list[str]:
    """Return OCR language metadata for a checkpoint record, fail-closed when required."""
    if not ocr_enabled:
        return []
    if len(ocr_languages_used) == 0:
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message="OCR chunk completed without observed OCR language metadata to persist.",
            retryable=False,
        )
    return list(ocr_languages_used)


def assemble_final_markdown_from_checkpoint_v2(
    *, upload_path: Path, checkpoint: PdfCheckpointV2
) -> str:
    """Assemble verified chunk markdown into a terminal artifact payload."""
    job_dir = upload_path.parent.parent
    ordered = _ordered_complete_succeeded_chunks(checkpoint)
    parts: list[str] = []
    for record in ordered:
        parts.append(_read_verified_chunk_text(job_dir=job_dir, record=record))
    return "\n\n".join(parts).rstrip("\n") + "\n"


def _expected_sha256(record: PdfChunkRecordV2) -> str:
    if not record.sha256.startswith("sha256:"):
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} has invalid sha256 metadata."
        )
    return record.sha256.removeprefix("sha256:")


def _read_verified_chunk_text(*, job_dir: Path, record: PdfChunkRecordV2) -> str:
    chunk_path = job_dir / record.artifact_relpath
    if not chunk_path.exists() or not chunk_path.is_file():
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact is missing."
        )
    payload = chunk_path.read_bytes()
    if len(payload) != record.size_bytes:
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact size does not match checkpoint metadata."
        )
    if hashlib.sha256(payload).hexdigest() != _expected_sha256(record):
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact checksum does not match checkpoint metadata."
        )
    try:
        return payload.decode("utf-8").rstrip("\n")
    except UnicodeDecodeError as exc:
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact is not valid UTF-8 markdown."
        ) from exc


def _ordered_complete_succeeded_chunks(checkpoint: PdfCheckpointV2) -> list[PdfChunkRecordV2]:
    if checkpoint.total_pages is None:
        raise PdfCheckpointArtifactIntegrityError("Checkpoint is missing total_pages.")
    succeeded = [chunk for chunk in checkpoint.chunks if chunk.status == "succeeded"]
    ordered = sorted(succeeded, key=lambda record: (record.start_page, record.end_page))
    if len(ordered) == 0:
        raise PdfCheckpointArtifactIntegrityError("Checkpoint has no succeeded chunks.")

    seen: set[tuple[int, int, int]] = set()
    expected_start_page = 1
    for record in ordered:
        key = chunk_identity_key_v2(
            chunk_index=record.chunk_index,
            start_page=record.start_page,
            end_page=record.end_page,
        )
        if key in seen:
            raise PdfCheckpointArtifactIntegrityError(
                f"Checkpoint has duplicate chunk identity for chunk {record.chunk_index}."
            )
        seen.add(key)
        if record.start_page != expected_start_page:
            raise PdfCheckpointArtifactIntegrityError(
                "Checkpoint succeeded chunks do not cover every page exactly once."
            )
        expected_start_page = record.end_page + 1
    if expected_start_page != checkpoint.total_pages + 1:
        raise PdfCheckpointArtifactIntegrityError(
            "Checkpoint succeeded chunks do not cover the full document."
        )
    return ordered
