"""Shared models for v2 non-PDF route execution.

Purpose:
    Keep small dataclasses used across non-PDF v2 route executors in one place
    to avoid circular imports and keep per-route modules focused on execution.

Relationships:
    - Used by `infrastructure.v2_conversion_executor_non_pdf` and per-route
      executor modules under `infrastructure.v2_non_pdf_routes_*`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NonPdfExecutionOutcomeV2:
    """Successful non-PDF v2 execution outcome (metadata only)."""

    pipeline_used: str
    backend_used: str
    acceleration_used: str | None
    warnings: list[str]
    phase_timings_ms: dict[str, int]
    template_id: str | None = None
    template_version: str | None = None
    template_artifact_sha256: str | None = None


@dataclass(frozen=True)
class ResolvedReferenceDocxV2:
    """Resolved DOCX reference path + optional template audit metadata."""

    path: Path | None
    template_id: str | None = None
    template_version: str | None = None
    template_artifact_sha256: str | None = None
