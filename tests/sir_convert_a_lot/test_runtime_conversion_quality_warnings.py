"""Tests for runtime conversion quality warnings.

Purpose:
    Ensure strict normalization strips reserved Docling protocol/control tokens
    and that deterministic quality contract warnings are surfaced in result
    metadata.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.runtime_conversion`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    ConversionSpec,
    ExecutionSpec,
    JobSpec,
    NormalizeMode,
    OcrMode,
    Priority,
    SourceKind,
    SourceSpec,
    TableMode,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    ConversionRequest,
    ConversionResultData,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_conversion import execute_job_conversion


class _Backend:
    def __init__(self, markdown_content: str) -> None:
        self._markdown_content = markdown_content

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        del request
        return ConversionResultData(
            markdown_content=self._markdown_content,
            backend_used="docling",
            acceleration_used="cuda",
            ocr_enabled=False,
        )


def test_execute_job_conversion_emits_quality_warnings_and_strips_reserved_tokens() -> None:
    columns = 300
    header_cells = " | ".join(["col"] * columns)
    header = f"| {header_cells} |"
    separator_cells = " | ".join(["---"] * columns)
    separator = f"| {separator_cells} |"
    row_cells = " | ".join(["val"] * columns)
    row = f"| {row_cells} |"
    raw_markdown = (
        "Intro paragraph.\n\n"
        "/negationslash\n\n"
        f"{header}\n"
        f"{separator}\n"
        f"{row}\n\n"
        "$$<formula><loc_1>\\\\alpha</formula$$\n"
    )
    spec = JobSpec(
        api_version="v1",
        source=SourceSpec(kind=SourceKind.UPLOAD, filename="paper.pdf"),
        conversion=ConversionSpec(
            output_format="md",
            backend_strategy=BackendStrategy.DOCLING,
            ocr_mode=OcrMode.OFF,
            table_mode=TableMode.ACCURATE,
            normalize=NormalizeMode.STRICT,
        ),
        execution=ExecutionSpec(
            acceleration_policy=AccelerationPolicy.GPU_REQUIRED,
            priority=Priority.NORMAL,
            document_timeout_seconds=1800,
        ),
    )

    markdown_content, metadata, warnings, timings = execute_job_conversion(
        spec=spec,
        source_filename="paper.pdf",
        source_bytes=b"%PDF-1.4 fixture",
        gpu_available=True,
        gpu_runtime_probe=None,
        docling_backend=_Backend(raw_markdown),
        pymupdf_backend=_Backend("unused"),
    )

    del metadata, timings

    assert "/negationslash" not in markdown_content
    assert "<formula>" not in markdown_content
    assert "</formula" not in markdown_content
    assert "<loc_1>" not in markdown_content

    assert any(
        warning.startswith("markdown_quality_sanitized_reserved_tokens:") for warning in warnings
    )
    assert any(
        warning.startswith("markdown_quality_normalized_extreme_lines:") for warning in warnings
    )
