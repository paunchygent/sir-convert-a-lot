"""PDF checkpoint + partial artifact persistence helpers for v2 long-running jobs.

Purpose:
    Persist deterministic chunk-level checkpoints and partial markdown artifacts
    during long-running PDF conversions so operators and clients can retrieve
    partial output before terminal completion and so recovered jobs can skip
    completed work after a crash/restart.

Relationships:
    - Written/loaded by `infrastructure.v2_conversion_executor` for PDF routes.
    - Read by `infrastructure.runtime_engine_v2` and v2 HTTP routes for
      `/v2/convert/jobs/{job_id}/checkpoint` and `/artifact/partial`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _job_dir_from_upload_path(upload_path: Path) -> Path:
    raw_dir = upload_path.parent
    return raw_dir.parent


def checkpoint_path_for_job_upload(*, upload_path: Path) -> Path:
    job_dir = _job_dir_from_upload_path(upload_path)
    return job_dir / "checkpoints" / "pdf_checkpoint.json"


def chunk_dir_for_job_upload(*, upload_path: Path) -> Path:
    job_dir = _job_dir_from_upload_path(upload_path)
    return job_dir / "checkpoints" / "chunks"


def partial_artifact_path_for_job_upload(*, upload_path: Path) -> Path:
    job_dir = _job_dir_from_upload_path(upload_path)
    return job_dir / "artifacts" / "partial.md"


class PdfChunkRecordV2(BaseModel):
    """One persisted chunk record for a PDF conversion."""

    model_config = ConfigDict(extra="forbid")

    chunk_index: int = Field(ge=0)
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    status: Literal["succeeded", "failed"]
    started_at: str | None = None
    completed_at: str | None = None
    artifact_relpath: str
    sha256: str
    size_bytes: int = Field(ge=0)
    backend_used: str = Field(min_length=1)
    acceleration_used: str = Field(min_length=1)
    ocr_enabled: bool
    ocr_engine_used: str | None = Field(default=None, min_length=1)
    ocr_languages_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    phase_timings_ms: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_succeeded_metadata(self) -> Self:
        if self.status != "succeeded":
            return self
        if self.ocr_enabled:
            if self.ocr_engine_used is None:
                raise ValueError("succeeded OCR chunks must record ocr_engine_used")
            if len(self.ocr_languages_used) == 0:
                raise ValueError("succeeded OCR chunks must record ocr_languages_used")
            return self
        if self.ocr_engine_used is not None:
            raise ValueError("non-OCR chunks must not record ocr_engine_used")
        if len(self.ocr_languages_used) > 0:
            raise ValueError("non-OCR chunks must not record ocr_languages_used")
        return self


class PdfCheckpointV2(BaseModel):
    """Durable checkpoint state for chunked PDF-to-markdown execution."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["v2_pdf_checkpoint_v2"] = "v2_pdf_checkpoint_v2"
    job_id: str = Field(min_length=1)
    updated_at: str
    total_pages: int | None = Field(default=None, ge=1)
    chunk_size_pages: int = Field(ge=1, le=500)
    processed_pages: int = Field(ge=0)
    failed_pages: int = Field(ge=0)
    chunks: list[PdfChunkRecordV2] = Field(default_factory=list)


@dataclass(frozen=True)
class PdfPartialArtifactMetadataV2:
    """Metadata for an assembled partial markdown artifact."""

    path: Path
    sha256: str
    size_bytes: int
    updated_at: datetime


def load_pdf_checkpoint(*, upload_path: Path) -> PdfCheckpointV2 | None:
    checkpoint_path = checkpoint_path_for_job_upload(upload_path=upload_path)
    if not checkpoint_path.exists():
        return None
    payload = read_json(checkpoint_path)
    return PdfCheckpointV2.model_validate(payload)


def _normalize_chunk_list(chunks: list[PdfChunkRecordV2]) -> list[PdfChunkRecordV2]:
    return sorted(
        chunks, key=lambda record: (record.start_page, record.end_page, record.chunk_index)
    )


def persist_pdf_checkpoint(*, upload_path: Path, checkpoint: PdfCheckpointV2) -> None:
    checkpoint_path = checkpoint_path_for_job_upload(upload_path=upload_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(checkpoint_path, checkpoint.model_dump(mode="json"))


def persist_pdf_chunk_markdown(
    *,
    upload_path: Path,
    chunk_index: int,
    start_page: int,
    end_page: int,
    markdown_content: str,
) -> tuple[str, int, str]:
    chunk_dir = chunk_dir_for_job_upload(upload_path=upload_path)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    filename = f"chunk_{chunk_index:04d}_p{start_page:06d}-{end_page:06d}.md"
    relpath = f"checkpoints/chunks/{filename}"
    path = chunk_dir / filename
    payload = markdown_content.encode("utf-8")
    _atomic_write_bytes(path, payload)
    return relpath, len(payload), _sha256_hex(payload)


def assemble_partial_markdown_artifact(
    *,
    upload_path: Path,
    checkpoint: PdfCheckpointV2,
) -> PdfPartialArtifactMetadataV2 | None:
    """Assemble and persist partial markdown from succeeded chunks.

    The partial artifact is intentionally annotated with deterministic HTML
    comments so downstream clients can detect boundaries and avoid accidental
    duplicate merges when debugging or resuming.
    """

    succeeded = [chunk for chunk in checkpoint.chunks if chunk.status == "succeeded"]
    if len(succeeded) == 0:
        return None

    job_dir = _job_dir_from_upload_path(upload_path)
    parts: list[str] = []
    parts.append(
        f"<!-- sir-convert-a-lot:partial job_id={checkpoint.job_id} "
        f"updated_at={checkpoint.updated_at} -->\n"
    )
    for record in _normalize_chunk_list(succeeded):
        chunk_path = job_dir / record.artifact_relpath
        if not chunk_path.exists():
            continue
        parts.append(
            f"\n<!-- sir-convert-a-lot:chunk index={record.chunk_index} "
            f"pages={record.start_page}-{record.end_page} sha256={record.sha256} -->\n"
        )
        parts.append(chunk_path.read_text(encoding="utf-8"))

    assembled = "".join(parts).encode("utf-8")
    now = utc_now()
    partial_path = partial_artifact_path_for_job_upload(upload_path=upload_path)
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(partial_path, assembled)
    return PdfPartialArtifactMetadataV2(
        path=partial_path,
        sha256=_sha256_hex(assembled),
        size_bytes=len(assembled),
        updated_at=now,
    )


def best_effort_checkpoint_updated_at(checkpoint: PdfCheckpointV2) -> datetime | None:
    return dt_from_rfc3339(checkpoint.updated_at)


def build_initial_pdf_checkpoint(
    *,
    job_id: str,
    chunk_size_pages: int,
    total_pages: int | None,
) -> PdfCheckpointV2:
    now = utc_now()
    updated_at = dt_to_rfc3339(now)
    if updated_at is None:
        raise RuntimeError("utc_now() must be serializable to RFC3339")
    return PdfCheckpointV2(
        job_id=job_id,
        updated_at=updated_at,
        total_pages=total_pages,
        chunk_size_pages=chunk_size_pages,
        processed_pages=0,
        failed_pages=0,
        chunks=[],
    )
