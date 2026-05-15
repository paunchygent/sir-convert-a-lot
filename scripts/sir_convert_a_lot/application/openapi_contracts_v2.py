"""OpenAPI contract DTOs for Sir Convert-a-Lot service API v2.

Purpose:
    Publish consumer-facing schema components that are not directly inferable
    from multipart `UploadFile`/`Form` route signatures or dataclass artifact
    writers.

Relationships:
    - Injected into FastAPI OpenAPI by `interfaces.http_openapi_contract_v2`.
    - Mirrors governed converter docs for DigiExam migration bundle v2.
    - Consumed by `openapi_export_v2` and downstream Skriptoteket type
      generation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlay,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DigiExamEffectiveExamSchemaVersion,
    DigiExamIntermediateExamSchemaVersion,
    DigiExamMigrationBundleSchemaVersion,
    IngestionOverlayReportSchemaVersion,
    TargetReadinessReportSchemaVersion,
)
from scripts.sir_convert_a_lot.domain.digiexam_target_readiness import DigiExamTargetReadiness
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2


class DigiExamMigrationBundleSourceV2(BaseModel):
    """Source summary in current DigiExam migration bundle manifests."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    sha256: str
    format: Literal["digiexam_dxe"]


class DigiExamMigrationBundleRetentionV2(BaseModel):
    """Retention summary in current DigiExam migration bundle manifests."""

    model_config = ConfigDict(extra="forbid")

    pin: bool
    expires_at: str | None = None


class DigiExamMigrationBundleArtifactEntryV2(BaseModel):
    """One named artifact entry in a DigiExam migration bundle manifest."""

    model_config = ConfigDict(extra="forbid")

    artifact_key: DigiExamMigrationArtifactKey
    filename: str
    content_type: str
    availability: DigiExamMigrationArtifactAvailability
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None
    download_path: str | None = None
    unavailable_code: str | None = None
    depends_on: str | None = None


class DigiExamMigrationBundleManualFollowUpV2(BaseModel):
    """Manual follow-up summary in current DigiExam migration bundle manifests."""

    model_config = ConfigDict(extra="forbid")

    required: bool
    artifact_key: Literal["manual_follow_up_report"]
    count: int = Field(ge=0)


class DigiExamMigrationBundleReadinessSummaryV2(BaseModel):
    """Readiness summary pointing consumers to the authoritative report."""

    model_config = ConfigDict(extra="forbid")

    artifact_key: Literal["target_readiness_report"]
    exportable_targets: list[str] = Field(default_factory=list)
    review_required: bool


class DigiExamMigrationBundleSourceBindingV2(BaseModel):
    """Source/effective IR hashes published in bundle manifests."""

    model_config = ConfigDict(extra="forbid")

    source_ir_schema_version: DigiExamIntermediateExamSchemaVersion
    source_ir_sha256: str
    effective_exam_schema_version: DigiExamEffectiveExamSchemaVersion
    effective_exam_sha256: str


class DigiExamMigrationBundleWarningsV2(BaseModel):
    """Warnings summary in current DigiExam migration bundle manifests."""

    model_config = ConfigDict(extra="forbid")

    artifact_key: Literal["warnings_report"]
    count: int = Field(ge=0)


class DigiExamMigrationBundleManifestV2(BaseModel):
    """Terminal artifact bundle manifest for DigiExam migration jobs."""

    model_config = ConfigDict(extra="forbid")

    schema_version: DigiExamMigrationBundleSchemaVersion
    job_id: str
    source: DigiExamMigrationBundleSourceV2
    bundle_status: Literal["complete", "partial", "needs_review", "failed"]
    retention: DigiExamMigrationBundleRetentionV2
    artifacts: list[DigiExamMigrationBundleArtifactEntryV2]
    manual_follow_up: DigiExamMigrationBundleManualFollowUpV2
    readiness: DigiExamMigrationBundleReadinessSummaryV2
    source_binding: DigiExamMigrationBundleSourceBindingV2
    warnings: DigiExamMigrationBundleWarningsV2


