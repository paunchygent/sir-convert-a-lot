"""DOCX-path branch tests for v2 conversion executor.

Purpose:
    Validate HTML/Markdown to DOCX branches and v1-policy mapping helpers used
    by the v2 conversion executor.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`.
    - Uses shared builders in `v2_conversion_executor_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_conversion_executor
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HtmlToDocxConversionError,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MarkdownToHtmlConversionError,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    _map_converter_error,
    execute_v2_job_conversion,
    fingerprint_job_options,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _build_v1_job_spec,
    _service_config,
    _UnusedBackend,
)


def test_validate_backend_strategy_v1_maps_policy_violation() -> None:
    spec = _build_v1_job_spec(
        backend_strategy="pymupdf",
        acceleration_policy="gpu_required",
    )

    with pytest.raises(ServiceError) as exc_info:
        v2_conversion_executor._validate_backend_strategy_v1(spec)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "validation_error"
    assert (
        error.message == "Requested backend is incompatible with the selected acceleration policy."
    )
    assert error.retryable is False
    assert error.details == {
        "field": "conversion.backend_strategy",
        "reason": "backend_incompatible_with_gpu_policy",
    }


def test_validate_acceleration_policy_v1_maps_rule_violation(tmp_path: Path) -> None:
    spec = _build_v1_job_spec(acceleration_policy="cpu_only")
    config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        gpu_available=False,
        allow_cpu_only=False,
        allow_cpu_fallback=False,
        enable_supervisor=False,
        processing_delay_seconds=0.0,
    )

    with pytest.raises(ServiceError) as exc_info:
        v2_conversion_executor._validate_acceleration_policy_v1(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 503
    assert error.code == "gpu_not_available"
    assert error.retryable is True
    assert "CPU-only execution is disabled during GPU-first rollout" in error.message
    assert error.details is None


def test_validate_acceleration_policy_v1_maps_runtime_probe_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    spec = _build_v1_job_spec(
        backend_strategy="auto",
        acceleration_policy="gpu_required",
    )
    config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data",
        gpu_available=True,
        allow_cpu_only=False,
        allow_cpu_fallback=False,
        enable_supervisor=False,
        processing_delay_seconds=0.0,
    )
    probe = GpuRuntimeProbeResult(
        runtime_kind="none",
        torch_version="2.10.0",
        hip_version=None,
        cuda_version=None,
        is_available=False,
        device_count=0,
        device_name=None,
    )

    def _fake_probe() -> GpuRuntimeProbeResult:
        return probe

    monkeypatch.setattr(v2_conversion_executor, "probe_torch_gpu_runtime", _fake_probe)

    with pytest.raises(ServiceError) as exc_info:
        v2_conversion_executor._validate_acceleration_policy_v1(spec=spec, config=config)

    error = exc_info.value
    assert error.status_code == 503
    assert error.code == "gpu_not_available"
    assert error.retryable is True
    assert (
        error.message
        == "GPU runtime is unavailable for the selected backend under GPU-required policy."
    )
    assert error.details == {
        "reason": "backend_gpu_runtime_unavailable",
        "backend": "docling",
        "runtime_kind": "none",
        "hip_version": None,
        "cuda_version": None,
    }


def test_map_converter_error_for_html_to_docx_error() -> None:
    mapped = _map_converter_error(
        HtmlToDocxConversionError(
            code="pandoc_not_installed",
            message="Pandoc is not installed.",
        )
    )

    assert mapped.status_code == 503
    assert mapped.code == "pandoc_not_installed"
    assert mapped.message == "Pandoc is not installed."
    assert mapped.retryable is True


def test_map_converter_error_for_unhandled_type_raises_assertion() -> None:
    with pytest.raises(AssertionError, match="Unhandled converter error type: AssertionError"):
        _map_converter_error(AssertionError("unexpected"))


def test_execute_v2_job_conversion_html_to_docx_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_docx_calls: list[tuple[Path, Path, Path, Path | None]] = []
    reference_docx = tmp_path / "reference-template.docx"
    reference_docx.write_bytes(b"template")

    def _fake_convert_html_to_docx(
        *,
        html_path: Path,
        output_docx_path: Path,
        resource_root: Path,
        reference_docx_path: Path | None,
    ) -> None:
        html_docx_calls.append((html_path, output_docx_path, resource_root, reference_docx_path))
        output_docx_path.write_bytes(b"stub-html-docx")

    monkeypatch.setattr(v2_conversion_executor, "convert_html_to_docx", _fake_convert_html_to_docx)

    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Hello DOCX</body></html>",
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.DOCX,
        reference_docx_path=reference_docx,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.artifact_bytes == b"stub-html-docx"
    assert result.pipeline_used == "html_to_docx_v2"
    assert result.backend_used == "pandoc"
    assert result.acceleration_used is None
    assert result.warnings == []
    assert result.phase_timings_ms == {}
    assert result.options_fingerprint == fingerprint_job_options(job.spec)
    assert len(html_docx_calls) == 1
    assert html_docx_calls[0][0].name == "page.html"
    assert html_docx_calls[0][1] == job.artifact_path
    assert html_docx_calls[0][2] == job.upload_path.parent / "workdir"
    assert html_docx_calls[0][3] == reference_docx


def test_execute_v2_job_conversion_html_to_docx_maps_converter_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _failing_convert_html_to_docx(
        *,
        html_path: Path,
        output_docx_path: Path,
        resource_root: Path,
        reference_docx_path: Path | None,
    ) -> None:
        del html_path, output_docx_path, resource_root, reference_docx_path
        raise HtmlToDocxConversionError(
            code="html_to_docx_failed",
            message="Pandoc failed to convert HTML to DOCX.",
        )

    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_docx",
        _failing_convert_html_to_docx,
    )

    job = _build_job(
        tmp_path,
        source_filename="page.html",
        source_bytes=b"<html><body>Broken</body></html>",
        source_format=SourceFormatV2.HTML,
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
    assert error.status_code == 500
    assert error.code == "html_to_docx_failed"
    assert error.message == "Pandoc failed to convert HTML to DOCX."
    assert error.retryable is False


def test_execute_v2_job_conversion_md_to_docx_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown_calls: list[tuple[Path, Path]] = []
    html_docx_calls: list[tuple[Path, Path, Path, Path | None]] = []

    def _fake_convert_markdown_to_html(*, markdown_path: Path, output_html_path: Path) -> None:
        markdown_calls.append((markdown_path, output_html_path))
        output_html_path.write_text("<html><body>Converted MD</body></html>", encoding="utf-8")

    def _fake_convert_html_to_docx(
        *,
        html_path: Path,
        output_docx_path: Path,
        resource_root: Path,
        reference_docx_path: Path | None,
    ) -> None:
        html_docx_calls.append((html_path, output_docx_path, resource_root, reference_docx_path))
        output_docx_path.write_bytes(b"stub-md-docx")

    monkeypatch.setattr(
        v2_conversion_executor, "convert_markdown_to_html", _fake_convert_markdown_to_html
    )
    monkeypatch.setattr(v2_conversion_executor, "convert_html_to_docx", _fake_convert_html_to_docx)

    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n\nBody\n",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
    )

    result = execute_v2_job_conversion(
        job=job,
        config=_service_config(tmp_path),
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert result.artifact_bytes == b"stub-md-docx"
    assert result.pipeline_used == "md_to_docx_v2"
    assert result.backend_used == "pandoc"
    assert result.acceleration_used is None
    assert result.warnings == []
    assert result.phase_timings_ms == {}
    assert result.options_fingerprint == fingerprint_job_options(job.spec)
    assert len(markdown_calls) == 1
    assert len(html_docx_calls) == 1
    assert markdown_calls[0][0].name == "note.md"
    assert markdown_calls[0][1].name == "note.html"
    assert html_docx_calls[0][0].name == "note.html"
    assert html_docx_calls[0][1] == job.artifact_path


def test_execute_v2_job_conversion_md_to_docx_maps_markdown_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _failing_convert_markdown_to_html(*, markdown_path: Path, output_html_path: Path) -> None:
        del markdown_path, output_html_path
        raise MarkdownToHtmlConversionError(
            code="pandoc_not_installed",
            message="Pandoc missing.",
        )

    def _unexpected_convert_html_to_docx(
        *,
        html_path: Path,
        output_docx_path: Path,
        resource_root: Path,
        reference_docx_path: Path | None,
    ) -> None:
        del html_path, output_docx_path, resource_root, reference_docx_path
        raise AssertionError("convert_html_to_docx should not run when markdown conversion fails.")

    monkeypatch.setattr(
        v2_conversion_executor, "convert_markdown_to_html", _failing_convert_markdown_to_html
    )
    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_docx",
        _unexpected_convert_html_to_docx,
    )

    job = _build_job(
        tmp_path,
        source_filename="broken.md",
        source_bytes=b"# Broken\n",
        source_format=SourceFormatV2.MD,
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
    assert error.status_code == 503
    assert error.code == "pandoc_not_installed"
    assert error.message == "Pandoc missing."
    assert error.retryable is True


def test_execute_v2_job_conversion_md_to_docx_maps_html_to_docx_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_convert_markdown_to_html(*, markdown_path: Path, output_html_path: Path) -> None:
        del markdown_path
        output_html_path.write_text("<html><body>Interim</body></html>", encoding="utf-8")

    def _failing_convert_html_to_docx(
        *,
        html_path: Path,
        output_docx_path: Path,
        resource_root: Path,
        reference_docx_path: Path | None,
    ) -> None:
        del html_path, output_docx_path, resource_root, reference_docx_path
        raise HtmlToDocxConversionError(
            code="html_to_docx_failed",
            message="Pandoc failed.",
        )

    monkeypatch.setattr(
        v2_conversion_executor, "convert_markdown_to_html", _fake_convert_markdown_to_html
    )
    monkeypatch.setattr(
        v2_conversion_executor,
        "convert_html_to_docx",
        _failing_convert_html_to_docx,
    )

    job = _build_job(
        tmp_path,
        source_filename="note.md",
        source_bytes=b"# Note\n",
        source_format=SourceFormatV2.MD,
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
    assert error.status_code == 500
    assert error.code == "html_to_docx_failed"
    assert error.message == "Pandoc failed."
    assert error.retryable is False
