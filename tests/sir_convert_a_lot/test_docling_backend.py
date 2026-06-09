"""Tests for Docling backend mapping and OCR auto-retry behavior.

Purpose:
    Validate Task 10 backend semantics: backend mapping, OCR policy mapping,
    deterministic auto-retry behavior, and metadata truth.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.docling_backend`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from docling.datamodel.accelerator_options import AcceleratorDevice
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions

import scripts.sir_convert_a_lot.infrastructure.docling_backend as docling_backend_module
from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OcrEngineV2
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
    ConversionRequest,
    ConversionResultData,
)
from scripts.sir_convert_a_lot.infrastructure.docling_backend import (
    DoclingConversionBackend,
    _ConverterKey,
    _DoclingAttempt,
    _resolve_layout_model_config,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_authority import (
    FORMULA_SOURCE_BACKED_VLM_REJECTED_WARNING,
    SourceFormulaEvidenceState,
    SourceLayerFormulaEvidence,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_FORMULA_ENRICHMENT_MS,
)
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


def _source_layer_evidence(state: SourceFormulaEvidenceState) -> SourceLayerFormulaEvidence:
    if state is SourceFormulaEvidenceState.USABLE:
        return SourceLayerFormulaEvidence(
            state=state,
            method="test",
            page_count=1,
            word_count=12,
            raw_character_count=42,
            text_character_count=42,
            pages_with_words=1,
            pages_with_raw_characters=1,
            reason="test_usable_source_layer",
        )
    return SourceLayerFormulaEvidence(
        state=state,
        method="test",
        page_count=1,
        word_count=0,
        raw_character_count=0,
        text_character_count=0,
        pages_with_words=0,
        pages_with_raw_characters=0,
        reason="test_no_authoritative_source_layer",
    )


def test_layout_model_default_is_heavier_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", raising=False)
    selected = _resolve_layout_model_config()
    assert selected.name == "docling_layout_egret_large"


def test_layout_model_env_override_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "docling_layout_heron")
    selected = _resolve_layout_model_config()
    assert selected.name == "docling_layout_heron"


def test_layout_model_env_invalid_value_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL", "not_a_real_layout_model")
    with pytest.raises(BackendExecutionError):
        _resolve_layout_model_config()


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


@pytest.fixture(autouse=True)
def _default_source_layer_evidence_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.docling_formula_authority."
        "collect_source_layer_formula_evidence",
        lambda source_bytes: _source_layer_evidence(SourceFormulaEvidenceState.ABSENT),
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
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment, formula_preset
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
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment, formula_preset
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
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment, formula_preset
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


def test_easyocr_options_use_pipeline_accelerator_device() -> None:
    backend = DoclingConversionBackend(easyocr_model_storage_directory="/opt/easyocr-models")
    converter = backend._get_converter(
        _ConverterKey(
            table_mode=TableMode.FAST,
            ocr_enabled=True,
            force_full_page_ocr=True,
            ocr_engine=OcrEngineV2.EASYOCR,
            ocr_languages=("sv", "en"),
            ocr_use_gpu=True,
            acceleration_device=AcceleratorDevice.CUDA,
            layout_model_key="docling_layout_heron",
            formula_enrichment=False,
            formula_preset="codeformulav2",
            document_timeout_seconds=97,
        )
    )

    format_option = converter.format_to_options[InputFormat.PDF]
    pipeline_options = format_option.pipeline_options

    assert isinstance(pipeline_options, PdfPipelineOptions)
    assert isinstance(pipeline_options.ocr_options, EasyOcrOptions)
    assert pipeline_options.accelerator_options.device == AcceleratorDevice.CUDA
    assert pipeline_options.document_timeout == 97
    assert pipeline_options.ocr_options.use_gpu is None
    assert pipeline_options.ocr_options.model_storage_directory == "/opt/easyocr-models"


def test_docling_backend_exposes_formula_vlm_timing_from_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = DoclingConversionBackend()
    token = object()

    def _fake_convert_with_active_formula_diagnostics(
        request: ConversionRequest,
    ) -> ConversionResultData:
        del request
        return ConversionResultData(
            markdown_content="Formula content",
            backend_used="docling",
            acceleration_used="cuda",
            ocr_enabled=False,
        )

    monkeypatch.setattr(
        docling_backend_module,
        "begin_docling_formula_diagnostics",
        lambda: token,
    )
    monkeypatch.setattr(
        docling_backend_module,
        "end_docling_formula_diagnostics",
        lambda received_token: {
            "formula_vlm_batch_count": 1,
            "formula_vlm_total_ms": 42,
            "token_seen": received_token is token,
        },
    )
    monkeypatch.setattr(
        backend,
        "_convert_with_active_formula_diagnostics",
        _fake_convert_with_active_formula_diagnostics,
    )

    result = backend.convert(_request(ocr_mode=OcrMode.OFF))

    assert result.phase_timings_ms[TIMING_KEY_FORMULA_ENRICHMENT_MS] == 42
    assert backend.last_formula_diagnostics()["token_seen"] is True


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
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, acceleration_device, formula_enrichment, formula_preset
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
        formula_preset: str,
    ) -> _DoclingAttempt:
        del (
            request,
            ocr_enabled,
            force_full_page_ocr,
            acceleration_device,
            formula_enrichment,
            formula_preset,
        )
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
    formula_flags: list[tuple[bool, str]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        formula_flags.append((formula_enrichment, formula_preset))
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
    assert formula_flags == [(True, "codeformulav2")]
    assert "docling_formula_enrichment_unavailable_fallback" not in result.warnings
    assert "ocr_layout_extract_ms" in result.phase_timings_ms
    assert "formula_enrichment_ms" not in result.phase_timings_ms


def test_formula_enrichment_falls_back_when_runtime_unavailable(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    formula_flags: list[tuple[bool, str]] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        formula_flags.append((formula_enrichment, formula_preset))
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
    assert formula_flags == [
        (True, "codeformulav2"),
        (True, "granite_docling"),
        (False, "codeformulav2"),
    ]
    assert result.warnings == ["docling_formula_enrichment_unavailable_fallback"]


def test_formula_enrichment_switches_to_granite_when_primary_has_placeholders(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[str] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        calls.append(formula_preset)
        if formula_enrichment and formula_preset == "codeformulav2":
            return _DoclingAttempt(
                markdown_content="before\n<!-- formula-not-decoded -->\nafter\n",
                page_count=1,
                low_confidence=False,
            )
        if formula_enrichment and formula_preset == "granite_docling":
            return _DoclingAttempt(
                markdown_content="formula resolved output",
                page_count=1,
                low_confidence=False,
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

    assert calls == ["codeformulav2", "granite_docling"]
    assert result.markdown_content == "formula resolved output"
    assert result.warnings == ["docling_formula_preset_switched_to_granite_docling"]


def test_formula_enrichment_switches_to_granite_on_structural_quality(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[str] = []
    runaway_padding = " \\" * 180

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        calls.append(formula_preset)
        if formula_enrichment and formula_preset == "codeformulav2":
            return _DoclingAttempt(
                markdown_content=(
                    "$$\\rho = \\frac { a } { b }" + runaway_padding + " $$\n/negationslash\n"
                ),
                page_count=1,
                low_confidence=False,
            )
        if formula_enrichment and formula_preset == "granite_docling":
            return _DoclingAttempt(
                markdown_content="$$\\rho = \\frac { a } { b }$$\n",
                page_count=1,
                low_confidence=False,
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

    assert calls == ["codeformulav2", "granite_docling"]
    assert result.markdown_content == "$$\\rho = \\frac { a } { b }$$\n"
    assert result.warnings == [
        "docling_formula_preset_switched_to_granite_docling",
        "docling_formula_quality_switch_applied",
    ]


def test_formula_enrichment_switches_to_granite_on_leaked_formula_tags(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[str] = []

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        calls.append(formula_preset)
        if formula_enrichment and formula_preset == "codeformulav2":
            return _DoclingAttempt(
                markdown_content="$$<formula><loc_34>\\alpha</formula$$\n",
                page_count=1,
                low_confidence=False,
            )
        if formula_enrichment and formula_preset == "granite_docling":
            return _DoclingAttempt(
                markdown_content="$$\\alpha$$\n",
                page_count=1,
                low_confidence=False,
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

    assert calls == ["codeformulav2", "granite_docling"]
    assert result.markdown_content == "$$\\alpha$$\n"
    assert result.warnings == [
        "docling_formula_preset_switched_to_granite_docling",
        "docling_formula_quality_switch_applied",
    ]


def test_formula_enrichment_switches_to_granite_on_real_hard_case_excerpt(monkeypatch) -> None:
    backend = DoclingConversionBackend()
    calls: list[str] = []
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "markdown_hardcases"
        / "alt_annotator_problem_excerpt.md"
    )
    primary_markdown = fixture_path.read_text()

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        calls.append(formula_preset)
        if formula_enrichment and formula_preset == "codeformulav2":
            return _DoclingAttempt(
                markdown_content=primary_markdown,
                page_count=1,
                low_confidence=False,
            )
        if formula_enrichment and formula_preset == "granite_docling":
            return _DoclingAttempt(
                markdown_content="$$\\rho = \\frac { a } { b }$$\n",
                page_count=1,
                low_confidence=False,
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

    assert calls == ["codeformulav2", "granite_docling"]
    assert result.markdown_content == "$$\\rho = \\frac { a } { b }$$\n"
    assert result.warnings == [
        "docling_formula_preset_switched_to_granite_docling",
        "docling_formula_quality_switch_applied",
    ]


def test_source_backed_formula_defect_rejects_generated_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = DoclingConversionBackend()
    calls: list[tuple[bool, str]] = []

    def _fake_collect_source_evidence(source_bytes: bytes) -> SourceLayerFormulaEvidence:
        assert source_bytes == fixture_pdf_bytes("paper_alpha.pdf")
        return _source_layer_evidence(SourceFormulaEvidenceState.USABLE)

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        calls.append((formula_enrichment, formula_preset))
        if formula_enrichment and formula_preset == "codeformulav2":
            return _DoclingAttempt(
                markdown_content="$$<formula><loc_34>\\alpha</formula$$\n",
                page_count=1,
                low_confidence=False,
            )
        if formula_enrichment and formula_preset == "granite_docling":
            return _DoclingAttempt(
                markdown_content="$$\\alpha$$\n",
                page_count=1,
                low_confidence=False,
            )
        return _DoclingAttempt(
            markdown_content="docling-output-without-generated-formula",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.docling_formula_authority."
        "collect_source_layer_formula_evidence",
        _fake_collect_source_evidence,
    )
    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)

    result = backend.convert(
        _request(
            ocr_mode=OcrMode.OFF,
            gpu_available=True,
            table_mode=TableMode.ACCURATE,
        )
    )

    assert calls == [
        (True, "codeformulav2"),
        (True, "granite_docling"),
        (False, "codeformulav2"),
    ]
    assert result.markdown_content == "docling-output-without-generated-formula"
    assert result.warnings == [
        FORMULA_SOURCE_BACKED_VLM_REJECTED_WARNING,
        "docling_formula_preset_switched_to_granite_docling",
        "docling_formula_quality_switch_applied",
    ]


def test_absent_source_evidence_keeps_granite_formula_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = DoclingConversionBackend()

    def _fake_collect_source_evidence(source_bytes: bytes) -> SourceLayerFormulaEvidence:
        assert source_bytes == fixture_pdf_bytes("paper_alpha.pdf")
        return _source_layer_evidence(SourceFormulaEvidenceState.ABSENT)

    def _fake_convert_once(
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        del request, ocr_enabled, force_full_page_ocr, acceleration_device
        if formula_enrichment and formula_preset == "codeformulav2":
            return _DoclingAttempt(
                markdown_content="$$<formula><loc_34>\\alpha</formula$$\n",
                page_count=1,
                low_confidence=False,
            )
        if formula_enrichment and formula_preset == "granite_docling":
            return _DoclingAttempt(
                markdown_content="$$\\alpha$$\n",
                page_count=1,
                low_confidence=False,
            )
        return _DoclingAttempt(
            markdown_content="docling-output-without-generated-formula",
            page_count=1,
            low_confidence=False,
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.docling_formula_authority."
        "collect_source_layer_formula_evidence",
        _fake_collect_source_evidence,
    )
    monkeypatch.setattr(backend, "_convert_once", _fake_convert_once)

    result = backend.convert(
        _request(
            ocr_mode=OcrMode.OFF,
            gpu_available=True,
            table_mode=TableMode.ACCURATE,
        )
    )

    assert result.markdown_content == "$$\\alpha$$\n"
    assert result.warnings == [
        "docling_formula_preset_switched_to_granite_docling",
        "docling_formula_quality_switch_applied",
    ]


def test_export_markdown_prefers_escape_html_false() -> None:
    backend = DoclingConversionBackend()

    class _Document:
        def __init__(self) -> None:
            self.kwargs_history: list[dict[str, bool]] = []

        def export_to_markdown(self, **kwargs: bool) -> str:
            self.kwargs_history.append(kwargs)
            return "markdown"

    document = _Document()

    markdown = backend._export_markdown(document)

    assert markdown == "markdown"
    assert document.kwargs_history == [{"escape_html": False, "compact_tables": True}]


def test_export_markdown_falls_back_when_escape_html_unsupported() -> None:
    backend = DoclingConversionBackend()

    class _Document:
        def __init__(self) -> None:
            self.calls = 0

        def export_to_markdown(self, **kwargs: bool) -> str:
            self.calls += 1
            if kwargs:
                raise TypeError("escape_html unsupported")
            return "fallback-markdown"

    document = _Document()

    markdown = backend._export_markdown(document)

    assert markdown == "fallback-markdown"
    assert document.calls == 2


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
