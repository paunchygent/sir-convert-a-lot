"""Object key derivation for terminal artifact storage.

Purpose:
    Build deterministic, non-PII object keys for terminal artifact blobs from
    route, owner-scope digest, job, artifact class, and content digest.

Relationships:
    - Used by local and R2 object-store adapters.
    - Mirrors the key-shape approved in the R2 artifact pre-runbook.
"""

from __future__ import annotations

import re

from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    TerminalArtifactWriteRequest,
)

_SAFE_SEGMENT = re.compile(r"[^a-zA-Z0-9_.=-]+")


def terminal_artifact_object_key(
    *,
    key_prefix: str,
    runtime_profile: str,
    request: TerminalArtifactWriteRequest,
    content_sha256: str,
) -> str:
    """Return the approved object key for one terminal artifact blob."""
    extension = _safe_extension(request.filename)
    segments = (
        key_prefix,
        runtime_profile,
        request.route_key,
        request.owner_scope_sha256,
        request.job_id,
        request.artifact_class,
        request.artifact_key,
        f"{content_sha256}{extension}",
    )
    return "/".join(_safe_segment(segment) for segment in segments if segment.strip() != "")


def _safe_segment(value: str) -> str:
    cleaned = _SAFE_SEGMENT.sub("-", value.strip()).strip("-")
    return cleaned if cleaned != "" else "unset"


def _safe_extension(filename: str) -> str:
    cleaned = filename.rsplit("/", maxsplit=1)[-1].rsplit("\\", maxsplit=1)[-1]
    if "." not in cleaned:
        return ""
    suffix = cleaned.rsplit(".", maxsplit=1)[-1].strip().lower()
    if suffix == "":
        return ""
    return "." + _safe_segment(suffix)
