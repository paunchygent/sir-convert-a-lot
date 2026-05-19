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
    AnswerKeyCompletionReportSchemaVersion,
    DigiExamChoiceAnswerKeyDecisionSchemaVersion,
    DigiExamEffectiveExamSchemaVersion,
    DigiExamGapFillAnswerKeyDecisionSchemaVersion,
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
    lineage: "DigiExamEffectiveAnswerKeyLineageV1 | None" = None


class DigiExamEffectiveAnswerKeyLineageV1(BaseModel):
    """Bounded reviewed-completion lineage in effective exam artifacts."""

    model_config = ConfigDict(extra="forbid")

    completion_report_sha256: str
    candidate_id: str
    candidate_payload_digest: str
    provider_profile_id: str
    schema_name: str
    schema_version: str
    prompt_template_version: str
    validation_state: Literal["valid"]
    review_decision_id: str
    review_outcome: Literal["accepted_unchanged", "teacher_edited"]


class DigiExamEffectiveItemPatchSummaryV1(BaseModel):
    """Visible effective item patch summary for teacher-review consumers."""

    model_config = ConfigDict(extra="forbid")

    changed_fields: list[str] = Field(default_factory=list)
    patched_alternative_ids: list[int] = Field(default_factory=list)
    patched_gap_ids: list[str] = Field(default_factory=list)


class DigiExamEffectivePointCorrectionV1(BaseModel):
    """Applied item point correction in effective exam artifacts."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["item_points"]
    source_max_score: int | None = None
    effective_max_score: int = Field(gt=0)
    source_item_fingerprint: str


class DigiExamEffectiveItemV1(BaseModel):
    """One item summary in current effective exam artifacts."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    sequence: int = Field(ge=1)
    item_type: str
    source_item_fingerprint: str
    effective_answer_key: DigiExamEffectiveAnswerKeyV1 | None = None
    effective_item_patch: DigiExamEffectiveItemPatchSummaryV1 | None = None
    effective_point_correction: DigiExamEffectivePointCorrectionV1 | None = None
    applied_overlay_entry_ids: list[str] = Field(default_factory=list)


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


class StructuredLLMProviderErrorDiagnosticV1(BaseModel):
    """Redacted upstream provider HTTP error diagnostic."""

    model_config = ConfigDict(extra="forbid")

    status_code: int | None = None
    request_id: str | None = None
    error_type: str | None = None
    error_code: str | None = None
    error_param: str | None = None
    message_sha256: str | None = None


class DigiExamAnswerKeyCompletionReportItemV1(BaseModel):
    """One advisory answer-key candidate lineage report item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    sequence: int = Field(ge=1)
    item_type: str
    decision_state: Literal["suggested", "manual_follow_up_required", "skipped"]
    validation_state: Literal["valid", "invalid", "manual_follow_up_required", "skipped"]
    candidate_id: str | None = None
    candidate_payload_digest: str | None = None
    answer_payload: dict[str, object] | None = None
    provider_profile_id: str | None = None
    model_profile: str | None = None
    schema_name: (
        DigiExamChoiceAnswerKeyDecisionSchemaVersion
        | DigiExamGapFillAnswerKeyDecisionSchemaVersion
        | None
    ) = None
    schema_version: (
        DigiExamChoiceAnswerKeyDecisionSchemaVersion
        | DigiExamGapFillAnswerKeyDecisionSchemaVersion
        | None
    ) = None
    prompt_template_version: str | None = None
    backend_status: str
    backend_failure_code: str | None = None
    provider_error_diagnostic: StructuredLLMProviderErrorDiagnosticV1 | None = None


class DigiExamAnswerKeyCompletionProviderLineageV1(BaseModel):
    """Report-level admitted provider route lineage."""

    model_config = ConfigDict(extra="forbid")

    provider_family: str
    provider_profile_id: str
    model: str
    endpoint_kind: str
    output_mode: str
    reasoning_effort: str | None = None
    text_verbosity: str | None = None
    settings_version: int = Field(gt=0)
    route_class: str
    route_decision: str
    remote_provider_authorized: bool


class DigiExamAnswerKeyCompletionReportV1(BaseModel):
    """Advisory answer-key completion report without source provenance."""

    model_config = ConfigDict(extra="forbid")

    schema_version: AnswerKeyCompletionReportSchemaVersion
    job_id: str
    completion_mode: Literal["local_llm_suggest_missing_machine_marked"]
    provider_lineage: DigiExamAnswerKeyCompletionProviderLineageV1 | None = None
    items: list[DigiExamAnswerKeyCompletionReportItemV1]


OPENAPI_CONTRACT_COMPONENT_MODELS: tuple[type[BaseModel], ...] = (
    JobSpecV2,
    DigiExamIngestionOverlay,
    DigiExamMigrationBundleManifestV2,
    DigiExamTargetReadinessReportV1,
    DigiExamEffectiveExamV1,
    DigiExamIngestionOverlayReportV1,
    DigiExamAnswerKeyCompletionReportV1,
)
