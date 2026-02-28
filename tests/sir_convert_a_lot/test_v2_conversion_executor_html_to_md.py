"""HTML-to-Markdown branch tests for v2 conversion executor.

Purpose:
    Validate the `html -> md` v2 branch, including local-resource validation,
    converter-error mapping, and deterministic normalization wiring.

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
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_markdown import (
    HtmlToMarkdownConversionError,
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


def test_execute_v2_job_conversion_html_to_md_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_html_to_markdown(
        *,
        html_path: Path,
        output_markdown_path: Path,
        resource_root: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del html_path, resource_root, timeout_seconds
        output_markdown_path.write_text("raw markdown with [MISSING_PAGE_POST]\n", encoding="utf-8")

    def _fake_normalize_markdown_for_v2_md_output(
        *,
        markdown_content: str,
        mode,
    ) -> tuple[str, list[str]]:
        del mode
        assert "raw markdown" in markdown_content
        return ("# Normalized\n\nBody\n", ["normalized_warning"])

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_markdown",
        _fake_convert_html_to_markdown,
    )
    monkeypatch.setattr(
        v2_conversion_executor,
        "normalize_markdown_for_v2_md_output",
        _fake_normalize_markdown_for_v2_md_output,
    )

    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.artifact_bytes == b"# Normalized\n\nBody\n"
    assert result.pipeline_used == "html_to_md_v2"
    assert result.backend_used == "pandoc"
    assert result.warnings == ["normalized_warning"]


def test_execute_v2_job_conversion_html_to_md_missing_resource(
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body><img src='assets/logo.png'></body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
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
    assert error.retryable is False


def test_execute_v2_job_conversion_html_to_md_invalid_resource_path(
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body><img src='../outside.png'></body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
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
    assert error.code == "html_resource_invalid"
    assert error.details == {"invalid_resources": ["../outside.png"]}
    assert error.retryable is False


def test_execute_v2_job_conversion_html_to_md_with_resources_zip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_html_to_markdown(
        *,
        html_path: Path,
        output_markdown_path: Path,
        resource_root: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del timeout_seconds
        assert (resource_root / "assets" / "logo.png").exists()
        assert html_path.name == "index.html"
        output_markdown_path.write_text("# Converted\n\nBody\n", encoding="utf-8")

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_markdown",
        _fake_convert_html_to_markdown,
    )

    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body><img src='assets/logo.png'></body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
    )
    resources_zip_path = tmp_path / "raw" / "resources.zip"
    with zipfile.ZipFile(resources_zip_path, mode="w") as archive:
        archive.writestr("assets/logo.png", b"\x89PNG\r\n")
    job.resources_zip_path = resources_zip_path

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.pipeline_used == "html_to_md_v2"
    assert result.artifact_bytes.startswith(b"# Converted")


def test_execute_v2_job_conversion_html_to_md_maps_converter_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _failing_convert_html_to_markdown(
        *,
        html_path: Path,
        output_markdown_path: Path,
        resource_root: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del html_path, output_markdown_path, resource_root, timeout_seconds
        raise HtmlToMarkdownConversionError(
            code="html_to_markdown_failed",
            message="Pandoc failed to convert HTML to Markdown.",
        )

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_markdown",
        _failing_convert_html_to_markdown,
    )

    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
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
    assert error.code == "html_to_markdown_failed"
    assert error.retryable is False


def test_execute_v2_job_conversion_html_to_md_uses_timeout_from_execution_spec(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_timeout_seconds: list[int] = []

    def _fake_convert_html_to_markdown(
        *,
        html_path: Path,
        output_markdown_path: Path,
        resource_root: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del html_path, resource_root
        captured_timeout_seconds.append(timeout_seconds)
        output_markdown_path.write_text("# Converted\n\nBody\n", encoding="utf-8")

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_markdown",
        _fake_convert_html_to_markdown,
    )

    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
        execution_timeout_seconds=45,
    )

    execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert captured_timeout_seconds == [45]


def test_execute_v2_job_conversion_html_to_md_uses_default_timeout_without_execution_spec(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_timeout_seconds: list[int] = []

    def _fake_convert_html_to_markdown(
        *,
        html_path: Path,
        output_markdown_path: Path,
        resource_root: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del html_path, resource_root
        captured_timeout_seconds.append(timeout_seconds)
        output_markdown_path.write_text("# Converted\n\nBody\n", encoding="utf-8")

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_markdown",
        _fake_convert_html_to_markdown,
    )

    job = _build_job(
        tmp_path,
        source_filename="index.html",
        source_bytes=b"<html><body>Hello</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
    )

    execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert captured_timeout_seconds == [300]
