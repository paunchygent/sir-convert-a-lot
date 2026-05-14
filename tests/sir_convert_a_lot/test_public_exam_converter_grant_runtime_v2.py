"""Runtime tests for public Exam Converter grant access.

Purpose:
    Prove that Sir Convert verifies HuleEdu public grants, creates
    public-grant-owned DigiExam migration jobs, and gates artifact reads behind
    exact public artifact-read leases.

Relationships:
    - Exercises service API v2 through FastAPI `TestClient`.
    - Covers Task 292 public grant verifier and read-lease runtime behavior.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from httpx import Response

from scripts.sir_convert_a_lot.application.public_exam_converter_access_policy_v2 import (
    PublicExamConverterAccessProfileV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import (
    PublicExamConverterRuntimeAccessConfig,
    ServiceConfig,
)
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_KEY = "secret-key"
_KEY_ID = "gateway-identity-rs256-v1"
_LEASE_SECRET = "public-artifact-read-lease-secret"


def test_public_exam_converter_grant_submit_poll_manifest_and_download(
    tmp_path: Path,
) -> None:
    signer = _PublicGrantSigner()
    client = _client(tmp_path=tmp_path, signer=signer)

    response = _post_public_digiexam_job(
        client=client,
        signer=signer,
        idempotency_key="idem-public-success",
        targets=("examnet_pdf",),
        wait_seconds=20,
    )

    assert response.status_code == 200
    body = response.json()
    job_id = body["job"]["job_id"]
    manifest_lease = body["public_artifact_read_lease"]["token"]

    grant_headers = _public_headers(signer=signer, targets=("examnet_pdf",))
    status_response = client.get(f"/v2/convert/jobs/{job_id}", headers=grant_headers)
    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=grant_headers)
    manifest_without_lease = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=grant_headers,
    )

    assert status_response.status_code == 200
    assert result_response.status_code == 200
    assert manifest_without_lease.status_code == 401
    assert manifest_without_lease.json()["error"]["code"] == "public_artifact_read_lease_required"

    manifest_headers = dict(grant_headers)
    manifest_headers["X-Public-Artifact-Read-Lease"] = manifest_lease
    manifest_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=manifest_headers,
    )

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    artifact_entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    exact_pdf_lease = artifact_entries["examnet_pdf"]["public_artifact_read_lease"]["token"]

    wrong_lease_download = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=manifest_headers,
    )
    assert wrong_lease_download.status_code == 403
    assert wrong_lease_download.json()["error"]["code"] == "public_artifact_read_lease_denied"

    pdf_headers = dict(grant_headers)
    pdf_headers["X-Public-Artifact-Read-Lease"] = exact_pdf_lease
    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=pdf_headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


def test_public_exam_converter_grant_rejects_uncovered_target(tmp_path: Path) -> None:
    signer = _PublicGrantSigner()
    client = _client(tmp_path=tmp_path, signer=signer)

    response = _post_public_digiexam_job(
        client=client,
        signer=signer,
        idempotency_key="idem-public-wrong-target",
        grant_targets=("qti_package",),
        targets=("examnet_pdf",),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "public_grant_target_not_allowed"


def test_public_exam_converter_grant_rejects_untrusted_signing_key(tmp_path: Path) -> None:
    trusted_signer = _PublicGrantSigner()
    untrusted_signer = _PublicGrantSigner()
    client = _client(tmp_path=tmp_path, signer=trusted_signer)

    response = _post_public_digiexam_job(
        client=client,
        signer=untrusted_signer,
        idempotency_key="idem-public-untrusted-key",
        targets=("examnet_pdf",),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "public_grant_untrusted"


class _PublicGrantSigner:
    """Small RS256 signer matching HuleEdu PublicConversionGrantV1."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self._private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def grant(
        self,
        *,
        upload_digest: str,
        targets: tuple[str, ...],
        audience: str = "sir-convert-a-lot",
    ) -> str:
        now = int(time.time())
        payload = {
            "grant_version": 1,
            "iss": "api_gateway_service",
            "aud": audience,
            "source_app": "skriptoteket",
            "capability": "documents.conversion_hub.exam_converter",
            "route_key": "digiexam_dxe_to_examnet_migration_bundle",
            "source_format": "digiexam_dxe",
            "output_format": "examnet_migration_bundle",
            "allowed_targets": list(targets),
            "upload_digest": upload_digest,
            "policy_version": "public-exam-converter-2026-05-13",
            "policy_profile_id": "skriptoteket-public-exam-converter-v1",
            "max_upload_bytes": 209_715_200,
            "allowed_mime_types": ["application/octet-stream", "application/pdf"],
            "request_time_budget_seconds": 300,
            "artifact_ttl_seconds": 86_400,
            "artifact_read_lease_seconds": 1800,
            "rate_limit_profile_id": "public-exam-converter-standard",
            "concurrency_profile_id": "public-exam-converter-standard",
            "correlation_id": "corr-public-exam-converter",
            "iat": now,
            "exp": now + 300,
            "jti": f"pcg_{hashlib.sha256(upload_digest.encode()).hexdigest()[:24]}",
        }
        return self._signed_jwt(payload)

    def _signed_jwt(self, payload: dict[str, object]) -> str:
        header = {"alg": "RS256", "kid": _KEY_ID, "typ": "JWT"}
        header_segment = _b64url(json.dumps(header, sort_keys=True).encode("utf-8"))
        payload_segment = _b64url(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        signature = self._private_key.sign(
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return f"{header_segment}.{payload_segment}.{_b64url(signature)}"


def _client(*, tmp_path: Path, signer: _PublicGrantSigner) -> TestClient:
    profile = PublicExamConverterAccessProfileV2()
    app = create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            gpu_available=False,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            public_exam_converter_access=PublicExamConverterRuntimeAccessConfig(
                profile=profile,
                grant_public_keys={_KEY_ID: signer.public_key_pem},
                artifact_read_lease_secret=_LEASE_SECRET,
            ),
        )
    )
    return TestClient(app)


