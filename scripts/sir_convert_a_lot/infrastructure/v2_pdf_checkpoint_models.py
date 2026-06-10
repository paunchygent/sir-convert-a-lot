"""Typed models for checkpointed PDF execution in service API v2.

Purpose:
    Share checkpoint progress, cancellation, and chunk-conversion outcome
    models across the v2 PDF executor, chunk runner, and runtime job runner
    without creating circular module dependencies.

Relationships:
    - Imported by `infrastructure.v2_pdf_checkpointed_executor`.
    - Imported by `infrastructure.v2_pdf_checkpoint_chunk_runner`.
    - Imported by runtime and v2 conversion orchestration for progress typing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
)


class PdfCheckpointPersistFunctionV2(Protocol):
    """Callable boundary for persisting checkpoint state."""

    def __call__(self, *, upload_path: Path, checkpoint: PdfCheckpointV2) -> None: ...


class PdfPartialArtifactAssemblerFunctionV2(Protocol):
    """Callable boundary for assembling partial checkpoint artifacts."""

    def __call__(self, *, upload_path: Path, checkpoint: PdfCheckpointV2) -> object: ...


@dataclass(frozen=True)
class PdfCheckpointProgressUpdateV2:
    """Progress snapshot emitted after a PDF chunk is checkpointed."""

    total_pages: int
    processed_pages: int
    failed_pages: int
    percent_complete: float
    pages_per_minute: float | None
    eta_seconds: int | None
    phase_timings_ms: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PdfConversionCanceledV2(Exception):
    """Raised when a running PDF conversion observes cancellation."""

    job_id: str


@dataclass(frozen=True)
class PdfChunkConversionOutcomeV2:
    """One converted PDF chunk outcome produced before checkpoint commit."""

    chunk_index: int
    start_page: int
    end_page: int
    markdown_content: str
    backend_used: str | None
    acceleration_used: str | None
    ocr_enabled: bool
    ocr_engine_used: str | None
    ocr_languages_used: list[str]
    warnings: list[str]
    phase_timings_ms: dict[str, int]
    formula_authority: dict[str, object]
    chunk_elapsed_ms: int
    started_at: str | None
    completed_at: str | None
