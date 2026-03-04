"""Contract tests for v2 `html -> md` lifecycle behavior.

Purpose:
    Verify `html -> md` is accepted on v2 routes, supports resources uploads,
    and returns deterministic result/artifact semantics.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_api.create_app`.
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
from scripts.sir_convert_a_lot.interfaces.http_api import create_app


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
            headers={"X-API-Key": api_key, "X-Correlation-ID": "corr_html_md_poll"},
        )
        assert response.status_code == 200
        status = JobStatus(response.json()["job"]["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def test_html_to_md_lifecycle_result_and_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _stub_executor(**kwargs) -> V2ExecutionResult:
        del kwargs
        return V2ExecutionResult(
            artifact_bytes=b"# Converted from HTML\n\nBody\n",
            pipeline_used="html_to_md_v2",
            backend_used="pandoc",
            acceleration_used=None,
            warnings=["normalized_warning"],
            phase_timings_ms={},
            options_fingerprint="html_md_contract_test",
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
        "source": {"kind": "upload", "filename": "index.html", "format": "html"},
        "conversion": {
            "output_format": "md",
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }

    create_response = client.post(
        "/v2/convert/jobs?wait_seconds=0",
        headers={
            "X-API-Key": "secret-key",
            "Idempotency-Key": "idem-html-to-md-lifecycle",
            "X-Correlation-ID": "corr_html_md_create",
        },
        files={
            "file": ("index.html", b"<html><body><h1>Hello</h1></body></html>", "text/html"),
            "job_spec": (None, json.dumps(spec)),
            "resources": ("resources.zip", b"PK\x03\x04fake-zip", "application/zip"),
        },
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]

    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_html_md_result"},
    )
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["result"]["artifact"]["format"] == "md"
    assert result_payload["result"]["artifact"]["content_type"] == "text/markdown"
    assert result_payload["result"]["conversion_metadata"]["pipeline_used"] == "html_to_md_v2"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_html_md_artifact"},
    )
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("text/markdown")
    assert artifact_response.content == b"# Converted from HTML\n\nBody\n"
