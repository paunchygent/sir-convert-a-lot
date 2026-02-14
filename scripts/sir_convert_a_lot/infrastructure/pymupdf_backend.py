"""PyMuPDF4LLM conversion backend for Sir Convert-a-Lot.

Purpose:
    Execute deterministic CPU-based PDF-to-markdown conversion using PyMuPDF4LLM
    while honoring canonical v1 conversion request semantics.

Relationships:
    - Implements `infrastructure.conversion_backend.ConversionBackend`.
    - Routed by `infrastructure.runtime_engine.ServiceRuntime` for explicit
      `backend_strategy="pymupdf"` requests.
"""

from __future__ import annotations

import contextlib
import io

import pymupdf

with contextlib.redirect_stdout(io.StringIO()):
    import pymupdf4llm

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendInputError,
    ConversionBackend,
    ConversionRequest,
    ConversionResultData,
)

_TABLE_STRATEGY_BY_MODE: dict[TableMode, str] = {
    TableMode.FAST: "lines",
    TableMode.ACCURATE: "lines_strict",
}


class PyMuPdfConversionBackend(ConversionBackend):
    """PyMuPDF4LLM implementation of the conversion backend protocol."""

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        if request.backend_strategy != BackendStrategy.PYMUPDF:
            raise ValueError(f"unsupported backend for pymupdf adapter: {request.backend_strategy}")
        if request.ocr_mode != OcrMode.OFF:
            raise ValueError(f"unsupported ocr_mode for pymupdf adapter: {request.ocr_mode}")

        table_strategy = _TABLE_STRATEGY_BY_MODE[request.table_mode]

        try:
            document = self._open_document(request.source_bytes)
        except (pymupdf.EmptyFileError, pymupdf.FileDataError, pymupdf.FileNotFoundError) as exc:
            raise BackendInputError(str(exc)) from exc
        except ValueError as exc:
            raise BackendInputError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive backend open guard.
            raise BackendExecutionError(f"PyMuPDF backend document-open failed: {exc}") from exc

        try:
            with document:
                markdown_content = self._to_markdown(document, table_strategy)
        except Exception as exc:  # pragma: no cover - defensive backend runtime guard.
            raise BackendExecutionError(f"PyMuPDF backend execution failed: {exc}") from exc

        if not isinstance(markdown_content, str):
            raise BackendExecutionError("PyMuPDF backend returned non-string markdown content.")

        return ConversionResultData(
            markdown_content=markdown_content,
            backend_used="pymupdf",
            acceleration_used="cpu",
            ocr_enabled=False,
            warnings=[],
        )

    def _open_document(self, source_bytes: bytes) -> pymupdf.Document:
        return pymupdf.open(stream=source_bytes, filetype="pdf")

    def _to_markdown(self, document: pymupdf.Document, table_strategy: str) -> str:
        return str(
            pymupdf4llm.to_markdown(
                document,
                page_chunks=False,
                table_strategy=table_strategy,
            )
        )
