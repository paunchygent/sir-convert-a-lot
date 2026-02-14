"""Tests for PyMuPDF backend mapping and deterministic conversion behavior.

Purpose:
    Validate Task 11 backend semantics: table-strategy mapping, deterministic
    output, and metadata truth for `backend_strategy="pymupdf"`.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.pymupdf_backend`.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendInputError,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.pymupdf_backend import PyMuPdfConversionBackend
from tests.sir_convert_a_lot.pdf_fixtures import fixture_pdf_bytes


def _request(*, table_mode: TableMode = TableMode.FAST) -> ConversionRequest:
    return ConversionRequest(
        source_filename="paper_alpha.pdf",
        source_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        backend_strategy=BackendStrategy.PYMUPDF,
        ocr_mode=OcrMode.OFF,
        table_mode=table_mode,
        gpu_available=False,
    )


def test_pymupdf_backend_real_fixture_reports_truthful_metadata() -> None:
    backend = PyMuPdfConversionBackend()
    result = backend.convert(_request(table_mode=TableMode.FAST))

    assert result.backend_used == "pymupdf"
    assert result.acceleration_used == "cpu"
    assert result.ocr_enabled is False
    assert isinstance(result.markdown_content, str)
    assert result.markdown_content.strip() != ""


def test_pymupdf_backend_is_deterministic_for_identical_input() -> None:
    backend = PyMuPdfConversionBackend()
    first = backend.convert(_request(table_mode=TableMode.ACCURATE))
    second = backend.convert(_request(table_mode=TableMode.ACCURATE))

    assert first.markdown_content == second.markdown_content
    assert first.backend_used == second.backend_used == "pymupdf"
    assert first.acceleration_used == second.acceleration_used == "cpu"


@pytest.mark.parametrize(
    ("table_mode", "expected_strategy"),
    [
        (TableMode.FAST, "lines"),
        (TableMode.ACCURATE, "lines_strict"),
    ],
)
def test_pymupdf_table_mode_mapping(
    monkeypatch, table_mode: TableMode, expected_strategy: str
) -> None:
    backend = PyMuPdfConversionBackend()
    observed_strategy: list[str] = []

    def _fake_to_markdown(_document, table_strategy: str) -> str:
        observed_strategy.append(table_strategy)
        return "mock markdown"

    monkeypatch.setattr(backend, "_to_markdown", _fake_to_markdown)
    result = backend.convert(_request(table_mode=table_mode))

    assert observed_strategy == [expected_strategy]
    assert result.markdown_content == "mock markdown"


def test_invalid_pdf_bytes_raise_backend_input_error() -> None:
    backend = PyMuPdfConversionBackend()
    request = ConversionRequest(
        source_filename="broken.pdf",
        source_bytes=b"not-a-pdf",
        backend_strategy=BackendStrategy.PYMUPDF,
        ocr_mode=OcrMode.OFF,
        table_mode=TableMode.FAST,
        gpu_available=False,
    )

    with pytest.raises(BackendInputError):
        backend.convert(request)


def test_unexpected_markdown_failure_raises_backend_execution_error(monkeypatch) -> None:
    backend = PyMuPdfConversionBackend()

    def _explode(_document, table_strategy: str) -> str:
        raise RuntimeError(f"boom-{table_strategy}")

    monkeypatch.setattr(backend, "_to_markdown", _explode)

    with pytest.raises(BackendExecutionError):
        backend.convert(_request(table_mode=TableMode.FAST))
