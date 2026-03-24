"""Helpers shared across non-PDF service API v2 route executors.

Purpose:
    Centralize shared route helpers (HTML resource validation, DOCX reference
    resolution, CSS preset wiring, and stable error mapping) so per-route
    executors remain small and SRP-aligned.

Relationships:
    - Used by `infrastructure.v2_non_pdf_routes_*`.
    - Used by `infrastructure.v2_conversion_executor` for the PDF->DOCX tail
      stage (markdown->docx).
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, PdfPageCssModeV2
from scripts.sir_convert_a_lot.infrastructure.docx_template_catalog_v2 import (
    DocxTemplateCatalogLoadError,
    DocxTemplateNotFoundError,
    DocxTemplateUnavailableError,
    DocxTemplateVersionNotFoundError,
    ResolvedDocxTemplateV2,
    load_default_docx_template_catalog,
)
from scripts.sir_convert_a_lot.infrastructure.html_resource_references import (
    validate_html_local_resources,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_html import (
    DOCX_TO_HTML_UNREADABLE,
    DocxToHtmlConversionError,
    convert_docx_to_html,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_markdown import (
    DOCX_TO_MARKDOWN_UNREADABLE,
    DocxToMarkdownConversionError,
    convert_docx_to_markdown,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HtmlToDocxConversionError,
    convert_html_to_docx,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_markdown import (
    HtmlToMarkdownConversionError,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MarkdownToHtmlConversionError,
    convert_markdown_to_html,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_layout_presets_v2 import (
    PdfLayoutPresetWriteError,
    write_pdf_layout_preset_stylesheet,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_models import ResolvedReferenceDocxV2
from scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf import (
    HTML_TO_PDF_RESOURCE_BLOCKED,
    HtmlToPdfConversionError,
    convert_html_to_pdf,
)


def _sanitize_filename_for_error(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


def resolve_workdir_resource_path(
    *,
    workdir: Path,
    filename: str,
    field: str,
    invalid_code: str,
) -> Path:
    safe_filename = _sanitize_filename_for_error(filename)
    candidate = (workdir / filename).resolve()
    resolved_workdir = workdir.resolve()
    if not candidate.is_relative_to(resolved_workdir):
        raise ServiceError(
            status_code=422,
            code=invalid_code,
            message=f"Resource path escapes workdir for field '{field}': {safe_filename}",
            retryable=False,
            details={"field": field, "filename": safe_filename},
        )
    return candidate


def validate_html_resources_for_route(*, input_path: Path, workdir: Path) -> None:
    resource_validation = validate_html_local_resources(
        html_path=input_path,
        resource_root=workdir,
    )
    if resource_validation.invalid_references:
        raise ServiceError(
            status_code=422,
            code="html_resource_invalid",
            message="HTML input contains invalid local resource references.",
            retryable=False,
            details={"invalid_resources": resource_validation.invalid_references},
        )
    if resource_validation.missing_references:
        raise ServiceError(
            status_code=422,
            code="html_resource_not_found",
            message="HTML input references missing local resources.",
            retryable=False,
            details={"missing_resources": resource_validation.missing_references},
        )


def resolve_pdf_stylesheets(*, job: StoredJobV2, workdir: Path) -> tuple[Path, ...]:
    css_paths = tuple(
        resolve_workdir_resource_path(
            workdir=workdir,
            filename=name,
            field="conversion.css_filenames",
            invalid_code="css_invalid",
        )
        for name in job.spec.conversion.css_filenames
    )
    for css_path in css_paths:
        if not css_path.exists():
            raise ServiceError(
                status_code=422,
                code="css_not_found",
                message=f"CSS file not found in resources bundle: {css_path.name}",
                retryable=False,
                details={"css_filename": css_path.name},
            )

    page_css_mode = job.spec.conversion.page_css_mode or PdfPageCssModeV2.PRESET_APPEND
    if page_css_mode is PdfPageCssModeV2.AUTHOR_OWNED:
        return css_paths

    layout = job.spec.conversion.pdf_layout
    if layout is None:
        return css_paths

    try:
        preset_path = write_pdf_layout_preset_stylesheet(workdir=workdir, layout=layout)
    except PdfLayoutPresetWriteError as exc:
        raise ServiceError(
            status_code=500,
            code="pdf_layout_write_failed",
            message=str(exc),
            retryable=True,
        ) from exc
    return css_paths + (preset_path,)


def resolve_reference_docx(*, job: StoredJobV2, workdir: Path) -> ResolvedReferenceDocxV2:
    if job.reference_docx_path is not None:
        return ResolvedReferenceDocxV2(path=job.reference_docx_path)
    selector = job.spec.conversion.template
    if selector is not None:
        try:
            resolved_template: ResolvedDocxTemplateV2 = (
                load_default_docx_template_catalog().resolve(
                    template_id=selector.template_id,
                    version=selector.version,
                )
            )
        except DocxTemplateCatalogLoadError as exc:
            raise ServiceError(
                status_code=500,
                code="template_catalog_invalid",
                message=exc.message,
                retryable=False,
            ) from exc
        except DocxTemplateNotFoundError as exc:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Unknown DOCX template id.",
                retryable=False,
                details={
                    "field": "conversion.template.template_id",
                    "template_id": exc.template_id,
                },
            ) from exc
        except DocxTemplateVersionNotFoundError as exc:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Unknown DOCX template version.",
                retryable=False,
                details={
                    "field": "conversion.template.version",
                    "template_id": exc.template_id,
                    "version": exc.version,
                },
            ) from exc
        except DocxTemplateUnavailableError as exc:
            raise ServiceError(
                status_code=409,
                code="template_unavailable",
                message="Requested DOCX template is currently unavailable.",
                retryable=False,
                details={
                    "template_id": exc.template_id,
                    "version": exc.version,
                    "status": exc.status.value,
                },
            ) from exc
        return ResolvedReferenceDocxV2(
            path=resolved_template.artifact_path,
            template_id=resolved_template.metadata.template_id,
            template_version=resolved_template.metadata.version,
            template_artifact_sha256=resolved_template.metadata.artifact_sha256,
        )
    filename = job.spec.conversion.reference_docx_filename
    if filename is None:
        return ResolvedReferenceDocxV2(path=None)
    candidate = resolve_workdir_resource_path(
        workdir=workdir,
        filename=filename,
        field="conversion.reference_docx_filename",
        invalid_code="reference_docx_invalid",
    )
    if not candidate.exists():
        raise ServiceError(
            status_code=422,
            code="reference_docx_not_found",
            message=f"reference_docx_filename was not found in resources: {filename}",
            retryable=False,
            details={"field": "conversion.reference_docx_filename", "filename": filename},
        )
    return ResolvedReferenceDocxV2(path=candidate)


def map_converter_error(exc: Exception) -> ServiceError:
    if isinstance(exc, DocxToMarkdownConversionError):
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("_timeout")
        status_code = 504 if exc.code.endswith("_timeout") else (503 if retryable else 500)
        return ServiceError(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, DocxToHtmlConversionError):
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("_timeout")
        status_code = 504 if exc.code.endswith("_timeout") else (503 if retryable else 500)
        return ServiceError(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, HtmlToMarkdownConversionError):
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("_timeout")
        status_code = 504 if exc.code.endswith("_timeout") else (503 if retryable else 500)
        return ServiceError(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, MarkdownToHtmlConversionError):
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("_timeout")
        status_code = 504 if exc.code.endswith("_timeout") else (503 if retryable else 500)
        return ServiceError(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, HtmlToPdfConversionError):
        if exc.code == HTML_TO_PDF_RESOURCE_BLOCKED:
            return ServiceError(
                status_code=422,
                code=exc.code,
                message=exc.message,
                retryable=False,
            )
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("deps_missing")
        return ServiceError(
            status_code=503 if retryable else 500,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, HtmlToDocxConversionError):
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("_timeout")
        status_code = 504 if exc.code.endswith("_timeout") else (503 if retryable else 500)
        return ServiceError(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    raise AssertionError(f"Unhandled converter error type: {type(exc).__name__}")


def convert_markdown_content_to_docx_v2(
    *,
    job: StoredJobV2,
    workdir: Path,
    markdown_content: str,
    document_timeout_seconds: int,
) -> ResolvedReferenceDocxV2:
    if job.output_format != OutputFormatV2.DOCX:
        raise ValueError("convert_markdown_content_to_docx_v2 requires output_format=docx")

    intermediate_md = workdir / "pdf_checkpointed_output.md"
    intermediate_md.write_text(markdown_content, encoding="utf-8")
    intermediate_html = workdir / "pdf_checkpointed_output.html"
    reference_docx = resolve_reference_docx(job=job, workdir=workdir)
    try:
        convert_markdown_to_html(
            markdown_path=intermediate_md,
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
    return reference_docx


def convert_docx_to_markdown_v2(
    *,
    input_docx_path: Path,
    output_markdown_path: Path,
    timeout_seconds: int,
) -> None:
    try:
        convert_docx_to_markdown(
            docx_path=input_docx_path,
            output_markdown_path=output_markdown_path,
            timeout_seconds=timeout_seconds,
        )
    except DocxToMarkdownConversionError as exc:
        if exc.code == DOCX_TO_MARKDOWN_UNREADABLE:
            raise ServiceError(
                status_code=422,
                code="docx_unreadable",
                message=f"Uploaded DOCX could not be converted: {exc.message}",
                retryable=False,
            ) from exc
        raise map_converter_error(exc) from exc


def convert_docx_to_pdf_v2(
    *,
    job: StoredJobV2,
    input_docx_path: Path,
    workdir: Path,
    output_pdf_path: Path,
    timeout_seconds: int,
) -> None:
    css_paths = resolve_pdf_stylesheets(job=job, workdir=workdir)
    intermediate_html = workdir / input_docx_path.with_suffix(".html").name
    extract_media_dir = workdir / "media"
    try:
        convert_docx_to_html(
            docx_path=input_docx_path,
            output_html_path=intermediate_html,
            extract_media_dir=extract_media_dir,
            timeout_seconds=timeout_seconds,
        )
        validate_html_resources_for_route(input_path=intermediate_html, workdir=workdir)
        convert_html_to_pdf(
            html_path=intermediate_html,
            output_pdf_path=output_pdf_path,
            css_paths=css_paths,
            base_url=workdir.resolve().as_uri(),
            allowed_resource_root=workdir,
        )
    except DocxToHtmlConversionError as exc:
        if exc.code == DOCX_TO_HTML_UNREADABLE:
            raise ServiceError(
                status_code=422,
                code="docx_unreadable",
                message=f"Uploaded DOCX could not be converted: {exc.message}",
                retryable=False,
            ) from exc
        raise map_converter_error(exc) from exc
    except HtmlToPdfConversionError as exc:
        raise map_converter_error(exc) from exc
