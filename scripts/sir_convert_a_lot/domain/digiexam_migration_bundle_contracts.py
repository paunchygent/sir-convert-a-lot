"""DigiExam migration artifact-bundle domain contract.

Purpose:
    Define deterministic artifact keys, filenames, availability states, and
    manifest value objects for the DigiExam-to-Exam.net service route.

Relationships:
    - Produced by `infrastructure.digiexam_migration_bundle_builder`.
    - Read by `interfaces.http_routes_job_artifacts_v2` for named artifact
      listing and download.
    - Mirrors `docs/converters/digiexam-migration-service-api-artifact-contract.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION: Literal["digiexam_migration_bundle_v1"] = (
    "digiexam_migration_bundle_v1"
)


class DigiExamMigrationArtifactKey(StrEnum):
    """Required artifact keys for DigiExam migration terminal bundles."""

    BUNDLE_MANIFEST = "bundle_manifest"
    EXAMNET_PDF = "examnet_pdf"
    QTI_PACKAGE = "qti_package"
    QTI_VALIDATION_REPORT = "qti_validation_report"
    IR_JSON = "ir_json"
    MIGRATION_MANIFEST = "migration_manifest"
    MANUAL_FOLLOW_UP_REPORT = "manual_follow_up_report"
    WARNINGS_REPORT = "warnings_report"
    ASSET_SUMMARY = "asset_summary"


class DigiExamMigrationArtifactAvailability(StrEnum):
    """Availability states for named bundle artifacts."""

    AVAILABLE = "available"
    BLOCKED = "blocked"
    FAILED = "failed"
    NOT_REQUESTED = "not_requested"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_SUPPORTED_BY_EXAMNET = "not_supported_by_examnet"


class DigiExamMigrationBundleStatus(StrEnum):
    """Terminal bundle status interpreted by Skriptoteket."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class DigiExamMigrationArtifactDefinition:
    """Static deterministic artifact identity."""

    artifact_key: DigiExamMigrationArtifactKey
    filename: str
    content_type: str


@dataclass(frozen=True)
class DigiExamMigrationArtifactEntry:
    """Manifest entry for one named artifact."""

    artifact_key: DigiExamMigrationArtifactKey
    filename: str
    content_type: str
    availability: DigiExamMigrationArtifactAvailability
    size_bytes: int | None
    sha256: str | None
    download_path: str | None
    blocker_code: str | None = None
    depends_on: str | None = None


ARTIFACT_DEFINITIONS: dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactDefinition] = {
    DigiExamMigrationArtifactKey.BUNDLE_MANIFEST: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.BUNDLE_MANIFEST,
        filename="artifact-bundle.json",
        content_type="application/json",
    ),
    DigiExamMigrationArtifactKey.EXAMNET_PDF: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.EXAMNET_PDF,
        filename="examnet-import.pdf",
        content_type="application/pdf",
    ),
    DigiExamMigrationArtifactKey.QTI_PACKAGE: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.QTI_PACKAGE,
        filename="qti-package.zip",
        content_type="application/zip",
    ),
    DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT,
        filename="qti-validation-report.json",
        content_type="application/json",
    ),
    DigiExamMigrationArtifactKey.IR_JSON: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.IR_JSON,
        filename="digiexam-ir.json",
        content_type="application/json",
    ),
    DigiExamMigrationArtifactKey.MIGRATION_MANIFEST: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.MIGRATION_MANIFEST,
        filename="migration-manifest.json",
        content_type="application/json",
    ),
    DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT,
        filename="manual-follow-up.md",
        content_type="text/markdown; charset=utf-8",
    ),
    DigiExamMigrationArtifactKey.WARNINGS_REPORT: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.WARNINGS_REPORT,
        filename="warnings.json",
        content_type="application/json",
    ),
    DigiExamMigrationArtifactKey.ASSET_SUMMARY: DigiExamMigrationArtifactDefinition(
        artifact_key=DigiExamMigrationArtifactKey.ASSET_SUMMARY,
        filename="asset-summary.json",
        content_type="application/json",
    ),
}

REQUIRED_ARTIFACT_KEYS: tuple[DigiExamMigrationArtifactKey, ...] = (
    DigiExamMigrationArtifactKey.BUNDLE_MANIFEST,
    DigiExamMigrationArtifactKey.EXAMNET_PDF,
    DigiExamMigrationArtifactKey.QTI_PACKAGE,
    DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT,
    DigiExamMigrationArtifactKey.IR_JSON,
    DigiExamMigrationArtifactKey.MIGRATION_MANIFEST,
    DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT,
    DigiExamMigrationArtifactKey.WARNINGS_REPORT,
    DigiExamMigrationArtifactKey.ASSET_SUMMARY,
)
