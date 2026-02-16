"""Tests for Docling ordering quality-gate fallback behavior.

Purpose:
    Validate deterministic layout-candidate resolution and ordering-based
    fallback selection behavior for Task 26 source-level mitigation.

Relationships:
    - Exercises ordering-gate flow in
      `scripts.sir_convert_a_lot.infrastructure.docling_backend`.
    - Covers layout candidate helpers exported from the backend module.
"""

from __future__ import annotations

import pytest
from docling.datamodel.accelerator_options import AcceleratorDevice

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.docling_backend import (
    DoclingConversionBackend,
    _DoclingAttempt,
    _resolve_layout_model_candidate_keys,
)
from scripts.sir_convert_a_lot.infrastructure.docling_ordering import OrderingQualityReport
from tests.sir_convert_a_lot.pdf_fixtures import fixture_pdf_bytes


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


def test_layout_model_candidates_default_include_heron_for_egret_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_egret_large")
    monkeypatch.delenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS", raising=False)
    assert _resolve_layout_model_candidate_keys() == (
        "docling_layout_egret_large",
        "docling_layout_heron",
    )


def test_layout_model_candidates_allow_explicit_override_with_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_egret_xlarge")
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS",
        "docling_layout_heron, docling_layout_egret_large, docling_layout_heron",
    )
    assert _resolve_layout_model_candidate_keys() == (
        "docling_layout_egret_xlarge",
        "docling_layout_heron",
        "docling_layout_egret_large",
    )


def test_layout_model_candidates_invalid_fallback_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_egret_large")
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS",
        "docling_layout_heron, unknown_layout",
    )
    with pytest.raises(BackendExecutionError):
        _resolve_layout_model_candidate_keys()


def _passing_ordering_report() -> OrderingQualityReport:
    return OrderingQualityReport(
        is_exam_like=True,
        option_line_count=8,
        question_count=4,
        min_question_number=1,
        max_question_number=4,
        missing_question_numbers=(),
        trailing_number_signals=0,
        standalone_number_signals=0,
        option_before_question_signals=0,
    )


def _failing_ordering_report(*, penalty_kind: str) -> OrderingQualityReport:
    if penalty_kind == "high":
        return OrderingQualityReport(
            is_exam_like=True,
            option_line_count=8,
            question_count=2,
            min_question_number=1,
            max_question_number=4,
            missing_question_numbers=(2, 3),
            trailing_number_signals=1,
            standalone_number_signals=1,
            option_before_question_signals=1,
        )
    if penalty_kind == "medium":
        return OrderingQualityReport(
            is_exam_like=True,
            option_line_count=8,
            question_count=3,
            min_question_number=1,
            max_question_number=4,
            missing_question_numbers=(2,),
            trailing_number_signals=0,
            standalone_number_signals=0,
            option_before_question_signals=1,
        )
    if penalty_kind == "low":
        return OrderingQualityReport(
            is_exam_like=True,
            option_line_count=8,
            question_count=4,
            min_question_number=1,
            max_question_number=4,
            missing_question_numbers=(),
            trailing_number_signals=0,
            standalone_number_signals=1,
            option_before_question_signals=0,
        )
    raise AssertionError(f"unknown penalty kind: {penalty_kind}")


def test_ordering_quality_gate_switches_to_passing_layout_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_egret_large")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS", "docling_layout_heron")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_ORDERING_QUALITY_GATE", "1")
    backend = DoclingConversionBackend()
    calls: list[tuple[str, bool]] = []

    def _fake_convert_once_with_layout(
        *,
        request: ConversionRequest,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
        layout_model_key: str,
        evaluate_ordering_quality: bool,
    ) -> _DoclingAttempt:
        del (
            request,
            ocr_enabled,
            force_full_page_ocr,
            acceleration_device,
            formula_enrichment,
            formula_preset,
        )
        calls.append((layout_model_key, evaluate_ordering_quality))
        if layout_model_key == "docling_layout_egret_large":
            report = _failing_ordering_report(penalty_kind="high")
        else:
            report = _passing_ordering_report()
        return _DoclingAttempt(
            markdown_content=f"content-{layout_model_key}",
            page_count=1,
            low_confidence=False,
            layout_model_key=layout_model_key,
            ordering_quality=report,
        )

    monkeypatch.setattr(backend, "_convert_once_with_layout", _fake_convert_once_with_layout)
    attempt = backend._convert_once(
        _request(ocr_mode=OcrMode.OFF),
        ocr_enabled=False,
        force_full_page_ocr=False,
        acceleration_device=AcceleratorDevice.CUDA,
        formula_enrichment=False,
        formula_preset="codeformulav2",
    )

    assert attempt.layout_model_key == "docling_layout_heron"
    assert attempt.ordering_retry_applied is True
    assert calls == [
        ("docling_layout_egret_large", True),
        ("docling_layout_heron", True),
    ]
    assert backend._ordering_warnings_for_attempt(attempt) == [
        "docling_ordering_layout_fallback_applied"
    ]


