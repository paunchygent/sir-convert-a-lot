"""Upload helper utilities for the Sir Convert-a-Lot service API v2 client.

Purpose:
    Centralize small, deterministic helpers used for multipart upload
    submissions, keeping `http_client_v2.py` lean and under the 500 LoC
    guardrail.

Relationships:
    - Used by `scripts.sir_convert_a_lot.interfaces.http_client_v2`.
"""

from __future__ import annotations

from pathlib import Path


def content_type_for_source_path(path: Path) -> str:
    """Return a best-effort Content-Type for one source file path."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix in {".html", ".htm"}:
        return "text/html"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"
