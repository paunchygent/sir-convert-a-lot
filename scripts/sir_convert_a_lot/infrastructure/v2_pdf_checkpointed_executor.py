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

import hashlib
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
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
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoint_metadata_v2 import (
    PdfCheckpointTerminalMetadataError,
    aggregate_pdf_checkpoint_terminal_metadata,
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
    phase_timings_ms: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PdfConversionCanceledV2(Exception):
    """Raised when a running PDF conversion observes cancellation."""

    job_id: str


@dataclass(frozen=True)
class PdfChunkConversionOutcomeV2:
    """One converted PDF chunk outcome produced before checkpoint commit."""

    chunk_index: int
    start_page: int
    end_page: int
    markdown_content: str
    backend_used: str | None
    acceleration_used: str | None
    ocr_enabled: bool
    ocr_engine_used: str | None
    ocr_languages_used: list[str]
    warnings: list[str]
    phase_timings_ms: dict[str, int]
    chunk_elapsed_ms: int


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


def _chunk_identity_key(
    *, chunk_index: int, start_page: int, end_page: int
) -> tuple[int, int, int]:
    return chunk_index, start_page, end_page


def _succeeded_chunk_keys(checkpoint: PdfCheckpointV2) -> set[tuple[int, int, int]]:
    keys: set[tuple[int, int, int]] = set()
    for chunk in checkpoint.chunks:
        if chunk.status != "succeeded":
            continue
        keys.add(
            _chunk_identity_key(
                chunk_index=chunk.chunk_index,
                start_page=chunk.start_page,
                end_page=chunk.end_page,
            )
        )
    return keys


def _resolve_checkpoint_processed_pages(checkpoint: PdfCheckpointV2) -> int:
    """Return processed pages from unique succeeded chunk identities."""
    processed_pages = 0
    for _chunk_index, start_page, end_page in _succeeded_chunk_keys(checkpoint):
        processed_pages += end_page - start_page + 1
    return processed_pages


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


def _convert_one_pdf_chunk(
    *,
    v1_spec: JobSpec,
    chunk_pdf_bytes: bytes,
    source_filename: str,
    config: ServiceConfig,
    probe: GpuRuntimeProbeResult | None,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    resolved_ocr: ResolvedPdfOcrRequestV2 | None,
) -> tuple[str, str | None, str | None, bool, str | None, list[str], list[str], dict[str, int]]:
    try:
        markdown_content, pdf_metadata, pdf_warnings, pdf_timings = execute_job_conversion(
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


def _upsert_checkpoint_chunk_record(
    *,
    checkpoint: PdfCheckpointV2,
    record: PdfChunkRecordV2,
) -> None:
    """Replace any existing chunk entry for the same identity and append latest record."""
    key = _chunk_identity_key(
        chunk_index=record.chunk_index,
        start_page=record.start_page,
        end_page=record.end_page,
    )
    filtered: list[PdfChunkRecordV2] = []
    for existing in checkpoint.chunks:
        existing_key = _chunk_identity_key(
            chunk_index=existing.chunk_index,
            start_page=existing.start_page,
            end_page=existing.end_page,
        )
        if existing_key == key:
            continue
        filtered.append(existing)
    filtered.append(record)
    checkpoint.chunks = filtered


class PdfCheckpointArtifactIntegrityError(Exception):
    """Raised when checkpoint chunk artifacts cannot safely assemble final markdown."""


def _expected_sha256(record: PdfChunkRecordV2) -> str:
    if not record.sha256.startswith("sha256:"):
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} has invalid sha256 metadata."
        )
    return record.sha256.removeprefix("sha256:")


def _read_verified_chunk_text(*, job_dir: Path, record: PdfChunkRecordV2) -> str:
    chunk_path = job_dir / record.artifact_relpath
    if not chunk_path.exists() or not chunk_path.is_file():
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact is missing."
        )
    payload = chunk_path.read_bytes()
    if len(payload) != record.size_bytes:
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact size does not match checkpoint metadata."
        )
    if hashlib.sha256(payload).hexdigest() != _expected_sha256(record):
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact checksum does not match checkpoint metadata."
        )
    try:
        return payload.decode("utf-8").rstrip("\n")
    except UnicodeDecodeError as exc:
        raise PdfCheckpointArtifactIntegrityError(
            f"Chunk {record.chunk_index} artifact is not valid UTF-8 markdown."
        ) from exc


