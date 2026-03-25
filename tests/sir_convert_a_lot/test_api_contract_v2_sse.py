"""Contract tests for v2 SSE lifecycle-event streaming.

Purpose:
    Verify that v2 event emission and SSE replay semantics match the published
    async-push contract while polling behavior remains unchanged.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_routes_job_events_v2`.
    - Uses the canonical API app from `scripts.sir_convert_a_lot.service`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import encode_replay_cursor
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.interfaces.http_api import create_app


def _job_spec_v2(*, filename: str, source_format: SourceFormatV2, output_format: OutputFormatV2):
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": source_format.value},
        "conversion": {
            "output_format": output_format.value,
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }


def _post_create(
    client: TestClient,
    *,
    file_name: str,
    file_bytes: bytes,
    idempotency_key: str,
    api_key: str = "secret-key",
) -> str:
    spec = _job_spec_v2(
        filename=file_name,
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    response = client.post(
        "/v2/convert/jobs",
        headers={
            "X-API-Key": api_key,
            "Idempotency-Key": idempotency_key,
            "X-Correlation-ID": "corr_test_contract_v2_sse",
        },
        files={
            "file": (file_name, file_bytes, "text/plain"),
            "job_spec": (None, json.dumps(spec)),
        },
    )
    assert response.status_code in {200, 202}
    payload = response.json()
    job_obj = payload.get("job")
    assert isinstance(job_obj, dict)
    job_id = job_obj.get("job_id")
    assert isinstance(job_id, str)
    return job_id


def _wait_for_terminal(client: TestClient, *, job_id: str, timeout_seconds: float = 8.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/v2/convert/jobs/{job_id}",
            headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_wait_terminal"},
        )
        assert response.status_code == 200
        payload = response.json()
        job_obj = payload.get("job")
        assert isinstance(job_obj, dict)
        status_obj = job_obj.get("status")
        assert isinstance(status_obj, str)
        status = JobStatus(status_obj)
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal state before timeout")


def _stream_sse_payloads(
    client: TestClient,
    *,
    job_id: str,
    cursor: str | None = None,
    last_event_id: str | None = None,
) -> tuple[int, dict[str, str], list[dict[str, object]]]:
    params: dict[str, str] = {}
    if cursor is not None:
        params["cursor"] = cursor
    if last_event_id is not None:
        params["last_event_id"] = last_event_id

    with client.stream(
        "GET",
        f"/v2/convert/jobs/{job_id}/events/stream",
        params=params,
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_stream_contract_v2_sse"},
    ) as response:
        text = "".join(chunk for chunk in response.iter_text())
        payloads: list[dict[str, object]] = []
        for frame in text.split("\n\n"):
            block = frame.strip()
            if block == "":
                continue
            data_lines = [line[6:] for line in block.splitlines() if line.startswith("data: ")]
            if len(data_lines) != 1:
                continue
            decoded = json.loads(data_lines[0])
            assert isinstance(decoded, dict)
            payloads.append(decoded)
        return response.status_code, dict(response.headers), payloads


def _stub_executor(**kwargs) -> V2ExecutionResult:
    """Produce deterministic conversion output for SSE contract tests."""
    del kwargs
    time.sleep(0.02)
    return V2ExecutionResult(
        artifact_bytes=b"%PDF-1.4\n% sse test\n%%EOF\n",
        pipeline_used="md_to_pdf_v2",
        backend_used="stubbed",
        acceleration_used=None,
        warnings=[],
        phase_timings_ms={"conversion_total_ms": 1},
        options_fingerprint="sse-contract-stub",
        ocr_enabled=None,
        ocr_engine_used=None,
        ocr_languages_used=None,
    )


def test_sse_stream_emits_ordered_progress_and_terminal_events(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_sse_ordered",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_sse_stream=True,
            sse_poll_interval_seconds=0.01,
            sse_stream_max_seconds=3.0,
        )
    )
    client = TestClient(app)
    job_id = _post_create(
        client,
        file_name="ordered.md",
        file_bytes=b"# Ordered\n",
        idempotency_key="idem-sse-ordered",
    )

    status_code, headers, payloads = _stream_sse_payloads(client, job_id=job_id)
    assert status_code == 200
    assert headers.get("content-type", "").startswith("text/event-stream")
    assert len(payloads) >= 2

    sequences: list[int] = []
    for payload in payloads:
        sequence_obj = payload.get("sequence")
        event_id = payload.get("event_id")
        metrics_obj = payload.get("sse_metrics")
        assert isinstance(sequence_obj, int)
        assert isinstance(event_id, str)
        assert len(event_id) == 26
        assert isinstance(metrics_obj, dict)
        emit_to_send_ms = metrics_obj.get("emit_to_send_ms")
        assert isinstance(emit_to_send_ms, int)
        sequences.append(sequence_obj)
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)
    assert payloads[0].get("event_type") == "job.queued"
    assert payloads[-1].get("event_type") == "job.succeeded"
    assert payloads[-1].get("status") == "succeeded"
    for payload in payloads:
        route = payload.get("route")
        progress = payload.get("progress")
        assert isinstance(route, dict)
        assert isinstance(progress, dict)
        for key in (
            "total_pages",
            "processed_pages",
            "failed_pages",
            "percent_complete",
            "pages_per_minute",
            "eta_seconds",
        ):
            assert key in progress


def test_sse_stream_cursor_replay_resumes_from_next_event(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_sse_cursor",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_sse_stream=True,
            sse_poll_interval_seconds=0.01,
            sse_stream_max_seconds=3.0,
        )
    )
    client = TestClient(app)
    job_id = _post_create(
        client,
        file_name="cursor.md",
        file_bytes=b"# Cursor\n",
        idempotency_key="idem-sse-cursor",
    )

    first_status, _, first_payloads = _stream_sse_payloads(client, job_id=job_id)
    assert first_status == 200
    assert len(first_payloads) >= 2
    first_sequence_obj = first_payloads[0].get("sequence")
    assert isinstance(first_sequence_obj, int)

    cursor = encode_replay_cursor(sequence=first_sequence_obj)
    resumed_status, _, resumed_payloads = _stream_sse_payloads(client, job_id=job_id, cursor=cursor)
    assert resumed_status == 200
    assert resumed_payloads
    for payload in resumed_payloads:
        sequence_obj = payload.get("sequence")
        assert isinstance(sequence_obj, int)
        assert sequence_obj > first_sequence_obj


def test_sse_stream_stale_cursor_returns_410_cursor_expired(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_sse_stale_cursor",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_sse_stream=True,
            sse_replay_horizon_seconds=1,
            sse_poll_interval_seconds=0.01,
            sse_stream_max_seconds=3.0,
        )
    )
    client = TestClient(app)
    job_id = _post_create(
        client,
        file_name="stale.md",
        file_bytes=b"# Stale\n",
        idempotency_key="idem-sse-stale",
    )
    _wait_for_terminal(client, job_id=job_id)
    time.sleep(1.2)

    cursor = encode_replay_cursor(sequence=1)
    response = client.get(
        f"/v2/convert/jobs/{job_id}/events/stream",
        params={"cursor": cursor},
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_stale_cursor"},
    )

    assert response.status_code == 410
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "cursor_expired"
    details = payload["error"]["details"]
    assert isinstance(details, dict)
    assert details.get("replay_horizon_hours") == 1
    latest_cursor = details.get("latest_cursor")
    assert isinstance(latest_cursor, str)


def test_sse_stream_returns_503_when_feature_flag_disabled(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_sse_disabled",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_sse_stream=False,
        )
    )
    client = TestClient(app)
    response = client.get(
        "/v2/convert/jobs/jobv2_unknown/events/stream",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_sse_disabled"},
    )
    assert response.status_code == 503
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "push_disabled"


def test_sse_stream_hides_internal_lane_jobs_from_public_key(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            internal_api_key="internal-secret-key",
            data_root=tmp_path / "service_data_sse_internal_scope",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_sse_stream=True,
            sse_poll_interval_seconds=0.01,
            sse_stream_max_seconds=3.0,
        )
    )
    client = TestClient(app)
    job_id = _post_create(
        client,
        file_name="internal.md",
        file_bytes=b"# Internal\n",
        idempotency_key="idem-sse-internal-owner",
        api_key="internal-secret-key",
    )

    response = client.get(
        f"/v2/convert/jobs/{job_id}/events/stream",
        headers={
            "X-API-Key": "secret-key",
            "X-Correlation-ID": "corr_stream_cross_lane_public",
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_sse_stream_hides_public_lane_jobs_from_internal_key(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _stub_executor)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            internal_api_key="internal-secret-key",
            data_root=tmp_path / "service_data_sse_public_scope",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_sse_stream=True,
            sse_poll_interval_seconds=0.01,
            sse_stream_max_seconds=3.0,
        )
    )
    client = TestClient(app)
    job_id = _post_create(
        client,
        file_name="public.md",
        file_bytes=b"# Public\n",
        idempotency_key="idem-sse-public-owner",
        api_key="secret-key",
    )

    response = client.get(
        f"/v2/convert/jobs/{job_id}/events/stream",
        headers={
            "X-API-Key": "internal-secret-key",
            "X-Correlation-ID": "corr_stream_cross_lane_internal",
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"
