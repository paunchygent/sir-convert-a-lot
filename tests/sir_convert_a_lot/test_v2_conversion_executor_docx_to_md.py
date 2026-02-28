"""DOCX-to-Markdown branch tests for v2 conversion executor.

Purpose:
    Validate the `docx -> md` v2 branch, including unreadable-input handling,
    converter-error mapping, and deterministic normalization wiring.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`.
    - Uses shared builders in `v2_conversion_executor_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_conversion_executor
from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_markdown import (
    DOCX_TO_MARKDOWN_UNREADABLE,
    DocxToMarkdownConversionError,
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


def test_execute_v2_job_conversion_docx_to_md_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_docx_to_markdown(*, docx_path: Path, output_markdown_path: Path) -> None:
        del docx_path
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
        "convert_docx_to_markdown",
        _fake_convert_docx_to_markdown,
    )
    monkeypatch.setattr(
        v2_conversion_executor,
        "normalize_markdown_for_v2_md_output",
        _fake_normalize_markdown_for_v2_md_output,
    )

    job = _build_job(
        tmp_path,
        source_filename="input.docx",
        source_bytes=b"PK\x03\x04docx-bytes",
        source_format=SourceFormatV2.DOCX,
        output_format=OutputFormatV2.MD,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.artifact_bytes == b"# Normalized\n\nBody\n"
    assert result.pipeline_used == "docx_to_md_v2"
    assert result.backend_used == "pandoc"
    assert result.warnings == ["normalized_warning"]


def test_execute_v2_job_conversion_docx_to_md_rejects_non_docx_bytes(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="input.docx",
        source_bytes=b"not-a-docx",
        source_format=SourceFormatV2.DOCX,
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
    assert error.code == "docx_unreadable"
    assert error.retryable is False


def test_execute_v2_job_conversion_docx_to_md_maps_unreadable_converter_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _failing_convert_docx_to_markdown(*, docx_path: Path, output_markdown_path: Path) -> None:
        del docx_path, output_markdown_path
        raise DocxToMarkdownConversionError(
            code=DOCX_TO_MARKDOWN_UNREADABLE,
            message="Pandoc failed to unpack DOCX container.",
        )

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_docx_to_markdown",
        _failing_convert_docx_to_markdown,
    )

    job = _build_job(
        tmp_path,
        source_filename="input.docx",
        source_bytes=b"PK\x03\x04docx-bytes",
        source_format=SourceFormatV2.DOCX,
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
    assert error.code == "docx_unreadable"
    assert error.retryable is False
