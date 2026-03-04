"""Markdown-source route executors for service API v2.

Purpose:
    Keep Markdown-based v2 routes isolated:
      - `md -> pdf`
      - `md -> docx`

Relationships:
    - Called by `infrastructure.v2_conversion_executor_non_pdf`.
    - Uses shared helpers in `infrastructure.v2_non_pdf_helpers`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HtmlToDocxConversionError,
    convert_html_to_docx,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MarkdownToHtmlConversionError,
    convert_markdown_to_html,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_helpers import (
    map_converter_error,
    resolve_pdf_stylesheets,
    resolve_reference_docx,
    validate_html_resources_for_route,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_models import NonPdfExecutionOutcomeV2
from scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf import (
    HtmlToPdfConversionError,
    convert_html_to_pdf,
)


def execute_markdown_source_route_v2(
    *,
    job: StoredJobV2,
    workdir: Path,
    input_path: Path,
    document_timeout_seconds: int,
) -> NonPdfExecutionOutcomeV2:
    if job.source_format != SourceFormatV2.MD:
        raise ValueError("execute_markdown_source_route_v2 requires source_format=md")

    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}

    if job.output_format == OutputFormatV2.PDF:
        pipeline_used = "md_to_pdf_v2"
        backend_used = "pandoc+weasyprint"
        css_paths = resolve_pdf_stylesheets(job=job, workdir=workdir)
        intermediate_html = workdir / input_path.with_suffix(".html").name
        try:
            convert_markdown_to_html(
                markdown_path=input_path,
                output_html_path=intermediate_html,
                timeout_seconds=document_timeout_seconds,
            )
            validate_html_resources_for_route(input_path=intermediate_html, workdir=workdir)
            convert_html_to_pdf(
                html_path=intermediate_html,
                output_pdf_path=job.artifact_path,
                css_paths=css_paths,
                base_url=workdir.resolve().as_uri(),
                allowed_resource_root=workdir,
            )
        except (MarkdownToHtmlConversionError, HtmlToPdfConversionError) as exc:
            raise map_converter_error(exc) from exc

        return NonPdfExecutionOutcomeV2(
            pipeline_used=pipeline_used,
            backend_used=backend_used,
            acceleration_used=None,
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
        )

    if job.output_format == OutputFormatV2.DOCX:
        pipeline_used = "md_to_docx_v2"
        backend_used = "pandoc"
        reference_docx = resolve_reference_docx(job=job, workdir=workdir)
        intermediate_html = workdir / input_path.with_suffix(".html").name
        try:
            convert_markdown_to_html(
                markdown_path=input_path,
                output_html_path=intermediate_html,
                timeout_seconds=document_timeout_seconds,
            )
            validate_html_resources_for_route(input_path=intermediate_html, workdir=workdir)
            convert_html_to_docx(
                html_path=intermediate_html,
                output_docx_path=job.artifact_path,
                resource_root=workdir,
                reference_docx_path=reference_docx.path,
                timeout_seconds=document_timeout_seconds,
            )
        except (MarkdownToHtmlConversionError, HtmlToDocxConversionError) as exc:
            raise map_converter_error(exc) from exc
        return NonPdfExecutionOutcomeV2(
            pipeline_used=pipeline_used,
            backend_used=backend_used,
            acceleration_used=None,
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
            template_id=reference_docx.template_id,
            template_version=reference_docx.template_version,
            template_artifact_sha256=reference_docx.template_artifact_sha256,
        )

    raise ServiceError(
        status_code=422,
        code="unsupported_route",
        message=(f"Unsupported route: {job.source_format.value} -> {job.output_format.value}."),
        retryable=False,
    )
