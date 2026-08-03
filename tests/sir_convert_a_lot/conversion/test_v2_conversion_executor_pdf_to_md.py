"""PDF-to-Markdown branch tests for the v2 conversion executor.

Purpose:
    Verify that the v2 executor supports `pdf -> md` directly and preserves
    backend metadata/warnings from the PDF conversion stage.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`.
    - Reuses shared builders in `v2_conversion_executor_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import (
    v2_pdf_checkpointed_executor as v2_pdf_checkpointed_executor,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
    fingerprint_job_options,
)
from tests.sir_convert_a_lot.conversion.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


def test_execute_v2_job_conversion_pdf_to_md_success_with_stubbed_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute_calls: list[dict[str, object]] = []

    def _fake_execute_job_conversion(
        **kwargs: object,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        execute_calls.append(dict(kwargs))
        return (
            "# Converted markdown\n\nBody\n",
            ConversionMetadata(
                backend_used="docling",
                acceleration_used="cuda",
                ocr_enabled=False,
                table_mode=TableMode.ACCURATE,
                options_fingerprint="sha256:pdf-md-options",
            ),
            ["ocr_retry_performed"],
            {"ocr_layout_extract_ms": 45, "markdown_normalize_ms": 6},
        )

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _fake_execute_job_conversion,
    )
    monkeypatch.setattr(v2_pdf_checkpointed_executor, "best_effort_pdf_total_pages", lambda _: None)

    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"%PDF-1.7\nvalid\n",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.pipeline_used == "pdf_to_md_v2"
    assert result.backend_used == "docling"
    assert result.acceleration_used == "cuda"
    assert result.warnings == ["ocr_retry_performed"]
    assert result.phase_timings_ms == {"ocr_layout_extract_ms": 45, "markdown_normalize_ms": 6}
    assert result.options_fingerprint == fingerprint_job_options(job.spec)
    assert result.artifact_bytes == b"# Converted markdown\n\nBody\n"
    assert job.artifact_path.read_text(encoding="utf-8") == "# Converted markdown\n\nBody\n"
    assert len(execute_calls) == 1
    assert execute_calls[0]["source_filename"] == "input.pdf"


def test_execute_v2_job_conversion_pdf_to_md_rejects_non_pdf_bytes(tmp_path: Path) -> None:
    job = _build_job(
        tmp_path,
        source_filename="input.pdf",
        source_bytes=b"not-a-pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_service_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "pdf_unreadable"
    assert error.retryable is False
    assert error.message == "Uploaded file is not a readable PDF."
