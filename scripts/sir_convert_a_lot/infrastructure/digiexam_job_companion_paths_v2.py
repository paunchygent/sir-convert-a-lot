"""DigiExam migration companion upload paths for service API v2 jobs.

Purpose:
    Keep route-specific DigiExam companion file storage predictable without
    widening the generic v2 job-store schema.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` when persisting accepted
      companion uploads beside the primary `.dxe` file.
    - Used by `infrastructure.digiexam_migration_bundle_builder` to discover
      optional sanitized graded-result and parity PDFs during execution.
"""

from __future__ import annotations

from pathlib import Path


def graded_result_pdf_path_for_upload(upload_path: Path) -> Path:
    """Return the raw-area path for an accepted sanitized graded-result PDF."""

    return upload_path.parent / "graded_result_pdf.pdf"


def parity_pdf_path_for_upload(upload_path: Path) -> Path:
    """Return the raw-area path for an accepted parity PDF."""

    return upload_path.parent / "parity_pdf.pdf"


def ingestion_overlay_path_for_upload(upload_path: Path) -> Path:
    """Return the raw-area path for an accepted DigiExam ingestion overlay."""

    return upload_path.parent / "digiexam_ingestion_overlay.json"
