"""DOCX template catalog loader and resolver for service API v2.

Purpose:
    Provide deterministic loading, integrity validation, and selection
    resolution for curated DOCX templates used by DOCX-producing v2 routes.

Relationships:
    - Used by v2 HTTP routes for template discovery and request validation.
    - Used by `infrastructure.v2_conversion_executor` to resolve template
      selectors into concrete `reference_docx` artifact paths.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_TEMPLATE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_TEMPLATE_VERSION_PATTERN = r"^\d+\.\d+\.\d+$"


class DocxTemplateStatusV2(StrEnum):
    """Lifecycle status for one DOCX template version."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class DocxTemplateProvenanceV2(BaseModel):
    """Provenance metadata for template governance and audit trails."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    change_note: str = Field(min_length=1)


class DocxTemplateVersionV2(BaseModel):
    """One versioned DOCX template metadata record."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(min_length=1, pattern=_TEMPLATE_ID_PATTERN)
    version: str = Field(min_length=1, pattern=_TEMPLATE_VERSION_PATTERN)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    domain_tags: list[str] = Field(default_factory=list)
    language_tags: list[str] = Field(default_factory=list)
    status: DocxTemplateStatusV2
    artifact_filename: str = Field(min_length=1)
    artifact_sha256: str = Field(min_length=64, max_length=64)
    artifact_size_bytes: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime
    provenance: DocxTemplateProvenanceV2


@dataclass(frozen=True)
class ResolvedDocxTemplateV2:
    """Resolved template selection with metadata and artifact location."""

    metadata: DocxTemplateVersionV2
    artifact_path: Path


@dataclass(frozen=True)
class DocxTemplateSummaryV2:
    """Selection-friendly summary for one template id."""

    template_id: str
    name: str
    description: str
    domain_tags: list[str]
    latest_active_version: str | None
    versions: list[str]
    statuses: list[DocxTemplateStatusV2]


@dataclass(frozen=True)
class DocxTemplateCatalogLoadError(Exception):
    """Raised when template catalog files are malformed or inconsistent."""

    message: str


@dataclass(frozen=True)
class DocxTemplateNotFoundError(Exception):
    """Raised when template id is unknown in the catalog."""

    template_id: str


@dataclass(frozen=True)
class DocxTemplateVersionNotFoundError(Exception):
    """Raised when template version is unknown for a known template id."""

    template_id: str
    version: str


@dataclass(frozen=True)
class DocxTemplateUnavailableError(Exception):
    """Raised when a selected template exists but is not selectable."""

    template_id: str
    version: str
    status: DocxTemplateStatusV2


def default_docx_template_root() -> Path:
    """Return canonical repository path for curated DOCX templates."""

    return Path(__file__).resolve().parents[1] / "templates" / "docx"


def _version_key(version: str) -> tuple[int, int, int]:
    major_text, minor_text, patch_text = version.split(".")
    return (int(major_text), int(minor_text), int(patch_text))


