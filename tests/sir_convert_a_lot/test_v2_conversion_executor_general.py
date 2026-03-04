"""General v2 conversion executor helper and route tests.

Purpose:
    Cover reference resolution, converter error mapping, and non-PDF route
    execution branches for the v2 conversion executor.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`.
    - Uses shared builders in `v2_conversion_executor_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_routes_md as v2_non_pdf_routes_md
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MarkdownToHtmlConversionError,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
    fingerprint_job_options,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_helpers import (
    map_converter_error,
    resolve_reference_docx,
)
from scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf import (
    HtmlToPdfConversionError,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


def test_resolve_reference_docx_prefers_explicit_path(tmp_path: Path) -> None:
    explicit_reference = tmp_path / "explicit-reference.docx"
    explicit_reference.write_bytes(b"template")
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True)
    (workdir / "from-conversion.docx").write_bytes(b"ignored")

    job = _build_job(
        tmp_path,
        source_filename="source.md",
        source_bytes=b"# Title\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
        reference_docx_filename="from-conversion.docx",
        reference_docx_path=explicit_reference,
    )

    resolved = resolve_reference_docx(job=job, workdir=workdir)

    assert resolved.path == explicit_reference
    assert resolved.template_id is None


def test_resolve_reference_docx_uses_workdir_filename_hit(tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True)
    expected = workdir / "reference.docx"
    expected.write_bytes(b"template")

    job = _build_job(
        tmp_path,
        source_filename="source.md",
        source_bytes=b"# Title\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
        reference_docx_filename="reference.docx",
    )

    resolved = resolve_reference_docx(job=job, workdir=workdir)

    assert resolved.path == expected
    assert resolved.template_id is None


def test_resolve_reference_docx_uses_workdir_filename_miss_returns_validation_error(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True)
    job = _build_job(
        tmp_path,
        source_filename="source.md",
        source_bytes=b"# Title\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
        reference_docx_filename="missing-reference.docx",
    )

    with pytest.raises(ServiceError) as exc_info:
        resolve_reference_docx(job=job, workdir=workdir)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "reference_docx_not_found"
    assert error.details == {
        "field": "conversion.reference_docx_filename",
        "filename": "missing-reference.docx",
    }


def test_resolve_reference_docx_none_when_no_filename_or_explicit_path(tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True)
    job = _build_job(
        tmp_path,
        source_filename="source.md",
        source_bytes=b"# Title\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
        reference_docx_filename=None,
    )

    resolved = resolve_reference_docx(job=job, workdir=workdir)

    assert resolved.path is None
    assert resolved.template_id is None


@pytest.mark.parametrize(
    ("error", "expected_code", "expected_message", "expected_status", "expected_retryable"),
    [
        (
            MarkdownToHtmlConversionError(
                code="pandoc_not_installed",
                message="Pandoc missing.",
            ),
            "pandoc_not_installed",
            "Pandoc missing.",
            503,
            True,
        ),
        (
            MarkdownToHtmlConversionError(
                code="markdown_to_html_failed",
                message="Pandoc failed.",
            ),
            "markdown_to_html_failed",
            "Pandoc failed.",
            500,
            False,
        ),
        (
            HtmlToPdfConversionError(
                code="weasyprint_not_installed",
                message="WeasyPrint missing.",
            ),
            "weasyprint_not_installed",
            "WeasyPrint missing.",
            503,
            True,
        ),
        (
            HtmlToPdfConversionError(
                code="html_to_pdf_failed",
                message="Render failed.",
            ),
            "html_to_pdf_failed",
            "Render failed.",
            500,
            False,
        ),
        (
            HtmlToPdfConversionError(
                code="html_to_pdf_resource_blocked",
                message="Blocked external resource URL: http://example.invalid",
            ),
            "html_to_pdf_resource_blocked",
            "Blocked external resource URL: http://example.invalid",
            422,
            False,
        ),
        (
            MarkdownToHtmlConversionError(
                code="markdown_to_html_timeout",
                message="Pandoc timed out after 300 seconds.",
            ),
            "markdown_to_html_timeout",
            "Pandoc timed out after 300 seconds.",
            504,
            True,
        ),
    ],
)
def test_map_converter_error_for_markdown_and_html_errors(
    error: Exception,
    expected_code: str,
    expected_message: str,
    expected_status: int,
    expected_retryable: bool,
) -> None:
    mapped = map_converter_error(error)

    assert mapped.status_code == expected_status
    assert mapped.code == expected_code
    assert mapped.message == expected_message
    assert mapped.retryable is expected_retryable


def test_execute_v2_job_conversion_html_to_pdf_css_not_found(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
        css_filenames=["missing.css"],
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "css_not_found"
    assert error.retryable is False
    assert error.details == {"css_filename": "missing.css"}


def test_resolve_reference_docx_rejects_workdir_traversal(tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True)
    job = _build_job(
        tmp_path,
        source_filename="source.md",
        source_bytes=b"# Title\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
        reference_docx_filename="../../../etc/passwd",
    )

    with pytest.raises(ServiceError) as exc_info:
        resolve_reference_docx(job=job, workdir=workdir)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "reference_docx_invalid"
    assert error.retryable is False


def test_execute_v2_job_conversion_html_to_pdf_rejects_css_traversal(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
        css_filenames=["../outside.css"],
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "css_invalid"
    assert error.retryable is False


def test_execute_v2_job_conversion_html_to_pdf_rejects_missing_local_resource(
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body><img src='assets/logo.png'></body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "html_resource_not_found"
    assert error.details == {"missing_resources": ["assets/logo.png"]}


def test_execute_v2_job_conversion_md_to_pdf_success_with_stubbed_converters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown_calls: list[tuple[Path, Path]] = []
    html_pdf_calls: list[tuple[Path, Path, tuple[Path, ...], str, Path | None]] = []

    def _fake_convert_markdown_to_html(
        *,
        markdown_path: Path,
        output_html_path: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del timeout_seconds
        markdown_calls.append((markdown_path, output_html_path))
        output_html_path.write_text("<html><body>Converted</body></html>", encoding="utf-8")

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
        allowed_resource_root: Path | None = None,
    ) -> None:
        html_pdf_calls.append(
            (html_path, output_pdf_path, css_paths, base_url or "", allowed_resource_root)
        )
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(
        v2_non_pdf_routes_md,
        "convert_markdown_to_html",
        _fake_convert_markdown_to_html,
    )
    monkeypatch.setattr(v2_non_pdf_routes_md, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n\nBody\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.artifact_bytes == b"%PDF-1.7\nstub-pdf\n"
    assert result.pipeline_used == "md_to_pdf_v2"
    assert result.backend_used == "pandoc+weasyprint"
    assert result.acceleration_used is None
    assert result.warnings == []
    assert result.phase_timings_ms == {}
    assert result.options_fingerprint == fingerprint_job_options(job.spec)
    assert len(markdown_calls) == 1
    assert len(html_pdf_calls) == 1
    assert markdown_calls[0][0].name == "note.md"
    assert markdown_calls[0][1].name == "note.html"
    assert html_pdf_calls[0][0].name == "note.html"
    assert html_pdf_calls[0][1] == job.artifact_path
    assert html_pdf_calls[0][2] == ()
    assert html_pdf_calls[0][3].startswith("file://")
    assert html_pdf_calls[0][4] == job.upload_path.parent / "workdir"


def test_execute_v2_job_conversion_pdf_to_docx_invalid_pdf_bytes(
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"not-a-pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.DOCX,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "pdf_unreadable"
    assert error.retryable is False
    assert error.message == "Uploaded file is not a readable PDF."


def test_execute_v2_job_conversion_unsupported_route(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"%PDF-1.7\nminimal\n",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.PDF,
        spec_source_format=SourceFormatV2.MD,
        spec_output_format=OutputFormatV2.PDF,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "unsupported_route"
    assert error.retryable is False
    assert error.message == "Unsupported route: pdf -> pdf."


def test_execute_v2_job_conversion_artifact_empty_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_markdown_to_html(
        *,
        markdown_path: Path,
        output_html_path: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del markdown_path, timeout_seconds
        output_html_path.write_text("<html><body>Converted</body></html>", encoding="utf-8")

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
        allowed_resource_root: Path | None = None,
    ) -> None:
        del html_path, css_paths, base_url, allowed_resource_root
        output_pdf_path.write_bytes(b"")

    monkeypatch.setattr(
        v2_non_pdf_routes_md,
        "convert_markdown_to_html",
        _fake_convert_markdown_to_html,
    )
    monkeypatch.setattr(v2_non_pdf_routes_md, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n\nBody\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 500
    assert error.code == "artifact_empty"
    assert error.retryable is True
    assert error.message == "Conversion produced an empty artifact file."
