"""HuleEdu InternalIdentityContextV1 verification for Sir Convert v2 routes.

Purpose:
    Verify HuleEdu Gateway-signed user identity contexts for user-originated
    Sir Convert jobs and derive stable owner scopes from signed payload fields.

Relationships:
    - Used by `interfaces.http_auth_v2` for route-specific authorization.
    - Follows the HuleEdu `InternalIdentityContextV1` header and RS256
      signature contract without minting or signing identity locally.
    - Feeds owner scopes into the existing v2 job store so artifact reads stay
      owner-bound without a parallel persistence model.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import time
from dataclasses import dataclass
from functools import lru_cache

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from starlette.datastructures import Headers

from scripts.sir_convert_a_lot.infrastructure.pem_public_key_config import rsa_public_key_from_pem
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError

INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER = "X-HuleEdu-Identity-Context-Version"
INTERNAL_IDENTITY_CONTEXT_HEADER = "X-HuleEdu-Identity-Context"
INTERNAL_IDENTITY_KEY_ID_HEADER = "X-HuleEdu-Identity-Key-Id"
INTERNAL_IDENTITY_SIGNATURE_HEADER = "X-HuleEdu-Identity-Signature"

_INTERNAL_IDENTITY_CONTEXT_VERSION = 1
_INTERNAL_IDENTITY_SIGNATURE_PREFIX = "rs256="
_USER_OWNER_KIND = "user"


class InternalIdentityContextV1(BaseModel):
    """Canonical HuleEdu Gateway-to-service identity context payload."""

    model_config = ConfigDict(extra="forbid")

    context_version: int
    iss: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    sub: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    org_id: str | None = None
    tenant_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    grants: list[str] = Field(default_factory=list)
    policy_version: str = Field(min_length=1)
    iat: int
    exp: int
    jti: str = Field(min_length=1)
    active_context: dict[str, object] | None = None
    feature_flags: list[str] = Field(default_factory=list)
    source_app: str | None = None
    active_app: str | None = None
    active_product_identity_realm: str | None = None
    realm_subject_id: str | None = None
    linked_identity_ids: dict[str, str] | None = None
    email: str | None = None
    email_verified: bool | None = None
    given_name: str | None = None
    family_name: str | None = None
    display_name: str | None = None
    locale: str | None = None

    @field_validator("iss", "aud", "sub", "session_id", "policy_version", "jti")
    @classmethod
    def _non_blank_required_string(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("value must not be blank")
        return normalized

    @field_validator(
        "source_app",
        "active_app",
        "active_product_identity_realm",
        "realm_subject_id",
        "email",
        "given_name",
        "family_name",
        "display_name",
        "locale",
    )
    @classmethod
    def _non_blank_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            raise ValueError("value must not be blank")
        return normalized


@dataclass(frozen=True)
class VerifiedInternalIdentityV2:
    """Verified identity and derived Sir Convert owner scope."""

    context: InternalIdentityContextV1
    owner_scope: str
    grants: frozenset[str]


def require_verified_internal_identity_v2(
    *,
    headers: Headers,
    config: ServiceConfig,
) -> VerifiedInternalIdentityV2:
    """Verify HuleEdu signed identity headers and derive a v2 owner scope."""

    if not config.internal_identity_public_keys:
        raise ServiceError(
            status_code=401,
            code="auth_internal_identity_not_configured",
            message="Signed internal identity verification is not configured.",
            retryable=False,
        )

    version_value = headers.get(INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER)
    encoded_context = headers.get(INTERNAL_IDENTITY_CONTEXT_HEADER)
    key_id = headers.get(INTERNAL_IDENTITY_KEY_ID_HEADER)
    signature_value = headers.get(INTERNAL_IDENTITY_SIGNATURE_HEADER)
    if (
        version_value is None
        or encoded_context is None
        or key_id is None
        or signature_value is None
    ):
        raise _identity_error("missing_internal_identity_headers")
    if version_value.strip() != str(_INTERNAL_IDENTITY_CONTEXT_VERSION):
        raise _identity_error("unsupported_internal_identity_version")
    normalized_key_id = key_id.strip()
    if normalized_key_id == "":
        raise _identity_error("missing_internal_identity_key_id")
    if not signature_value.startswith(_INTERNAL_IDENTITY_SIGNATURE_PREFIX):
        raise _identity_error("invalid_internal_identity_signature_format")
    expected_key_id = _configured_trust_profile_key_id(config)
    if expected_key_id is not None and normalized_key_id != expected_key_id:
        raise _identity_error("unknown_internal_identity_key_id")

    public_key = config.internal_identity_public_keys.get(normalized_key_id)
    if public_key is None:
        raise _identity_error("unknown_internal_identity_key_id")

    supplied_signature = signature_value[len(_INTERNAL_IDENTITY_SIGNATURE_PREFIX) :]
    try:
        _verify_rs256_signature(
            encoded_context=encoded_context,
            supplied_signature=supplied_signature,
            public_key=public_key,
        )
    except (InvalidSignature, ValueError):
        raise _identity_error("invalid_internal_identity_signature") from None

    context = _decode_context(encoded_context)
    _validate_context_claims(context=context, config=config)
    return VerifiedInternalIdentityV2(
        context=context,
        owner_scope=_owner_scope_for_context(context),
        grants=frozenset(context.grants),
    )


def _identity_error(reason: str) -> ServiceError:
    return ServiceError(
        status_code=401,
        code="auth_invalid_internal_identity",
        message="Missing or invalid signed internal identity context.",
        retryable=False,
        details={"reason": reason},
    )


def _b64url_decode(value: str) -> bytes:
    padding_length = (-len(value)) % 4
    try:
        return base64.urlsafe_b64decode(f"{value}{'=' * padding_length}")
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64url value") from exc


@lru_cache(maxsize=32)
def _load_public_key(public_key_text: str) -> rsa.RSAPublicKey:
    return rsa_public_key_from_pem(
        public_key_text,
        field_name="internal_identity_public_key",
    )


def _verify_rs256_signature(
    *,
    encoded_context: str,
    supplied_signature: str,
    public_key: str,
) -> None:
    _load_public_key(public_key).verify(
        _b64url_decode(supplied_signature),
        encoded_context.encode("ascii"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def _decode_context(encoded_context: str) -> InternalIdentityContextV1:
    try:
        decoded = json.loads(_b64url_decode(encoded_context).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _identity_error("invalid_internal_identity_payload") from exc
    if not isinstance(decoded, dict):
        raise _identity_error("invalid_internal_identity_payload")
    string_keyed: dict[str, object] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            raise _identity_error("invalid_internal_identity_payload")
        string_keyed[key] = value
    try:
        return InternalIdentityContextV1.model_validate(string_keyed)
    except ValidationError as exc:
        raise _identity_error("invalid_internal_identity_payload") from exc


def _validate_context_claims(
    *,
    context: InternalIdentityContextV1,
    config: ServiceConfig,
) -> None:
    if context.context_version != _INTERNAL_IDENTITY_CONTEXT_VERSION:
        raise _identity_error("unsupported_internal_identity_payload_version")
    if context.iss != _configured_expected_issuer(config):
        raise _identity_error("invalid_internal_identity_issuer")
    if context.aud != _configured_expected_audience(config):
        raise _identity_error("invalid_internal_identity_audience")
    if context.exp < context.iat:
        raise _identity_error("invalid_internal_identity_timestamps")
    if (context.exp - context.iat) > _configured_ttl_seconds(config):
        raise _identity_error("internal_identity_ttl_exceeded")

    now_ts = int(time.time())
    skew_seconds = _configured_allowed_clock_skew_seconds(config)
    if context.iat > now_ts + skew_seconds:
        raise _identity_error("internal_identity_issued_in_future")
    if context.exp <= now_ts - skew_seconds:
        raise _identity_error("internal_identity_expired")


def _configured_trust_profile_key_id(config: ServiceConfig) -> str | None:
    trust_profile = config.internal_identity_trust_profile
    if trust_profile is None:
        return None
    return trust_profile.key_id


def _configured_expected_issuer(config: ServiceConfig) -> str:
    trust_profile = config.internal_identity_trust_profile
    if trust_profile is not None:
        return trust_profile.issuer
    return config.internal_identity_expected_issuer


def _configured_expected_audience(config: ServiceConfig) -> str:
    trust_profile = config.internal_identity_trust_profile
    if trust_profile is not None:
        return trust_profile.audience
    return config.internal_identity_expected_audience


def _configured_ttl_seconds(config: ServiceConfig) -> int:
    trust_profile = config.internal_identity_trust_profile
    if trust_profile is not None:
        return trust_profile.ttl_seconds
    return config.internal_identity_ttl_seconds


def _configured_allowed_clock_skew_seconds(config: ServiceConfig) -> int:
    trust_profile = config.internal_identity_trust_profile
    if trust_profile is not None:
        return trust_profile.allowed_clock_skew_seconds
    return config.internal_identity_allowed_clock_skew_seconds


def _owner_scope_for_context(context: InternalIdentityContextV1) -> str:
    owner_realm = context.active_product_identity_realm or context.source_app or "huleedu"
    owner_subject = context.realm_subject_id or context.sub
    owner_payload = {
        "owner_kind": _USER_OWNER_KIND,
        "owner_realm": owner_realm,
        "owner_subject_id": owner_subject,
        "org_id": context.org_id,
        "tenant_id": context.tenant_id,
        "source_app": context.source_app,
    }
    normalized = json.dumps(owner_payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"identity:v1:{_USER_OWNER_KIND}:sha256:{digest}"
