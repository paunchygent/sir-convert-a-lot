"""Docling conversion backend for Sir Convert-a-Lot.

Purpose:
    Execute PDF-to-markdown conversion using Docling while mapping v1
    backend/table/OCR semantics to Docling pipeline options.

Relationships:
    - Implements `infrastructure.conversion_backend.ConversionBackend`.
    - Called by `infrastructure.runtime_engine.ServiceRuntime`.
"""

from __future__ import annotations

import threading
import warnings
from dataclasses import dataclass, replace
from io import BytesIO

from docling.datamodel.accelerator_options import AcceleratorDevice
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.exceptions import ConversionError as DoclingConversionError
from docling_core.types.io import DocumentStream

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
    ConversionBackend,
    ConversionRequest,
    ConversionResultData,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_fallback import (
    convert_once_guarded_formula,
)
from scripts.sir_convert_a_lot.infrastructure.docling_layout_models import (
    DEFAULT_LAYOUT_MODEL_KEY as _DEFAULT_LAYOUT_MODEL_KEY,
)
from scripts.sir_convert_a_lot.infrastructure.docling_layout_models import (
    DOCLING_ORDERING_PATCH_ENV_VAR as _DOCLING_ORDERING_PATCH_ENV_VAR,
)
from scripts.sir_convert_a_lot.infrastructure.docling_layout_models import (
    DOCLING_ORDERING_QUALITY_GATE_ENV_VAR as _DOCLING_ORDERING_QUALITY_GATE_ENV_VAR,
)
from scripts.sir_convert_a_lot.infrastructure.docling_layout_models import (
    is_env_flag_enabled as _is_env_flag_enabled,
)
from scripts.sir_convert_a_lot.infrastructure.docling_layout_models import (
    resolve_layout_model_candidate_keys as _resolve_layout_model_candidate_keys,
)
from scripts.sir_convert_a_lot.infrastructure.docling_layout_models import (
    resolve_layout_model_config as _resolve_layout_model_config,
)
from scripts.sir_convert_a_lot.infrastructure.docling_ordering import (
    OrderingQualityReport,
    evaluate_docling_ordering_quality,
    install_docling_form_ordering_patch,
)
from scripts.sir_convert_a_lot.infrastructure.docling_ordering_fallback import (
    ordering_warnings_for_attempt,
    select_best_ordering_attempt,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import (
    GpuRuntimeProbeResult,
    probe_torch_gpu_runtime,
)

_AUTO_OCR_CHARS_PER_PAGE_THRESHOLD = 120.0
_LOW_CONFIDENCE_GRADES = {"poor", "fair"}
_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING = (
    r"This field is deprecated\. Use `generate_page_images=True` and call "
    r"`TableItem\.get_image\(\)` to extract table images from page images\."
)
_DOCLING_FORMULA_ENRICHMENT_FALLBACK_WARNING = "docling_formula_enrichment_unavailable_fallback"
_DOCLING_FORMULA_PRESET_SWITCH_WARNING = "docling_formula_preset_switched_to_granite_docling"
_DOCLING_FORMULA_QUALITY_SWITCH_WARNING = "docling_formula_quality_switch_applied"

warnings.filterwarnings(
    "ignore",
    message=_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING,
    category=DeprecationWarning,
)


@dataclass(frozen=True)
class _DoclingAttempt:
    markdown_content: str
    page_count: int
    low_confidence: bool
    layout_model_key: str = _DEFAULT_LAYOUT_MODEL_KEY
    ordering_quality: OrderingQualityReport | None = None
    ordering_retry_applied: bool = False


@dataclass(frozen=True)
class _ConverterKey:
    table_mode: TableMode
    ocr_enabled: bool
    force_full_page_ocr: bool
    acceleration_device: AcceleratorDevice
    layout_model_key: str
    formula_enrichment: bool
    formula_preset: str


class DoclingConversionBackend(ConversionBackend):
    """Docling implementation of the conversion backend protocol."""

    def __init__(self) -> None:
        self._thread_local = threading.local()
        self._ordering_patch_enabled = _is_env_flag_enabled(
            env_var=_DOCLING_ORDERING_PATCH_ENV_VAR,
            default=True,
        )
        self._ordering_quality_gate_enabled = _is_env_flag_enabled(
            env_var=_DOCLING_ORDERING_QUALITY_GATE_ENV_VAR,
            default=True,
        )
        if self._ordering_patch_enabled:
            install_docling_form_ordering_patch()

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        if request.backend_strategy not in {BackendStrategy.AUTO, BackendStrategy.DOCLING}:
            raise ValueError(f"unsupported backend for docling adapter: {request.backend_strategy}")

        warnings: list[str] = []
        phase_timings_ms: dict[str, int] = {}
        acceleration_device, acceleration_used = self._resolve_acceleration(
            request.gpu_available,
            request.gpu_runtime_probe,
        )

        if request.ocr_mode == OcrMode.OFF:
            attempt, attempt_warnings, attempt_timings = self._convert_once_guarded_formula(
                request,
                ocr_enabled=False,
                force_full_page_ocr=False,
                acceleration_device=acceleration_device,
            )
            warnings.extend(attempt_warnings)
            phase_timings_ms.update(attempt_timings)
            ocr_enabled = False
        elif request.ocr_mode == OcrMode.FORCE:
            attempt, attempt_warnings, attempt_timings = self._convert_once_guarded_formula(
                request,
                ocr_enabled=True,
                force_full_page_ocr=True,
                acceleration_device=acceleration_device,
            )
            warnings.extend(attempt_warnings)
            phase_timings_ms.update(attempt_timings)
            ocr_enabled = True
        else:
            first, first_warnings, first_timings = self._convert_once_guarded_formula(
                request,
                ocr_enabled=False,
                force_full_page_ocr=False,
                acceleration_device=acceleration_device,
            )
            warnings.extend(first_warnings)
            phase_timings_ms = self._merge_phase_timings(phase_timings_ms, first_timings)
            stripped = first.markdown_content.strip()
            chars_per_page = len(stripped) / max(1, first.page_count)
            needs_ocr_retry = (
                len(stripped) == 0
                or chars_per_page < _AUTO_OCR_CHARS_PER_PAGE_THRESHOLD
                or first.low_confidence
            )
            if needs_ocr_retry:
                attempt, retry_warnings, retry_timings = self._convert_once_guarded_formula(
                    request,
                    ocr_enabled=True,
                    force_full_page_ocr=True,
                    acceleration_device=acceleration_device,
                )
                warnings.extend(retry_warnings)
                warnings.append("docling_auto_ocr_retry_applied")
                phase_timings_ms = self._merge_phase_timings(phase_timings_ms, retry_timings)
                ocr_enabled = True
            else:
                attempt = first
                ocr_enabled = False

        return ConversionResultData(
            markdown_content=attempt.markdown_content,
            backend_used="docling",
            acceleration_used=acceleration_used,
            ocr_enabled=ocr_enabled,
            warnings=warnings,
            phase_timings_ms=phase_timings_ms,
        )

    def _convert_once_guarded_formula(
        self,
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device: AcceleratorDevice,
    ) -> tuple[_DoclingAttempt, list[str], dict[str, int]]:
        return convert_once_guarded_formula(
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            convert_once=self._convert_once,
            ordering_warnings_resolver=self._ordering_warnings_for_attempt,
            formula_enrichment_fallback_warning=_DOCLING_FORMULA_ENRICHMENT_FALLBACK_WARNING,
            formula_preset_switch_warning=_DOCLING_FORMULA_PRESET_SWITCH_WARNING,
            formula_quality_switch_warning=_DOCLING_FORMULA_QUALITY_SWITCH_WARNING,
        )

    def _convert_once(
        self,
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device: AcceleratorDevice,
        formula_enrichment: bool,
        formula_preset: str,
    ) -> _DoclingAttempt:
        candidate_layout_keys = _resolve_layout_model_candidate_keys()
        primary_layout_key = candidate_layout_keys[0]
        primary_attempt = self._convert_once_with_layout(
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            formula_enrichment=formula_enrichment,
            formula_preset=formula_preset,
            layout_model_key=primary_layout_key,
            evaluate_ordering_quality=self._ordering_quality_gate_enabled,
        )
        if not self._ordering_quality_gate_enabled or len(candidate_layout_keys) == 1:
            return primary_attempt

        primary_quality = primary_attempt.ordering_quality
        if primary_quality is not None and primary_quality.passes:
            return primary_attempt

        attempts: list[_DoclingAttempt] = [primary_attempt]
        for fallback_layout_key in candidate_layout_keys[1:]:
            fallback_attempt = self._convert_once_with_layout(
                request=request,
                ocr_enabled=ocr_enabled,
                force_full_page_ocr=force_full_page_ocr,
                acceleration_device=acceleration_device,
                formula_enrichment=formula_enrichment,
                formula_preset=formula_preset,
                layout_model_key=fallback_layout_key,
                evaluate_ordering_quality=True,
            )
            attempts.append(fallback_attempt)
            fallback_quality = fallback_attempt.ordering_quality
            if fallback_quality is not None and fallback_quality.passes:
                return replace(fallback_attempt, ordering_retry_applied=True)

        selected_attempt = select_best_ordering_attempt(attempts)
        if selected_attempt.layout_model_key != primary_layout_key:
            return replace(selected_attempt, ordering_retry_applied=True)
        return selected_attempt

    def _convert_once_with_layout(
        self,
        *,
        request: ConversionRequest,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device: AcceleratorDevice,
        formula_enrichment: bool,
        formula_preset: str,
        layout_model_key: str,
        evaluate_ordering_quality: bool,
    ) -> _DoclingAttempt:
        key = _ConverterKey(
            table_mode=request.table_mode,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            layout_model_key=layout_model_key,
            formula_enrichment=formula_enrichment,
            formula_preset=formula_preset,
        )
        converter = self._get_converter(key)
        document_stream = DocumentStream(
            name=request.source_filename,
            stream=BytesIO(request.source_bytes),
        )
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING,
                    category=DeprecationWarning,
                )
                result = converter.convert(document_stream)
        except DoclingConversionError as exc:
            raise BackendInputError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guard for backend runtime issues.
            raise BackendExecutionError(f"Docling backend execution failed: {exc}") from exc
        markdown_content = self._export_markdown(result.document)

        raw_pages = getattr(result, "pages", None)
        page_count = len(raw_pages) if raw_pages is not None else 1
        low_confidence = self._is_low_confidence(result)
        ordering_quality: OrderingQualityReport | None = None
        if evaluate_ordering_quality:
            ordering_quality = evaluate_docling_ordering_quality(markdown_content)
        return _DoclingAttempt(
            markdown_content=markdown_content,
            page_count=max(1, page_count),
            low_confidence=low_confidence,
            layout_model_key=layout_model_key,
            ordering_quality=ordering_quality,
        )

    def _is_low_confidence(self, result: object) -> bool:
        confidence = getattr(result, "confidence", None)
        if confidence is None:
            return False
        low_grade = getattr(confidence, "low_grade", None)
        if low_grade is None:
            return False
        if hasattr(low_grade, "value"):
            grade_value = str(low_grade.value).lower()
        else:
            grade_value = str(low_grade).lower()
        return grade_value in _LOW_CONFIDENCE_GRADES

    def _resolve_acceleration(
        self,
        gpu_available: bool,
        runtime_probe: GpuRuntimeProbeResult | None,
    ) -> tuple[AcceleratorDevice, str]:
        del gpu_available
        probe = runtime_probe if runtime_probe is not None else probe_torch_gpu_runtime()
        if probe.is_available and probe.runtime_kind in {"rocm", "cuda"}:
            return AcceleratorDevice.CUDA, "cuda"
        raise BackendGpuUnavailableError(backend="docling", probe=probe)

    def _merge_phase_timings(
        self,
        current: dict[str, int],
        next_timings: dict[str, int],
    ) -> dict[str, int]:
        merged = dict(current)
        for key, value in next_timings.items():
            merged[key] = merged.get(key, 0) + value
        return merged

    def _ordering_warnings_for_attempt(self, attempt: _DoclingAttempt) -> list[str]:
        del self
        return ordering_warnings_for_attempt(attempt)

    def _get_converter(self, key: _ConverterKey) -> DocumentConverter:
        cache = self._converter_cache()
        converter = cache.get(key)
        if converter is None:
            converter = self._build_converter(key)
            cache[key] = converter
        return converter

    def _converter_cache(self) -> dict[_ConverterKey, DocumentConverter]:
        cache = getattr(self._thread_local, "converter_cache", None)
        if cache is None:
            cache = {}
            self._thread_local.converter_cache = cache
        return cache

    def _build_converter(self, key: _ConverterKey) -> DocumentConverter:
        pipeline_options = PdfPipelineOptions()
        layout_options = pipeline_options.layout_options
        if hasattr(layout_options, "model_spec"):
            setattr(
                layout_options,
                "model_spec",
                _resolve_layout_model_config(layout_model_key=key.layout_model_key),
            )
        pipeline_options.do_ocr = key.ocr_enabled
        pipeline_options.do_table_structure = True
        pipeline_options.do_formula_enrichment = key.formula_enrichment
        if key.formula_enrichment:
            pipeline_options.code_formula_options = (
                pipeline_options.code_formula_options.from_preset(key.formula_preset)
            )
            pipeline_options.code_formula_options.extract_formulas = True
            pipeline_options.code_formula_options.extract_code = False
        pipeline_options.table_structure_options = TableStructureOptions(
            mode=TableFormerMode(key.table_mode.value),
            do_cell_matching=key.table_mode == TableMode.ACCURATE,
        )
        pipeline_options.accelerator_options.device = key.acceleration_device
        if hasattr(pipeline_options.ocr_options, "force_full_page_ocr"):
            pipeline_options.ocr_options.force_full_page_ocr = key.force_full_page_ocr
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING,
                category=DeprecationWarning,
            )
            return DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
                }
            )

    def _export_markdown(self, document: object) -> str:
        """Export markdown with deterministic escaping policy.

        Prefers `escape_html=False` when supported by the installed Docling
        version to reduce escaped symbol artifacts in scientific text.
        """
        export_to_markdown = getattr(document, "export_to_markdown")
        try:
            exported = export_to_markdown(escape_html=False, compact_tables=True)
        except TypeError:
            exported = export_to_markdown()
        if not isinstance(exported, str):
            raise BackendExecutionError("Docling backend returned non-string markdown content.")
        return exported