class DigiExamTargetReadinessRowV1(BaseModel):
    """One target or target/item readiness row consumed by Skriptoteket."""

    model_config = ConfigDict(extra="forbid")

    target: str
    readiness: DigiExamTargetReadiness
    export_enabled: bool
    artifact_key: str | None = None
    reason_code: str
    teacher_action: str
    retryable: bool
    message_key: str
    item_id: str | None = None
    sequence: int | None = Field(default=None, ge=1)
    source_item_fingerprint: str | None = None


class DigiExamTargetReadinessReportV1(BaseModel):
    """Authoritative target-readiness report for migration bundle consumers."""

    model_config = ConfigDict(extra="forbid")

    schema_version: TargetReadinessReportSchemaVersion
    job_id: str
    source_ir_sha256: str
    effective_exam_sha256: str
    targets: list[DigiExamTargetReadinessRowV1]


class DigiExamEffectiveAnswerKeyV1(BaseModel):
    """Effective answer-key summary without changing source provenance."""

    model_config = ConfigDict(extra="forbid")

    provenance: str
    correct_alternative_ids: list[int] = Field(default_factory=list)
    correct_gap_answers: list[dict[str, str]] = Field(default_factory=list)


class DigiExamEffectiveItemPatchSummaryV1(BaseModel):
    """Visible effective item patch summary for teacher-review consumers."""

    model_config = ConfigDict(extra="forbid")

    changed_fields: list[str] = Field(default_factory=list)
    patched_alternative_ids: list[int] = Field(default_factory=list)
    patched_gap_ids: list[str] = Field(default_factory=list)


class DigiExamEffectiveReviewDecisionV1(BaseModel):
    """Applied review decision surfaced in effective exam artifacts."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    decision_id: str
    accepted_targets: list[str]
    note: str | None = None


class DigiExamEffectiveItemV1(BaseModel):
    """One item summary in current effective exam artifacts."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    sequence: int = Field(ge=1)
    item_type: str
    source_item_fingerprint: str
    effective_answer_key: DigiExamEffectiveAnswerKeyV1 | None = None
    effective_item_patch: DigiExamEffectiveItemPatchSummaryV1 | None = None
    applied_overlay_entry_ids: list[str] = Field(default_factory=list)
    review_decisions: list[DigiExamEffectiveReviewDecisionV1] = Field(default_factory=list)


class DigiExamEffectiveExamV1(BaseModel):
    """Effective exam artifact emitted when overlay changes renderer input."""

    model_config = ConfigDict(extra="forbid")

    schema_version: DigiExamEffectiveExamSchemaVersion
    source_file_sha256: str
    source_ir_schema_version: DigiExamIntermediateExamSchemaVersion
    source_ir_sha256: str
    ingestion_overlay_sha256: str | None = None
    answer_key_completion_report_sha256: str | None = None
    items: list[DigiExamEffectiveItemV1]


class DigiExamIngestionOverlayAcceptedEntryV1(BaseModel):
    """Accepted overlay entry summary excluding raw overlay payloads."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    sequence: int = Field(ge=1)
    applied_fields: list[str]


class DigiExamIngestionOverlayRejectedEntryV1(BaseModel):
    """Rejected overlay entry summary with stable reason fields."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    sequence: int = Field(ge=1)
    reason_code: str
    message: str


class DigiExamIngestionOverlayReportV1(BaseModel):
    """Overlay application report emitted beside effective IR artifacts."""

    model_config = ConfigDict(extra="forbid")

    schema_version: IngestionOverlayReportSchemaVersion
    overlay_sha256: str
    source_ir_sha256: str
    accepted_entries: list[DigiExamIngestionOverlayAcceptedEntryV1]
    rejected_entries: list[DigiExamIngestionOverlayRejectedEntryV1]


OPENAPI_CONTRACT_COMPONENT_MODELS: tuple[type[BaseModel], ...] = (
    JobSpecV2,
    DigiExamIngestionOverlay,
    DigiExamMigrationBundleManifestV2,
    DigiExamTargetReadinessReportV1,
    DigiExamEffectiveExamV1,
    DigiExamIngestionOverlayReportV1,
)