def _ordered_complete_succeeded_chunks(checkpoint: PdfCheckpointV2) -> list[PdfChunkRecordV2]:
    if checkpoint.total_pages is None:
        raise PdfCheckpointArtifactIntegrityError("Checkpoint is missing total_pages.")
    succeeded = [chunk for chunk in checkpoint.chunks if chunk.status == "succeeded"]
    ordered = sorted(succeeded, key=lambda record: (record.start_page, record.end_page))
    if len(ordered) == 0:
        raise PdfCheckpointArtifactIntegrityError("Checkpoint has no succeeded chunks.")

    seen: set[tuple[int, int, int]] = set()
    expected_start_page = 1
    for record in ordered:
        key = _chunk_identity_key(
            chunk_index=record.chunk_index,
            start_page=record.start_page,
            end_page=record.end_page,
        )
        if key in seen:
            raise PdfCheckpointArtifactIntegrityError(
                f"Checkpoint has duplicate chunk identity for chunk {record.chunk_index}."
            )
        seen.add(key)
        if record.start_page != expected_start_page:
            raise PdfCheckpointArtifactIntegrityError(
                "Checkpoint succeeded chunks do not cover every page exactly once."
            )
        expected_start_page = record.end_page + 1
    if expected_start_page != checkpoint.total_pages + 1:
        raise PdfCheckpointArtifactIntegrityError(
            "Checkpoint succeeded chunks do not cover the full document."
        )
    return ordered


def _assemble_final_markdown_from_checkpoint(
    *, upload_path: Path, checkpoint: PdfCheckpointV2
) -> str:
    job_dir = upload_path.parent.parent
    ordered = _ordered_complete_succeeded_chunks(checkpoint)
    parts: list[str] = []
    for record in ordered:
        parts.append(_read_verified_chunk_text(job_dir=job_dir, record=record))
    return "\n\n".join(parts).rstrip("\n") + "\n"


def _merge_phase_timings(current: dict[str, int], additional: dict[str, int]) -> dict[str, int]:
    return merge_phase_timings_canonical_v2(current=current, additional=additional)


def _load_pdf_checkpoint_or_fail_closed(*, upload_path: Path) -> PdfCheckpointV2 | None:
    try:
        return load_pdf_checkpoint(upload_path=upload_path)
    except Exception as exc:
        raise ServiceError(
            status_code=500,
            code="checkpoint_invalid",
            message=("PDF checkpoint payload is incompatible with the required metadata schema."),
            retryable=False,
        ) from exc


def _required_checkpoint_metadata_value(*, label: str, value: str | None) -> str:
    if value is None or value.strip() == "":
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message=f"PDF chunk completed without {label} metadata to persist.",
            retryable=False,
        )
    return value


def _observed_ocr_engine_used_for_checkpoint_record(
    *,
    ocr_enabled: bool,
    ocr_engine_used: str | None,
) -> str | None:
    if not ocr_enabled:
        return None
    if ocr_engine_used is None or ocr_engine_used.strip() == "":
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message="OCR chunk completed without observed OCR engine metadata to persist.",
            retryable=False,
        )
    return ocr_engine_used


def _observed_ocr_languages_used_for_checkpoint_record(
    *,
    ocr_enabled: bool,
    ocr_languages_used: list[str],
) -> list[str]:
    if not ocr_enabled:
        return []
    if len(ocr_languages_used) == 0:
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message="OCR chunk completed without observed OCR language metadata to persist.",
            retryable=False,
        )
    return list(ocr_languages_used)


