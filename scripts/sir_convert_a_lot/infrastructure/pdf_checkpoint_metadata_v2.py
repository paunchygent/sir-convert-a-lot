"""PDF checkpoint terminal metadata aggregation for v2 conversions.

Purpose:
    Derive terminal PDF conversion metadata from committed checkpoint chunk
    records without reprocessing already-finished chunks or inferring facts from
    request options.

Relationships:
    - Consumes `infrastructure.pdf_checkpoints_v2` chunk records.
    - Used by `infrastructure.v2_pdf_checkpointed_executor` during final
      checkpointed PDF artifact assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
    PdfChunkRecordV2,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    merge_phase_timings,
)


class PdfCheckpointTerminalMetadataError(Exception):
    """Raised when checkpoint records cannot truthfully explain terminal metadata."""


@dataclass(frozen=True)
class PdfCheckpointTerminalMetadataV2:
    """Aggregated terminal metadata derived from checkpoint chunk records."""

    backend_used: str
    acceleration_used: str
    ocr_enabled: bool
    ocr_engine_used: str | None
    ocr_languages_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    phase_timings_ms: dict[str, int] = field(default_factory=dict)
    formula_authority: dict[str, object] = field(default_factory=dict)


def _succeeded_chunks(checkpoint: PdfCheckpointV2) -> list[PdfChunkRecordV2]:
    succeeded = [chunk for chunk in checkpoint.chunks if chunk.status == "succeeded"]
    return sorted(succeeded, key=lambda record: (record.start_page, record.end_page))


def _single_terminal_value(*, label: str, values: list[str]) -> str:
    unique: list[str] = []
    for value in values:
        if value in unique:
            continue
        unique.append(value)
    if len(unique) == 0:
        raise PdfCheckpointTerminalMetadataError(
            f"Checkpoint has no succeeded chunk {label} metadata."
        )
    if len(unique) > 1:
        raise PdfCheckpointTerminalMetadataError(
            f"Checkpoint has mixed succeeded chunk {label} metadata: {', '.join(unique)}."
        )
    return unique[0]


def _append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value in target:
            continue
        target.append(value)


def _formula_authority_page_window(record: PdfChunkRecordV2) -> dict[str, object] | None:
    if not record.formula_authority:
        return None
    return {
        "start_page": record.start_page,
        "end_page": record.end_page,
        **dict(record.formula_authority),
    }


def _aggregate_formula_authority(succeeded: list[PdfChunkRecordV2]) -> dict[str, object]:
    page_windows: list[dict[str, object]] = []
    for record in succeeded:
        window = _formula_authority_page_window(record)
        if window is None:
            continue
        page_windows.append(window)
    if len(page_windows) == 0:
        return {}
    if len(page_windows) == 1:
        return dict(page_windows[0])
    return {
        "scope": "document",
        "page_windows": page_windows,
    }


def aggregate_pdf_checkpoint_terminal_metadata(
    checkpoint: PdfCheckpointV2,
) -> PdfCheckpointTerminalMetadataV2:
    """Return terminal metadata derived only from succeeded checkpoint chunks."""
    succeeded = _succeeded_chunks(checkpoint)
    if len(succeeded) == 0:
        raise PdfCheckpointTerminalMetadataError("Checkpoint has no succeeded chunks.")

    backend_used = _single_terminal_value(
        label="backend_used",
        values=[record.backend_used for record in succeeded],
    )
    acceleration_used = _single_terminal_value(
        label="acceleration_used",
        values=[record.acceleration_used for record in succeeded],
    )

    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}
    ocr_engine_values: list[str] = []
    ocr_languages_used: list[str] = []
    ocr_enabled = False
    for record in succeeded:
        _append_unique(warnings, record.warnings)
        phase_timings_ms = merge_phase_timings(
            current=phase_timings_ms,
            additional=record.phase_timings_ms,
        )
        if not record.ocr_enabled:
            continue
        ocr_enabled = True
        if record.ocr_engine_used is None:
            raise PdfCheckpointTerminalMetadataError(
                "Checkpoint OCR chunk is missing ocr_engine_used metadata."
            )
        ocr_engine_values.append(record.ocr_engine_used)
        _append_unique(ocr_languages_used, record.ocr_languages_used)

    ocr_engine_used = (
        _single_terminal_value(label="ocr_engine_used", values=ocr_engine_values)
        if ocr_enabled
        else None
    )
    return PdfCheckpointTerminalMetadataV2(
        backend_used=backend_used,
        acceleration_used=acceleration_used,
        ocr_enabled=ocr_enabled,
        ocr_engine_used=ocr_engine_used,
        ocr_languages_used=ocr_languages_used if ocr_enabled else [],
        warnings=warnings,
        phase_timings_ms=phase_timings_ms,
        formula_authority=_aggregate_formula_authority(succeeded),
    )