def _post_public_digiexam_job(
    *,
    client: TestClient,
    signer: _PublicGrantSigner,
    idempotency_key: str,
    targets: tuple[str, ...],
    grant_targets: tuple[str, ...] | None = None,
    wait_seconds: int = 0,
) -> Response:
    file_bytes = json.dumps(_digiexam_payload()).encode("utf-8")
    headers = _public_headers(
        signer=signer,
        targets=grant_targets or targets,
        upload_digest=_upload_digest(file_bytes),
    )
    headers["Idempotency-Key"] = idempotency_key
    spec = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "exam.dxe", "format": "digiexam_dxe"},
        "conversion": {
            "output_format": "examnet_migration_bundle",
            "targets": list(targets),
            "artifact_language": "sv",
        },
        "digiexam_migration_options": {
            "result_pdf_usage": "correct_machine_marked_answers_only",
            "manual_follow_up_policy": "emit_item_addressable_report",
        },
        "retention": {"pin": False},
    }
    return client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers=headers,
        files=[
            ("file", ("exam.dxe", file_bytes, "application/octet-stream")),
            ("job_spec", (None, json.dumps(spec))),
        ],
    )


def _public_headers(
    *,
    signer: _PublicGrantSigner,
    targets: tuple[str, ...],
    upload_digest: str | None = None,
) -> dict[str, str]:
    digest = upload_digest or _upload_digest(json.dumps(_digiexam_payload()).encode("utf-8"))
    return {
        "X-API-Key": _API_KEY,
        "X-Correlation-ID": "corr-public-exam-converter",
        "X-Public-Conversion-Grant": signer.grant(upload_digest=digest, targets=targets),
    }


def _upload_digest(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _digiexam_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
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
                    }
                ]
            }
        ]
    }
