"""Ordered PDF chunk conversion runner for service API v2 checkpoints.

Purpose:
    Execute pending PDF page-window chunks with bounded parallelism, commit
    completed chunks in deterministic page order, persist checkpoint/partial
    artifacts, and emit progress updates.

Relationships:
    - Called by `infrastructure.v2_pdf_checkpointed_executor`.
    - Uses chunk planning from `infrastructure.v2_pdf_checkpoint_planning`.
    - Mutates checkpoint state through `infrastructure.v2_pdf_checkpoint_state`
      and `infrastructure.pdf_checkpoints_v2`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError

from scripts.sir_convert_a_lot.domain.specs import JobSpec
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import ConversionBackend
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.ocr_resolution_v2 import ResolvedPdfOcrRequestV2
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    PdfCheckpointV2,
    PdfChunkRecordV2,
    assemble_partial_markdown_artifact,
    persist_pdf_checkpoint,
    persist_pdf_chunk_markdown,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_CHECKPOINT_PERSIST_MS,
    TIMING_KEY_CHUNK_TOTAL_MS,
    normalize_phase_timings_map,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    merge_phase_timings as merge_phase_timings_canonical_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfCheckpointPersistFunctionV2,
    PdfCheckpointProgressUpdateV2,
    PdfChunkConversionOutcomeV2,
    PdfConversionCanceledV2,
    PdfPartialArtifactAssemblerFunctionV2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_planning import (
    chunk_identity_key_v2,
    pending_pdf_chunks_v2,
    resolve_checkpoint_processed_pages_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_state import (
    observed_ocr_engine_used_for_checkpoint_record_v2,
    observed_ocr_languages_used_for_checkpoint_record_v2,
    required_checkpoint_metadata_value_v2,
    upsert_checkpoint_chunk_record_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_chunk_conversion import (
    PdfChunkConversionFunctionV2,
    convert_pending_pdf_chunk_v2,
    extract_pdf_page_range_bytes_v2,
)


def run_pdf_checkpoint_chunk_conversion_plan_v2(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    checkpoint: PdfCheckpointV2,
    v1_spec: JobSpec,
    probe: GpuRuntimeProbeResult | None,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    resolved_ocr: ResolvedPdfOcrRequestV2 | None,
    total_pages: int,
    chunk_size_pages: int,
    completed_chunk_keys: set[tuple[int, int, int]],
    max_chunk_workers: int,
    parallel_enabled: bool,
    progress_callback: Callable[[PdfCheckpointProgressUpdateV2], None] | None,
    is_cancel_requested: Callable[[], bool] | None,
    execute_chunk_conversion: PdfChunkConversionFunctionV2,
    persist_checkpoint: PdfCheckpointPersistFunctionV2 = persist_pdf_checkpoint,
    assemble_partial_artifact: PdfPartialArtifactAssemblerFunctionV2 = (
        assemble_partial_markdown_artifact
    ),
    on_chunk_worker_start: Callable[[], None] | None = None,
    on_chunk_worker_finish: Callable[[], None] | None = None,
) -> dict[str, int]:
    """Convert pending chunks, persist checkpoint state, and return phase timings."""
    resolved_max_chunk_workers = max(1, int(max_chunk_workers))
    if not parallel_enabled:
        resolved_max_chunk_workers = 1

    try:
        import pymupdf
    except Exception as exc:  # pragma: no cover
        raise ServiceError(
            status_code=503,
            code="pdf_backend_not_available",
            message="PyMuPDF is unavailable in this runtime environment.",
            retryable=True,
        ) from exc

    conversion_started = time.perf_counter()
    phase_timings_ms: dict[str, int] = {}
    document = pymupdf.open(job.upload_path.as_posix())
    try:
        pending_chunks = pending_pdf_chunks_v2(
            total_pages=total_pages,
            chunk_size_pages=chunk_size_pages,
            completed_chunk_keys=completed_chunk_keys,
        )
        with ThreadPoolExecutor(max_workers=resolved_max_chunk_workers) as executor:
            futures_by_chunk_index: dict[int, Future[PdfChunkConversionOutcomeV2]] = {}
            pending_by_chunk_index = {
                chunk.chunk_index: (chunk.start_page, chunk.end_page) for chunk in pending_chunks
            }
            ordered_pending_chunk_indexes = [chunk.chunk_index for chunk in pending_chunks]
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
                    chunk_pdf_bytes = extract_pdf_page_range_bytes_v2(
                        document=document,
                        start_page=start_page,
                        end_page=end_page,
                    )
                    if is_cancel_requested is not None and is_cancel_requested():
                        return
                    futures_by_chunk_index[chunk_index] = executor.submit(
                        convert_pending_pdf_chunk_v2,
                        chunk_index=chunk_index,
                        start_page=start_page,
                        end_page=end_page,
                        chunk_pdf_bytes=chunk_pdf_bytes,
                        job=job,
                        config=config,
                        v1_spec=v1_spec,
                        probe=probe,
                        docling_backend=docling_backend,
                        pymupdf_backend=pymupdf_backend,
                        resolved_ocr=resolved_ocr,
                        on_chunk_worker_start=on_chunk_worker_start,
                        on_chunk_worker_finish=on_chunk_worker_finish,
                        execute_chunk_conversion=execute_chunk_conversion,
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
                    phase_timings_ms = _commit_chunk_outcome_v2(
                        job=job,
                        checkpoint=checkpoint,
                        outcome=outcome,
                        completed_chunk_keys=completed_chunk_keys,
                        total_pages=total_pages,
                        current_phase_timings=phase_timings_ms,
                        conversion_started=conversion_started,
                        progress_callback=progress_callback,
                        is_cancel_requested=is_cancel_requested,
                        persist_checkpoint=persist_checkpoint,
                        assemble_partial_artifact=assemble_partial_artifact,
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
    return phase_timings_ms


def _commit_chunk_outcome_v2(
    *,
    job: StoredJobV2,
    checkpoint: PdfCheckpointV2,
    outcome: PdfChunkConversionOutcomeV2,
    completed_chunk_keys: set[tuple[int, int, int]],
    total_pages: int,
    current_phase_timings: dict[str, int],
    conversion_started: float,
    progress_callback: Callable[[PdfCheckpointProgressUpdateV2], None] | None,
    is_cancel_requested: Callable[[], bool] | None,
    persist_checkpoint: PdfCheckpointPersistFunctionV2,
    assemble_partial_artifact: PdfPartialArtifactAssemblerFunctionV2,
) -> dict[str, int]:
    chunk_key = chunk_identity_key_v2(
        chunk_index=outcome.chunk_index,
        start_page=outcome.start_page,
        end_page=outcome.end_page,
    )
    if chunk_key in completed_chunk_keys:
        return current_phase_timings

    phase_timings_ms = _merge_phase_timings(current_phase_timings, outcome.phase_timings_ms)
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
    chunk_record = _build_chunk_record_v2(
        outcome=outcome,
        artifact_relpath=relpath,
        sha_hex=sha_hex,
        size_bytes=size_bytes,
    )
    upsert_checkpoint_chunk_record_v2(checkpoint=checkpoint, record=chunk_record)
    completed_chunk_keys.add(chunk_key)
    checkpoint.processed_pages = min(total_pages, resolve_checkpoint_processed_pages_v2(checkpoint))
    checkpoint.total_pages = total_pages
    checkpoint.updated_at = dt_to_rfc3339(utc_now()) or checkpoint.updated_at
    checkpoint_persist_started = time.perf_counter()
    persist_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)
    assemble_partial_artifact(upload_path=job.upload_path, checkpoint=checkpoint)
    checkpoint_persist_ms = max(0, int((time.perf_counter() - checkpoint_persist_started) * 1000))
    phase_timings_ms = _merge_phase_timings(
        phase_timings_ms,
        {TIMING_KEY_CHECKPOINT_PERSIST_MS: checkpoint_persist_ms},
    )
    chunk_record.phase_timings_ms = _merge_phase_timings(
        chunk_record.phase_timings_ms,
        {TIMING_KEY_CHECKPOINT_PERSIST_MS: checkpoint_persist_ms},
    )
    checkpoint.updated_at = dt_to_rfc3339(utc_now()) or checkpoint.updated_at
    persist_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)
    if is_cancel_requested is not None and is_cancel_requested():
        raise PdfConversionCanceledV2(job_id=job.job_id)
    if progress_callback is not None:
        progress_callback(
            _progress_update_v2(checkpoint, total_pages, conversion_started, phase_timings_ms)
        )
    return phase_timings_ms


def _build_chunk_record_v2(
    *,
    outcome: PdfChunkConversionOutcomeV2,
    artifact_relpath: str,
    sha_hex: str,
    size_bytes: int,
) -> PdfChunkRecordV2:
    chunk_phase_timings_ms = normalize_phase_timings_map(
        {
            **outcome.phase_timings_ms,
            TIMING_KEY_CHUNK_TOTAL_MS: outcome.chunk_elapsed_ms,
        }
    )
    return PdfChunkRecordV2(
        chunk_index=outcome.chunk_index,
        start_page=outcome.start_page,
        end_page=outcome.end_page,
        status="succeeded",
        started_at=outcome.started_at,
        completed_at=outcome.completed_at,
        artifact_relpath=artifact_relpath,
        sha256=f"sha256:{sha_hex}",
        size_bytes=size_bytes,
        backend_used=required_checkpoint_metadata_value_v2(
            label="backend_used",
            value=outcome.backend_used,
        ),
        acceleration_used=required_checkpoint_metadata_value_v2(
            label="acceleration_used",
            value=outcome.acceleration_used,
        ),
        ocr_enabled=outcome.ocr_enabled,
        ocr_engine_used=observed_ocr_engine_used_for_checkpoint_record_v2(
            ocr_enabled=outcome.ocr_enabled,
            ocr_engine_used=outcome.ocr_engine_used,
        ),
        ocr_languages_used=observed_ocr_languages_used_for_checkpoint_record_v2(
            ocr_enabled=outcome.ocr_enabled,
            ocr_languages_used=outcome.ocr_languages_used,
        ),
        warnings=list(outcome.warnings),
        phase_timings_ms=chunk_phase_timings_ms,
        formula_authority=dict(outcome.formula_authority),
    )


def _progress_update_v2(
    checkpoint: PdfCheckpointV2,
    total_pages: int,
    conversion_started: float,
    phase_timings_ms: dict[str, int],
) -> PdfCheckpointProgressUpdateV2:
    elapsed = max(0.001, time.perf_counter() - conversion_started)
    minutes = elapsed / 60.0
    pages_per_minute = float(checkpoint.processed_pages) / minutes
    remaining = max(0, total_pages - checkpoint.processed_pages)
    eta_seconds = int((remaining / max(1e-6, pages_per_minute)) * 60.0)
    return PdfCheckpointProgressUpdateV2(
        total_pages=total_pages,
        processed_pages=checkpoint.processed_pages,
        failed_pages=checkpoint.failed_pages,
        percent_complete=(checkpoint.processed_pages / float(total_pages)) * 100.0,
        pages_per_minute=pages_per_minute,
        eta_seconds=eta_seconds,
        phase_timings_ms=dict(phase_timings_ms),
    )


def _merge_phase_timings(current: dict[str, int], additional: dict[str, int]) -> dict[str, int]:
    return merge_phase_timings_canonical_v2(current=current, additional=additional)
