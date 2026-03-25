"""Cross-lane job access tests for v2 lifecycle routes.

Purpose:
    Verify that public and internal API-key lanes cannot read or mutate each
    other's jobs once trusted-bundle support introduces a second auth scope.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_routes_jobs_v2`.
    - Reuses the shared route test helpers from
      `http_routes_jobs_v2_edge_cases_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    disable_run_job_async,
    job_spec_v2,
    post_create,
)


def _html_to_pdf_spec(filename: str) -> dict[str, object]:
    return job_spec_v2(
        filename=filename,
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
    )


def _create_owned_job(
    *,
    client,
    api_key: str,
    idempotency_key: str,
) -> str:
    response = post_create(
        client,
        file_name="page.html",
        file_bytes=b"<html><body>Hello</body></html>",
        spec=_html_to_pdf_spec("page.html"),
        api_key=api_key,
        idempotency_key=idempotency_key,
    )
    assert response.status_code in {200, 202}
    return response.json()["job"]["job_id"]


@pytest.mark.parametrize(
    ("method", "path_template", "extra_headers"),
    [
        ("GET", "/v2/convert/jobs/{job_id}", {}),
        ("GET", "/v2/convert/jobs/{job_id}/result", {}),
        ("GET", "/v2/convert/jobs/{job_id}/artifact", {}),
        ("GET", "/v2/convert/jobs/{job_id}/artifact/partial", {}),
        ("GET", "/v2/convert/jobs/{job_id}/checkpoint", {}),
        ("POST", "/v2/convert/jobs/{job_id}/cancel", {}),
        ("POST", "/v2/convert/jobs/{job_id}/resume", {"Idempotency-Key": "idem-cross-lane-resume"}),
    ],
)
def test_public_key_cannot_access_internal_lane_job_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path_template: str,
    extra_headers: dict[str, str],
) -> None:
    disable_run_job_async(monkeypatch)
    client, _ = build_client(tmp_path, internal_api_key="internal-secret-key")
    job_id = _create_owned_job(
        client=client,
        api_key="internal-secret-key",
        idempotency_key="idem-cross-lane-internal-owner",
    )

    response = client.request(
        method,
        path_template.format(job_id=job_id),
        headers={
            "X-API-Key": "secret-key",
            "X-Correlation-ID": "corr_cross_lane_public_denied",
            **extra_headers,
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


@pytest.mark.parametrize(
    ("method", "path_template", "extra_headers"),
    [
        ("GET", "/v2/convert/jobs/{job_id}", {}),
        ("GET", "/v2/convert/jobs/{job_id}/result", {}),
        ("GET", "/v2/convert/jobs/{job_id}/artifact", {}),
        ("GET", "/v2/convert/jobs/{job_id}/artifact/partial", {}),
        ("GET", "/v2/convert/jobs/{job_id}/checkpoint", {}),
        ("POST", "/v2/convert/jobs/{job_id}/cancel", {}),
        ("POST", "/v2/convert/jobs/{job_id}/resume", {"Idempotency-Key": "idem-cross-lane-resume"}),
    ],
)
def test_internal_key_cannot_access_public_lane_job_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path_template: str,
    extra_headers: dict[str, str],
) -> None:
    disable_run_job_async(monkeypatch)
    client, _ = build_client(tmp_path, internal_api_key="internal-secret-key")
    job_id = _create_owned_job(
        client=client,
        api_key="secret-key",
        idempotency_key="idem-cross-lane-public-owner",
    )

    response = client.request(
        method,
        path_template.format(job_id=job_id),
        headers={
            "X-API-Key": "internal-secret-key",
            "X-Correlation-ID": "corr_cross_lane_internal_denied",
            **extra_headers,
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_public_lane_job_survives_public_api_key_rotation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path, internal_api_key="internal-secret-key")
    job_id = _create_owned_job(
        client=client,
        api_key="secret-key",
        idempotency_key="idem-public-rotation",
    )

    rotated_app = create_app(
        ServiceConfig(
            api_key="rotated-public-key",
            internal_api_key="internal-secret-key",
            data_root=app.state.runtime_v2.config.data_root,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    rotated_client = TestClient(rotated_app)

    response = rotated_client.get(
        f"/v2/convert/jobs/{job_id}",
        headers={
            "X-API-Key": "rotated-public-key",
            "X-Correlation-ID": "corr_public_rotation",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["job"]["job_id"] == job_id


def test_internal_lane_job_survives_internal_api_key_rotation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path, internal_api_key="internal-secret-key")
    job_id = _create_owned_job(
        client=client,
        api_key="internal-secret-key",
        idempotency_key="idem-internal-rotation",
    )

    rotated_app = create_app(
        ServiceConfig(
            api_key="secret-key",
            internal_api_key="rotated-internal-key",
            data_root=app.state.runtime_v2.config.data_root,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    rotated_client = TestClient(rotated_app)

    response = rotated_client.get(
        f"/v2/convert/jobs/{job_id}",
        headers={
            "X-API-Key": "rotated-internal-key",
            "X-Correlation-ID": "corr_internal_rotation",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["job"]["job_id"] == job_id
