"""PDF-to-DOCX branch tests for v2 conversion executor.

Purpose:
    Validate PDF source handling, backend error mapping, and success-path stage
    orchestration for the v2 PDF-to-DOCX route.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`.
    - Uses shared builders in `v2_conversion_executor_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import (
    v2_non_pdf_helpers as v2_non_pdf_helpers,
)
from scripts.sir_convert_a_lot.infrastructure import (
    v2_pdf_checkpointed_executor as v2_pdf_checkpointed_executor,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
    fingerprint_job_options,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


def test_execute_v2_job_conversion_pdf_to_docx_invalid_job_spec_missing_sections(
    tmp_path: Path,
) -> None:
    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"%PDF-1.7\nvalid\n",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.DOCX,
        spec_source_format=SourceFormatV2.MD,
        spec_output_format=OutputFormatV2.DOCX,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 500
    assert error.code == "invalid_job_spec"
    assert error.message == "v2 job spec is missing required pdf_options/execution for pdf routes."
    assert error.retryable is False


@pytest.mark.parametrize(
    (
        "raised_error",
        "expected_status",
        "expected_code",
        "expected_message",
        "expected_retryable",
        "expected_details",
    ),
    [
        (
            BackendGpuUnavailableError(
                backend="docling",
                probe=GpuRuntimeProbeResult(
                    runtime_kind="none",
                    torch_version="2.10.0",
                    hip_version=None,
                    cuda_version=None,
                    is_available=False,
                    device_count=0,
                    device_name=None,
                ),
            ),
            503,
            "gpu_not_available",
            "GPU runtime is unavailable for the selected backend under GPU-required policy.",
            True,
            {
                "reason": "backend_gpu_runtime_unavailable",
                "backend": "docling",
                "runtime_kind": "none",
                "hip_version": None,
                "cuda_version": None,
            },
        ),
        (
            BackendInputError("invalid PDF payload"),
            422,
            "pdf_unreadable",
            "Uploaded PDF could not be converted: invalid PDF payload",
            False,
            None,
        ),
        (
            BackendExecutionError("backend crashed"),
            500,
            "conversion_internal_error",
            "Unexpected backend conversion failure: backend crashed",
            True,
            None,
        ),
    ],
)
def test_execute_v2_job_conversion_pdf_to_docx_maps_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    raised_error: Exception,
    expected_status: int,
    expected_code: str,
    expected_message: str,
    expected_retryable: bool,
    expected_details: dict[str, object] | None,
) -> None:
    def _raise_execute_job_conversion(
        **kwargs: object,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del kwargs
        raise raised_error

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _raise_execute_job_conversion,
    )
    monkeypatch.setattr(v2_pdf_checkpointed_executor, "best_effort_pdf_total_pages", lambda _: None)

    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"%PDF-1.7\nvalid\n",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.DOCX,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == expected_status
    assert error.code == expected_code
    assert error.message == expected_message
    assert error.retryable is expected_retryable
    assert error.details == expected_details


def test_execute_v2_job_conversion_pdf_to_docx_success_with_stubbed_stages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute_calls: list[dict[str, object]] = []
    markdown_calls: list[tuple[Path, Path]] = []
    html_docx_calls: list[tuple[Path, Path, Path, Path | None]] = []
    reference_docx = tmp_path / "reference-template.docx"
    reference_docx.write_bytes(b"template")

    def _fake_execute_job_conversion(
        **kwargs: object,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        execute_calls.append(dict(kwargs))
        return (
            "# Converted from PDF\n",
            ConversionMetadata(
                backend_used="docling",
                acceleration_used="cuda",
                ocr_enabled=False,
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:backend-options",
            ),
            ["table_detection_degraded"],
            {"ocr_layout_extract_ms": 12, "markdown_normalize_ms": 3},
        )

    def _fake_convert_markdown_to_html(
        *,
        markdown_path: Path,
        output_html_path: Path,
        timeout_seconds: int = 300,
    ) -> None:
        del timeout_seconds
        markdown_calls.append((markdown_path, output_html_path))
        output_html_path.write_text("<html><body>Converted</body></html>", encoding="utf-8")

    def _fake_convert_html_to_docx(
        *,
        html_path: Path,
        output_docx_path: Path,
        resource_root: Path,
        reference_docx_path: Path | None,
        timeout_seconds: int = 300,
    ) -> None:
        del timeout_seconds
        html_docx_calls.append((html_path, output_docx_path, resource_root, reference_docx_path))
        output_docx_path.write_bytes(b"stub-pdf-docx")

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _fake_execute_job_conversion,
    )
    monkeypatch.setattr(
        v2_non_pdf_helpers, "convert_markdown_to_html", _fake_convert_markdown_to_html
    )
    monkeypatch.setattr(v2_non_pdf_helpers, "convert_html_to_docx", _fake_convert_html_to_docx)
    monkeypatch.setattr(v2_pdf_checkpointed_executor, "best_effort_pdf_total_pages", lambda _: None)

    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"%PDF-1.7\nvalid\n",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.DOCX,
        reference_docx_path=reference_docx,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.artifact_bytes == b"stub-pdf-docx"
    assert result.pipeline_used == "pdf_to_docx_v2"
    assert result.backend_used == "docling"
    assert result.acceleration_used == "cuda"
    assert result.warnings == ["table_detection_degraded"]
    assert result.phase_timings_ms == {"ocr_layout_extract_ms": 12, "markdown_normalize_ms": 3}
    assert result.options_fingerprint == fingerprint_job_options(job.spec)
    assert len(execute_calls) == 1
    assert execute_calls[0]["source_filename"] == "input.pdf"
    assert execute_calls[0]["source_bytes"] == b"%PDF-1.7\nvalid\n"
    assert execute_calls[0]["gpu_available"] is False
    assert execute_calls[0]["gpu_runtime_probe"] is None
    assert isinstance(execute_calls[0]["docling_backend"], _UnusedBackend)
    assert isinstance(execute_calls[0]["pymupdf_backend"], _UnusedBackend)
    assert len(markdown_calls) == 1
    assert len(html_docx_calls) == 1
    assert markdown_calls[0][0].name == "pdf_checkpointed_output.md"
    assert markdown_calls[0][1].name == "pdf_checkpointed_output.html"
    assert html_docx_calls[0][0].name == "pdf_checkpointed_output.html"
    assert html_docx_calls[0][1] == job.artifact_path
    assert html_docx_calls[0][3] == reference_docx
