"""Contract tests for Sir Convert-a-Lot v1 API.

Purpose:
    Verify that endpoint behavior matches the locked v1 schema and semantics
    for auth, idempotency, async lifecycle, and error envelope handling.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.service.create_app` directly.
    - Asserts behavior documented in `docs/converters/pdf_to_md_service_api_v1.md`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.models import JobStatus
from scripts.sir_convert_a_lot.service import ServiceConfig, create_app
from tests.sir_convert_a_lot.pdf_fixtures import fixture_pdf_bytes


def _job_spec(
    *,
    filename: str,
    table_mode: str = "fast",
    acceleration_policy: str = "gpu_required",
) -> dict[str, object]:
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": table_mode,
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def _pdf_bytes(label: str) -> bytes:
    if label == "research":
        return fixture_pdf_bytes("paper_alpha.pdf")
    return fixture_pdf_bytes("paper_beta.pdf")


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
        f"/v1/convert/jobs?wait_seconds={wait_seconds}",
        headers={
            "X-API-Key": api_key,
            "Idempotency-Key": idempotency_key,
            "X-Correlation-ID": "corr_test_contract",
        },
        files={
            "file": (file_name, file_bytes, "application/pdf"),
            "job_spec": (None, json.dumps(spec)),
        },
    )


def _wait_for_terminal(
    client: TestClient, api_key: str, job_id: str, timeout_seconds: float = 20.0
) -> JobStatus:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/v1/convert/jobs/{job_id}",
            headers={"X-API-Key": api_key, "X-Correlation-ID": "corr_poll"},
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
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = client.get("/v1/convert/jobs/job_missing")

    assert response.status_code == 401
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["error"]["code"] == "auth_invalid_api_key"
    assert isinstance(payload["error"]["correlation_id"], str)
    assert isinstance(response.headers.get("X-Correlation-ID"), str)


def test_create_job_idempotency_replay_returns_same_job_id(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.25,
        )
    )
    client = TestClient(app)

    spec = _job_spec(filename="paper.pdf")
    first = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-replay",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("first"),
        spec=spec,
    )
    second = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-replay",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("first"),
        spec=spec,
    )

    assert first.status_code in {200, 202}
    assert second.status_code in {200, 202}
    assert first.json()["job"]["job_id"] == second.json()["job"]["job_id"]
    assert second.headers.get("X-Idempotent-Replay") == "true"


def test_create_job_idempotency_collision_returns_conflict(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    first_spec = _job_spec(filename="paper.pdf", table_mode="fast")
    second_spec = _job_spec(filename="paper.pdf", table_mode="accurate")

    first = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-collision",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("first"),
        spec=first_spec,
    )
    collision = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-collision",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("first"),
        spec=second_spec,
    )

    assert first.status_code in {200, 202}
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_result_endpoint_returns_inline_markdown_when_succeeded(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.1,
        )
    )
    client = TestClient(app)

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-result",
        file_name="research-paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(filename="research-paper.pdf"),
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    terminal_status = _wait_for_terminal(client, "secret-key", job_id)
    assert terminal_status == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v1/convert/jobs/{job_id}/result?inline=true",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_result"},
    )

    assert result_response.status_code == 200
    payload = result_response.json()
    assert payload["api_version"] == "v1"
    assert payload["job_id"] == job_id
    assert payload["status"] == "succeeded"
    assert isinstance(payload["result"]["artifact"]["sha256"], str)
    assert payload["result"]["conversion_metadata"]["acceleration_used"] == "cuda"
    markdown_content = payload["result"]["markdown_content"]
    assert isinstance(markdown_content, str)
    assert "fixture line one" in markdown_content.lower()


def test_pymupdf_backend_is_rejected_until_task_11(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    spec = _job_spec(filename="paper.pdf")
    conversion = spec["conversion"]
    assert isinstance(conversion, dict)
    conversion["backend_strategy"] = "pymupdf"
    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pymupdf-blocked",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=spec,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.backend_strategy",
        "reason": "backend_not_available",
        "requested": "pymupdf",
        "available": ["auto", "docling"],
    }


def test_gpu_required_returns_503_when_gpu_unavailable(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_only=False,
            allow_cpu_fallback=False,
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-gpu",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("gpu"),
        spec=_job_spec(filename="paper.pdf", acceleration_policy="gpu_required"),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "gpu_not_available"
    assert payload["error"]["retryable"] is True


def test_gpu_prefer_returns_503_when_gpu_unavailable_under_rollout_lock(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_only=False,
            allow_cpu_fallback=False,
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-gpu-prefer",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("gpu-prefer"),
        spec=_job_spec(filename="paper.pdf", acceleration_policy="gpu_prefer"),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "gpu_not_available"
    assert payload["error"]["retryable"] is True


def test_cpu_only_returns_503_when_rollout_lock_active(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_only=False,
            allow_cpu_fallback=False,
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-cpu-only-locked",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("cpu-only"),
        spec=_job_spec(filename="paper.pdf", acceleration_policy="cpu_only"),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "gpu_not_available"
    assert payload["error"]["retryable"] is True
