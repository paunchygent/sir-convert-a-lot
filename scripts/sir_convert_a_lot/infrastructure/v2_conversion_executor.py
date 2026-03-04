"""Service API v2 conversion execution helpers.

Purpose:
    Provide the stable v2 conversion executor entrypoint used by the v2 runtime
    engine, while keeping the long-PDF chunked checkpointing implementation in
    a dedicated module.

Relationships:
    - Called by `infrastructure.runtime_engine_v2`.
    - Delegates PDF execution to `infrastructure.v2_pdf_checkpointed_executor`.
    - Delegates non-PDF routes to `infrastructure.v2_conversion_executor_non_pdf`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import ConversionBackend
from scripts.sir_convert_a_lot.infrastructure.resources_zip import (
    ResourcesZipError,
    extract_resources_zip,
    reset_directory,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor_non_pdf import (
    execute_v2_non_pdf_job_conversion,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_helpers import (
    convert_markdown_content_to_docx_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_models import NonPdfExecutionOutcomeV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpointed_executor import (
    PdfCheckpointProgressUpdateV2,
    execute_pdf_to_markdown_with_checkpoints_v2,
)


@dataclass(frozen=True)
class V2ExecutionResult:
    """Successful execution outcome for a v2 conversion job."""

    artifact_bytes: bytes
    pipeline_used: str
    backend_used: str | None
    acceleration_used: str | None
    warnings: list[str]
    phase_timings_ms: dict[str, int]
    options_fingerprint: str
    template_id: str | None = None
    template_version: str | None = None
    template_artifact_sha256: str | None = None


DEFAULT_NON_PDF_DOCUMENT_TIMEOUT_SECONDS = 300
DEFAULT_PDF_CHECKPOINT_CHUNK_SIZE_PAGES = 10


def fingerprint_job_options(spec: JobSpecV2) -> str:
    """Return a deterministic SHA256 fingerprint for a v2 job spec."""
    normalized = json.dumps(spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _resolve_document_timeout_seconds(spec: JobSpecV2) -> int:
    execution = spec.execution
    if execution is None:
        return DEFAULT_NON_PDF_DOCUMENT_TIMEOUT_SECONDS
    return execution.document_timeout_seconds


def _prepare_workdir(job: StoredJobV2) -> tuple[Path, Path]:
    raw_dir = job.upload_path.parent
    workdir = raw_dir / "workdir"
    reset_directory(workdir)

    if job.resources_zip_path is not None:
        try:
            extract_resources_zip(zip_path=job.resources_zip_path, output_dir=workdir)
        except ResourcesZipError as exc:
            raise ServiceError(
                status_code=422,
                code=exc.code,
                message=exc.message,
                retryable=False,
            ) from exc

    source_name = Path(job.source_filename).name
    input_path = workdir / source_name
    input_path.write_bytes(job.upload_path.read_bytes())
    return workdir, input_path


def execute_v2_job_conversion(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
    progress_callback: Callable[[PdfCheckpointProgressUpdateV2], None] | None = None,
) -> V2ExecutionResult:
    """Execute one v2 job conversion and return artifact bytes + metadata."""
    options_fingerprint = fingerprint_job_options(job.spec)
    document_timeout_seconds = _resolve_document_timeout_seconds(job.spec)

    pipeline_used: str
    backend_used: str | None = None
    acceleration_used: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    template_artifact_sha256: str | None = None

    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}

    if job.source_format == SourceFormatV2.PDF and job.output_format in {
        OutputFormatV2.MD,
        OutputFormatV2.DOCX,
    }:
        pipeline_used = (
            "pdf_to_md_v2" if job.output_format == OutputFormatV2.MD else "pdf_to_docx_v2"
        )
        (
            markdown_content,
            backend_used,
            acceleration_used,
            pdf_warnings,
            pdf_timings,
        ) = execute_pdf_to_markdown_with_checkpoints_v2(
            job=job,
            config=config,
            docling_backend=docling_backend,
            pymupdf_backend=pymupdf_backend,
            chunk_size_pages=DEFAULT_PDF_CHECKPOINT_CHUNK_SIZE_PAGES,
            progress_callback=progress_callback,
        )
        warnings.extend(pdf_warnings)
        phase_timings_ms.update(pdf_timings)

        if job.output_format == OutputFormatV2.MD:
            job.artifact_path.write_text(markdown_content, encoding="utf-8")
        else:
            workdir, _ = _prepare_workdir(job)
            reference_docx = convert_markdown_content_to_docx_v2(
                job=job,
                workdir=workdir,
                markdown_content=markdown_content,
                document_timeout_seconds=document_timeout_seconds,
            )
            template_id = reference_docx.template_id
            template_version = reference_docx.template_version
            template_artifact_sha256 = reference_docx.template_artifact_sha256
    else:
        workdir, input_path = _prepare_workdir(job)
        outcome: NonPdfExecutionOutcomeV2 = execute_v2_non_pdf_job_conversion(
            job=job,
            workdir=workdir,
            input_path=input_path,
            document_timeout_seconds=document_timeout_seconds,
        )
        pipeline_used = outcome.pipeline_used
        backend_used = outcome.backend_used
        acceleration_used = outcome.acceleration_used
        warnings = list(outcome.warnings)
        phase_timings_ms = dict(outcome.phase_timings_ms)
        template_id = outcome.template_id
        template_version = outcome.template_version
        template_artifact_sha256 = outcome.template_artifact_sha256

    artifact_bytes = job.artifact_path.read_bytes()
    if len(artifact_bytes) == 0:
        raise ServiceError(
            status_code=500,
            code="artifact_empty",
            message="Conversion produced an empty artifact file.",
            retryable=True,
        )

    return V2ExecutionResult(
        artifact_bytes=artifact_bytes,
        pipeline_used=pipeline_used,
        backend_used=backend_used,
        acceleration_used=acceleration_used,
        warnings=warnings,
        phase_timings_ms=phase_timings_ms,
        options_fingerprint=options_fingerprint,
        template_id=template_id,
        template_version=template_version,
        template_artifact_sha256=template_artifact_sha256,
    )
