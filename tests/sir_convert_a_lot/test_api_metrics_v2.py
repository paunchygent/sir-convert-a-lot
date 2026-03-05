"""Contract tests for v2 runtime metrics exposure and label cardinality safety.

Purpose:
    Verify `/metrics` exposes v2 telemetry with bounded labels and without
    per-job identifiers while preserving job-level timing visibility via status.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_api.create_app`.
    - Stubs `execute_v2_job_conversion` to emit deterministic timing/warning data.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.interfaces.http_api import create_app


def _job_spec_v2(*, filename: str) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": SourceFormatV2.MD.value},
        "conversion": {
            "output_format": OutputFormatV2.PDF.value,
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }


def _post_create(client: TestClient, *, file_name: str, idempotency_key: str) -> str:
    response = client.post(
        "/v2/convert/jobs?wait_seconds=0",
        headers={
            "X-API-Key": "secret-key",
            "Idempotency-Key": idempotency_key,
            "X-Correlation-ID": f"corr_{idempotency_key}",
        },
        files={
            "file": (file_name, b"# Metrics test\n", "text/markdown"),
            "job_spec": (None, json.dumps(_job_spec_v2(filename=file_name))),
        },
    )
    assert response.status_code == 202
    payload = response.json()
    return str(payload["job"]["job_id"])


def _wait_for_terminal(
    client: TestClient,
    *,
    job_id: str,
    timeout_seconds: float = 8.0,
) -> JobStatus:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/v2/convert/jobs/{job_id}",
            headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_metrics_poll"},
        )
        assert response.status_code == 200
        status = JobStatus(response.json()["job"]["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def _stub_executor(**kwargs) -> V2ExecutionResult:
    del kwargs
    return V2ExecutionResult(
        artifact_bytes=b"%PDF-1.4\n% metrics test\n%%EOF\n",
        pipeline_used="md_to_pdf_v2",
        backend_used="pandoc+weasyprint",
        acceleration_used="cpu",
        warnings=["docling_auto_ocr_retry_applied"],
        phase_timings_ms={
            "backend_convert_ms": 12,
            "normalize_ms": 5,
            "conversion_attempt_ms": 20,
        },
        options_fingerprint="metrics-contract-stub",
    )


def _stub_executor_failure(**kwargs) -> V2ExecutionResult:
    del kwargs
    raise ServiceError(
        status_code=503,
        code="gpu_not_available",
        message="GPU runtime unavailable for benchmarked conversion.",
        retryable=True,
        details={"reason": "backend_gpu_runtime_unavailable"},
    )


def test_metrics_exposes_bounded_v2_runtime_telemetry_without_job_id_labels(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_metrics",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    first_job_id = _post_create(
        client,
        file_name="metrics-01.md",
        idempotency_key="idem-metrics-01",
    )
    second_job_id = _post_create(
        client,
        file_name="metrics-02.md",
        idempotency_key="idem-metrics-02",
    )

    assert _wait_for_terminal(client, job_id=first_job_id) == JobStatus.SUCCEEDED
    assert _wait_for_terminal(client, job_id=second_job_id) == JobStatus.SUCCEEDED

    status_payload = client.get(
        f"/v2/convert/jobs/{first_job_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_metrics_status"},
    ).json()
    progress = status_payload["job"]["progress"]
    phase_timings = progress["phase_timings_ms"]
    assert "ocr_layout_extract_ms" in phase_timings
    assert "markdown_normalize_ms" in phase_timings
    assert "conversion_total_ms" in phase_timings
    assert "final_artifact_persist_ms" in phase_timings
    assert "backend_convert_ms" not in phase_timings
    assert "normalize_ms" not in phase_timings
    assert "conversion_attempt_ms" not in phase_timings
    assert "persist_ms" not in phase_timings

    result_payload = client.get(
        f"/v2/convert/jobs/{first_job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_metrics_result"},
    ).json()
    conversion_metadata = result_payload["result"]["conversion_metadata"]
    assert conversion_metadata["acceleration_policy_requested"] is None
    assert conversion_metadata["gpu_runtime_kind"] is None
    assert conversion_metadata["gpu_device_count"] is None
    assert conversion_metadata["gpu_busy_percent"] is None
    assert conversion_metadata["gpu_memory_used_percent"] is None

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    metrics_text = metrics_response.text
    assert "sir_convert_a_lot_v2_jobs_active" in metrics_text
    assert "sir_convert_a_lot_v2_jobs_queued" in metrics_text
    assert "sir_convert_a_lot_v2_worker_saturation_ratio" in metrics_text
    assert "sir_convert_a_lot_v2_gpu_concurrency_cap" in metrics_text
    assert "sir_convert_a_lot_v2_jobs_terminal_total" in metrics_text
    assert "sir_convert_a_lot_v2_stage_duration_seconds" in metrics_text
    assert "sir_convert_a_lot_v2_job_retries_total" in metrics_text
    assert 'retry_kind="ocr_auto"' in metrics_text
    assert 'acceleration_policy="none"' in metrics_text

    assert "job_id=" not in metrics_text
    assert first_job_id not in metrics_text
    assert second_job_id not in metrics_text


def test_metrics_exposes_failed_terminal_counts_without_job_id_labels(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor_failure)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_metrics_failed",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    failed_job_id = _post_create(
        client,
        file_name="metrics-failed.md",
        idempotency_key="idem-metrics-failed",
    )

    assert _wait_for_terminal(client, job_id=failed_job_id) == JobStatus.FAILED
    metrics_text = client.get("/metrics").text
    assert 'status="failed"' in metrics_text
    assert "sir_convert_a_lot_v2_jobs_terminal_total" in metrics_text
    assert "sir_convert_a_lot_v2_stage_duration_seconds" in metrics_text
    assert "job_id=" not in metrics_text
    assert failed_job_id not in metrics_text
