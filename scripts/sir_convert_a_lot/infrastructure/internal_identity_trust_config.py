"""HuleEdu internal identity trust-profile runtime configuration.

Purpose:
    Load HuleEdu's sanitized `InternalIdentityContextV1` trust profile, bind it
    to configured public key material, and produce verifier-ready typed config.

Relationships:
    - Called by `infrastructure.runtime_config.service_config_from_env`.
    - Uses `infrastructure.pem_public_key_config` to compare canonical DER SPKI
      SHA-256 fingerprints, not PEM file-byte hashes.
    - Produces `HuleEduInternalIdentityTrustRuntimeConfig` consumed by
      `interfaces.http_internal_identity_v2`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from scripts.sir_convert_a_lot.infrastructure.pem_public_key_config import (
    normalize_pem_text,
    read_pem_text_path,
    spki_sha256_fingerprint,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import (
    HuleEduInternalIdentityAudience,
    HuleEduInternalIdentityEnvironmentId,
    HuleEduInternalIdentityIssuer,
    HuleEduInternalIdentityKeyId,
    HuleEduInternalIdentityTrustRuntimeConfig,
)

_DEFAULT_KEY_ID = "gateway-identity-rs256-v1"
_DEFAULT_AUDIENCE = "sir-convert-a-lot"
_DEFAULT_ISSUER = "api_gateway_service"
_HEX_DIGITS = frozenset("0123456789abcdef")


class HuleEduInternalIdentityTrustProfileV1(BaseModel):
    """Sanitized HuleEdu trust profile consumed by Sir Convert runtime config."""

    model_config = ConfigDict(extra="forbid")

    audience: HuleEduInternalIdentityAudience
    environment_id: HuleEduInternalIdentityEnvironmentId
    issuer: HuleEduInternalIdentityIssuer
    key_id: HuleEduInternalIdentityKeyId
    skew_seconds: int = Field(ge=0, le=300)
    spki_sha256_fingerprint: str = Field(min_length=64, max_length=64)
    trusted_public_key_source: str = Field(min_length=1)
    ttl_seconds: int = Field(ge=1, le=60)

    @field_validator("spki_sha256_fingerprint")
    @classmethod
    def _canonical_lower_hex_fingerprint(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("spki_sha256_fingerprint must not include surrounding whitespace")
        if len(value) != 64 or any(character not in _HEX_DIGITS for character in value):
            raise ValueError("spki_sha256_fingerprint must be lowercase 64-character hex")
        return value

    @field_validator("trusted_public_key_source")
    @classmethod
    def _non_blank_public_key_source(cls, value: str) -> str:
        if value != value.strip() or value == "":
            raise ValueError(
                "trusted_public_key_source must be nonblank without whitespace padding"
            )
        return value

    def to_runtime_config(self) -> HuleEduInternalIdentityTrustRuntimeConfig:
        """Convert the sanitized profile into the verifier runtime shape."""

        return HuleEduInternalIdentityTrustRuntimeConfig(
            environment_id=self.environment_id,
            issuer=self.issuer,
            audience=self.audience,
            key_id=self.key_id,
            trusted_public_key_source=self.trusted_public_key_source,
            spki_sha256_fingerprint=self.spki_sha256_fingerprint,
            ttl_seconds=self.ttl_seconds,
            allowed_clock_skew_seconds=self.skew_seconds,
        )


@dataclass(frozen=True)
class InternalIdentityRuntimeConfig:
    """Verifier-ready internal identity config derived from env and profile."""

    public_keys: dict[str, str]
    expected_audience: str
    expected_issuer: str
    ttl_seconds: int
    allowed_clock_skew_seconds: int
    trust_profile: HuleEduInternalIdentityTrustRuntimeConfig | None = None


def internal_identity_runtime_config_from_env() -> InternalIdentityRuntimeConfig:
    """Load HuleEdu internal identity trust config from environment variables."""

    trust_profile = _trust_profile_from_env()
    if trust_profile is None:
        return InternalIdentityRuntimeConfig(
            public_keys=_internal_identity_public_keys_from_env(),
            expected_audience=os.getenv(
                "HULEEDU_INTERNAL_IDENTITY_AUDIENCE", _DEFAULT_AUDIENCE
            ).strip()
            or _DEFAULT_AUDIENCE,
            expected_issuer=os.getenv("HULEEDU_INTERNAL_IDENTITY_ISSUER", _DEFAULT_ISSUER).strip()
            or _DEFAULT_ISSUER,
            ttl_seconds=_parse_bounded_int_env(
                name="HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS",
                default=60,
                minimum=1,
                maximum=3600,
            ),
            allowed_clock_skew_seconds=_parse_bounded_int_env(
                name="HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS",
                default=5,
                minimum=0,
                maximum=300,
            ),
        )

    _ensure_legacy_overrides_match_profile(trust_profile)
    public_keys = _internal_identity_public_keys_from_env()
    public_key = public_keys.get(trust_profile.key_id)
    if public_key is None:
        raise ValueError(
            "HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON requires a configured public key "
            f"for key id {trust_profile.key_id}"
        )
    actual_fingerprint = spki_sha256_fingerprint(
        public_key,
        field_name=f"HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY[{trust_profile.key_id}]",
    )
    if actual_fingerprint != trust_profile.spki_sha256_fingerprint:
        raise ValueError(
            "HuleEdu internal identity SPKI SHA-256 fingerprint mismatch for key id "
            f"{trust_profile.key_id}: expected {trust_profile.spki_sha256_fingerprint}, "
            f"got {actual_fingerprint}"
        )
    runtime_profile = trust_profile.to_runtime_config()
    return InternalIdentityRuntimeConfig(
        public_keys={runtime_profile.key_id: public_key},
        expected_audience=runtime_profile.audience,
        expected_issuer=runtime_profile.issuer,
        ttl_seconds=runtime_profile.ttl_seconds,
        allowed_clock_skew_seconds=runtime_profile.allowed_clock_skew_seconds,
        trust_profile=runtime_profile,
    )


def _trust_profile_from_env() -> HuleEduInternalIdentityTrustProfileV1 | None:
    raw_json = os.getenv("HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON")
    raw_path = os.getenv("HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_PATH")
    has_json = raw_json is not None and raw_json.strip() != ""
    has_path = raw_path is not None and raw_path.strip() != ""
    if has_json and has_path:
        raise ValueError(
            "Configure only one of HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON or "
            "HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_PATH"
        )
    if has_json:
        assert raw_json is not None
        return _parse_trust_profile_json(
            raw_json,
            field_name="HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON",
        )
    if has_path:
        assert raw_path is not None
        path = Path(raw_path.strip())
        if not path.exists():
            raise ValueError(
                f"HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_PATH points to a missing file: {path}"
            )
        return _parse_trust_profile_json(
            path.read_text(encoding="utf-8"),
            field_name="HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_PATH",
        )
    return None


def _parse_trust_profile_json(
    raw_json: str,
    *,
    field_name: str,
) -> HuleEduInternalIdentityTrustProfileV1:
    try:
        return HuleEduInternalIdentityTrustProfileV1.model_validate_json(raw_json)
    except ValidationError as exc:
        raise ValueError(f"{field_name} must be a valid HuleEdu trust profile JSON") from exc


def _ensure_legacy_overrides_match_profile(
    trust_profile: HuleEduInternalIdentityTrustProfileV1,
) -> None:
    _ensure_optional_string_env_matches(
        name="HULEEDU_INTERNAL_IDENTITY_AUDIENCE",
        expected=trust_profile.audience,
    )
    _ensure_optional_string_env_matches(
        name="HULEEDU_INTERNAL_IDENTITY_ISSUER",
        expected=trust_profile.issuer,
    )
    _ensure_optional_string_env_matches(
        name="HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID",
        expected=trust_profile.key_id,
    )
    _ensure_optional_int_env_matches(
        name="HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS",
        expected=trust_profile.ttl_seconds,
        minimum=1,
        maximum=3600,
    )
    _ensure_optional_int_env_matches(
        name="HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS",
        expected=trust_profile.skew_seconds,
        minimum=0,
        maximum=300,
    )


def _ensure_optional_string_env_matches(*, name: str, expected: str) -> None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return
    if raw.strip() != expected:
        raise ValueError(f"{name} must match the configured HuleEdu trust profile")


def _ensure_optional_int_env_matches(
    *,
    name: str,
    expected: int,
    minimum: int,
    maximum: int,
) -> None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return
    value = _parse_bounded_int_value(name=name, raw=raw, minimum=minimum, maximum=maximum)
    if value != expected:
        raise ValueError(f"{name} must match the configured HuleEdu trust profile")


def _parse_bounded_int_env(
    *,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return _parse_bounded_int_value(name=name, raw=raw, minimum=minimum, maximum=maximum)


def _parse_bounded_int_value(*, name: str, raw: str, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {name}: {raw!r}.") from exc
    if value < minimum or value > maximum:
        raise ValueError(
            f"Invalid value for {name}: {value}. Expected range [{minimum}, {maximum}]."
        )
    return value


def _internal_identity_public_keys_from_env() -> dict[str, str]:
    """Return configured HuleEdu internal-identity public keys by key id."""

    public_keys: dict[str, str] = {}
    trusted_json = os.getenv("HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON")
    if trusted_json is not None and trusted_json.strip() != "":
        try:
            decoded: object = json.loads(trusted_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON must be valid JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise ValueError(
                "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON must decode to an object"
            )
        for raw_key_id, raw_public_key in decoded.items():
            if not isinstance(raw_key_id, str) or not isinstance(raw_public_key, str):
                raise ValueError(
                    "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON entries must map "
                    "string key ids to PEM strings"
                )
            key_id = raw_key_id.strip()
            if key_id == "":
                raise ValueError(
                    "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON contains a blank key id"
                )
            public_keys[key_id] = normalize_pem_text(
                raw_public_key,
                field_name=f"HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON[{key_id}]",
            )

    signing_key_id = os.getenv("HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID", _DEFAULT_KEY_ID).strip()
    inline_public_key = os.getenv("HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY")
    public_key_path = os.getenv("HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH")
    if inline_public_key is not None and inline_public_key.strip() != "":
        public_keys.setdefault(
            signing_key_id,
            normalize_pem_text(
                inline_public_key,
                field_name="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY",
            ),
        )
    elif public_key_path is not None and public_key_path.strip() != "":
        public_keys.setdefault(
            signing_key_id,
            read_pem_text_path(
                public_key_path,
                field_name="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH",
            ),
        )
    return public_keys
