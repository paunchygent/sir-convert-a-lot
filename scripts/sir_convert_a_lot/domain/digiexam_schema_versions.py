"""DigiExam migration schema-version authority.

Purpose:
    Centralize the public DigiExam migration artifact schema versions shared by
    parser IR, ingestion overlays, effective exams, migration bundles, target
    readiness reports, and OpenAPI publication.

Relationships:
    - Imported by DigiExam domain contracts and API DTOs that expose artifact
      schema versions.
    - Exported through the OpenAPI contract so downstream consumers can bind to
      generated constants instead of copying version strings.
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

DigiExamIntermediateExamSchemaVersion: TypeAlias = Literal["digiexam_intermediate_exam_v3"]
DigiExamIrManifestSchemaVersion: TypeAlias = Literal["digiexam_ir_manifest_v3"]
DigiExamIngestionOverlaySchemaVersion: TypeAlias = Literal["digiexam_ingestion_overlay_v2"]
DigiExamEffectiveExamSchemaVersion: TypeAlias = Literal["digiexam_effective_exam_v2"]
DigiExamMigrationBundleSchemaVersion: TypeAlias = Literal["digiexam_migration_bundle_v3"]
TargetReadinessReportSchemaVersion: TypeAlias = Literal["target_readiness_report_v1"]
AnswerKeyReviewStateSchemaVersion: TypeAlias = Literal["digiexam_answer_key_review_state_v1"]
IngestionOverlayReportSchemaVersion: TypeAlias = Literal["ingestion_overlay_report_v1"]
AnswerKeyCompletionReportSchemaVersion: TypeAlias = Literal["answer_key_completion_report_v1"]
DigiExamChoiceAnswerKeyDecisionSchemaVersion: TypeAlias = Literal[
    "digiexam_choice_answer_key_decision_v1"
]
DigiExamGapFillAnswerKeyDecisionSchemaVersion: TypeAlias = Literal[
    "digiexam_gap_fill_answer_key_decision_v1"
]

DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION: Final[DigiExamIntermediateExamSchemaVersion] = (
    "digiexam_intermediate_exam_v3"
)
DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION: Final[DigiExamIrManifestSchemaVersion] = (
    "digiexam_ir_manifest_v3"
)
DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION: Final[DigiExamIngestionOverlaySchemaVersion] = (
    "digiexam_ingestion_overlay_v2"
)
DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION: Final[DigiExamEffectiveExamSchemaVersion] = (
    "digiexam_effective_exam_v2"
)
DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION: Final[DigiExamMigrationBundleSchemaVersion] = (
    "digiexam_migration_bundle_v3"
)
TARGET_READINESS_REPORT_SCHEMA_VERSION: Final[TargetReadinessReportSchemaVersion] = (
    "target_readiness_report_v1"
)
ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION: Final[AnswerKeyReviewStateSchemaVersion] = (
    "digiexam_answer_key_review_state_v1"
)
INGESTION_OVERLAY_REPORT_SCHEMA_VERSION: Final[IngestionOverlayReportSchemaVersion] = (
    "ingestion_overlay_report_v1"
)
ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION: Final[AnswerKeyCompletionReportSchemaVersion] = (
    "answer_key_completion_report_v1"
)
DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION: Final[
    DigiExamChoiceAnswerKeyDecisionSchemaVersion
] = "digiexam_choice_answer_key_decision_v1"
DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION: Final[
    DigiExamGapFillAnswerKeyDecisionSchemaVersion
] = "digiexam_gap_fill_answer_key_decision_v1"


def digiexam_schema_version_extension() -> dict[str, str]:
    """Return the OpenAPI extension payload for downstream code generation."""

    return {
        "intermediate_exam": DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
        "ir_manifest": DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
        "ingestion_overlay": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
        "effective_exam": DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
        "migration_bundle": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        "target_readiness_report": TARGET_READINESS_REPORT_SCHEMA_VERSION,
        "answer_key_review_state_report": ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
        "ingestion_overlay_report": INGESTION_OVERLAY_REPORT_SCHEMA_VERSION,
        "answer_key_completion_report": ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
        "choice_answer_key_decision": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        "gap_fill_answer_key_decision": DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    }