def execute_pdf_to_markdown_with_checkpoints_v2(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    chunk_size_pages: int,
    max_chunk_workers: int,
    parallel_enabled: bool,
    progress_callback: Callable[[PdfCheckpointProgressUpdateV2], None] | None,
    is_cancel_requested: Callable[[], bool] | None,
    on_chunk_worker_start: Callable[[], None] | None = None,
    on_chunk_worker_finish: Callable[[], None] | None = None,
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

    checkpoint = _load_pdf_checkpoint_or_fail_closed(upload_path=job.upload_path)
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
        return (
            markdown_content,
            pdf_metadata.backend_used,
            pdf_metadata.acceleration_used,
            ocr_enabled,
            pdf_metadata.ocr_engine_used if ocr_enabled else None,
            list(pdf_metadata.ocr_languages_used) if ocr_enabled else [],
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

    checkpoint.processed_pages = min(total_pages, _resolve_checkpoint_processed_pages(checkpoint))
    checkpoint.total_pages = total_pages
    processed_pages = checkpoint.processed_pages
    completed_chunk_keys = _succeeded_chunk_keys(checkpoint)

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
                    phase_timings_ms={},
                )
            )

    phase_timings_ms: dict[str, int] = {}
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

    resolved_max_chunk_workers = max(1, int(max_chunk_workers))
    if not parallel_enabled:
        resolved_max_chunk_workers = 1

    document = pymupdf.open(job.upload_path.as_posix())
    try:
        chunks = _iter_pdf_chunks(total_pages=total_pages, chunk_size_pages=chunk_size_pages)
        pending_chunks: list[tuple[int, int, int]] = []
        for chunk_index, (start_page, end_page) in enumerate(chunks):
            key = _chunk_identity_key(
                chunk_index=chunk_index,
                start_page=start_page,
                end_page=end_page,
            )
            if key in completed_chunk_keys:
                continue
            pending_chunks.append((chunk_index, start_page, end_page))

        def _convert_pending_chunk(
            *,
            chunk_index: int,
            start_page: int,
            end_page: int,
            chunk_pdf_bytes: bytes,
        ) -> PdfChunkConversionOutcomeV2:
            acquired_chunk_slot = False
            if on_chunk_worker_start is not None:
                on_chunk_worker_start()
                acquired_chunk_slot = True
            try:
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
                ) = _convert_one_pdf_chunk(
                    v1_spec=v1_spec,
                    chunk_pdf_bytes=chunk_pdf_bytes,
                    source_filename=job.source_filename,
                    config=config,
                    probe=probe,
                    docling_backend=docling_backend,
                    pymupdf_backend=pymupdf_backend,
                    resolved_ocr=resolved_ocr,
                )
                chunk_elapsed_ms = max(0, int((time.perf_counter() - chunk_started) * 1000))
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
                )
            finally:
                if acquired_chunk_slot and on_chunk_worker_finish is not None:
                    on_chunk_worker_finish()

        with ThreadPoolExecutor(max_workers=resolved_max_chunk_workers) as executor:
            futures_by_chunk_index: dict[int, Future[PdfChunkConversionOutcomeV2]] = {}
            pending_by_chunk_index = {
                chunk_index: (start_page, end_page)
                for chunk_index, start_page, end_page in pending_chunks
            }
            ordered_pending_chunk_indexes = [chunk_index for chunk_index, _, _ in pending_chunks]
            dispatch_cursor = 0
            commit_cursor = 0

            def _dispatch_until_capacity() -> None:
                nonlocal dispatch_cursor
                while len(
                    futures_by_chunk_index
                ) < resolved_max_chunk_workers and dispatch_cursor < len(
                    ordered_pending_chunk_indexes
                ):
                    if is_cancel_requested is not None and is_cancel_requested():
                        return
                    chunk_index = ordered_pending_chunk_indexes[dispatch_cursor]
                    dispatch_cursor += 1
                    start_page, end_page = pending_by_chunk_index[chunk_index]
                    chunk_pdf_bytes = _extract_pdf_page_range_bytes(
                        document=document,
                        start_page=start_page,
                        end_page=end_page,
                    )
                    if is_cancel_requested is not None and is_cancel_requested():
                        return
                    futures_by_chunk_index[chunk_index] = executor.submit(
                        _convert_pending_chunk,
                        chunk_index=chunk_index,
                        start_page=start_page,
                        end_page=end_page,
                        chunk_pdf_bytes=chunk_pdf_bytes,
                    )

            _dispatch_until_capacity()
            try:
                while commit_cursor < len(ordered_pending_chunk_indexes):
                    if is_cancel_requested is not None and is_cancel_requested():
                        raise PdfConversionCanceledV2(job_id=job.job_id)

                    expected_chunk_index = ordered_pending_chunk_indexes[commit_cursor]
                    future = futures_by_chunk_index.get(expected_chunk_index)
                    if future is None:
                        _dispatch_until_capacity()
                        continue

                    try:
                        outcome = future.result(timeout=0.05)
                    except TimeoutError:
                        continue

                    del futures_by_chunk_index[expected_chunk_index]
                    _dispatch_until_capacity()

                    chunk_key = _chunk_identity_key(
                        chunk_index=outcome.chunk_index,
                        start_page=outcome.start_page,
                        end_page=outcome.end_page,
                    )
                    if chunk_key in completed_chunk_keys:
                        commit_cursor += 1
                        continue

                    phase_timings_ms = _merge_phase_timings(
                        phase_timings_ms, outcome.phase_timings_ms
                    )
                    phase_timings_ms = _merge_phase_timings(
                        phase_timings_ms,
                        {TIMING_KEY_CHUNK_TOTAL_MS: outcome.chunk_elapsed_ms},
                    )

                    relpath, size_bytes, sha_hex = persist_pdf_chunk_markdown(
                        upload_path=job.upload_path,
                        chunk_index=outcome.chunk_index,
                        start_page=outcome.start_page,
                        end_page=outcome.end_page,
                        markdown_content=outcome.markdown_content,
                    )
                    chunk_phase_timings_ms = normalize_phase_timings_map(
                        {
                            **outcome.phase_timings_ms,
                            TIMING_KEY_CHUNK_TOTAL_MS: outcome.chunk_elapsed_ms,
                        }
                    )
                    chunk_record = PdfChunkRecordV2(
                        chunk_index=outcome.chunk_index,
                        start_page=outcome.start_page,
                        end_page=outcome.end_page,
                        status="succeeded",
                        started_at=dt_to_rfc3339(utc_now()),
                        completed_at=dt_to_rfc3339(utc_now()),
                        artifact_relpath=relpath,
                        sha256=f"sha256:{sha_hex}",
                        size_bytes=size_bytes,
                        backend_used=_required_checkpoint_metadata_value(
                            label="backend_used",
                            value=outcome.backend_used,
                        ),
                        acceleration_used=_required_checkpoint_metadata_value(
                            label="acceleration_used",
                            value=outcome.acceleration_used,
                        ),
                        ocr_enabled=outcome.ocr_enabled,
                        ocr_engine_used=_observed_ocr_engine_used_for_checkpoint_record(
                            ocr_enabled=outcome.ocr_enabled,
                            ocr_engine_used=outcome.ocr_engine_used,
                        ),
                        ocr_languages_used=_observed_ocr_languages_used_for_checkpoint_record(
                            ocr_enabled=outcome.ocr_enabled,
                            ocr_languages_used=outcome.ocr_languages_used,
                        ),
                        warnings=list(outcome.warnings),
                        phase_timings_ms=chunk_phase_timings_ms,
                    )
                    _upsert_checkpoint_chunk_record(
                        checkpoint=checkpoint,
                        record=chunk_record,
                    )
                    completed_chunk_keys.add(chunk_key)
                    checkpoint.processed_pages = min(
                        total_pages, _resolve_checkpoint_processed_pages(checkpoint)
                    )
                    checkpoint.total_pages = total_pages
                    checkpoint.updated_at = dt_to_rfc3339(utc_now()) or checkpoint.updated_at
                    checkpoint_persist_started = time.perf_counter()
                    persist_pdf_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)
                    assemble_partial_markdown_artifact(
                        upload_path=job.upload_path, checkpoint=checkpoint
                    )
                    checkpoint_persist_ms = max(
                        0, int((time.perf_counter() - checkpoint_persist_started) * 1000)
                    )
                    phase_timings_ms = _merge_phase_timings(
                        phase_timings_ms,
                        {TIMING_KEY_CHECKPOINT_PERSIST_MS: checkpoint_persist_ms},
                    )
                    chunk_record.phase_timings_ms = _merge_phase_timings(
                        chunk_record.phase_timings_ms,
                        {TIMING_KEY_CHECKPOINT_PERSIST_MS: checkpoint_persist_ms},
                    )
                    checkpoint.updated_at = dt_to_rfc3339(utc_now()) or checkpoint.updated_at
                    persist_pdf_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)
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
                                percent_complete=(checkpoint.processed_pages / float(total_pages))
                                * 100.0,
                                pages_per_minute=pages_per_minute,
                                eta_seconds=eta_seconds,
                                phase_timings_ms=dict(phase_timings_ms),
                            )
                        )
                    commit_cursor += 1
            except Exception:
                for future in futures_by_chunk_index.values():
                    future.cancel()
                raise
    finally:
        try:
            document.close()
        except Exception:
            pass

    try:
        final_markdown = _assemble_final_markdown_from_checkpoint(
            upload_path=job.upload_path,
            checkpoint=checkpoint,
        )
        terminal_metadata = aggregate_pdf_checkpoint_terminal_metadata(checkpoint)
    except PdfCheckpointArtifactIntegrityError as exc:
        raise ServiceError(
            status_code=500,
            code="checkpoint_artifact_invalid",
            message=f"PDF checkpoint artifact integrity check failed: {exc}",
            retryable=False,
        ) from exc
    except PdfCheckpointTerminalMetadataError as exc:
        raise ServiceError(
            status_code=500,
            code="checkpoint_metadata_missing",
            message=f"PDF checkpoint cannot explain terminal conversion metadata: {exc}",
            retryable=False,
        ) from exc
    return (
        final_markdown,
        terminal_metadata.backend_used,
        terminal_metadata.acceleration_used,
        terminal_metadata.ocr_enabled,
        terminal_metadata.ocr_engine_used,
        terminal_metadata.ocr_languages_used,
        terminal_metadata.warnings,
        terminal_metadata.phase_timings_ms,
    )
