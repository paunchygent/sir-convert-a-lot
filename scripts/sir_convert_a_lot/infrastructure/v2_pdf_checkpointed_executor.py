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
    assemble_partial_markdown_artifact,
    build_initial_pdf_checkpoint,
    persist_pdf_checkpoint,
)
from scripts.sir_convert_a_lot.infrastructure.pdf_metadata_v2 import best_effort_pdf_total_pages
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import normalize_phase_timings_map
from scripts.sir_convert_a_lot.infrastructure.runtime_conversion import execute_job_conversion
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_chunk_runner import (
    run_pdf_checkpoint_chunk_conversion_plan_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfCheckpointProgressUpdateV2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_planning import (
    resolve_checkpoint_processed_pages_v2,
    succeeded_chunk_keys_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_state import (
    PdfCheckpointArtifactIntegrityError,
    assemble_final_markdown_from_checkpoint_v2,
    load_pdf_checkpoint_or_fail_closed_v2,
)


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

    checkpoint = load_pdf_checkpoint_or_fail_closed_v2(upload_path=job.upload_path)
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

    checkpoint.processed_pages = min(total_pages, resolve_checkpoint_processed_pages_v2(checkpoint))
    checkpoint.total_pages = total_pages
    processed_pages = checkpoint.processed_pages
    completed_chunk_keys = succeeded_chunk_keys_v2(checkpoint)

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

    run_pdf_checkpoint_chunk_conversion_plan_v2(
        job=job,
        config=config,
        checkpoint=checkpoint,
        v1_spec=v1_spec,
        probe=probe,
        docling_backend=docling_backend,
        pymupdf_backend=pymupdf_backend,
        resolved_ocr=resolved_ocr,
        total_pages=total_pages,
        chunk_size_pages=chunk_size_pages,
        completed_chunk_keys=completed_chunk_keys,
        max_chunk_workers=max_chunk_workers,
        parallel_enabled=parallel_enabled,
        progress_callback=progress_callback,
        is_cancel_requested=is_cancel_requested,
        on_chunk_worker_start=on_chunk_worker_start,
        on_chunk_worker_finish=on_chunk_worker_finish,
        execute_chunk_conversion=execute_job_conversion,
        persist_checkpoint=persist_pdf_checkpoint,
        assemble_partial_artifact=assemble_partial_markdown_artifact,
    )

    try:
        final_markdown = assemble_final_markdown_from_checkpoint_v2(
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
