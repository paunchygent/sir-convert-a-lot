"""Contract tests for Sir Convert-a-Lot v2 API.

Purpose:
    Verify that endpoint behavior matches the documented v2 schema and semantics
    for auth, idempotency, async lifecycle (pending/terminal), and cancellation.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.service.create_app` directly.
    - Stubs `scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2.execute_v2_job_conversion`
      to avoid requiring Pandoc/WeasyPrint in the unit test lane.
    - Asserts behavior documented in `docs/converters/multi_format_conversion_service_api_v2.md`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.service import create_app


def _job_spec_v2(*, filename: str, source_format: SourceFormatV2, output_format: OutputFormatV2):
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": source_format.value},
        "conversion": {
            "output_format": output_format.value,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }


def _post_create(
    client: TestClient,
    *,
    api_key: str,
    idempotency_key: str,
    file_name: str,
    file_bytes: bytes,
    spec: dict[str, object],
    wait_seconds: int = 0,
):
    return client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers={
            "X-API-Key": api_key,
            "Idempotency-Key": idempotency_key,
            "X-Correlation-ID": "corr_test_contract_v2",
        },
        files={
            "file": (file_name, file_bytes, "text/plain"),
            "job_spec": (None, json.dumps(spec)),
        },
    )


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
            headers={"X-API-Key": api_key, "X-Correlation-ID": "corr_poll_v2"},
        )
        assert response.status_code == 200
        status = JobStatus(response.json()["job"]["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def test_requires_api_key_with_standard_error_envelope(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    response = client.get("/v2/convert/jobs/job_missing")

    assert response.status_code == 401
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "auth_invalid_api_key"
    assert payload["error"]["correlation_id"] == response.headers.get("X-Correlation-ID")


def test_create_job_idempotency_replay_returns_same_job_id(tmp_path: Path, monkeypatch) -> None:
    def _noop_run_job_async(self: ServiceRuntimeV2, job_id: str) -> None:
        del self, job_id

    monkeypatch.setattr(ServiceRuntimeV2, "run_job_async", _noop_run_job_async)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    first = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-replay-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=spec,
    )
    second = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-replay-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=spec,
    )

    assert first.status_code in {200, 202}
    assert second.status_code in {200, 202}
    assert first.json()["job"]["job_id"] == second.json()["job"]["job_id"]
    assert second.headers.get("X-Idempotent-Replay") == "true"


def test_create_job_idempotency_collision_returns_conflict(tmp_path: Path, monkeypatch) -> None:
    def _noop_run_job_async(self: ServiceRuntimeV2, job_id: str) -> None:
        del self, job_id

    monkeypatch.setattr(ServiceRuntimeV2, "run_job_async", _noop_run_job_async)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    first_spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    second_spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
    )

    first = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-collision-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=first_spec,
    )
    collision = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-collision-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=second_spec,
    )

    assert first.status_code in {200, 202}
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_result_and_artifact_return_pending_when_job_not_terminal(
    tmp_path: Path, monkeypatch
) -> None:
    def _noop_run_job_async(self: ServiceRuntimeV2, job_id: str) -> None:
        del self, job_id

    monkeypatch.setattr(ServiceRuntimeV2, "run_job_async", _noop_run_job_async)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pending-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_result_v2"},
    )
    assert result_response.status_code == 202
    result_payload = result_response.json()
    assert result_payload["api_version"] == "v2"
    assert result_payload["job_id"] == job_id
    assert result_payload["status"] == "queued"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_artifact_v2"},
    )
    assert artifact_response.status_code == 202
    artifact_payload = artifact_response.json()
    assert artifact_payload["api_version"] == "v2"
    assert artifact_payload["job_id"] == job_id
    assert artifact_payload["status"] == "queued"


def test_result_and_artifact_return_conflict_when_job_failed(tmp_path: Path, monkeypatch) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _failing_executor(**kwargs) -> V2ExecutionResult:
        del kwargs
        raise ServiceError(
            status_code=500,
            code="conversion_failed_for_test",
            message="Intentional failure for contract test.",
            retryable=False,
        )

    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _failing_executor)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-failed-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.FAILED

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_failed_result_v2"},
    )
    assert result_response.status_code == 409
    result_payload = result_response.json()
    assert result_payload["api_version"] == "v2"
    assert result_payload["error"]["code"] == "job_not_succeeded"
    assert result_payload["error"]["details"] == {"status": "failed"}

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_failed_artifact_v2"},
    )
    assert artifact_response.status_code == 409
    artifact_payload = artifact_response.json()
    assert artifact_payload["api_version"] == "v2"
    assert artifact_payload["error"]["code"] == "job_not_succeeded"
    assert artifact_payload["error"]["details"] == {"status": "failed"}


def test_cancel_returns_202_then_200_for_already_canceled(tmp_path: Path, monkeypatch) -> None:
    def _noop_run_job_async(self: ServiceRuntimeV2, job_id: str) -> None:
        del self, job_id

    monkeypatch.setattr(ServiceRuntimeV2, "run_job_async", _noop_run_job_async)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-cancel-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    cancel_response = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_cancel_v2"},
    )
    assert cancel_response.status_code == 202
    cancel_payload = cancel_response.json()
    assert cancel_payload["api_version"] == "v2"
    assert cancel_payload["job"]["job_id"] == job_id
    assert cancel_payload["job"]["status"] == "canceled"

    already_response = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_cancel_again_v2"},
    )
    assert already_response.status_code == 200
    already_payload = already_response.json()
    assert already_payload["api_version"] == "v2"
    assert already_payload["job"]["job_id"] == job_id
    assert already_payload["job"]["status"] == "canceled"


def test_cancel_returns_conflict_for_terminal_jobs(tmp_path: Path, monkeypatch) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _successful_executor(**kwargs) -> V2ExecutionResult:
        job = kwargs["job"]
        if job.output_format == OutputFormatV2.PDF:
            artifact_bytes = b"%PDF-1.4\n% fake\n%%EOF\n"
        else:
            artifact_bytes = b"PK\x03\x04fake-docx"
        pipeline_used = f"{job.source_format.value}_to_{job.output_format.value}_v2"
        return V2ExecutionResult(
            artifact_bytes=artifact_bytes,
            pipeline_used=pipeline_used,
            backend_used="stub",
            acceleration_used=None,
            warnings=[],
            phase_timings_ms={},
            options_fingerprint="contract_test_stub",
        )

    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _successful_executor)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-cancel-terminal-v2",
        file_name="note.md",
        file_bytes=b"# Title\n\nHello.\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    cancel_response = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_cancel_terminal_v2"},
    )
    assert cancel_response.status_code == 409
    payload = cancel_response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_cancelable"
