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
    def __init__(
        self,
        markdown_content: str,
        phase_timings_ms: dict[str, int] | None = None,
        formula_authority: dict[str, object] | None = None,
    ) -> None:
        self._markdown_content = markdown_content
        self._phase_timings_ms = phase_timings_ms or {}
        self._formula_authority = formula_authority or {}

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        del request
        return ConversionResultData(
            markdown_content=self._markdown_content,
            backend_used="docling",
            acceleration_used="cuda",
            ocr_enabled=False,
            phase_timings_ms=dict(self._phase_timings_ms),
            formula_authority=dict(self._formula_authority),
        )


class _CapturingBackend:
    def __init__(self) -> None:
        self.requests: list[ConversionRequest] = []

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        self.requests.append(request)
        return ConversionResultData(
            markdown_content="# converted\n",
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


def test_execute_job_conversion_exposes_canonical_v2_timing_keys() -> None:
    spec = JobSpec(
        api_version="v1",
        source=SourceSpec(kind=SourceKind.UPLOAD, filename="paper.pdf"),
        conversion=ConversionSpec(
            output_format="md",
            backend_strategy=BackendStrategy.DOCLING,
            ocr_mode=OcrMode.OFF,
            table_mode=TableMode.ACCURATE,
            normalize=NormalizeMode.STANDARD,
        ),
        execution=ExecutionSpec(
            acceleration_policy=AccelerationPolicy.GPU_REQUIRED,
            priority=Priority.NORMAL,
            document_timeout_seconds=1800,
        ),
    )

    _, _, _, timings = execute_job_conversion(
        spec=spec,
        source_filename="paper.pdf",
        source_bytes=b"%PDF-1.4 fixture",
        gpu_available=True,
        gpu_runtime_probe=None,
        docling_backend=_Backend("# converted\n"),
        pymupdf_backend=_Backend("unused"),
    )

    assert "backend_convert_ms" in timings
    assert "normalize_ms" in timings
    assert "ocr_layout_extract_ms" in timings
    assert "markdown_normalize_ms" in timings


def test_execute_job_conversion_preserves_formula_authority_metadata() -> None:
    spec = JobSpec(
        api_version="v1",
        source=SourceSpec(kind=SourceKind.UPLOAD, filename="paper.pdf"),
        conversion=ConversionSpec(
            output_format="md",
            backend_strategy=BackendStrategy.DOCLING,
            ocr_mode=OcrMode.OFF,
            table_mode=TableMode.ACCURATE,
            normalize=NormalizeMode.STANDARD,
        ),
        execution=ExecutionSpec(
            acceleration_policy=AccelerationPolicy.GPU_REQUIRED,
            priority=Priority.NORMAL,
            document_timeout_seconds=1800,
        ),
    )
    formula_authority = {
        "scope": "page_window",
        "action": "skipped",
        "source_evidence_state": "usable",
        "vlm_attempted": False,
    }

    _, metadata, _, _ = execute_job_conversion(
        spec=spec,
        source_filename="paper.pdf",
        source_bytes=b"%PDF-1.4 fixture",
        gpu_available=True,
        gpu_runtime_probe=None,
        docling_backend=_Backend("# converted\n", formula_authority=formula_authority),
        pymupdf_backend=_Backend("unused"),
    )

    assert metadata.formula_authority == formula_authority


def test_execute_job_conversion_passes_document_timeout_to_backend_request() -> None:
    backend = _CapturingBackend()
    spec = JobSpec(
        api_version="v1",
        source=SourceSpec(kind=SourceKind.UPLOAD, filename="paper.pdf"),
        conversion=ConversionSpec(
            output_format="md",
            backend_strategy=BackendStrategy.DOCLING,
            ocr_mode=OcrMode.OFF,
            table_mode=TableMode.ACCURATE,
            normalize=NormalizeMode.STANDARD,
        ),
        execution=ExecutionSpec(
            acceleration_policy=AccelerationPolicy.GPU_REQUIRED,
            priority=Priority.NORMAL,
            document_timeout_seconds=77,
        ),
    )

    execute_job_conversion(
        spec=spec,
        source_filename="paper.pdf",
        source_bytes=b"%PDF-1.4 fixture",
        gpu_available=True,
        gpu_runtime_probe=None,
        docling_backend=backend,
        pymupdf_backend=_Backend("unused"),
    )

    assert len(backend.requests) == 1
    assert backend.requests[0].document_timeout_seconds == 77
