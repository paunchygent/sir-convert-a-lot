"""API tests for DigiExam migration access-control behavior.

Purpose:
    Cover InternalIdentityContextV1 audience/owner enforcement and companion
    upload rejection for DigiExam migration jobs.

Relationships:
    - Exercises the v2 DigiExam migration route through shared API fixtures.
    - Keeps authorization behavior separate from artifact-generation tests.
"""

from __future__ import annotations

from pathlib import Path

from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _API_KEY,
    _client,
    _headers,
    _IdentitySigner,
    _post_digiexam_job,
    _read_grants,
)


def test_digiexam_migration_rejects_wrong_identity_audience(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(
        identity,
        subject="teacher-1",
        grants={"sir-convert:jobs:create"},
        audience="skriptoteket",
    )
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-wrong-audience",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_invalid_internal_identity"
    assert response.json()["error"]["details"]["reason"] == "invalid_internal_identity_audience"


def test_digiexam_migration_user_owner_cannot_be_read_by_another_user(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-cross-owner",
        wait_seconds=20,
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]

    other_headers = _headers(identity, subject="teacher-2", grants=_read_grants())
    status_response = client.get(f"/v2/convert/jobs/{job_id}", headers=other_headers)
    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=other_headers,
    )

    assert status_response.status_code == 403
    assert status_response.json()["error"]["code"] == "job_access_denied"
    assert artifact_response.status_code == 403
    assert artifact_response.json()["error"]["code"] == "artifact_access_denied"


def test_digiexam_migration_rejects_api_key_only_user_originated_create(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-api-key-only",
        headers={
            "X-API-Key": _API_KEY,
            "Idempotency-Key": "idem-api-key-only",
            "X-Correlation-ID": "corr-api-key-only",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_invalid_internal_identity"


def test_digiexam_migration_rejects_generic_resources_companion(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-generic-resource",
        extra_files=[("resources", ("resources.zip", b"not-a-real-zip", "application/zip"))],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "digiexam_companion_unsupported"
    assert response.json()["error"]["details"]["unsupported_parts"] == ["resources"]
