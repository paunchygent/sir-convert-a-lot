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

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.models import JobStatus
from scripts.sir_convert_a_lot.service import ServiceConfig, create_app
from tests.sir_convert_a_lot.pdf_fixtures import (
    docling_cuda_available,
    expected_acceleration_for_gpu_requested,
    fixture_pdf_bytes,
)


def _job_spec(
    *,
    filename: str,
    table_mode: str = "fast",
    acceleration_policy: str = "gpu_required",
    backend_strategy: str = "auto",
    ocr_mode: str = "auto",
) -> dict[str, object]:
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": backend_strategy,
            "ocr_mode": ocr_mode,
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
            gpu_available=False,
            allow_cpu_fallback=True,
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
            gpu_available=False,
            allow_cpu_fallback=True,
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


@pytest.mark.skipif(
    not docling_cuda_available(),
    reason="Docling success-path contract tests require a GPU runtime.",
)
def test_result_endpoint_returns_inline_markdown_when_succeeded(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_fallback=True,
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
    assert payload["result"]["conversion_metadata"]["backend_used"] == "docling"
    assert (
        payload["result"]["conversion_metadata"]["acceleration_used"]
        == expected_acceleration_for_gpu_requested()
    )
    markdown_content = payload["result"]["markdown_content"]
    assert isinstance(markdown_content, str)
    assert "fixture line one" in markdown_content.lower()


@pytest.mark.skipif(
    not docling_cuda_available(),
    reason="Docling success-path contract tests require a GPU runtime.",
)
def test_explicit_docling_backend_strategy_succeeds_and_reports_docling(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_fallback=True,
            processing_delay_seconds=0.1,
        )
    )
    client = TestClient(app)

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-result-docling",
        file_name="research-paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(filename="research-paper.pdf", backend_strategy="docling"),
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    terminal_status = _wait_for_terminal(client, "secret-key", job_id)
    assert terminal_status == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v1/convert/jobs/{job_id}/result?inline=true",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_result_docling"},
    )
    assert result_response.status_code == 200
    payload = result_response.json()
    metadata = payload["result"]["conversion_metadata"]
    assert metadata["backend_used"] == "docling"
    assert metadata["acceleration_used"] == expected_acceleration_for_gpu_requested()


def test_docling_gpu_runtime_unavailable_returns_deterministic_503(
    monkeypatch, tmp_path: Path
) -> None:
    probe = GpuRuntimeProbeResult(
        runtime_kind="none",
        torch_version="2.10.0+cu128",
        hip_version=None,
        cuda_version="12.8",
        is_available=False,
        device_count=0,
        device_name=None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.infrastructure.runtime_engine.probe_torch_gpu_runtime",
        lambda: probe,
    )
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=True,
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-docling-gpu-runtime-unavailable",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="auto",
            ocr_mode="off",
            acceleration_policy="gpu_required",
        ),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "gpu_not_available"
    assert payload["error"]["retryable"] is True
    assert payload["error"]["details"] == {
        "reason": "backend_gpu_runtime_unavailable",
        "backend": "docling",
        "runtime_kind": "none",
        "hip_version": None,
        "cuda_version": "12.8",
    }


def test_pymupdf_gpu_required_is_rejected_with_compatibility_error(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pymupdf-gpu-required",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="pymupdf",
            ocr_mode="off",
            acceleration_policy="gpu_required",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.backend_strategy",
        "reason": "backend_incompatible_with_gpu_policy",
    }


def test_pymupdf_gpu_prefer_is_rejected_with_compatibility_error(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pymupdf-gpu-prefer",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="pymupdf",
            ocr_mode="off",
            acceleration_policy="gpu_prefer",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.backend_strategy",
        "reason": "backend_incompatible_with_gpu_policy",
    }


def test_pymupdf_ocr_mode_force_is_rejected(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pymupdf-ocr-force",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="pymupdf",
            ocr_mode="force",
            acceleration_policy="cpu_only",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.ocr_mode",
        "reason": "backend_option_incompatible",
        "backend": "pymupdf",
        "supported": ["off"],
    }


def test_pymupdf_ocr_mode_auto_is_rejected(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pymupdf-ocr-auto",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="pymupdf",
            ocr_mode="auto",
            acceleration_policy="cpu_only",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.ocr_mode",
        "reason": "backend_option_incompatible",
        "backend": "pymupdf",
        "supported": ["off"],
    }


