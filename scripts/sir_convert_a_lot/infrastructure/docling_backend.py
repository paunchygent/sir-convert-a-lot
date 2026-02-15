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
from dataclasses import dataclass
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
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import probe_torch_gpu_runtime

_AUTO_OCR_CHARS_PER_PAGE_THRESHOLD = 120.0
_LOW_CONFIDENCE_GRADES = {"poor", "fair"}
_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING = (
    r"This field is deprecated\. Use `generate_page_images=True` and call "
    r"`TableItem\.get_image\(\)` to extract table images from page images\."
)
_DOCLING_FORMULA_ENRICHMENT_FALLBACK_WARNING = "docling_formula_enrichment_unavailable_fallback"
_FORMULA_RUNTIME_UNAVAILABLE_HINTS: tuple[str, ...] = (
    "codeformula",
    "formula",
    "vlm",
    "transformers",
    "huggingface",
    "snapshot",
    "tokenizer",
    "checkpoint",
    "weights",
)

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


@dataclass(frozen=True)
class _ConverterKey:
    table_mode: TableMode
    ocr_enabled: bool
    force_full_page_ocr: bool
    acceleration_device: AcceleratorDevice
    formula_enrichment: bool


class DoclingConversionBackend(ConversionBackend):
    """Docling implementation of the conversion backend protocol."""

    def __init__(self) -> None:
        self._thread_local = threading.local()

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        if request.backend_strategy not in {BackendStrategy.AUTO, BackendStrategy.DOCLING}:
            raise ValueError(f"unsupported backend for docling adapter: {request.backend_strategy}")

        warnings: list[str] = []
        acceleration_device, acceleration_used = self._resolve_acceleration(request.gpu_available)

        if request.ocr_mode == OcrMode.OFF:
            attempt, attempt_warnings = self._convert_once_guarded_formula(
                request,
                ocr_enabled=False,
                force_full_page_ocr=False,
                acceleration_device=acceleration_device,
            )
            warnings.extend(attempt_warnings)
            ocr_enabled = False
        elif request.ocr_mode == OcrMode.FORCE:
            attempt, attempt_warnings = self._convert_once_guarded_formula(
                request,
                ocr_enabled=True,
                force_full_page_ocr=True,
                acceleration_device=acceleration_device,
            )
            warnings.extend(attempt_warnings)
            ocr_enabled = True
        else:
            first, first_warnings = self._convert_once_guarded_formula(
                request,
                ocr_enabled=False,
                force_full_page_ocr=False,
                acceleration_device=acceleration_device,
            )
            warnings.extend(first_warnings)
            stripped = first.markdown_content.strip()
            chars_per_page = len(stripped) / max(1, first.page_count)
            needs_ocr_retry = (
                len(stripped) == 0
                or chars_per_page < _AUTO_OCR_CHARS_PER_PAGE_THRESHOLD
                or first.low_confidence
            )
            if needs_ocr_retry:
                attempt, retry_warnings = self._convert_once_guarded_formula(
                    request,
                    ocr_enabled=True,
                    force_full_page_ocr=True,
                    acceleration_device=acceleration_device,
                )
                warnings.extend(retry_warnings)
                warnings.append("docling_auto_ocr_retry_applied")
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
        )

    def _convert_once_guarded_formula(
        self,
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device: AcceleratorDevice,
    ) -> tuple[_DoclingAttempt, list[str]]:
        formula_enrichment = request.table_mode == TableMode.ACCURATE
        if not formula_enrichment:
            return (
                self._convert_once(
                    request,
                    ocr_enabled=ocr_enabled,
                    force_full_page_ocr=force_full_page_ocr,
                    acceleration_device=acceleration_device,
                    formula_enrichment=False,
                ),
                [],
            )
        try:
            return (
                self._convert_once(
                    request,
                    ocr_enabled=ocr_enabled,
                    force_full_page_ocr=force_full_page_ocr,
                    acceleration_device=acceleration_device,
                    formula_enrichment=True,
                ),
                [],
            )
        except BackendExecutionError as exc:
            if not self._is_formula_runtime_unavailable(exc):
                raise
        return (
            self._convert_once(
                request,
                ocr_enabled=ocr_enabled,
                force_full_page_ocr=force_full_page_ocr,
                acceleration_device=acceleration_device,
                formula_enrichment=False,
            ),
            [_DOCLING_FORMULA_ENRICHMENT_FALLBACK_WARNING],
        )

    def _is_formula_runtime_unavailable(self, error: BackendExecutionError) -> bool:
        message = str(error).lower()
        return any(hint in message for hint in _FORMULA_RUNTIME_UNAVAILABLE_HINTS)

    def _convert_once(
        self,
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
        acceleration_device: AcceleratorDevice,
        formula_enrichment: bool,
    ) -> _DoclingAttempt:
        key = _ConverterKey(
            table_mode=request.table_mode,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            formula_enrichment=formula_enrichment,
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
        markdown_content = result.document.export_to_markdown()

        raw_pages = getattr(result, "pages", None)
        page_count = len(raw_pages) if raw_pages is not None else 1
        low_confidence = self._is_low_confidence(result)
        return _DoclingAttempt(
            markdown_content=markdown_content,
            page_count=max(1, page_count),
            low_confidence=low_confidence,
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

    def _resolve_acceleration(self, gpu_available: bool) -> tuple[AcceleratorDevice, str]:
        if not gpu_available:
            return AcceleratorDevice.CPU, "cpu"

        probe = probe_torch_gpu_runtime()
        if probe.is_available and probe.runtime_kind in {"rocm", "cuda"}:
            return AcceleratorDevice.CUDA, "cuda"
        raise BackendGpuUnavailableError(backend="docling", probe=probe)

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
        pipeline_options.do_ocr = key.ocr_enabled
        pipeline_options.do_table_structure = True
        pipeline_options.do_formula_enrichment = key.formula_enrichment
        if key.formula_enrichment:
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
