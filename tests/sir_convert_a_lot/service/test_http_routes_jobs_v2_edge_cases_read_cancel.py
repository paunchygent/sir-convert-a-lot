"""V2 get/result/artifact/cancel route edge-case tests.

Purpose:
    Validate terminal-state, retrieval, and cancellation edge behavior for v2
    jobs routes using deterministic runtime stubs.

Relationships:
    - Tests `scripts.sir_convert_a_lot.interfaces.http_routes_jobs_v2`.
    - Reuses typed request helpers from
      `http_routes_jobs_v2_edge_cases_test_support`.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import Request

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces import http_routes_jobs_v2
from tests.sir_convert_a_lot.service.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    disable_run_job_async,
    post_create,
)


@pytest.mark.parametrize("endpoint_suffix", ["result", "artifact"])
def test_result_and_artifact_terminal_failed_return_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, endpoint_suffix: str
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    create_response = post_create(
        client,
        idempotency_key=f"idem-edge-failed-{endpoint_suffix}",
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    runtime = app.state.runtime_v2
    original_get_job = runtime.get_job
    base_job = original_get_job(job_id)
    assert base_job is not None
    failed_job = replace(base_job, status=JobStatus.FAILED)

    def _failed_job(job_id_value: str):
        if job_id_value == job_id:
            return failed_job
        return original_get_job(job_id_value)

    monkeypatch.setattr(runtime, "get_job", _failed_job)

    response = client.get(
        f"/v2/convert/jobs/{job_id}/{endpoint_suffix}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_terminal_failed"},
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_succeeded"
    assert payload["error"]["details"] == {"status": "failed", "failure_retryable": False}


def test_get_job_missing_returns_404(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = client.get(
        "/v2/convert/jobs/jobv2_missing",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_get_missing"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_get_result_missing_returns_404(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = client.get(
        "/v2/convert/jobs/jobv2_missing/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_result_missing"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_get_artifact_missing_returns_404(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = client.get(
        "/v2/convert/jobs/jobv2_missing/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_artifact_missing"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_get_result_and_artifact_success_paths_return_200(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    create_response = post_create(client, idempotency_key="idem-edge-success-result")
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    runtime = app.state.runtime_v2
    original_get_job = runtime.get_job
    base_job = original_get_job(job_id)
    assert base_job is not None

    artifact_bytes = b"%PDF-1.7\nstub\n"
    base_job.artifact_path.write_bytes(artifact_bytes)
    succeeded_job = replace(
        base_job,
        status=JobStatus.SUCCEEDED,
        artifact_sha256="deadbeef",
        artifact_size_bytes=len(artifact_bytes),
        pipeline_used="md_to_pdf_v2",
        backend_used="pandoc+weasyprint",
        acceleration_used=None,
        options_fingerprint="sha256:options",
        warnings=["quality_warning"],
    )

    def _succeeded_job(job_id_value: str):
        if job_id_value == job_id:
            return succeeded_job
        return original_get_job(job_id_value)

    monkeypatch.setattr(runtime, "get_job", _succeeded_job)

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_result_success"},
    )
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["api_version"] == "v2"
    assert result_payload["result"]["artifact"]["sha256"] == "deadbeef"
    assert result_payload["result"]["conversion_metadata"]["pipeline_used"] == "md_to_pdf_v2"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_artifact_success"},
    )
    assert artifact_response.status_code == 200
    assert artifact_response.content == artifact_bytes


def test_get_result_succeeded_missing_artifact_metadata_returns_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    create_response = post_create(client, idempotency_key="idem-edge-missing-artifact-meta")
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    runtime = app.state.runtime_v2
    original_get_job = runtime.get_job
    base_job = original_get_job(job_id)
    assert base_job is not None
    succeeded_missing_artifact = replace(
        base_job,
        status=JobStatus.SUCCEEDED,
        artifact_sha256=None,
        artifact_size_bytes=None,
    )

    def _missing_artifact_metadata(job_id_value: str):
        if job_id_value == job_id:
            return succeeded_missing_artifact
        return original_get_job(job_id_value)

    monkeypatch.setattr(runtime, "get_job", _missing_artifact_metadata)

    response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_missing_artifact_meta"},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "result_missing_artifact"


def test_get_result_succeeded_missing_conversion_metadata_returns_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    create_response = post_create(client, idempotency_key="idem-edge-missing-conversion-meta")
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    runtime = app.state.runtime_v2
    original_get_job = runtime.get_job
    base_job = original_get_job(job_id)
    assert base_job is not None
    succeeded_missing_conversion_metadata = replace(
        base_job,
        status=JobStatus.SUCCEEDED,
        artifact_sha256="deadbeef",
        artifact_size_bytes=9,
        pipeline_used=None,
        options_fingerprint=None,
    )

    def _missing_conversion_metadata(job_id_value: str):
        if job_id_value == job_id:
            return succeeded_missing_conversion_metadata
        return original_get_job(job_id_value)

    monkeypatch.setattr(runtime, "get_job", _missing_conversion_metadata)

    response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={
            "X-API-Key": "secret-key",
            "X-Correlation-ID": "corr_v2_missing_conversion_meta",
        },
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "result_missing_metadata"


def test_cancel_job_accepted_then_missing_job_returns_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _CancelRuntimeStub:
        def __init__(self, *, data_root: Path) -> None:
            self.config = ServiceConfig(
                api_key="secret-key",
                data_root=data_root,
                enable_supervisor=False,
                processing_delay_seconds=0.0,
            )

        def cancel_job(self, job_id: str) -> str:
            del job_id
            return "accepted"

        def get_job(self, job_id: str) -> None:
            del job_id
            return None

    runtime_stub = _CancelRuntimeStub(data_root=tmp_path / "stub_data")

    def _runtime_v2_stub(request: Request, *, utc_now_iso: str) -> _CancelRuntimeStub:
        del request, utc_now_iso
        return runtime_stub

    monkeypatch.setattr(http_routes_jobs_v2, "runtime_v2_for_request", _runtime_v2_stub)
    client, _ = build_client(tmp_path)

    response = client.post(
        "/v2/convert/jobs/job_cancel_gap/cancel",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_cancel_gap"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_cancel_job_missing_returns_404(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = client.post(
        "/v2/convert/jobs/jobv2_missing/cancel",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v2_cancel_missing"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"
