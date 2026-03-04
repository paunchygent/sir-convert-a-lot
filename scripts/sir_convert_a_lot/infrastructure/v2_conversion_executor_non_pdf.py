"""Non-PDF conversion execution helpers for service API v2.

Purpose:
    Keep non-PDF v2 routes (docx/html/md sources) isolated from the PDF
    checkpointed execution path so each module stays SRP-aligned and below the
    500 LoC guardrail.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for non-PDF routes.
    - Delegates per-source execution to `infrastructure.v2_non_pdf_routes_*`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_models import NonPdfExecutionOutcomeV2
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_routes_docx import (
    execute_docx_source_route_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_routes_html import (
    execute_html_source_route_v2,
)
from scripts.sir_convert_a_lot.infrastructure.v2_non_pdf_routes_md import (
    execute_markdown_source_route_v2,
)


def execute_v2_non_pdf_job_conversion(
    *,
    job: StoredJobV2,
    workdir: Path,
    input_path: Path,
    document_timeout_seconds: int,
) -> NonPdfExecutionOutcomeV2:
    """Execute a non-PDF v2 route and write the final artifact to job storage."""
    if job.source_format == SourceFormatV2.DOCX:
        return execute_docx_source_route_v2(
            job=job,
            workdir=workdir,
            input_path=input_path,
            document_timeout_seconds=document_timeout_seconds,
        )
    if job.source_format == SourceFormatV2.HTML:
        return execute_html_source_route_v2(
            job=job,
            workdir=workdir,
            input_path=input_path,
            document_timeout_seconds=document_timeout_seconds,
        )
    if job.source_format == SourceFormatV2.MD:
        return execute_markdown_source_route_v2(
            job=job,
            workdir=workdir,
            input_path=input_path,
            document_timeout_seconds=document_timeout_seconds,
        )

    raise ServiceError(
        status_code=422,
        code="unsupported_route",
        message=(f"Unsupported route: {job.source_format.value} -> {job.output_format.value}."),
        retryable=False,
    )
