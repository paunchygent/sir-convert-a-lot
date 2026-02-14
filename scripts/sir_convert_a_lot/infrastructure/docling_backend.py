"""Docling conversion backend for Sir Convert-a-Lot.

Purpose:
    Execute PDF-to-markdown conversion using Docling while mapping v1
    backend/table/OCR semantics to Docling pipeline options.

Relationships:
    - Implements `infrastructure.conversion_backend.ConversionBackend`.
    - Called by `infrastructure.runtime_engine.ServiceRuntime`.
"""

from __future__ import annotations

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
from docling_core.types.io import DocumentStream

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    ConversionBackend,
    ConversionRequest,
    ConversionResultData,
)

_AUTO_OCR_CHARS_PER_PAGE_THRESHOLD = 120.0
_LOW_CONFIDENCE_GRADES = {"poor", "fair"}
_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING = (
    r"This field is deprecated\. Use `generate_page_images=True` and call "
    r"`TableItem\.get_image\(\)` to extract table images from page images\."
)


@dataclass(frozen=True)
class _DoclingAttempt:
    markdown_content: str
    page_count: int
    low_confidence: bool


class DoclingConversionBackend(ConversionBackend):
    """Docling implementation of the conversion backend protocol."""

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        if request.backend_strategy not in {BackendStrategy.AUTO, BackendStrategy.DOCLING}:
            raise ValueError(f"unsupported backend for docling adapter: {request.backend_strategy}")

        warnings: list[str] = []
        if request.ocr_mode == OcrMode.OFF:
            attempt = self._convert_once(request, ocr_enabled=False, force_full_page_ocr=False)
            ocr_enabled = False
        elif request.ocr_mode == OcrMode.FORCE:
            attempt = self._convert_once(request, ocr_enabled=True, force_full_page_ocr=True)
            ocr_enabled = True
        else:
            first = self._convert_once(request, ocr_enabled=False, force_full_page_ocr=False)
            stripped = first.markdown_content.strip()
            chars_per_page = len(stripped) / max(1, first.page_count)
            needs_ocr_retry = (
                len(stripped) == 0
                or chars_per_page < _AUTO_OCR_CHARS_PER_PAGE_THRESHOLD
                or first.low_confidence
            )
            if needs_ocr_retry:
                attempt = self._convert_once(request, ocr_enabled=True, force_full_page_ocr=True)
                warnings.append("docling_auto_ocr_retry_applied")
                ocr_enabled = True
            else:
                attempt = first
                ocr_enabled = False

        return ConversionResultData(
            markdown_content=attempt.markdown_content,
            backend_used="docling",
            acceleration_used="cuda" if request.gpu_available else "cpu",
            ocr_enabled=ocr_enabled,
            warnings=warnings,
        )

    def _convert_once(
        self,
        request: ConversionRequest,
        *,
        ocr_enabled: bool,
        force_full_page_ocr: bool,
    ) -> _DoclingAttempt:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = ocr_enabled
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options = TableStructureOptions(
            mode=TableFormerMode(request.table_mode.value),
            do_cell_matching=request.table_mode == TableMode.ACCURATE,
        )
        pipeline_options.accelerator_options.device = (
            AcceleratorDevice.CUDA if request.gpu_available else AcceleratorDevice.CPU
        )

        if hasattr(pipeline_options.ocr_options, "force_full_page_ocr"):
            pipeline_options.ocr_options.force_full_page_ocr = force_full_page_ocr

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
        document_stream = DocumentStream(
            name=request.source_filename,
            stream=BytesIO(request.source_bytes),
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=_DOCLING_DEPRECATED_TABLE_IMAGES_WARNING,
                category=DeprecationWarning,
                module=r"docling\.pipeline\.standard_pdf_pipeline",
            )
            result = converter.convert(document_stream)
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
