"""Unit tests for v2 DOCX template catalog loading and resolution.

Purpose:
    Validate catalog integrity checks and deterministic template resolution from
    metadata + artifact fixtures.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.docx_template_catalog_v2`.
    - Uses temporary fixture roots to cover failure branches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.docx_template_catalog_v2 import (
    DocxTemplateCatalogLoadError,
    DocxTemplateCatalogV2,
    DocxTemplateNotFoundError,
    DocxTemplateVersionNotFoundError,
    default_docx_template_root,
)


def test_load_default_catalog_contains_curated_template_ids() -> None:
    catalog = DocxTemplateCatalogV2.load(root=default_docx_template_root())

    summaries = catalog.list_template_summaries()
    template_ids = {summary.template_id for summary in summaries}
    assert {"academic-report", "classroom-handout", "project-week-summary"}.issubset(template_ids)


def test_catalog_resolve_without_version_uses_latest_active() -> None:
    catalog = DocxTemplateCatalogV2.load(root=default_docx_template_root())

    resolved = catalog.resolve(template_id="academic-report", version=None)

    assert resolved.metadata.template_id == "academic-report"
    assert resolved.metadata.version == "1.0.0"
    assert resolved.artifact_path.exists()


def test_catalog_resolve_unknown_template_raises_not_found() -> None:
    catalog = DocxTemplateCatalogV2.load(root=default_docx_template_root())

    with pytest.raises(DocxTemplateNotFoundError):
        catalog.resolve(template_id="unknown", version=None)


def test_catalog_resolve_unknown_version_raises_not_found() -> None:
    catalog = DocxTemplateCatalogV2.load(root=default_docx_template_root())

    with pytest.raises(DocxTemplateVersionNotFoundError):
        catalog.resolve(template_id="academic-report", version="9.9.9")


def test_catalog_load_rejects_artifact_sha_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "templates" / "docx" / "tampered-template" / "1.0.0"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / "template.docx"
    artifact_path.write_bytes(b"not-a-real-docx")
    metadata = {
        "template_id": "tampered-template",
        "version": "1.0.0",
        "name": "Tampered",
        "description": "Tampered test fixture",
        "domain_tags": ["general"],
        "language_tags": ["en-US"],
        "status": "active",
        "artifact_filename": "template.docx",
        "artifact_sha256": "0" * 64,
        "artifact_size_bytes": len(b"not-a-real-docx"),
        "created_at": "2026-02-28T00:00:00Z",
        "updated_at": "2026-02-28T00:00:00Z",
        "provenance": {
            "source": "internal_curated",
            "owner": "platform",
            "change_note": "test",
        },
    }
    (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(DocxTemplateCatalogLoadError, match="sha256 mismatch"):
        DocxTemplateCatalogV2.load(root=tmp_path / "templates" / "docx")
