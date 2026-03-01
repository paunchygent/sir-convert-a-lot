"""V2 conversion executor tests for the `docx -> pdf` route."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_conversion_executor
from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_html import (
    DOCX_TO_HTML_UNREADABLE,
    DocxToHtmlConversionError,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


def test_execute_v2_job_conversion_docx_to_pdf_success_with_stubbed_converters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_docx_to_html(
        *,
        docx_path: Path,
        output_html_path: Path,
        extract_media_dir: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del docx_path, extract_media_dir, timeout_seconds
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
        output_pdf_path.write_bytes(b"%PDF-1.7\nstub-pdf\n")

    monkeypatch.setattr(v2_conversion_executor, "convert_docx_to_html", _fake_convert_docx_to_html)
    monkeypatch.setattr(v2_conversion_executor, "convert_html_to_pdf", _fake_convert_html_to_pdf)

    job = _build_job(
        tmp_path,
        source_filename="input.docx",
        source_bytes=b"PK\x03\x04fake-docx-content",
        source_format=SourceFormatV2.DOCX,
        output_format=OutputFormatV2.PDF,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.pipeline_used == "docx_to_pdf_v2"
    assert result.backend_used == "pandoc+weasyprint"
    assert result.artifact_bytes.startswith(b"%PDF-")


def test_execute_v2_job_conversion_docx_to_pdf_rejects_non_docx_bytes(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="input.docx",
        source_bytes=b"not-a-docx",
        source_format=SourceFormatV2.DOCX,
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
    assert error.code == "docx_unreadable"


def test_execute_v2_job_conversion_docx_to_pdf_maps_unreadable_pandoc_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _raise_unreadable(
        *,
        docx_path: Path,
        output_html_path: Path,
        extract_media_dir: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del docx_path, output_html_path, extract_media_dir, timeout_seconds
        raise DocxToHtmlConversionError(
            code=DOCX_TO_HTML_UNREADABLE,
            message="couldn't unpack docx container: not a valid zip",
        )

    monkeypatch.setattr(v2_conversion_executor, "convert_docx_to_html", _raise_unreadable)

    job = _build_job(
        tmp_path,
        source_filename="input.docx",
        source_bytes=b"PK\x03\x04fake-docx-content",
        source_format=SourceFormatV2.DOCX,
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
    assert error.code == "docx_unreadable"
