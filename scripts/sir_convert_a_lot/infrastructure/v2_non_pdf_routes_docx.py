"""DOCX-source route executors for service API v2.

Purpose:
    Keep DOCX-based v2 routes isolated so the main non-PDF router stays small:
      - `docx -> md`
      - `docx -> pdf`

Relationships:
    - Called by `infrastructure.v2_conversion_executor_non_pdf`.
    - Uses shared helpers in `infrastructure.v2_non_pdf_helpers`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import NormalizeMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.markdown_normalization_v2 import (
    normalize_markdown_for_v2_md_output,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_helpers import (
    convert_docx_to_markdown_v2,
    convert_docx_to_pdf_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_models import NonPdfExecutionOutcomeV2


def execute_docx_source_route_v2(
    *,
    job: StoredJobV2,
    workdir: Path,
    input_path: Path,
    document_timeout_seconds: int,
) -> NonPdfExecutionOutcomeV2:
    if job.source_format != SourceFormatV2.DOCX:
        raise ValueError("execute_docx_source_route_v2 requires source_format=docx")

    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}

    source_bytes = job.upload_path.read_bytes()
    if not source_bytes.startswith(b"PK"):
        raise ServiceError(
            status_code=422,
            code="docx_unreadable",
            message="Uploaded file is not a readable DOCX.",
            retryable=False,
        )

    if job.output_format == OutputFormatV2.MD:
        pipeline_used = "docx_to_md_v2"
        backend_used = "pandoc"
        intermediate_markdown = workdir / input_path.with_suffix(".md").name
        convert_docx_to_markdown_v2(
            input_docx_path=input_path,
            output_markdown_path=intermediate_markdown,
            timeout_seconds=document_timeout_seconds,
        )
        normalized_markdown, normalization_warnings = normalize_markdown_for_v2_md_output(
            markdown_content=intermediate_markdown.read_text(encoding="utf-8"),
            mode=NormalizeMode.STRICT,
        )
        warnings.extend(normalization_warnings)
        job.artifact_path.write_text(normalized_markdown, encoding="utf-8")
        return NonPdfExecutionOutcomeV2(
            pipeline_used=pipeline_used,
            backend_used=backend_used,
            acceleration_used=None,
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
        )

    if job.output_format == OutputFormatV2.PDF:
        pipeline_used = "docx_to_pdf_v2"
        backend_used = "pandoc+weasyprint"
        convert_docx_to_pdf_v2(
            job=job,
            input_docx_path=input_path,
            workdir=workdir,
            output_pdf_path=job.artifact_path,
            timeout_seconds=document_timeout_seconds,
        )
        return NonPdfExecutionOutcomeV2(
            pipeline_used=pipeline_used,
            backend_used=backend_used,
            acceleration_used=None,
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
        )

    raise ServiceError(
        status_code=422,
        code="unsupported_route",
        message=(f"Unsupported route: {job.source_format.value} -> {job.output_format.value}."),
        retryable=False,
    )
