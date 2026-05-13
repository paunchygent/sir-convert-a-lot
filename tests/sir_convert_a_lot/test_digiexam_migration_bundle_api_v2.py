"""API tests for Task 282 DigiExam migration bundle routes.

Purpose:
    Prove that the service API v2 runtime accepts authenticated DigiExam `.dxe`
    jobs, produces deterministic named artifacts, and enforces
    InternalIdentityContextV1 owner isolation.

Relationships:
    - Exercises `interfaces.http_api` through FastAPI TestClient.
    - Covers the runtime bundle builder, QTI package integration, singular
      artifact compatibility, named artifact routes, and identity-derived
      ownership.
"""

from __future__ import annotations

import base64
import json
import time
import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from httpx import Response

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_KEY_ID = "gateway-identity-rs256-v1"
_API_KEY = "secret-key"
_FIXTURE_DIR = Path("inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types")
_EMBEDDED_IMAGE_DXE = _FIXTURE_DIR / "sanitized-embedded-image.dxe"
_ONEDRIVE_CORPUS_ROOT = Path("inputs/examples/digiexam-evidence/OneDrive_1_5-12-2026")
_LIVE_CORPUS_DXE_FILENAMES = (
    "1776888013-ak7-lag-och-ratt.dxe",
    "1790207116-23c-atom-och-karnfysik-eca.dxe",
)
_MultipartFileValue = tuple[str | None, bytes | str, str | None]
_MultipartFormValue = tuple[str | None, str]
_MultipartValue = _MultipartFileValue | _MultipartFormValue


def test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-bundle-success",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value

    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    artifact_entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert manifest["schema_version"] == "digiexam_migration_bundle_v1"
    assert manifest["source"]["format"] == "digiexam_dxe"
    assert manifest["bundle_status"] == "partial"
    assert set(artifact_entries) == {
        "bundle_manifest",
        "examnet_pdf",
        "qti_package",
        "qti_validation_report",
        "ir_json",
        "migration_manifest",
        "manual_follow_up_report",
        "warnings_report",
        "asset_summary",
    }
    assert artifact_entries["examnet_pdf"]["availability"] == "available"
    assert artifact_entries["qti_package"]["availability"] == "available"
    assert artifact_entries["qti_validation_report"]["availability"] == "available"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        assert "imsmanifest.xml" in archive.namelist()
        assert "items/item_002.xml" in archive.namelist()

    report_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_validation_report",
        headers=headers,
    )
    assert report_response.status_code == 200
    assert report_response.json()["schema_version"] == "examnet_qti_validation_report_v1"

    singular_response = client.get(f"/v2/convert/jobs/{job_id}/artifact", headers=headers)
    assert singular_response.status_code == 200
    assert singular_response.json()["schema_version"] == "digiexam_migration_bundle_v1"


