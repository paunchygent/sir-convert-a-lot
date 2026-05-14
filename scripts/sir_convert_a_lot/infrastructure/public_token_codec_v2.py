"""Compact public token codec for service API v2.

Purpose:
    Decode and verify compact JWT/JWS-style tokens for public conversion grants
    and artifact-read leases without owning Exam Converter route policy.

Relationships:
    - Used by public Exam Converter HTTP access adapters.
    - Keeps cryptographic mechanics separate from contract DTOs and policy
      decisions.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from functools import lru_cache

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class PublicTokenCodecError(ValueError):
    """Raised when a compact public token cannot be decoded or verified."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class CompactPublicTokenV2:
    """Decoded compact token parts before contract-specific validation."""

    header: dict[str, object]
    payload: dict[str, object]
    signature: bytes
    signing_input: bytes


def read_rs256_public_token_v2(
    *,
    token: str,
    public_keys: dict[str, str],
) -> dict[str, object]:
    """Return verified RS256 token claims."""

    decoded = _decode_compact_public_token(token)
    if decoded.header.get("alg") != "RS256":
        raise PublicTokenCodecError("unsupported_rs256_token_algorithm")
    key_id = decoded.header.get("kid")
    if not isinstance(key_id, str) or key_id.strip() == "":
        raise PublicTokenCodecError("missing_rs256_token_key_id")
    public_key = public_keys.get(key_id.strip())
    if public_key is None:
        raise PublicTokenCodecError("unknown_rs256_token_key_id")
    _verify_rs256(decoded=decoded, public_key=public_key)
    return decoded.payload


def read_hs256_public_token_v2(*, token: str, secret: str) -> dict[str, object]:
    """Return verified HS256 token claims."""

    decoded = _decode_compact_public_token(token)
    if decoded.header.get("alg") != "HS256":
        raise PublicTokenCodecError("unsupported_hs256_token_algorithm")
    expected = hmac.new(secret.encode("utf-8"), decoded.signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, decoded.signature):
        raise PublicTokenCodecError("invalid_hs256_signature")
    return decoded.payload


def sign_hs256_public_token_v2(*, payload: dict[str, object], secret: str) -> str:
    """Encode and sign a compact token with HMAC SHA-256."""

    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url_encode(json.dumps(header, sort_keys=True).encode("utf-8"))
    payload_segment = _b64url_encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def _decode_compact_public_token(token: str) -> CompactPublicTokenV2:
    parts = token.split(".")
    if len(parts) != 3 or any(part == "" for part in parts):
        raise PublicTokenCodecError("invalid_compact_token_format")
    header_segment, payload_segment, signature_segment = parts
    header = _decode_json_object(header_segment, reason="invalid_compact_token_header")
    payload = _decode_json_object(payload_segment, reason="invalid_compact_token_payload")
    try:
        signature = _b64url_decode(signature_segment)
    except ValueError as exc:
        raise PublicTokenCodecError("invalid_compact_token_signature") from exc
    return CompactPublicTokenV2(
        header=header,
        payload=payload,
        signature=signature,
        signing_input=f"{header_segment}.{payload_segment}".encode("ascii"),
    )


def _decode_json_object(segment: str, *, reason: str) -> dict[str, object]:
    try:
        decoded = json.loads(_b64url_decode(segment).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublicTokenCodecError(reason) from exc
    if not isinstance(decoded, dict):
        raise PublicTokenCodecError(reason)
    string_keyed: dict[str, object] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            raise PublicTokenCodecError(reason)
        string_keyed[key] = value
    return string_keyed


def _verify_rs256(*, decoded: CompactPublicTokenV2, public_key: str) -> None:
    try:
        _load_public_key(public_key).verify(
            decoded.signature,
            decoded.signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (InvalidSignature, ValueError) as exc:
        raise PublicTokenCodecError("invalid_rs256_signature") from exc


@lru_cache(maxsize=32)
def _load_public_key(public_key_text: str) -> rsa.RSAPublicKey:
    loaded_key = serialization.load_pem_public_key(public_key_text.encode("utf-8"))
    if not isinstance(loaded_key, rsa.RSAPublicKey):
        raise PublicTokenCodecError("verification_key_not_rsa")
    return loaded_key


def _b64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding_length = (-len(value)) % 4
    try:
        return base64.urlsafe_b64decode(f"{value}{'=' * padding_length}")
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64url value") from exc
