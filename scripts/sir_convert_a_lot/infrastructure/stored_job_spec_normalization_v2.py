"""Stored v2 job-spec manifest normalization.

Purpose:
    Normalize retained on-disk v2 job manifests before strict domain validation,
    preserving the public `JobSpecV2` request contract while keeping retained
    dev and production job stores readable across governed schema cuts.

Relationships:
    - Used only by `job_store_manifest_v2` when loading persisted manifests.
    - Does not relax HTTP request validation or generated OpenAPI schemas.
"""

from __future__ import annotations

from collections.abc import Mapping

_RETIRED_CONVERSION_KEYS: frozenset[str] = frozenset({"input_trust_mode"})


def normalize_stored_job_spec_payload_v2(spec_payload: Mapping[str, object]) -> dict[str, object]:
    """Return a stored-manifest job spec with retired persistence-only keys removed."""
    normalized = dict(spec_payload)
    conversion = normalized.get("conversion")
    if isinstance(conversion, Mapping):
        normalized_conversion = dict(conversion)
        for key in _RETIRED_CONVERSION_KEYS:
            normalized_conversion.pop(key, None)
        normalized["conversion"] = normalized_conversion
    return normalized