def test_digiexam_migration_respects_examnet_pdf_only_target(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-examnet-pdf-only",
        wait_seconds=20,
        targets=("examnet_pdf",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "not_requested"
    assert entries["qti_validation_report"]["availability"] == "not_requested"

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 409
    assert qti_response.json()["error"]["code"] == "digiexam_artifact_not_requested"

    warnings_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/warnings_report",
        headers=headers,
    )
    assert warnings_response.status_code == 200
    assert warnings_response.json()["qti_warnings"] == []


def test_digiexam_migration_respects_qti_only_target(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-qti-only",
        wait_seconds=20,
        targets=("qti_package",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "not_requested"
    assert entries["qti_package"]["availability"] == "available"
    assert entries["qti_validation_report"]["availability"] == "available"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 409
    assert pdf_response.json()["error"]["code"] == "digiexam_artifact_not_requested"


def test_digiexam_migration_result_metadata_matches_bundle_manifest(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-result-metadata",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=headers)

    assert manifest_response.status_code == 200
    assert result_response.status_code == 200
    manifest = manifest_response.json()
    result = result_response.json()["result"]
    metadata = result["conversion_metadata"]
    target_availability = {
        entry["artifact_key"]: entry["availability"]
        for entry in manifest["artifacts"]
        if entry["artifact_key"] in {"examnet_pdf", "qti_package"}
    }

    assert metadata["route_key"] == "digiexam_dxe_to_examnet_migration_bundle"
    assert metadata["bundle_schema_version"] == manifest["schema_version"]
    assert metadata["bundle_status"] == manifest["bundle_status"]
    assert metadata["source_sha256"] == manifest["source"]["sha256"]
    assert metadata["target_availability"] == target_availability
    assert metadata["manual_follow_up_required"] == manifest["manual_follow_up"]["required"]
    assert metadata["warning_count"] == manifest["warnings"]["count"]
    assert metadata["artifact_count"] == len(manifest["artifacts"])


def test_digiexam_migration_idempotency_includes_companion_digest(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    first_parity_pdf = _pdf_bytes("first parity")
    changed_parity_pdf = _pdf_bytes("changed parity")
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", first_parity_pdf),
    )
    assert response.status_code in {200, 202}

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", first_parity_pdf),
    )
    assert replay.status_code in {200, 202}
    assert replay.headers["X-Idempotent-Replay"] == "true"

    conflict = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", changed_parity_pdf),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_digiexam_migration_blocked_pdf_target_returns_named_artifact_error(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)

    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-blocked-pdf-target",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    entries = {entry["artifact_key"]: entry for entry in manifest_response.json()["artifacts"]}
    assert entries["examnet_pdf"]["availability"] == "blocked"
    assert entries["examnet_pdf"]["blocker_code"] == "manual_answer_key_required"
    assert manifest_response.json()["manual_follow_up"]["required"] is True

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert artifact_response.status_code == 409
    assert artifact_response.json()["error"]["code"] == "manual_answer_key_required"


def test_digiexam_migration_bundle_downloads_embedded_image_pdf(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-embedded-image",
        wait_seconds=20,
        payload=_embedded_image_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        assert document.page_count == 1
        page = document[0]
        assert page.get_images(full=True)
        assert "Look at the embedded prompt image." in str(page.get_text("text", sort=True))


def test_digiexam_migration_live_onedrive_dxe_corpus_subset(tmp_path: Path) -> None:
    missing = [
        filename
        for filename in _LIVE_CORPUS_DXE_FILENAMES
        if not (_ONEDRIVE_CORPUS_ROOT / filename).exists()
    ]
    if missing:
        pytest.skip(f"local raw OneDrive `.dxe` validation files are not present: {missing}")

    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    for index, filename in enumerate(_LIVE_CORPUS_DXE_FILENAMES, start=1):
        source_path = _ONEDRIVE_CORPUS_ROOT / filename
        response = _post_digiexam_job(
            client=client,
            identity=identity,
            subject="teacher-1",
            idempotency_key=f"idem-onedrive-corpus-{index}",
            wait_seconds=20,
            source_file=(filename, source_path.read_bytes()),
        )
        assert response.status_code == 200
        job_id = response.json()["job"]["job_id"]

        manifest_response = client.get(
            f"/v2/convert/jobs/{job_id}/artifacts",
            headers=headers,
        )
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()
        entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

        assert manifest["schema_version"] == "digiexam_migration_bundle_v1"
        assert manifest["source"]["filename"] == filename
        assert manifest["source"]["format"] == "digiexam_dxe"
        assert manifest["bundle_status"] in {"complete", "partial", "blocked"}
        assert entries["qti_validation_report"]["availability"] == "available"
        assert entries["manual_follow_up_report"]["availability"] == "available"
        assert entries["asset_summary"]["availability"] == "available"


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


class _IdentitySigner:
    """Small RS256 test signer matching HuleEdu InternalIdentityContextV1."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self._private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def headers(
        self,
        *,
        subject: str,
        grants: set[str],
        audience: str = "sir-convert-a-lot",
    ) -> dict[str, str]:
        now = int(time.time())
        payload = {
            "context_version": 1,
            "iss": "api_gateway_service",
            "aud": audience,
            "sub": subject,
            "session_id": f"session-{subject}",
            "org_id": "org-1",
            "tenant_id": None,
            "roles": ["teacher"],
            "grants": sorted(grants),
            "policy_version": "2026-04-09",
            "iat": now,
            "exp": now + 60,
            "jti": f"ctx-{subject}-{now}",
            "source_app": "skriptoteket",
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "realm_subject_id": subject,
        }
        encoded = _b64url(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        signature = self._private_key.sign(
            encoded.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "X-HuleEdu-Identity-Context-Version": "1",
            "X-HuleEdu-Identity-Context": encoded,
            "X-HuleEdu-Identity-Key-Id": _KEY_ID,
            "X-HuleEdu-Identity-Signature": f"rs256={_b64url(signature)}",
        }


def _client(tmp_path: Path, identity: _IdentitySigner) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            gpu_available=False,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            internal_identity_public_keys={_KEY_ID: identity.public_key_pem},
        )
    )
    return TestClient(app)


def _headers(
    identity: _IdentitySigner,
    *,
    subject: str,
    grants: set[str],
    audience: str = "sir-convert-a-lot",
) -> dict[str, str]:
    headers = {
        "X-API-Key": _API_KEY,
        "X-Correlation-ID": f"corr-{subject}",
    }
    headers.update(identity.headers(subject=subject, grants=grants, audience=audience))
    return headers


def _post_digiexam_job(
    *,
    client: TestClient,
    identity: _IdentitySigner,
    subject: str,
    idempotency_key: str,
    wait_seconds: int = 0,
    parity_pdf: tuple[str, bytes] | None = None,
    extra_files: list[tuple[str, _MultipartFileValue]] | None = None,
    payload: dict[str, object] | None = None,
    source_file: tuple[str, bytes] | None = None,
    headers: dict[str, str] | None = None,
    targets: tuple[str, ...] = ("examnet_pdf", "qti_package"),
) -> Response:
    request_headers = headers or _headers(
        identity,
        subject=subject,
        grants={"sir-convert:jobs:create"},
    )
    request_headers["Idempotency-Key"] = idempotency_key
    file_name = source_file[0] if source_file is not None else "exam.dxe"
    file_bytes = (
        source_file[1]
        if source_file is not None
        else json.dumps(payload or _digiexam_payload()).encode("utf-8")
    )
    spec = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": file_name, "format": "digiexam_dxe"},
        "conversion": {
            "output_format": "examnet_migration_bundle",
            "targets": list(targets),
            "artifact_language": "sv",
        },
        "digiexam_migration_options": {
            "parity_pdf_filename": parity_pdf[0] if parity_pdf is not None else None,
            "result_pdf_usage": "correct_machine_marked_answers_only",
            "manual_follow_up_policy": "emit_item_addressable_report",
        },
        "retention": {"pin": False},
    }
    files: list[tuple[str, _MultipartValue]] = [
        (
            "file",
            (
                file_name,
                file_bytes,
                "application/octet-stream",
            ),
        ),
        ("job_spec", (None, json.dumps(spec))),
    ]
    if parity_pdf is not None:
        files.append(("parity_pdf", (parity_pdf[0], parity_pdf[1], "application/pdf")))
    if extra_files is not None:
        files.extend(extra_files)
    return client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers=request_headers,
        files=files,
    )


def _read_grants() -> set[str]:
    return {"sir-convert:jobs:read-own", "sir-convert:artifacts:read-own"}


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    try:
        page = doc.new_page()
        if page is None:
            raise RuntimeError("PyMuPDF returned no page")
        page.insert_text((72, 72), text, fontsize=12)
        return bytes(doc.tobytes())
    finally:
        doc.close()


def _digiexam_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Essay",
                        "about": "",
                        "bodyHTML": "<p>Explain the water cycle.</p>",
                        "images": [],
                        "maxScore": 3,
                        "type": 0,
                    },
                    {
                        "id": 2,
                        "title": "Single",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Multiple",
                        "about": "",
                        "bodyHTML": "<p>Choose the ordinal words.</p>",
                        "images": [],
                        "maxScore": 4,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "First", "about": "", "right": True},
                            {"id": 2, "title": "Between", "about": "", "right": False},
                            {"id": 3, "title": "Third", "about": "", "right": True},
                        ],
                    },
                ]
            }
        ]
    }


def _missing_answer_key_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Single without key",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": False},
                        ],
                    }
                ]
            }
        ]
    }


def _embedded_image_payload() -> dict[str, object]:
    loaded_payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    if not isinstance(loaded_payload, dict):
        raise RuntimeError("Embedded image fixture has no root object")
    payload = {str(key): value for key, value in loaded_payload.items()}
    exams = payload["exams"]
    if not isinstance(exams, list):
        raise RuntimeError("Embedded image fixture has no exams list")
    exam = exams[0]
    if not isinstance(exam, dict):
        raise RuntimeError("Embedded image fixture has no exam object")
    questions = exam["questions"]
    if not isinstance(questions, list):
        raise RuntimeError("Embedded image fixture has no questions list")
    question = questions[0]
    if not isinstance(question, dict):
        raise RuntimeError("Embedded image fixture has no question object")
    question["title"] = "Embedded image prompt"
    question["about"] = "Look at the embedded prompt image."
    question["bodyHTML"] = (
        "<p>Look at the embedded prompt image.</p>"
        '<p><img data-image-id="0" class="fr-fic fr-dib" /></p>'
    )
    question["type"] = 0
    question["blanks"] = []
    return payload
