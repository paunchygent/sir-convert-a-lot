"""Contract tests for v2 DOCX template discovery routes.

Purpose:
    Verify list/get/version template endpoints for deterministic payload shape,
    auth handling, and not-found semantics.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_routes_templates_v2`.
    - Uses the shared FastAPI app factory from `scripts.sir_convert_a_lot.service`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_HEADERS = {
    "X-API-Key": "secret-key",
    "X-Correlation-ID": "corr_templates_v2",
}


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    return TestClient(app)


def test_list_docx_templates_requires_api_key(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/v2/templates/docx")

    assert response.status_code == 401
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "auth_invalid_api_key"


def test_list_docx_templates_returns_curated_summaries(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/v2/templates/docx", headers=_API_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v2"
    templates = payload["templates"]
    assert isinstance(templates, list)
    template_ids = {item["template_id"] for item in templates}
    assert {"academic-report", "classroom-handout", "project-week-summary"}.issubset(template_ids)


def test_get_docx_template_returns_versions(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/v2/templates/docx/academic-report", headers=_API_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["template_id"] == "academic-report"
    assert payload["versions"][0]["version"] == "1.0.0"


def test_get_docx_template_unknown_id_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/v2/templates/docx/missing-template", headers=_API_HEADERS)

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "template_not_found"
    assert payload["error"]["details"] == {"template_id": "missing-template"}


def test_get_docx_template_version_returns_record(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/v2/templates/docx/academic-report/versions/1.0.0",
        headers=_API_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["template"]["template_id"] == "academic-report"
    assert payload["template"]["version"] == "1.0.0"
    assert payload["template"]["status"] == "active"


def test_get_docx_template_unknown_version_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/v2/templates/docx/academic-report/versions/9.9.9",
        headers=_API_HEADERS,
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "template_version_not_found"
    assert payload["error"]["details"] == {
        "template_id": "academic-report",
        "version": "9.9.9",
    }
