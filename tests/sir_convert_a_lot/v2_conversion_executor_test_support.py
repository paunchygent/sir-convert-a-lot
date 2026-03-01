"""Shared test helpers for v2 conversion executor tests.

Purpose:
    Provide reusable builders and stubs for v2 conversion executor unit tests so
    scenario-focused test modules stay below the repository file-size limit.

Relationships:
    - Imported by the split `test_v2_conversion_executor_*` modules.
    - Uses v2 runtime/domain models to construct deterministic stored-job fixtures.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    ConversionRequest,
    ConversionResultData,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


class _UnusedBackend:
    """Backend test double that must never be called in these unit tests."""

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        del request
        raise AssertionError("PDF backend conversion should not be invoked in this test.")


def _service_config(tmp_path: Path) -> ServiceConfig:
    return ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        gpu_available=False,
        allow_cpu_only=True,
        allow_cpu_fallback=False,
        enable_supervisor=False,
        processing_delay_seconds=0.0,
    )


def _build_job_spec(
    *,
    source_filename: str,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
    css_filenames: list[str] | None = None,
    pdf_layout: dict[str, object] | None = None,
    template: dict[str, str | None] | None = None,
    reference_docx_filename: str | None = None,
    execution_timeout_seconds: int | None = None,
) -> JobSpecV2:
    payload: dict[str, object] = {
        "api_version": "v2",
        "source": {
            "kind": "upload",
            "filename": source_filename,
            "format": source_format.value,
        },
        "conversion": {
            "output_format": output_format.value,
            "template": template,
            "css_filenames": list(css_filenames or []),
            "reference_docx_filename": reference_docx_filename,
        },
        "retention": {"pin": False},
    }
    if pdf_layout is not None:
        conversion = payload["conversion"]
        assert isinstance(conversion, dict)
        conversion["pdf_layout"] = pdf_layout
    if source_format == SourceFormatV2.PDF:
        payload["pdf_options"] = {
            "backend_strategy": "auto",
            "ocr_mode": "off",
            "table_mode": "fast",
            "normalize": "standard",
        }
    if source_format == SourceFormatV2.PDF or execution_timeout_seconds is not None:
        payload["execution"] = {
            "acceleration_policy": "cpu_only",
            "priority": "normal",
            "document_timeout_seconds": (
                1800 if execution_timeout_seconds is None else execution_timeout_seconds
            ),
        }
    return JobSpecV2.model_validate(payload)


def _build_job(
    tmp_path: Path,
    *,
    source_filename: str,
    source_bytes: bytes,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
    css_filenames: list[str] | None = None,
    pdf_layout: dict[str, object] | None = None,
    template: dict[str, str | None] | None = None,
    reference_docx_filename: str | None = None,
    reference_docx_path: Path | None = None,
    spec_source_format: SourceFormatV2 | None = None,
    spec_output_format: OutputFormatV2 | None = None,
    execution_timeout_seconds: int | None = None,
) -> StoredJobV2:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    upload_path = raw_dir / source_filename
    upload_path.write_bytes(source_bytes)

    if output_format == OutputFormatV2.PDF:
        artifact_suffix = ".pdf"
    elif output_format == OutputFormatV2.MD:
        artifact_suffix = ".md"
    else:
        artifact_suffix = ".docx"
    artifact_path = raw_dir / f"artifact{artifact_suffix}"

    spec = _build_job_spec(
        source_filename=source_filename,
        source_format=spec_source_format or source_format,
        output_format=spec_output_format or output_format,
        css_filenames=css_filenames,
        pdf_layout=pdf_layout,
        template=template,
        reference_docx_filename=reference_docx_filename,
        execution_timeout_seconds=execution_timeout_seconds,
    )
    now = datetime.now(UTC)
    return StoredJobV2(
        job_id="job-v2-unit-test",
        spec=spec,
        source_filename=source_filename,
        source_format=source_format,
        output_format=output_format,
        upload_path=upload_path,
        resources_zip_path=None,
        reference_docx_path=reference_docx_path,
        artifact_path=artifact_path,
        status=JobStatus.QUEUED,
        created_at=now,
        updated_at=now,
        expires_at=None,
        progress_stage="queued",
    )


def _build_v1_job_spec(
    *,
    backend_strategy: str = "auto",
    acceleration_policy: str = "cpu_only",
    ocr_mode: str = "off",
) -> JobSpec:
    return JobSpec.model_validate(
        {
            "api_version": "v1",
            "source": {
                "kind": "upload",
                "filename": "input.pdf",
            },
            "conversion": {
                "output_format": "md",
                "backend_strategy": backend_strategy,
                "ocr_mode": ocr_mode,
                "table_mode": "fast",
                "normalize": "standard",
            },
            "execution": {
                "acceleration_policy": acceleration_policy,
                "priority": "normal",
                "document_timeout_seconds": 1800,
            },
            "retention": {"pin": False},
        }
    )
