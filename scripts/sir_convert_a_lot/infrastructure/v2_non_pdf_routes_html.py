"""HTML-source route executors for service API v2.

Purpose:
    Keep HTML-based v2 routes isolated:
      - `html -> md`
      - `html -> pdf`
      - `html -> docx`

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
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HtmlToDocxConversionError,
    convert_html_to_docx,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_markdown import (
    HtmlToMarkdownConversionError,
    convert_html_to_markdown,
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
    HtmlToPdfInputTrustMode,
    convert_html_to_pdf,
)


def execute_html_source_route_v2(
    *,
    job: StoredJobV2,
    workdir: Path,
    input_path: Path,
    document_timeout_seconds: int,
) -> NonPdfExecutionOutcomeV2:
    if job.source_format != SourceFormatV2.HTML:
        raise ValueError("execute_html_source_route_v2 requires source_format=html")

    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}

    validate_html_resources_for_route(input_path=input_path, workdir=workdir)

    if job.output_format == OutputFormatV2.MD:
        pipeline_used = "html_to_md_v2"
        backend_used = "pandoc"
        try:
            convert_html_to_markdown(
                html_path=input_path,
                output_markdown_path=job.artifact_path,
                resource_root=workdir,
                timeout_seconds=document_timeout_seconds,
            )
        except HtmlToMarkdownConversionError as exc:
            raise map_converter_error(exc) from exc

        normalized_markdown, normalization_warnings = normalize_markdown_for_v2_md_output(
            markdown_content=job.artifact_path.read_text(encoding="utf-8"),
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
        pipeline_used = "html_to_pdf_v2"
        backend_used = "weasyprint"
        css_paths = resolve_pdf_stylesheets(job=job, workdir=workdir)
        try:
            convert_html_to_pdf(
                html_path=input_path,
                output_pdf_path=job.artifact_path,
                css_paths=css_paths,
                base_url=workdir.resolve().as_uri(),
                allowed_resource_root=workdir,
                input_trust_mode=HtmlToPdfInputTrustMode(
                    job.spec.conversion.input_trust_mode.value
                ),
            )
        except HtmlToPdfConversionError as exc:
            raise map_converter_error(exc) from exc
        return NonPdfExecutionOutcomeV2(
            pipeline_used=pipeline_used,
            backend_used=backend_used,
            acceleration_used=None,
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
        )

    if job.output_format == OutputFormatV2.DOCX:
        pipeline_used = "html_to_docx_v2"
        backend_used = "pandoc"
        reference_docx = resolve_reference_docx(job=job, workdir=workdir)
        try:
            convert_html_to_docx(
                html_path=input_path,
                output_docx_path=job.artifact_path,
                resource_root=workdir,
                reference_docx_path=reference_docx.path,
                timeout_seconds=document_timeout_seconds,
            )
        except HtmlToDocxConversionError as exc:
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
