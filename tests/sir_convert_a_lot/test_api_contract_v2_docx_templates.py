"""Template-selection contract tests for Sir Convert-a-Lot v2 API.

Purpose:
    Verify that DOCX template-selected conversions are accepted in v2 and
    expose template audit metadata in result payloads.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.service.create_app`.
    - Stubs `execute_v2_job_conversion` through `runtime_engine_v2`.
"""

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
            headers={"X-API-Key": api_key, "X-Correlation-ID": "corr_template_poll"},
        )
        assert response.status_code == 200
        status = JobStatus(response.json()["job"]["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def test_template_selected_md_to_docx_result_includes_template_audit_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _stub_executor(**kwargs) -> V2ExecutionResult:
        del kwargs
        return V2ExecutionResult(
            artifact_bytes=b"PK\x03\x04stub-docx-artifact",
            pipeline_used="md_to_docx_v2",
            backend_used="pandoc",
            acceleration_used=None,
            warnings=[],
            phase_timings_ms={},
            options_fingerprint="template_contract_test",
            template_id="academic-report",
            template_version="1.0.0",
            template_artifact_sha256="a" * 64,
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
        "source": {"kind": "upload", "filename": "note.md", "format": "md"},
        "conversion": {
            "output_format": "docx",
            "template": {"template_id": "academic-report", "version": "1.0.0"},
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }

    create_response = client.post(
        "/v2/convert/jobs?wait_seconds=0",
        headers={
            "X-API-Key": "secret-key",
            "Idempotency-Key": "idem-template-selected",
            "X-Correlation-ID": "corr_template_create",
        },
        files={
            "file": ("note.md", b"# Note\n\nBody\n", "text/markdown"),
            "job_spec": (None, json.dumps(spec)),
        },
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_template_result"},
    )

    assert result_response.status_code == 200
    result_payload = result_response.json()
    metadata = result_payload["result"]["conversion_metadata"]
    assert metadata["template_id"] == "academic-report"
    assert metadata["template_version"] == "1.0.0"
    assert metadata["template_artifact_sha256"] == "a" * 64

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_template_artifact"},
    )
    assert artifact_response.status_code == 200
    assert len(artifact_response.content) > 0
