"""PDF chunk extraction and conversion helpers for service API v2.

Purpose:
    Convert one planned PDF page window through the canonical backend surface
    while keeping ordered scheduling and checkpoint commit logic in the chunk
    runner.

Relationships:
    - Used by `infrastructure.v2_pdf_checkpoint_chunk_runner`.
    - Uses `infrastructure.runtime_conversion.execute_job_conversion` through
      an injected callable so tests can patch the executor boundary.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import JobSpec
from scripts.sir_convert_a_lot.domain.specs_v2 import OcrEngineV2
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
    ConversionBackend,
)
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.ocr_resolution_v2 import ResolvedPdfOcrRequestV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfChunkConversionOutcomeV2,
)


class PdfChunkConversionFunctionV2(Protocol):
    """Callable that converts one PDF chunk through the canonical backend surface."""

    def __call__(
        self,
        *,
        spec: JobSpec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe: GpuRuntimeProbeResult | None,
        docling_backend: ConversionBackend,
        pymupdf_backend: ConversionBackend,
        ocr_engine: OcrEngineV2 | None = None,
        ocr_languages: tuple[str, ...] = (),
        ocr_use_gpu: bool | None = None,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        """Convert one chunk and return markdown plus metadata."""


def extract_pdf_page_range_bytes_v2(*, document: object, start_page: int, end_page: int) -> bytes:
    """Return a standalone PDF byte window for one page range."""
    try:
        import pymupdf
    except Exception as exc:  # pragma: no cover
        raise ServiceError(
            status_code=503,
            code="pdf_backend_not_available",
            message="PyMuPDF is unavailable in this runtime environment.",
            retryable=True,
        ) from exc

    if not isinstance(document, pymupdf.Document):
        raise TypeError("document must be a pymupdf.Document")
    if start_page < 1 or end_page < start_page:
        raise ValueError("invalid page range")

    window = pymupdf.open()
    try:
        window.insert_pdf(document, from_page=start_page - 1, to_page=end_page - 1)
        return bytes(window.tobytes())
    finally:
        try:
            window.close()
        except Exception:
            pass


def convert_pending_pdf_chunk_v2(
    *,
    chunk_index: int,
    start_page: int,
    end_page: int,
    chunk_pdf_bytes: bytes,
    job: StoredJobV2,
    config: ServiceConfig,
    v1_spec: JobSpec,
    probe: GpuRuntimeProbeResult | None,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    resolved_ocr: ResolvedPdfOcrRequestV2 | None,
    execute_chunk_conversion: PdfChunkConversionFunctionV2,
    on_chunk_worker_start: Callable[[], None] | None,
    on_chunk_worker_finish: Callable[[], None] | None,
) -> PdfChunkConversionOutcomeV2:
    """Convert one pending chunk and return pre-commit metadata."""
    acquired_chunk_slot = False
    if on_chunk_worker_start is not None:
        on_chunk_worker_start()
        acquired_chunk_slot = True
    try:
        chunk_started_at = dt_to_rfc3339(utc_now())
        chunk_started = time.perf_counter()
        (
            markdown_content,
            chunk_backend_used,
            chunk_acceleration_used,
            chunk_ocr_enabled,
            chunk_ocr_engine_used,
            chunk_ocr_languages_used,
            chunk_warnings,
            chunk_phase_timings,
        ) = _convert_one_pdf_chunk_v2(
            v1_spec=v1_spec,
            chunk_pdf_bytes=chunk_pdf_bytes,
            source_filename=job.source_filename,
            config=config,
            probe=probe,
            docling_backend=docling_backend,
            pymupdf_backend=pymupdf_backend,
            resolved_ocr=resolved_ocr,
            execute_chunk_conversion=execute_chunk_conversion,
        )
        chunk_elapsed_ms = max(0, int((time.perf_counter() - chunk_started) * 1000))
        chunk_completed_at = dt_to_rfc3339(utc_now())
        return PdfChunkConversionOutcomeV2(
            chunk_index=chunk_index,
            start_page=start_page,
            end_page=end_page,
            markdown_content=markdown_content,
            backend_used=chunk_backend_used,
            acceleration_used=chunk_acceleration_used,
            ocr_enabled=chunk_ocr_enabled,
            ocr_engine_used=chunk_ocr_engine_used,
            ocr_languages_used=chunk_ocr_languages_used,
            warnings=chunk_warnings,
            phase_timings_ms=chunk_phase_timings,
            chunk_elapsed_ms=chunk_elapsed_ms,
            started_at=chunk_started_at,
            completed_at=chunk_completed_at,
        )
    finally:
        if acquired_chunk_slot and on_chunk_worker_finish is not None:
            on_chunk_worker_finish()


def _convert_one_pdf_chunk_v2(
    *,
    v1_spec: JobSpec,
    chunk_pdf_bytes: bytes,
    source_filename: str,
    config: ServiceConfig,
    probe: GpuRuntimeProbeResult | None,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    resolved_ocr: ResolvedPdfOcrRequestV2 | None,
    execute_chunk_conversion: PdfChunkConversionFunctionV2,
) -> tuple[str, str | None, str | None, bool, str | None, list[str], list[str], dict[str, int]]:
    try:
        markdown_content, pdf_metadata, pdf_warnings, pdf_timings = execute_chunk_conversion(
            spec=v1_spec,
            source_filename=source_filename,
            source_bytes=chunk_pdf_bytes,
            gpu_available=config.gpu_available,
            gpu_runtime_probe=probe,
            docling_backend=docling_backend,
            pymupdf_backend=pymupdf_backend,
            ocr_engine=resolved_ocr.engine if resolved_ocr is not None else None,
            ocr_languages=resolved_ocr.languages if resolved_ocr is not None else (),
            ocr_use_gpu=resolved_ocr.use_gpu if resolved_ocr is not None else None,
        )
    except BackendGpuUnavailableError as exc:
        raise ServiceError(
            status_code=503,
            code="gpu_not_available",
            message=(
                "GPU runtime is unavailable for the selected backend under GPU-required policy."
            ),
            retryable=True,
            details={
                "reason": "backend_gpu_runtime_unavailable",
                "backend": "docling",
                "runtime_kind": exc.probe.runtime_kind,
                "hip_version": exc.probe.hip_version,
                "cuda_version": exc.probe.cuda_version,
            },
        ) from exc
    except BackendInputError as exc:
        raise ServiceError(
            status_code=422,
            code="pdf_unreadable",
            message=f"Uploaded PDF could not be converted: {exc}",
            retryable=False,
        ) from exc
    except BackendExecutionError as exc:
        raise ServiceError(
            status_code=500,
            code="conversion_internal_error",
            message=f"Unexpected backend conversion failure: {exc}",
            retryable=True,
        ) from exc
    return (
        markdown_content,
        pdf_metadata.backend_used,
        pdf_metadata.acceleration_used,
        bool(pdf_metadata.ocr_enabled),
        pdf_metadata.ocr_engine_used,
        list(pdf_metadata.ocr_languages_used),
        list(pdf_warnings),
        dict(pdf_timings),
    )
