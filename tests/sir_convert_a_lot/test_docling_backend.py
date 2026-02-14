"""Tests for Docling backend mapping and OCR auto-retry behavior.

Purpose:
    Validate Task 10 backend semantics: backend mapping, OCR policy mapping,
    deterministic auto-retry behavior, and metadata truth.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.docling_backend`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import ConversionRequest
from scripts.sir_convert_a_lot.infrastructure.docling_backend import (
    DoclingConversionBackend,
    _DoclingAttempt,
)
from tests.sir_convert_a_lot.pdf_fixtures import fixture_pdf_bytes


def _request(
    *,
    ocr_mode: OcrMode = OcrMode.AUTO,
    gpu_available: bool = True,
) -> ConversionRequest:
    return ConversionRequest(
        source_filename="paper_alpha.pdf",
        source_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        backend_strategy=BackendStrategy.DOCLING,
        ocr_mode=ocr_mode,
        table_mode=TableMode.FAST,
        gpu_available=gpu_available,
    )


def test_docling_backend_real_fixture_reports_truthful_metadata() -> None:
    backend = DoclingConversionBackend()
    result = backend.convert(_request(ocr_mode=OcrMode.OFF, gpu_available=True))

    assert result.backend_used == "docling"
    assert result.acceleration_used == "cuda"
    assert result.ocr_enabled is False
    assert isinstance(result.markdown_content, str)
    assert result.markdown_content.strip() != ""


def test_auto_mode_retries_when_first_pass_is_sparse(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[tuple[bool, bool]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
    ) -> _DoclingAttempt:
        calls.append((ocr_enabled, force_full_page_ocr))
        if len(calls) == 1:
            return _DoclingAttempt(markdown_content="", page_count=1, low_confidence=False)
        return _DoclingAttempt(
            markdown_content="Recovered text after OCR retry.",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(_request(ocr_mode=OcrMode.AUTO, gpu_available=False))

    assert calls == [(False, False), (True, True)]
    assert result.ocr_enabled is True
    assert "docling_auto_ocr_retry_applied" in result.warnings
    assert "Recovered text after OCR retry." in result.markdown_content
    assert result.acceleration_used == "cpu"


def test_auto_mode_skips_retry_when_dense_and_confident(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[tuple[bool, bool]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
    ) -> _DoclingAttempt:
        calls.append((ocr_enabled, force_full_page_ocr))
        return _DoclingAttempt(
            markdown_content=" ".join(["dense"] * 200),
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(_request(ocr_mode=OcrMode.AUTO))

    assert calls == [(False, False)]
    assert result.ocr_enabled is False
    assert result.warnings == []


def test_force_mode_runs_single_ocr_pass(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[tuple[bool, bool]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
    ) -> _DoclingAttempt:
        calls.append((ocr_enabled, force_full_page_ocr))
        return _DoclingAttempt(
            markdown_content="OCR forced content.",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(_request(ocr_mode=OcrMode.FORCE))

    assert calls == [(True, True)]
    assert result.ocr_enabled is True
    assert result.warnings == []
