"""Tests for Docling backend mapping and OCR auto-retry behavior.

Purpose:
    Validate Task 10 backend semantics: backend mapping, OCR policy mapping,
    deterministic auto-retry behavior, and metadata truth.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.docling_backend`.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.docling_backend import (
    DoclingConversionBackend,
    _DoclingAttempt,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from tests.sir_convert_a_lot.pdf_fixtures import docling_cuda_available, fixture_pdf_bytes


def _request(
    *,
    ocr_mode: OcrMode = OcrMode.AUTO,
    gpu_available: bool = True,
    table_mode: TableMode = TableMode.FAST,
) -> ConversionRequest:
    return ConversionRequest(
        source_filename="paper_alpha.pdf",
        source_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        backend_strategy=BackendStrategy.DOCLING,
        ocr_mode=ocr_mode,
        table_mode=table_mode,
        gpu_available=gpu_available,
    )


@pytest.fixture(autouse=True)
def _probe_gpu_available(monkeypatch: pytest.MonkeyPatch) -> None:
    probe = GpuRuntimeProbeResult(
        runtime_kind="rocm",
        torch_version="2.10.0+rocm7.1",
        hip_version="7.1.25424",
        cuda_version=None,
        is_available=True,
        device_count=1,
        device_name="AMD Radeon AI PRO R9700",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.docling_backend.probe_torch_gpu_runtime",
        lambda: probe,
    )


@pytest.mark.skipif(
    not docling_cuda_available(),
    reason="Docling real-conversion tests require a GPU runtime.",
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
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment
        calls.append((ocr_enabled, force_full_page_ocr))
        if len(calls) == 1:
            return _DoclingAttempt(markdown_content="", page_count=1, low_confidence=False)
        return _DoclingAttempt(
            markdown_content="Recovered text after OCR retry.",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(_request(ocr_mode=OcrMode.AUTO, gpu_available=True))

    assert calls == [(False, False), (True, True)]
    assert result.ocr_enabled is True
    assert "docling_auto_ocr_retry_applied" in result.warnings
    assert "Recovered text after OCR retry." in result.markdown_content
    assert result.acceleration_used == "cuda"


def test_auto_mode_skips_retry_when_dense_and_confident(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[tuple[bool, bool]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment
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
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment
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


def test_auto_mode_retries_when_low_confidence_even_if_dense(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[tuple[bool, bool]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment
        calls.append((ocr_enabled, force_full_page_ocr))
        if len(calls) == 1:
            return _DoclingAttempt(
                markdown_content=" ".join(["dense"] * 200),
                page_count=1,
                low_confidence=True,
            )
        return _DoclingAttempt(
            markdown_content="Recovered text after low confidence retry.",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(_request(ocr_mode=OcrMode.AUTO))

    assert calls == [(False, False), (True, True)]
    assert result.ocr_enabled is True
    assert "docling_auto_ocr_retry_applied" in result.warnings


def test_gpu_runtime_unavailable_fails_closed_even_when_gpu_flag_false(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    probe = GpuRuntimeProbeResult(
        runtime_kind="none",
        torch_version="2.10.0+cu128",
        hip_version=None,
        cuda_version="12.8",
        is_available=False,
        device_count=0,
        device_name=None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.docling_backend.probe_torch_gpu_runtime",
        lambda: probe,
    )

    with pytest.raises(BackendGpuUnavailableError):
        backend.convert(_request(ocr_mode=OcrMode.OFF, gpu_available=False))


def test_gpu_flag_false_still_reports_cuda_when_runtime_available(monkeypatch) -> None:
    backend = DoclingConversionBackend()

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device, formula_enrichment
        return _DoclingAttempt(
            markdown_content="ok",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(_request(ocr_mode=OcrMode.OFF, gpu_available=False))
    assert result.acceleration_used == "cuda"


def test_accurate_mode_attempts_formula_enrichment(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    formula_flags: list[bool] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        formula_flags.append(formula_enrichment)
        return _DoclingAttempt(
            markdown_content="formula-enriched-output",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(
        _request(
            ocr_mode=OcrMode.OFF,
            gpu_available=True,
            table_mode=TableMode.ACCURATE,
        )
    )

    assert result.markdown_content == "formula-enriched-output"
    assert formula_flags == [True]
    assert "docling_formula_enrichment_unavailable_fallback" not in result.warnings


def test_formula_enrichment_falls_back_when_runtime_unavailable(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    formula_flags: list[bool] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        formula_flags.append(formula_enrichment)
        if formula_enrichment:
            raise BackendExecutionError(
                "Docling backend execution failed: CodeFormulaV2 model unavailable"
            )
        return _DoclingAttempt(
            markdown_content="fallback-without-formula",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)
    result = backend.convert(
        _request(
            ocr_mode=OcrMode.OFF,
            gpu_available=True,
            table_mode=TableMode.ACCURATE,
        )
    )

    assert result.markdown_content == "fallback-without-formula"
    assert formula_flags == [True, False]
    assert result.warnings == ["docling_formula_enrichment_unavailable_fallback"]


@pytest.mark.skipif(
    not docling_cuda_available(),
    reason="Docling real-conversion tests require a GPU runtime.",
)
def test_invalid_pdf_raises_backend_input_error() -> None:
    backend = DoclingConversionBackend()
    request = ConversionRequest(
        source_filename="broken.pdf",
        source_bytes=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n",
        backend_strategy=BackendStrategy.DOCLING,
        ocr_mode=OcrMode.OFF,
        table_mode=TableMode.FAST,
        gpu_available=True,
    )

    with pytest.raises(BackendInputError):
        backend.convert(request)
