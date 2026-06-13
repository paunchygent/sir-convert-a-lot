"""PEM public-key loading helpers for runtime trust configuration.

Purpose:
    Normalize configured PEM public keys, read key files, and derive canonical
    RSA SubjectPublicKeyInfo fingerprints for verifier trust checks.

Relationships:
    - Used by `infrastructure.runtime_config` for public-key env surfaces.
    - Used by `infrastructure.internal_identity_trust_config` to bind HuleEdu
      trust-profile fingerprints to active verifier keys.
    - Used by `interfaces.http_internal_identity_v2` before RS256 signature
      verification.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def normalize_pem_text(value: str, *, field_name: str) -> str:
    """Normalize PEM text supplied inline or through JSON environment values."""

    normalized = value.strip().replace("\\n", "\n")
    if normalized == "":
        raise ValueError(f"{field_name} must not be empty when configured")
    return normalized


def read_pem_text_path(value: str, *, field_name: str) -> str:
    """Read and normalize a configured PEM public-key path."""

    path = Path(value.strip())
    if not path.exists():
        raise ValueError(f"{field_name} points to a missing file: {path}")
    return normalize_pem_text(path.read_text(encoding="utf-8"), field_name=field_name)


def rsa_public_key_from_pem(public_key_text: str, *, field_name: str) -> rsa.RSAPublicKey:
    """Load a configured PEM value as an RSA public key."""

    try:
        loaded_key = serialization.load_pem_public_key(public_key_text.encode("utf-8"))
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise ValueError(f"{field_name} must be a valid PEM public key") from exc
    if not isinstance(loaded_key, rsa.RSAPublicKey):
        raise ValueError(f"{field_name} must be an RSA public key")
    return loaded_key


def spki_sha256_fingerprint(public_key_text: str, *, field_name: str) -> str:
    """Return the canonical DER SPKI SHA-256 fingerprint for a PEM RSA key."""

    public_key = rsa_public_key_from_pem(public_key_text, field_name=field_name)
    spki_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(spki_der).hexdigest()
