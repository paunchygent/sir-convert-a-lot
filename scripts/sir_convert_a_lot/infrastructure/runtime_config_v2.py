"""Runtime configuration helpers for multi-format service API v2.

Purpose:
    Provide v2-specific request fingerprint logic for idempotency semantics,
    including optional auxiliary uploads (resources zip and reference docx).

Relationships:
    - Imported by `interfaces` v2 routes when computing idempotency fingerprints.
    - Coexists with v1 helpers in `infrastructure.runtime_config`.
"""

from __future__ import annotations

import hashlib
import json


def fingerprint_for_request_v2(
    *,
    spec_payload: dict[str, object],
    file_sha256: str,
    resources_sha256: str | None,
    reference_docx_sha256: str | None,
) -> str:
    """Create deterministic idempotency fingerprint for a v2 create-job request."""
    normalized = json.dumps(spec_payload, sort_keys=True, separators=(",", ":"))
    resources_part = resources_sha256 or ""
    reference_part = reference_docx_sha256 or ""
    return hashlib.sha256(
        f"{normalized}:{file_sha256}:{resources_part}:{reference_part}".encode("utf-8")
    ).hexdigest()