class DocxTemplateCatalogV2:
    """In-memory view of curated DOCX templates with deterministic resolution."""

    def __init__(
        self,
        *,
        root: Path,
        by_template: dict[str, dict[str, ResolvedDocxTemplateV2]],
    ) -> None:
        self.root = root
        self._by_template = by_template

    @classmethod
    def load(cls, *, root: Path | None = None) -> "DocxTemplateCatalogV2":
        """Load and verify template catalog from disk."""

        template_root = root or default_docx_template_root()
        if not template_root.exists():
            raise DocxTemplateCatalogLoadError(
                f"Template catalog root does not exist: {template_root}"
            )

        by_template: dict[str, dict[str, ResolvedDocxTemplateV2]] = {}

        metadata_paths = sorted(template_root.glob("*/*/metadata.json"))
        for metadata_path in metadata_paths:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise DocxTemplateCatalogLoadError(
                    f"metadata.json must contain an object: {metadata_path}"
                )
            metadata = DocxTemplateVersionV2.model_validate(payload)
            template_id_dir = metadata_path.parent.parent.name
            version_dir = metadata_path.parent.name
            if metadata.template_id != template_id_dir:
                raise DocxTemplateCatalogLoadError(
                    "template_id mismatch between metadata and directory "
                    f"({metadata.template_id} != {template_id_dir}) at {metadata_path}"
                )
            if metadata.version != version_dir:
                raise DocxTemplateCatalogLoadError(
                    "version mismatch between metadata and directory "
                    f"({metadata.version} != {version_dir}) at {metadata_path}"
                )

            artifact_path = metadata_path.parent / metadata.artifact_filename
            if not artifact_path.exists():
                raise DocxTemplateCatalogLoadError(f"Template artifact is missing: {artifact_path}")
            artifact_bytes = artifact_path.read_bytes()
            artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
            artifact_size_bytes = len(artifact_bytes)
            if artifact_sha256 != metadata.artifact_sha256:
                raise DocxTemplateCatalogLoadError(
                    "Template artifact sha256 mismatch for "
                    f"{metadata.template_id}@{metadata.version}: "
                    f"{artifact_sha256} != {metadata.artifact_sha256}"
                )
            if artifact_size_bytes != metadata.artifact_size_bytes:
                raise DocxTemplateCatalogLoadError(
                    "Template artifact size mismatch for "
                    f"{metadata.template_id}@{metadata.version}: "
                    f"{artifact_size_bytes} != {metadata.artifact_size_bytes}"
                )

            versions = by_template.setdefault(metadata.template_id, {})
            versions[metadata.version] = ResolvedDocxTemplateV2(
                metadata=metadata,
                artifact_path=artifact_path,
            )

        return cls(root=template_root, by_template=by_template)

    def list_template_summaries(self) -> list[DocxTemplateSummaryV2]:
        """Return deterministic template summaries for GUI discovery."""

        summaries: list[DocxTemplateSummaryV2] = []
        for template_id in sorted(self._by_template.keys()):
            versions_map = self._by_template[template_id]
            versions = sorted(versions_map.keys(), key=_version_key)
            latest_metadata = versions_map[versions[-1]].metadata
            latest_active = self._resolve_latest_active(versions_map)
            statuses = [versions_map[version].metadata.status for version in versions]
            summaries.append(
                DocxTemplateSummaryV2(
                    template_id=template_id,
                    name=latest_metadata.name,
                    description=latest_metadata.description,
                    domain_tags=list(latest_metadata.domain_tags),
                    latest_active_version=(
                        latest_active.metadata.version if latest_active is not None else None
                    ),
                    versions=versions,
                    statuses=statuses,
                )
            )
        return summaries

    def list_versions(self, *, template_id: str) -> list[ResolvedDocxTemplateV2]:
        """Return all versions for one template id sorted ascending by version."""

        versions_map = self._by_template.get(template_id)
        if versions_map is None:
            raise DocxTemplateNotFoundError(template_id=template_id)
        versions = sorted(versions_map.keys(), key=_version_key)
        return [versions_map[version] for version in versions]

    def resolve(self, *, template_id: str, version: str | None) -> ResolvedDocxTemplateV2:
        """Resolve a template selector to one concrete template version."""

        versions_map = self._by_template.get(template_id)
        if versions_map is None:
            raise DocxTemplateNotFoundError(template_id=template_id)

        if version is None:
            latest_active = self._resolve_latest_active(versions_map)
            if latest_active is None:
                highest_version = sorted(versions_map.keys(), key=_version_key)[-1]
                status = versions_map[highest_version].metadata.status
                raise DocxTemplateUnavailableError(
                    template_id=template_id,
                    version=highest_version,
                    status=status,
                )
            return latest_active

        resolved = versions_map.get(version)
        if resolved is None:
            raise DocxTemplateVersionNotFoundError(template_id=template_id, version=version)
        if resolved.metadata.status == DocxTemplateStatusV2.DISABLED:
            raise DocxTemplateUnavailableError(
                template_id=template_id,
                version=version,
                status=resolved.metadata.status,
            )
        return resolved

    @staticmethod
    def _resolve_latest_active(
        versions_map: dict[str, ResolvedDocxTemplateV2],
    ) -> ResolvedDocxTemplateV2 | None:
        active_versions = [
            resolved
            for resolved in versions_map.values()
            if resolved.metadata.status == DocxTemplateStatusV2.ACTIVE
        ]
        if not active_versions:
            return None
        return max(active_versions, key=lambda item: _version_key(item.metadata.version))


@lru_cache(maxsize=1)
def load_default_docx_template_catalog() -> DocxTemplateCatalogV2:
    """Load canonical template catalog once per process."""

    return DocxTemplateCatalogV2.load(root=default_docx_template_root())
