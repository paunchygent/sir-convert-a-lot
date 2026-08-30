"""Generic HuleEdu internal-identity helpers for service route tests."""

from __future__ import annotations

import base64
import json
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

API_KEY = "secret-key"
KEY_ID = "gateway-identity-rs256-v1"


class IdentitySigner:
    """Create signed HuleEdu identity headers for authenticated service tests."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key_pem = (
            self._private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

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
            "X-HuleEdu-Identity-Key-Id": KEY_ID,
            "X-HuleEdu-Identity-Signature": f"rs256={_b64url(signature)}",
        }


def headers(
    identity: IdentitySigner,
    *,
    subject: str,
    grants: set[str],
    audience: str = "sir-convert-a-lot",
) -> dict[str, str]:
    request_headers = {
        "X-API-Key": API_KEY,
        "X-Correlation-ID": f"corr-{subject}",
    }
    request_headers.update(identity.headers(subject=subject, grants=grants, audience=audience))
    return request_headers


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
