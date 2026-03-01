"""Contract tests for v2 `docx -> pdf` lifecycle behavior."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.service import create_app


def _wait_for_terminal(
    client: TestClient,
    api_key: str,
    job_id: str,
    timeout_seconds: float = 10.0,
) -> JobStatus:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/v2/convert/jobs/{job_id}",
            headers={"X-API-Key": api_key, "X-Correlation-ID": "corr_docx_pdf_poll"},
        )
        assert response.status_code == 200
        status = JobStatus(response.json()["job"]["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def test_docx_to_pdf_lifecycle_result_and_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _stub_executor(**kwargs) -> V2ExecutionResult:
        del kwargs
        return V2ExecutionResult(
            artifact_bytes=b"%PDF-1.7\nstub\n",
            pipeline_used="docx_to_pdf_v2",
            backend_used="pandoc+weasyprint",
            acceleration_used=None,
            warnings=[],
            phase_timings_ms={},
            options_fingerprint="docx_pdf_contract_test",
        )

    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "input.docx", "format": "docx"},
        "conversion": {
            "output_format": "pdf",
            "template": None,
            "css_filenames": [],
            "pdf_layout": {"paper_size": "a4", "orientation": "portrait", "margins_mm": 12},
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }

    create_response = client.post(
        "/v2/convert/jobs?wait_seconds=0",
        headers={
            "X-API-Key": "secret-key",
            "Idempotency-Key": "idem-docx-to-pdf-lifecycle",
            "X-Correlation-ID": "corr_docx_pdf_create",
        },
        files={
            "file": (
                "input.docx",
                b"PK\x03\x04fake-docx-content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            "job_spec": (None, json.dumps(spec)),
        },
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_docx_pdf_result"},
    )
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["result"]["artifact"]["format"] == "pdf"
    assert result_payload["result"]["artifact"]["content_type"] == "application/pdf"
    assert result_payload["result"]["conversion_metadata"]["pipeline_used"] == "docx_to_pdf_v2"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_docx_pdf_artifact"},
    )
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("application/pdf")
    assert artifact_response.content.startswith(b"%PDF-")
