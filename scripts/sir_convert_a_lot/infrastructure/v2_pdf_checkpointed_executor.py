"""Checkpointed PDF execution helpers for service API v2.

Purpose:
    Execute long-running PDF conversions in deterministic chunks while
    persisting:
      - a durable checkpoint (`/v2/convert/jobs/{job_id}/checkpoint`), and
      - a partial markdown artifact (`/v2/convert/jobs/{job_id}/artifact/partial`)
    that can be retrieved before terminal completion.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for PDF routes.
    - Writes checkpoint/partial artifacts via `infrastructure.pdf_checkpoints_v2`.
    - Uses the canonical PDF backend surface via `infrastructure.runtime_conversion`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    ConversionSpec,
    ExecutionSpec,
    JobSpec,
    RetentionSpec,
    SourceKind,
    SourceSpec,
)
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    validate_acceleration_policy as validate_acceleration_policy_rule,
)
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    validate_backend_strategy as validate_backend_strategy_rule,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
    ConversionBackend,
)
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import (
    GpuRuntimeProbeResult,
    probe_torch_gpu_runtime,
)
from scripts.sir_convert_a_lot.infrastructure.ocr_resolution_v2 import (
    ResolvedPdfOcrRequestV2,
    resolve_pdf_ocr_request,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
    PdfChunkRecordV2,
    assemble_partial_markdown_artifact,
    build_initial_pdf_checkpoint,
    load_pdf_checkpoint,
    persist_pdf_checkpoint,
    persist_pdf_chunk_markdown,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_metadata_v2 import best_effort_pdf_total_pages
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CHECKPOINT_PERSIST_MS,
    TIMING_KEY_CHUNK_TOTAL_MS,
    normalize_phase_timings_map,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    merge_phase_timings as merge_phase_timings_canonical_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_conversion import execute_job_conversion
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class PdfCheckpointProgressUpdateV2:
    """Progress snapshot emitted after a PDF chunk is checkpointed."""

    total_pages: int
    processed_pages: int
    failed_pages: int
    percent_complete: float
    pages_per_minute: float | None
    eta_seconds: int | None


@dataclass(frozen=True)
class PdfConversionCanceledV2(Exception):
    """Raised when a running PDF conversion observes cancellation."""

    job_id: str


def validate_backend_strategy_v1(spec: JobSpec) -> None:
    violation = validate_backend_strategy_rule(spec)
    if violation is None:
        return
    raise ServiceError(
        status_code=violation.status_code,
        code=violation.code,
        message=violation.message,
        retryable=violation.retryable,
        details=violation.details,
    )


def validate_acceleration_policy_v1(
    *, spec: JobSpec, config: ServiceConfig
) -> GpuRuntimeProbeResult | None:
    violation = validate_acceleration_policy_rule(
        spec,
        gpu_available=config.gpu_available,
        allow_cpu_only=config.allow_cpu_only,
        allow_cpu_fallback=config.allow_cpu_fallback,
    )
    if violation is not None:
        raise ServiceError(
            status_code=violation.status_code,
            code=violation.code,
            message=violation.message,
            retryable=violation.retryable,
            details=violation.details,
        )

    probe: GpuRuntimeProbeResult | None = None
    if (
        config.gpu_available
        and spec.execution.acceleration_policy
        in {AccelerationPolicy.GPU_REQUIRED, AccelerationPolicy.GPU_PREFER}
        and spec.conversion.backend_strategy in {BackendStrategy.AUTO, BackendStrategy.DOCLING}
    ):
        probe = probe_torch_gpu_runtime()
        if not (probe.is_available and probe.runtime_kind in {"rocm", "cuda"}):
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
                    "runtime_kind": probe.runtime_kind,
                    "hip_version": probe.hip_version,
                    "cuda_version": probe.cuda_version,
                },
            )
    return probe


def _resolve_contiguous_checkpoint_progress(checkpoint: PdfCheckpointV2) -> tuple[int, int]:
    succeeded = [chunk for chunk in checkpoint.chunks if chunk.status == "succeeded"]
    ordered = sorted(succeeded, key=lambda record: (record.start_page, record.end_page))
    completed_end = 0
    processed_pages = 0
    for record in ordered:
        if record.start_page != completed_end + 1:
            break
        processed_pages += record.end_page - record.start_page + 1
        completed_end = record.end_page
    return completed_end, processed_pages


def _iter_pdf_chunks(*, total_pages: int, chunk_size_pages: int) -> list[tuple[int, int]]:
    if total_pages <= 0:
        return []
    resolved_chunk_size = max(1, int(chunk_size_pages))
    chunks: list[tuple[int, int]] = []
    start = 1
    while start <= total_pages:
        end = min(total_pages, start + resolved_chunk_size - 1)
        chunks.append((start, end))
        start = end + 1
    return chunks


def _extract_pdf_page_range_bytes(*, document: object, start_page: int, end_page: int) -> bytes:
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


def _assemble_final_markdown_from_checkpoint(
    *, upload_path: Path, checkpoint: PdfCheckpointV2
) -> str:
    job_dir = upload_path.parent.parent
    succeeded = [chunk for chunk in checkpoint.chunks if chunk.status == "succeeded"]
    ordered = sorted(succeeded, key=lambda record: (record.start_page, record.end_page))
    parts: list[str] = []
    for record in ordered:
        chunk_path = job_dir / record.artifact_relpath
        if not chunk_path.exists():
            continue
        parts.append(chunk_path.read_text(encoding="utf-8").rstrip("\n"))
    if len(parts) == 0:
        return ""
    return "\n\n".join(parts).rstrip("\n") + "\n"


def _append_unique_warnings(target: list[str], additional: list[str]) -> None:
    seen = set(target)
    for warning in additional:
        if warning in seen:
            continue
        target.append(warning)
        seen.add(warning)


def _merge_phase_timings(current: dict[str, int], additional: dict[str, int]) -> dict[str, int]:
    return merge_phase_timings_canonical_v2(current=current, additional=additional)


def execute_pdf_to_markdown_with_checkpoints_v2(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    chunk_size_pages: int,
    progress_callback: Callable[[PdfCheckpointProgressUpdateV2], None] | None,
    is_cancel_requested: Callable[[], bool] | None,
) -> tuple[str, str | None, str | None, bool, str | None, list[str], list[str], dict[str, int]]:
    """Return markdown content + metadata while persisting checkpoints/partials."""
    if job.spec.pdf_options is None or job.spec.execution is None:
        raise ServiceError(
            status_code=500,
            code="invalid_job_spec",
            message="v2 job spec is missing required pdf_options/execution for pdf routes.",
            retryable=False,
        )

    resolved_ocr: ResolvedPdfOcrRequestV2 | None = resolve_pdf_ocr_request(
        spec=job.spec,
        config=config,
    )
    resolved_ocr_engine = resolved_ocr.engine if resolved_ocr is not None else None
    resolved_ocr_languages = resolved_ocr.languages if resolved_ocr is not None else ()
    resolved_ocr_use_gpu = resolved_ocr.use_gpu if resolved_ocr is not None else None

    v1_spec = JobSpec(
        api_version="v1",
        source=SourceSpec(kind=SourceKind.UPLOAD, filename=job.source_filename),
        conversion=ConversionSpec(
            output_format="md",
            backend_strategy=job.spec.pdf_options.backend_strategy,
            ocr_mode=job.spec.pdf_options.ocr_mode,
            table_mode=job.spec.pdf_options.table_mode,
            normalize=job.spec.pdf_options.normalize,
        ),
        execution=ExecutionSpec(
            acceleration_policy=job.spec.execution.acceleration_policy,
            priority=job.spec.execution.priority,
            document_timeout_seconds=job.spec.execution.document_timeout_seconds,
        ),
        retention=RetentionSpec(pin=job.spec.retention.pin),
    )
    validate_backend_strategy_v1(v1_spec)
    probe = validate_acceleration_policy_v1(spec=v1_spec, config=config)

    source_bytes = job.upload_path.read_bytes()
    if not source_bytes.startswith(b"%PDF"):
        raise ServiceError(
            status_code=422,
            code="pdf_unreadable",
            message="Uploaded file is not a readable PDF.",
            retryable=False,
        )

    checkpoint = load_pdf_checkpoint(upload_path=job.upload_path)
    total_pages_obj = checkpoint.total_pages if checkpoint is not None else None
    if total_pages_obj is None:
        total_pages_obj = best_effort_pdf_total_pages(job.upload_path)

    if total_pages_obj is None:
        try:
            markdown_content, pdf_metadata, pdf_warnings, pdf_timings = execute_job_conversion(
                spec=v1_spec,
                source_filename=job.source_filename,
                source_bytes=source_bytes,
                gpu_available=config.gpu_available,
                gpu_runtime_probe=probe,
                docling_backend=docling_backend,
                pymupdf_backend=pymupdf_backend,
                ocr_engine=resolved_ocr_engine,
                ocr_languages=resolved_ocr_languages,
                ocr_use_gpu=resolved_ocr_use_gpu,
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
        ocr_enabled = bool(pdf_metadata.ocr_enabled)
        ocr_engine_used = resolved_ocr_engine.value if ocr_enabled and resolved_ocr_engine else None
        ocr_languages_used = list(resolved_ocr_languages) if ocr_enabled else []
        return (
            markdown_content,
            pdf_metadata.backend_used,
            pdf_metadata.acceleration_used,
            ocr_enabled,
            ocr_engine_used,
            ocr_languages_used,
            list(pdf_warnings),
            normalize_phase_timings_map(dict(pdf_timings)),
        )

    total_pages = int(total_pages_obj)
    if checkpoint is None:
        checkpoint = build_initial_pdf_checkpoint(
            job_id=job.job_id,
            chunk_size_pages=chunk_size_pages,
            total_pages=total_pages,
        )
        persist_pdf_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)

    completed_end, processed_pages = _resolve_contiguous_checkpoint_progress(checkpoint)
    checkpoint.processed_pages = processed_pages
    next_start_page = completed_end + 1

    if processed_pages > 0:
        assemble_partial_markdown_artifact(upload_path=job.upload_path, checkpoint=checkpoint)
        if progress_callback is not None:
            progress_callback(
                PdfCheckpointProgressUpdateV2(
                    total_pages=total_pages,
                    processed_pages=processed_pages,
                    failed_pages=checkpoint.failed_pages,
                    percent_complete=(processed_pages / float(total_pages)) * 100.0,
                    pages_per_minute=None,
                    eta_seconds=None,
                )
            )

    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}
    backend_used: str | None = None
    acceleration_used: str | None = None
    ocr_enabled_any = False
    conversion_started = time.perf_counter()

    try:
        import pymupdf
    except Exception as exc:  # pragma: no cover
        raise ServiceError(
            status_code=503,
            code="pdf_backend_not_available",
            message="PyMuPDF is unavailable in this runtime environment.",
            retryable=True,
        ) from exc

    document = pymupdf.open(job.upload_path.as_posix())
    try:
        chunks = _iter_pdf_chunks(total_pages=total_pages, chunk_size_pages=chunk_size_pages)
        for chunk_index, (start_page, end_page) in enumerate(chunks):
            if is_cancel_requested is not None and is_cancel_requested():
                raise PdfConversionCanceledV2(job_id=job.job_id)
            if end_page < next_start_page:
                continue

            chunk_started = time.perf_counter()
            chunk_pdf_bytes = _extract_pdf_page_range_bytes(
                document=document,
                start_page=start_page,
                end_page=end_page,
            )
            if is_cancel_requested is not None and is_cancel_requested():
                raise PdfConversionCanceledV2(job_id=job.job_id)
            try:
                markdown_content, pdf_metadata, pdf_warnings, pdf_timings = execute_job_conversion(
                    spec=v1_spec,
                    source_filename=job.source_filename,
                    source_bytes=chunk_pdf_bytes,
                    gpu_available=config.gpu_available,
                    gpu_runtime_probe=probe,
                    docling_backend=docling_backend,
                    pymupdf_backend=pymupdf_backend,
                    ocr_engine=resolved_ocr_engine,
                    ocr_languages=resolved_ocr_languages,
                    ocr_use_gpu=resolved_ocr_use_gpu,
                )
            except BackendGpuUnavailableError as exc:
                raise ServiceError(
                    status_code=503,
                    code="gpu_not_available",
                    message=(
                        "GPU runtime is unavailable for the selected backend under GPU-required "
                        "policy."
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

            if backend_used is None:
                backend_used = pdf_metadata.backend_used
            if acceleration_used is None:
                acceleration_used = pdf_metadata.acceleration_used
            ocr_enabled_any = ocr_enabled_any or bool(pdf_metadata.ocr_enabled)
            _append_unique_warnings(warnings, list(pdf_warnings))
            phase_timings_ms = _merge_phase_timings(phase_timings_ms, dict(pdf_timings))

            relpath, size_bytes, sha_hex = persist_pdf_chunk_markdown(
                upload_path=job.upload_path,
                chunk_index=chunk_index,
                start_page=start_page,
                end_page=end_page,
                markdown_content=markdown_content,
            )
            chunk_elapsed_ms = max(0, int((time.perf_counter() - chunk_started) * 1000))
            checkpoint.chunks.append(
                PdfChunkRecordV2(
                    chunk_index=chunk_index,
                    start_page=start_page,
                    end_page=end_page,
                    status="succeeded",
                    started_at=dt_to_rfc3339(utc_now()),
                    completed_at=dt_to_rfc3339(utc_now()),
                    artifact_relpath=relpath,
                    sha256=f"sha256:{sha_hex}",
                    size_bytes=size_bytes,
                    phase_timings_ms=normalize_phase_timings_map(
                        {
                            **dict(pdf_timings),
                            TIMING_KEY_CHUNK_TOTAL_MS: chunk_elapsed_ms,
                        }
                    ),
                )
            )
            checkpoint.processed_pages = min(
                total_pages,
                checkpoint.processed_pages + (end_page - start_page + 1),
            )
            checkpoint.total_pages = total_pages
            checkpoint.updated_at = dt_to_rfc3339(utc_now()) or checkpoint.updated_at
            checkpoint_persist_started = time.perf_counter()
            persist_pdf_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)
            assemble_partial_markdown_artifact(upload_path=job.upload_path, checkpoint=checkpoint)
            checkpoint_persist_ms = max(
                0, int((time.perf_counter() - checkpoint_persist_started) * 1000)
            )
            phase_timings_ms = _merge_phase_timings(
                phase_timings_ms,
                {TIMING_KEY_CHECKPOINT_PERSIST_MS: checkpoint_persist_ms},
            )
            if is_cancel_requested is not None and is_cancel_requested():
                raise PdfConversionCanceledV2(job_id=job.job_id)

            if progress_callback is not None:
                elapsed = max(0.001, time.perf_counter() - conversion_started)
                minutes = elapsed / 60.0
                pages_per_minute = float(checkpoint.processed_pages) / minutes
                remaining = max(0, total_pages - checkpoint.processed_pages)
                eta_seconds = int((remaining / max(1e-6, pages_per_minute)) * 60.0)
                progress_callback(
                    PdfCheckpointProgressUpdateV2(
                        total_pages=total_pages,
                        processed_pages=checkpoint.processed_pages,
                        failed_pages=checkpoint.failed_pages,
                        percent_complete=(checkpoint.processed_pages / float(total_pages)) * 100.0,
                        pages_per_minute=pages_per_minute,
                        eta_seconds=eta_seconds,
                    )
                )
    finally:
        try:
            document.close()
        except Exception:
            pass

    final_markdown = _assemble_final_markdown_from_checkpoint(
        upload_path=job.upload_path,
        checkpoint=checkpoint,
    )
    ocr_engine_used = resolved_ocr_engine.value if ocr_enabled_any and resolved_ocr_engine else None
    ocr_languages_used = list(resolved_ocr_languages) if ocr_enabled_any else []
    return (
        final_markdown,
        backend_used,
        acceleration_used,
        ocr_enabled_any,
        ocr_engine_used,
        ocr_languages_used,
        warnings,
        phase_timings_ms,
    )
