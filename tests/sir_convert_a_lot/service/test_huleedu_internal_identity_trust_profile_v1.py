"""HuleEdu internal identity trust-profile acceptance tests.

Purpose:
    Prove Sir Convert consumes HuleEdu's sanitized
    `InternalIdentityContextV1` trust profile through runtime configuration and
    the existing signed identity verifier.

Relationships:
    - Exercises `infrastructure.runtime_config.service_config_from_env`.
    - Exercises `interfaces.http_internal_identity_v2` as the canonical
      verifier path for HuleEdu-signed identity contexts.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from starlette.datastructures import Headers

from scripts.sir_convert_a_lot.infrastructure.runtime_config import service_config_from_env
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.interfaces.http_internal_identity_v2 import (
    require_verified_internal_identity_v2,
)

_KEY_ID = "gateway-identity-rs256-v1"
_ISSUER = "api_gateway_service"
_AUDIENCE = "sir-convert-a-lot"
_ENVIRONMENT_ID = "local-auth-integration"
_TRUSTED_PUBLIC_KEY_SOURCE = (
    "huleedu-repo:secrets/local-runtime/internal-identity/gateway-internal-identity-public-key.pem"
)
_INTERNAL_IDENTITY_ENV_NAMES = (
    "HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON",
    "HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_PATH",
    "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON",
    "HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID",
    "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY",
    "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH",
    "HULEEDU_INTERNAL_IDENTITY_AUDIENCE",
    "HULEEDU_INTERNAL_IDENTITY_ISSUER",
    "HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS",
    "HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS",
)


def test_huleedu_trust_profile_acceptance_smoke_accepts_content_safe_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_internal_identity_env(monkeypatch)
    signer = _TrustProfileProbeSigner()
    _configure_profile_env(monkeypatch, tmp_path, signer)

    config = service_config_from_env()

    trust_profile = config.internal_identity_trust_profile
    assert trust_profile is not None
    assert trust_profile.environment_id == _ENVIRONMENT_ID
    assert trust_profile.issuer == _ISSUER
    assert trust_profile.audience == _AUDIENCE
    assert trust_profile.key_id == _KEY_ID
    assert trust_profile.trusted_public_key_source == _TRUSTED_PUBLIC_KEY_SOURCE
    assert trust_profile.spki_sha256_fingerprint == signer.spki_sha256_fingerprint
    assert trust_profile.ttl_seconds == 60
    assert trust_profile.allowed_clock_skew_seconds == 5
    assert config.internal_identity_expected_issuer == _ISSUER
    assert config.internal_identity_expected_audience == _AUDIENCE
    assert config.internal_identity_ttl_seconds == 60
    assert config.internal_identity_allowed_clock_skew_seconds == 5

    verified = require_verified_internal_identity_v2(
        headers=Headers(signer.headers(subject="probe-subject")),
        config=config,
    )

    assert verified.context.sub == "probe-subject"
    assert verified.grants == frozenset({"sir-convert:jobs:create"})
    evidence = _sanitized_acceptance_evidence(config, accepted=True)
    assert evidence == {
        "accepted": True,
        "audience": _AUDIENCE,
        "environment_id": _ENVIRONMENT_ID,
        "issuer": _ISSUER,
        "key_id": _KEY_ID,
        "skew_seconds": 5,
        "spki_sha256_fingerprint": signer.spki_sha256_fingerprint,
        "trusted_public_key_source": _TRUSTED_PUBLIC_KEY_SOURCE,
        "ttl_seconds": 60,
    }
    serialized_evidence = json.dumps(evidence, sort_keys=True)
    assert "X-HuleEdu-Identity-Context" not in serialized_evidence
    assert "rs256=" not in serialized_evidence
    assert "PRIVATE KEY" not in serialized_evidence


def test_huleedu_trust_profile_rejects_missing_public_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_internal_identity_env(monkeypatch)
    signer = _TrustProfileProbeSigner()
    monkeypatch.setenv("HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON", signer.profile_json())

    with pytest.raises(ValueError, match="requires a configured public key"):
        service_config_from_env()


def test_huleedu_trust_profile_rejects_canonical_spki_fingerprint_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_internal_identity_env(monkeypatch)
    signer = _TrustProfileProbeSigner()
    _configure_profile_env(
        monkeypatch,
        tmp_path,
        signer,
        profile_fingerprint="0" * 64,
    )

    with pytest.raises(ValueError, match="SPKI SHA-256 fingerprint mismatch"):
        service_config_from_env()


def test_huleedu_trust_profile_rejects_pem_file_byte_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_internal_identity_env(monkeypatch)
    signer = _TrustProfileProbeSigner()
    _configure_profile_env(
        monkeypatch,
        tmp_path,
        signer,
        profile_fingerprint=signer.pem_file_sha256_fingerprint,
    )

    with pytest.raises(ValueError, match="SPKI SHA-256 fingerprint mismatch"):
        service_config_from_env()


def test_huleedu_trust_profile_rejects_unknown_key_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config, signer = _configured_service_config(monkeypatch, tmp_path)

    reason = _verification_failure_reason(
        config,
        signer.headers(subject="unknown-key", key_id="gateway-identity-rs256-v2"),
    )

    assert reason == "unknown_internal_identity_key_id"


def test_huleedu_trust_profile_rejects_invalid_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config, _signer = _configured_service_config(monkeypatch, tmp_path)
    impostor = _TrustProfileProbeSigner()

    reason = _verification_failure_reason(config, impostor.headers(subject="bad-signature"))

    assert reason == "invalid_internal_identity_signature"


def test_huleedu_trust_profile_rejects_wrong_issuer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config, signer = _configured_service_config(monkeypatch, tmp_path)

    reason = _verification_failure_reason(
        config,
        signer.headers(subject="wrong-issuer", issuer="sir-convert-a-lot"),
    )

    assert reason == "invalid_internal_identity_issuer"


def test_huleedu_trust_profile_rejects_wrong_audience(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config, signer = _configured_service_config(monkeypatch, tmp_path)

    reason = _verification_failure_reason(
        config,
        signer.headers(subject="wrong-audience", audience="other-service"),
    )

    assert reason == "invalid_internal_identity_audience"


def test_huleedu_trust_profile_rejects_expired_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config, signer = _configured_service_config(monkeypatch, tmp_path)
    now = int(time.time())

    reason = _verification_failure_reason(
        config,
        signer.headers(subject="expired", iat=now - 120, exp=now - 61),
    )

    assert reason == "internal_identity_expired"


def _configured_service_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[ServiceConfig, "_TrustProfileProbeSigner"]:
    _clear_internal_identity_env(monkeypatch)
    signer = _TrustProfileProbeSigner()
    _configure_profile_env(monkeypatch, tmp_path, signer)
    return service_config_from_env(), signer


def _configure_profile_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    signer: "_TrustProfileProbeSigner",
    *,
    profile_fingerprint: str | None = None,
) -> None:
    public_key_path = tmp_path / "gateway-internal-identity-public-key.pem"
    public_key_path.write_text(signer.public_key_pem, encoding="utf-8")
    monkeypatch.setenv("HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH", str(public_key_path))
    monkeypatch.setenv("HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON", signer.profile_json())
    if profile_fingerprint is not None:
        monkeypatch.setenv(
            "HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON",
            signer.profile_json(spki_sha256_fingerprint=profile_fingerprint),
        )


def _clear_internal_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in _INTERNAL_IDENTITY_ENV_NAMES:
        monkeypatch.delenv(env_name, raising=False)


def _verification_failure_reason(config: ServiceConfig, headers: dict[str, str]) -> str:
    with pytest.raises(ServiceError) as error_info:
        require_verified_internal_identity_v2(headers=Headers(headers), config=config)

    assert error_info.value.status_code == 401
    details = error_info.value.details
    assert details is not None
    reason = details.get("reason")
    assert isinstance(reason, str)
    return reason


def _sanitized_acceptance_evidence(
    config: ServiceConfig,
    *,
    accepted: bool,
) -> dict[str, str | int | bool]:
    trust_profile = config.internal_identity_trust_profile
    assert trust_profile is not None
    return {
        "accepted": accepted,
        "audience": trust_profile.audience,
        "environment_id": trust_profile.environment_id,
        "issuer": trust_profile.issuer,
        "key_id": trust_profile.key_id,
        "skew_seconds": trust_profile.allowed_clock_skew_seconds,
        "spki_sha256_fingerprint": trust_profile.spki_sha256_fingerprint,
        "trusted_public_key_source": trust_profile.trusted_public_key_source,
        "ttl_seconds": trust_profile.ttl_seconds,
    }


class _TrustProfileProbeSigner:
    """Small RS256 signer for content-safe HuleEdu-contract probe payloads."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self._private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        spki_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.spki_sha256_fingerprint = hashlib.sha256(spki_der).hexdigest()
        self.pem_file_sha256_fingerprint = hashlib.sha256(
            self.public_key_pem.encode("utf-8")
        ).hexdigest()

    def profile_json(self, *, spki_sha256_fingerprint: str | None = None) -> str:
        profile: dict[str, object] = {
            "audience": _AUDIENCE,
            "environment_id": _ENVIRONMENT_ID,
            "issuer": _ISSUER,
            "key_id": _KEY_ID,
            "skew_seconds": 5,
            "spki_sha256_fingerprint": spki_sha256_fingerprint or self.spki_sha256_fingerprint,
            "trusted_public_key_source": _TRUSTED_PUBLIC_KEY_SOURCE,
            "ttl_seconds": 60,
        }
        return json.dumps(profile, sort_keys=True, separators=(",", ":"))

    def headers(
        self,
        *,
        subject: str,
        issuer: str = _ISSUER,
        audience: str = _AUDIENCE,
        key_id: str = _KEY_ID,
        iat: int | None = None,
        exp: int | None = None,
    ) -> dict[str, str]:
        now = int(time.time())
        issued_at = iat if iat is not None else now
        expires_at = exp if exp is not None else issued_at + 30
        payload: dict[str, object] = {
            "context_version": 1,
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "session_id": f"session-{subject}",
            "org_id": "org-probe",
            "tenant_id": None,
            "roles": ["teacher"],
            "grants": ["sir-convert:jobs:create"],
            "policy_version": "trust-profile-acceptance-smoke-v1",
            "iat": issued_at,
            "exp": expires_at,
            "jti": f"jti-{subject}-{issued_at}",
            "source_app": "huleedu",
            "active_app": "huleedu",
            "active_product_identity_realm": "huleedu",
            "realm_subject_id": subject,
        }
        encoded_context = _b64url(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signature = self._private_key.sign(
            encoded_context.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "X-HuleEdu-Identity-Context-Version": "1",
            "X-HuleEdu-Identity-Context": encoded_context,
            "X-HuleEdu-Identity-Key-Id": key_id,
            "X-HuleEdu-Identity-Signature": f"rs256={_b64url(signature)}",
        }


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
