"""General v2 conversion executor helper and route tests.

Purpose:
    Cover reference resolution, converter error mapping, and non-PDF route
    execution branches for the v2 conversion executor.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`.
    - Uses shared builders in `v2_conversion_executor_test_support`.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_conversion_executor
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MarkdownToHtmlConversionError,
)
from scripts.sir_convert_a_lot.infrastructure.resources_zip import ResourcesZipError
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    _map_converter_error,
    _resolve_reference_docx,
    execute_v2_job_conversion,
    fingerprint_job_options,
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

    resolved = _resolve_reference_docx(job=job, workdir=workdir)

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

    resolved = _resolve_reference_docx(job=job, workdir=workdir)

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
        _resolve_reference_docx(job=job, workdir=workdir)

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

    resolved = _resolve_reference_docx(job=job, workdir=workdir)

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
    ],
)
def test_map_converter_error_for_markdown_and_html_errors(
    error: Exception,
    expected_code: str,
    expected_message: str,
    expected_status: int,
    expected_retryable: bool,
) -> None:
    mapped = _map_converter_error(error)

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


def test_execute_v2_job_conversion_md_to_pdf_success_with_stubbed_converters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown_calls: list[tuple[Path, Path]] = []
    html_pdf_calls: list[tuple[Path, Path, tuple[Path, ...], str]] = []

    def _fake_convert_markdown_to_html(*, markdown_path: Path, output_html_path: Path) -> None:
        markdown_calls.append((markdown_path, output_html_path))
        output_html_path.write_text("<html><body>Converted</body></html>", encoding="utf-8")

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
    ) -> None:
        html_pdf_calls.append((html_path, output_pdf_path, css_paths, base_url or ""))
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(
        v2_conversion_executor, "convert_markdown_to_html", _fake_convert_markdown_to_html
    )
    monkeypatch.setattr(v2_conversion_executor, "convert_html_to_pdf", _fake_convert_html_to_pdf)

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


def test_execute_v2_job_conversion_pdf_to_docx_invalid_pdf_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _unexpected_execute_job_conversion(
        **kwargs: object,
    ) -> tuple[str, object, list[str], dict[str, int]]:
        del kwargs
        raise AssertionError("execute_job_conversion should not run for invalid PDF bytes")

    monkeypatch.setattr(
        v2_conversion_executor, "execute_job_conversion", _unexpected_execute_job_conversion
    )

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
    def _fake_convert_markdown_to_html(*, markdown_path: Path, output_html_path: Path) -> None:
        del markdown_path
        output_html_path.write_text("<html><body>Converted</body></html>", encoding="utf-8")

    def _fake_convert_html_to_pdf(
        *,
        html_path: Path,
        output_pdf_path: Path,
        css_paths: tuple[Path, ...] = (),
        base_url: str | None = None,
    ) -> None:
        del html_path, css_paths, base_url
        output_pdf_path.write_bytes(b"")

    monkeypatch.setattr(
        v2_conversion_executor, "convert_markdown_to_html", _fake_convert_markdown_to_html
    )
    monkeypatch.setattr(v2_conversion_executor, "convert_html_to_pdf", _fake_convert_html_to_pdf)

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


def test_prepare_workdir_extracts_resources_zip_and_copies_source(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Source</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.DOCX,
    )
    resources_zip_path = tmp_path / "raw" / "resources.zip"
    with zipfile.ZipFile(resources_zip_path, mode="w") as archive:
        archive.writestr("styles/site.css", "body { color: #111; }\n")
        archive.writestr("assets/data.txt", "ok\n")
    job.resources_zip_path = resources_zip_path

    workdir, input_path = v2_conversion_executor._prepare_workdir(job)

    assert workdir == job.upload_path.parent / "workdir"
    assert input_path == workdir / "page.html"
    assert input_path.read_bytes() == b"<html><body>Source</body></html>"
    assert (workdir / "styles/site.css").read_text(encoding="utf-8") == "body { color: #111; }\n"
    assert (workdir / "assets/data.txt").read_text(encoding="utf-8") == "ok\n"


def test_prepare_workdir_maps_resources_zip_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
    )
    resources_zip_path = tmp_path / "raw" / "broken.zip"
    resources_zip_path.write_bytes(b"not-a-real-zip")
    job.resources_zip_path = resources_zip_path

    def _raise_resources_zip_error(*, zip_path: Path, output_dir: Path) -> None:
        del zip_path, output_dir
        raise ResourcesZipError(
            code="resources_zip_invalid",
            message="Uploaded resources bundle is not a valid zip file.",
        )

    monkeypatch.setattr(v2_conversion_executor, "extract_resources_zip", _raise_resources_zip_error)

    with pytest.raises(ServiceError) as exc_info:
        v2_conversion_executor._prepare_workdir(job)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "resources_zip_invalid"
    assert error.message == "Uploaded resources bundle is not a valid zip file."
    assert error.retryable is False
