"""Additional v2 contract tests for clean-break route behavior.

Purpose:
    Lock the `pdf -> md` lifecycle on v2 and assert v1 conversion endpoints are
    no longer registered after the clean-break cutover.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_api.create_app`.
    - Reuses shared helper functions from `test_api_contract_v2`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.service.test_api_contract_v2 import (
    _job_spec_v2,
    _post_create,
    _wait_for_terminal,
)


def test_pdf_to_md_lifecycle_result_and_artifact(tmp_path: Path, monkeypatch) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _successful_executor(**kwargs) -> V2ExecutionResult:
        job = kwargs["job"]
        assert job.source_format == SourceFormatV2.PDF
        assert job.output_format == OutputFormatV2.MD
        return V2ExecutionResult(
            artifact_bytes=b"# Converted from PDF\n\nBody\n",
            pipeline_used="pdf_to_md_v2",
            backend_used="docling",
            acceleration_used="cuda",
            warnings=["ocr_retry_performed"],
            phase_timings_ms={"ocr_layout_extract_ms": 12},
            options_fingerprint="contract_test_pdf_md",
            ocr_enabled=True,
            ocr_engine_used="auto",
            ocr_languages_used=["en"],
            formula_authority={
                "action": "skipped",
                "representation": "source_layer_markdown",
                "source_evidence_state": "usable",
                "vlm_attempted": False,
                "reason": "source_layer_authoritative_formula_vlm_skipped",
            },
        )

    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _successful_executor)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_fallback=True,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="paper.pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    spec["pdf_options"] = {
        "backend_strategy": "auto",
        "ocr_mode": "auto",
        "table_mode": "accurate",
        "normalize": "strict",
    }
    spec["execution"] = {
        "acceleration_policy": "gpu_required",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pdf-md-v2",
        file_name="paper.pdf",
        file_bytes=b"%PDF-1.4\n% fake\n%%EOF\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    status_response = client.get(
        f"/v2/convert/jobs/{job_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_pdf_md_status_v2"},
    )
    assert status_response.status_code == 200
    job_payload = status_response.json()["job"]
    assert job_payload["formula_authority"] == {
        "action": "skipped",
        "representation": "source_layer_markdown",
        "source_evidence_state": "usable",
        "vlm_attempted": False,
        "reason": "source_layer_authoritative_formula_vlm_skipped",
    }
    progress = job_payload["progress"]
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
    assert progress["percent_complete"] == 100.0
    assert progress["eta_seconds"] == 0

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_pdf_md_result_v2"},
    )
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["api_version"] == "v2"
    assert result_payload["result"]["artifact"]["format"] == "md"
    assert result_payload["result"]["artifact"]["content_type"] == "text/markdown"
    metadata = result_payload["result"]["conversion_metadata"]
    assert metadata["pipeline_used"] == "pdf_to_md_v2"
    assert metadata["formula_authority"] == {
        "action": "skipped",
        "representation": "source_layer_markdown",
        "source_evidence_state": "usable",
        "vlm_attempted": False,
        "reason": "source_layer_authoritative_formula_vlm_skipped",
    }
    assert metadata["ocr_enabled"] is True
    assert metadata["ocr_engine_used"] == "auto"
    assert metadata["ocr_languages_used"] == ["en"]
    legacy_requested_field = "ocr_languages_" + "requested"
    legacy_ocr_acceleration_field = "ocr_" + "acceleration_used"
    assert legacy_requested_field not in metadata
    assert legacy_ocr_acceleration_field not in metadata

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_pdf_md_artifact_v2"},
    )
    assert artifact_response.status_code == 200
    assert artifact_response.headers.get("content-type", "").startswith("text/markdown")
    assert artifact_response.text == "# Converted from PDF\n\nBody\n"


def test_pdf_to_md_no_ocr_result_uses_empty_language_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2

    def _successful_executor(**kwargs) -> V2ExecutionResult:
        job = kwargs["job"]
        assert job.source_format == SourceFormatV2.PDF
        assert job.output_format == OutputFormatV2.MD
        return V2ExecutionResult(
            artifact_bytes=b"# Converted without OCR\n\nSelectable text\n",
            pipeline_used="pdf_to_md_v2",
            backend_used="docling",
            acceleration_used="cpu",
            warnings=[],
            phase_timings_ms={"markdown_normalize_ms": 3},
            options_fingerprint="contract_test_pdf_md_no_ocr",
            ocr_enabled=False,
            ocr_engine_used=None,
            ocr_languages_used=[],
        )

    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _successful_executor)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_fallback=True,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="selectable.pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    spec["pdf_options"] = {
        "backend_strategy": "auto",
        "ocr_mode": "off",
        "table_mode": "accurate",
        "normalize": "strict",
    }
    spec["execution"] = {
        "acceleration_policy": "cpu_only",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pdf-md-no-ocr-v2",
        file_name="selectable.pdf",
        file_bytes=b"%PDF-1.4\n% fake selectable\n%%EOF\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_pdf_md_no_ocr_v2"},
    )
    assert result_response.status_code == 200
    metadata = result_response.json()["result"]["conversion_metadata"]
    assert metadata["ocr_enabled"] is False
    assert metadata["ocr_engine_used"] is None
    assert metadata["ocr_languages_used"] == []


def test_v1_conversion_routes_are_not_registered(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)
    headers = {"X-API-Key": "secret-key", "X-Correlation-ID": "corr_v1_removed"}
    registered_paths = {
        getattr(route, "path", "")
        for route in app.routes
        if isinstance(getattr(route, "path", None), str)
    }
    assert not any(path.startswith("/v1/convert/jobs") for path in registered_paths)

    create_response = client.post(
        "/v1/convert/jobs",
        headers=headers,
        files={
            "file": ("paper.pdf", b"%PDF-1.4\n% fake\n%%EOF\n", "application/pdf"),
            "job_spec": (None, "{}"),
        },
    )
    status_response = client.get("/v1/convert/jobs/job_missing", headers=headers)
    result_response = client.get("/v1/convert/jobs/job_missing/result", headers=headers)
    cancel_response = client.post("/v1/convert/jobs/job_missing/cancel", headers=headers)

    assert create_response.status_code == 404
    assert status_response.status_code == 404
    assert result_response.status_code == 404
    assert cancel_response.status_code == 404