def test_pymupdf_cpu_only_succeeds_when_cpu_unlock_enabled(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_only=True,
            allow_cpu_fallback=False,
            processing_delay_seconds=0.05,
        )
    )
    client = TestClient(app)

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pymupdf-cpu-only",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="pymupdf",
            ocr_mode="off",
            acceleration_policy="cpu_only",
        ),
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    terminal_status = _wait_for_terminal(client, "secret-key", job_id)
    assert terminal_status == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v1/convert/jobs/{job_id}/result?inline=true",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_result_pymupdf"},
    )
    assert result_response.status_code == 200
    payload = result_response.json()
    metadata = payload["result"]["conversion_metadata"]
    assert metadata["backend_used"] == "pymupdf"
    assert metadata["acceleration_used"] == "cpu"
    assert metadata["ocr_enabled"] is False


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


def test_job_status_exposes_heartbeat_and_phase_timings(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_only=True,
            processing_delay_seconds=0.01,
            heartbeat_interval_seconds=0.02,
        )
    )
    client = TestClient(app)

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-diagnostics-fields",
        file_name="paper.pdf",
        file_bytes=_pdf_bytes("research"),
        spec=_job_spec(
            filename="paper.pdf",
            backend_strategy="pymupdf",
            ocr_mode="off",
            acceleration_policy="cpu_only",
        ),
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    terminal = _wait_for_terminal(client, "secret-key", job_id)
    assert terminal == JobStatus.SUCCEEDED

    status_response = client.get(
        f"/v1/convert/jobs/{job_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_diag"},
    )
    assert status_response.status_code == 200
    progress = status_response.json()["job"]["progress"]
    assert isinstance(progress["phase_timings_ms"], dict)
    assert isinstance(progress["last_heartbeat_at"], str)
    assert isinstance(progress["current_phase_started_at"], str)


def test_readyz_reports_ready_for_matching_revision_profile_and_data_root(
    monkeypatch, tmp_path: Path
) -> None:
    service_data = tmp_path / "service_data"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "rev_ready")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_ready")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", service_data.as_posix())

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=service_data,
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
        ),
        service_profile="prod",
        expected_service_profile="prod",
    )
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["service_revision"] == "rev_ready"
    assert payload["expected_revision"] == "rev_ready"
    assert payload["service_profile"] == "prod"
    assert payload["reasons"] == []


def test_readyz_fails_closed_on_stale_revision(monkeypatch, tmp_path: Path) -> None:
    service_data = tmp_path / "service_data"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "rev_old")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_new")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", service_data.as_posix())

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=service_data,
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
        ),
        service_profile="prod",
        expected_service_profile="prod",
    )
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    reasons = response.json()["reasons"]
    assert any(reason["code"] == "stale_revision" for reason in reasons)


def test_readyz_fails_when_profile_mismatches_expected_profile(monkeypatch, tmp_path: Path) -> None:
    service_data = tmp_path / "service_data"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "rev_profile")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_profile")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", service_data.as_posix())

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=service_data,
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
        ),
        service_profile="prod",
        expected_service_profile="eval",
    )
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    reasons = response.json()["reasons"]
    assert any(reason["code"] == "profile_mismatch" for reason in reasons)


def test_readyz_fails_when_prod_eval_data_roots_collide(monkeypatch, tmp_path: Path) -> None:
    shared_root = tmp_path / "shared_data"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "rev_roots")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_roots")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", shared_root.as_posix())
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EVAL_DATA_DIR", shared_root.as_posix())

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=shared_root,
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
        ),
        service_profile="eval",
        expected_service_profile="eval",
    )
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    reasons = response.json()["reasons"]
    assert any(reason["code"] == "data_root_configuration_collision" for reason in reasons)


def test_readyz_uses_startup_cached_expected_revision(monkeypatch, tmp_path: Path) -> None:
    service_data = tmp_path / "service_data"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "rev_cached")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_cached")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", service_data.as_posix())

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=service_data,
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
        ),
        service_profile="prod",
        expected_service_profile="prod",
    )
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_changed_after_startup")

    client = TestClient(app)
    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["expected_revision"] == "rev_cached"


def test_metrics_endpoint_exposes_http_metrics(monkeypatch, tmp_path: Path) -> None:
    service_data = tmp_path / "service_data"
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "rev_metrics")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "rev_metrics")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", service_data.as_posix())

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=service_data,
            enable_supervisor=False,
            gpu_available=False,
            allow_cpu_only=True,
        ),
        service_profile="prod",
        expected_service_profile="prod",
    )
    client = TestClient(app)

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert "text/plain" in metrics_response.headers.get("content-type", "")
    content = metrics_response.text
    assert "sir_convert_a_lot_http_requests_total" in content
    assert "sir_convert_a_lot_http_request_duration_seconds" in content
    assert 'path="/healthz"' in content
