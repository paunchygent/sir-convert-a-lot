"""Runtime conversion failure classification tests for Sir Convert-a-Lot.

Purpose:
    Verify runtime maps backend input/execution failures to stable service
    error codes and retryability semantics.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.runtime_engine`.
    - Uses backend error contracts from `infrastructure.conversion_backend`.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, JobSpec, JobStatus
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.runtime_engine import ServiceConfig, ServiceRuntime
from tests.sir_convert_a_lot.pdf_fixtures import fixture_pdf_bytes


def _job_spec(
    filename: str,
    *,
    backend_strategy: BackendStrategy = BackendStrategy.AUTO,
    acceleration_policy: str = "cpu_only",
) -> JobSpec:
    return JobSpec.model_validate(
        {
            "api_version": "v1",
            "source": {"kind": "upload", "filename": filename},
            "conversion": {
                "output_format": "md",
                "backend_strategy": backend_strategy.value,
                "ocr_mode": "off",
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


def _wait_for_terminal(
    runtime: ServiceRuntime, job_id: str, timeout_seconds: float = 20.0
) -> JobStatus:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = runtime.get_job(job_id)
        assert job is not None
        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return job.status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def test_backend_execution_error_maps_to_internal_failure(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
        )
    )
    spec = _job_spec("paper.pdf")
    job = runtime.create_job(
        spec=spec,
        upload_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        source_filename="paper.pdf",
    )

    def _raise_execution_error(_request) -> None:
        raise BackendExecutionError("simulated backend execution failure")

    monkeypatch.setattr(runtime.docling_backend, "convert", _raise_execution_error)
    runtime.run_job_async(job.job_id)

    status = _wait_for_terminal(runtime, job.job_id)
    assert status == JobStatus.FAILED

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.failure_code == "conversion_internal_error"
    assert stored.failure_retryable is True


def test_backend_input_error_maps_to_pdf_unreadable(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
        )
    )
    spec = _job_spec("paper.pdf")
    job = runtime.create_job(
        spec=spec,
        upload_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        source_filename="paper.pdf",
    )

    def _raise_input_error(_request) -> None:
        raise BackendInputError("simulated unreadable document")

    monkeypatch.setattr(runtime.docling_backend, "convert", _raise_input_error)
    runtime.run_job_async(job.job_id)

    status = _wait_for_terminal(runtime, job.job_id)
    assert status == JobStatus.FAILED

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.failure_code == "pdf_unreadable"
    assert stored.failure_retryable is False


def test_pymupdf_execution_error_maps_to_internal_failure(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
        )
    )
    spec = _job_spec("paper.pdf", backend_strategy=BackendStrategy.PYMUPDF)
    job = runtime.create_job(
        spec=spec,
        upload_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        source_filename="paper.pdf",
    )

    def _raise_execution_error(_request) -> None:
        raise BackendExecutionError("simulated pymupdf execution failure")

    monkeypatch.setattr(runtime.pymupdf_backend, "convert", _raise_execution_error)
    runtime.run_job_async(job.job_id)

    status = _wait_for_terminal(runtime, job.job_id)
    assert status == JobStatus.FAILED

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.failure_code == "conversion_internal_error"
    assert stored.failure_retryable is True


def test_pymupdf_input_error_maps_to_pdf_unreadable(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
        )
    )
    spec = _job_spec("paper.pdf", backend_strategy=BackendStrategy.PYMUPDF)
    job = runtime.create_job(
        spec=spec,
        upload_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        source_filename="paper.pdf",
    )

    def _raise_input_error(_request) -> None:
        raise BackendInputError("simulated pymupdf unreadable document")

    monkeypatch.setattr(runtime.pymupdf_backend, "convert", _raise_input_error)
    runtime.run_job_async(job.job_id)

    status = _wait_for_terminal(runtime, job.job_id)
    assert status == JobStatus.FAILED

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.failure_code == "pdf_unreadable"
    assert stored.failure_retryable is False


def test_backend_gpu_unavailable_maps_to_gpu_not_available(monkeypatch, tmp_path: Path) -> None:
    available_probe = GpuRuntimeProbeResult(
        runtime_kind="rocm",
        torch_version="2.10.0+rocm7.2",
        hip_version="7.2.0",
        cuda_version=None,
        is_available=True,
        device_count=1,
        device_name="AMD Radeon AI PRO R9700",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.runtime_engine.probe_torch_gpu_runtime",
        lambda: available_probe,
    )
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=True,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
        )
    )
    spec = _job_spec("paper.pdf", acceleration_policy="gpu_required")
    job = runtime.create_job(
        spec=spec,
        upload_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        source_filename="paper.pdf",
    )

    probe = GpuRuntimeProbeResult(
        runtime_kind="none",
        torch_version="2.10.0+cu128",
        hip_version=None,
        cuda_version="12.8",
        is_available=False,
        device_count=0,
        device_name=None,
    )

    def _raise_gpu_unavailable(_request) -> None:
        raise BackendGpuUnavailableError(backend="docling", probe=probe)

    monkeypatch.setattr(runtime.docling_backend, "convert", _raise_gpu_unavailable)
    runtime.run_job_async(job.job_id)

    status = _wait_for_terminal(runtime, job.job_id)
    assert status == JobStatus.FAILED

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.failure_code == "gpu_not_available"
    assert stored.failure_retryable is True
    assert stored.failure_details == {
        "reason": "backend_gpu_runtime_unavailable",
        "backend": "docling",
        "runtime_kind": "none",
        "hip_version": None,
        "cuda_version": "12.8",
    }


def test_run_job_async_ignores_duplicate_active_job_id(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
        )
    )
    run_started = threading.Event()
    release_run = threading.Event()
    call_count = 0

    def _fake_run_job(job_id: str) -> None:
        nonlocal call_count
        call_count += 1
        run_started.set()
        release_run.wait(timeout=2.0)
        with runtime._lock:
            runtime._active_job_ids.discard(job_id)

    monkeypatch.setattr(runtime, "_run_job", _fake_run_job)

    runtime.run_job_async("job_duplicate_check")
    assert run_started.wait(timeout=1.0)
    runtime.run_job_async("job_duplicate_check")
    time.sleep(0.05)
    release_run.set()

    assert call_count == 1


def test_cross_runtime_same_job_only_one_execution_owner(monkeypatch, tmp_path: Path) -> None:
    shared_root = tmp_path / "shared_runtime_data"
    config = ServiceConfig(
        api_key="secret-key",
        data_root=shared_root,
        gpu_available=False,
        allow_cpu_only=True,
        processing_delay_seconds=0.01,
        enable_supervisor=False,
    )
    runtime_a = ServiceRuntime(config)
    runtime_b = ServiceRuntime(config)
    job = runtime_a.create_job(
        spec=_job_spec("paper.pdf"),
        upload_bytes=fixture_pdf_bytes("paper_alpha.pdf"),
        source_filename="paper.pdf",
    )

    count_a = {"value": 0}
    count_b = {"value": 0}
    metadata = ConversionMetadata(
        backend_used="docling",
        acceleration_used="cuda",
        ocr_enabled=False,
        table_mode=job.spec.conversion.table_mode,
        options_fingerprint="sha256:test",
    )

    def _execute_a(_job) -> tuple[str, ConversionMetadata, list[str]]:
        count_a["value"] += 1
        time.sleep(0.05)
        return ("runtime-a", metadata, [])

    def _execute_b(_job) -> tuple[str, ConversionMetadata, list[str]]:
        count_b["value"] += 1
        time.sleep(0.05)
        return ("runtime-b", metadata, [])

    monkeypatch.setattr(runtime_a, "_execute_conversion", _execute_a)
    monkeypatch.setattr(runtime_b, "_execute_conversion", _execute_b)

    runtime_a.run_job_async(job.job_id)
    runtime_b.run_job_async(job.job_id)

    status = _wait_for_terminal(runtime_a, job.job_id)
    assert status == JobStatus.SUCCEEDED
    assert count_a["value"] + count_b["value"] == 1