def test_ordering_quality_gate_uses_best_failed_candidate_when_all_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_egret_large")
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS",
        "docling_layout_heron,docling_layout_egret_medium",
    )
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_ORDERING_QUALITY_GATE", "1")
    backend = DoclingConversionBackend()
    calls: list[str] = []

    def _fake_convert_once_with_layout(
        *,
        request: ConversionRequest,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
        layout_model_key: str,
        evaluate_ordering_quality: bool,
    ) -> _DoclingAttempt:
        del (
            request,
            ocr_enabled,
            force_full_page_ocr,
            acceleration_device,
            formula_enrichment,
            formula_preset,
            evaluate_ordering_quality,
        )
        calls.append(layout_model_key)
        report_by_layout = {
            "docling_layout_egret_large": _failing_ordering_report(penalty_kind="high"),
            "docling_layout_heron": _failing_ordering_report(penalty_kind="medium"),
            "docling_layout_egret_medium": _failing_ordering_report(penalty_kind="low"),
        }
        return _DoclingAttempt(
            markdown_content=f"content-{layout_model_key}",
            page_count=1,
            low_confidence=False,
            layout_model_key=layout_model_key,
            ordering_quality=report_by_layout[layout_model_key],
        )

    monkeypatch.setattr(backend, "_convert_once_with_layout", _fake_convert_once_with_layout)
    attempt = backend._convert_once(
        _request(ocr_mode=OcrMode.OFF),
        ocr_enabled=False,
        force_full_page_ocr=False,
        acceleration_device=AcceleratorDevice.CUDA,
        formula_enrichment=False,
        formula_preset="codeformulav2",
    )

    assert calls == [
        "docling_layout_egret_large",
        "docling_layout_heron",
        "docling_layout_egret_medium",
    ]
    assert attempt.layout_model_key == "docling_layout_egret_medium"
    assert attempt.ordering_retry_applied is True
    assert backend._ordering_warnings_for_attempt(attempt) == [
        "docling_ordering_layout_fallback_applied",
        "docling_ordering_quality_gate_unresolved",
    ]


def test_ordering_quality_gate_disabled_skips_layout_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_egret_large")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS", "docling_layout_heron")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_ORDERING_QUALITY_GATE", "0")
    backend = DoclingConversionBackend()
    calls: list[tuple[str, bool]] = []

    def _fake_convert_once_with_layout(
        *,
        request: ConversionRequest,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
        layout_model_key: str,
        evaluate_ordering_quality: bool,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device, formula_enrichment
        del formula_preset
        calls.append((layout_model_key, evaluate_ordering_quality))
        return _DoclingAttempt(
            markdown_content=f"content-{layout_model_key}",
            page_count=1,
            low_confidence=False,
            layout_model_key=layout_model_key,
            ordering_quality=None,
        )

    monkeypatch.setattr(backend, "_convert_once_with_layout", _fake_convert_once_with_layout)
    attempt = backend._convert_once(
        _request(ocr_mode=OcrMode.OFF),
        ocr_enabled=False,
        force_full_page_ocr=False,
        acceleration_device=AcceleratorDevice.CUDA,
        formula_enrichment=False,
        formula_preset="codeformulav2",
    )

    assert calls == [("docling_layout_egret_large", False)]
    assert attempt.layout_model_key == "docling_layout_egret_large"
    assert attempt.ordering_retry_applied is False
