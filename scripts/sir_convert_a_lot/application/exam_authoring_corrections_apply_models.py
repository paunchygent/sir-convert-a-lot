"""Source-neutral exam authoring correction apply DTOs.

Purpose:
    Publish the request, response, source-state, correction-entry, readiness,
    and report DTOs used by the unified exam-authoring correction apply route.

Relationships:
    - Used by `application.exam_authoring_corrections_apply_contracts` for
      runtime application semantics.
    - Exposed by `interfaces.http_routes_exam_authoring_corrections_v2` through
      FastAPI and generated OpenAPI.
    - Mirrors the accepted ADR-0011 and Task 327 source-neutral correction
      contract without depending on source-adapter-specific overlay names.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)

ExamAuthoringCorrectionTargetV1 = Literal["examnet_pdf", "qti_package"]
ExamAuthoringCorrectionReadinessV1 = Literal[
    "ready",
    "target_validation_failed",
    "unsupported_target_shape",
]
ExamAuthoringCorrectionArtifactAvailabilityV1 = Literal["available", "unavailable"]
ExamAuthoringAnswerKeySubmissionOriginV1 = Literal[
    "teacher_authored",
    "accepted_advisory_candidate",
    "teacher_edited_advisory_candidate",
]


class ExamAuthoringCorrectionSourceBindingV1(BaseModel):
    """Request-level binding to the producer-returned authoring state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_authoring_schema_version: ExamAuthoringIrSchemaVersion
    source_state_sha256: str = Field(min_length=1)
    source_bundle_id: str | None = Field(default=None, min_length=1)
    source_file_sha256: str | None = Field(default=None, min_length=1)


class ExamAuthoringSourceEvidenceV1(BaseModel):
    """Source-neutral evidence reference for an authoring interaction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_family: str = Field(min_length=1)
    source_id: str | None = Field(default=None, min_length=1)
    locator: str | None = Field(default=None, min_length=1)


class ExamAuthoringMatchingChoiceV1(BaseModel):
    """One ordered source or target choice in a matching interaction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    choice_id: str = Field(min_length=1)
    order: int
    text: str = Field(min_length=1)
    match_min: int
    match_max: int


class ExamAuthoringMatchingPairV1(BaseModel):
    """One directed source-to-target matching pair."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)


class ExamAuthoringMatchingAnswerKeyV1(BaseModel):
    """Source-neutral matching answer key for effective authoring state."""

    model_config = ConfigDict(extra="forbid")

    provenance: Literal["absent", "source_provided", "teacher_provided", "reviewed", "mixed"]
    pairs: tuple[ExamAuthoringMatchingPairV1, ...] = ()


class ExamAuthoringMatchingInteractionV1(BaseModel):
    """Source-neutral matching interaction carried by a producer state surface."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: ExamAuthoringIrSchemaVersion = EXAM_AUTHORING_IR_SCHEMA_VERSION
    interaction_id: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)
    source_choices: tuple[ExamAuthoringMatchingChoiceV1, ...]
    target_choices: tuple[ExamAuthoringMatchingChoiceV1, ...]
    min_associations: int
    max_associations: int
    answer_key: ExamAuthoringMatchingAnswerKeyV1
    evidence: tuple[ExamAuthoringSourceEvidenceV1, ...] = ()


class ExamAuthoringCorrectionSourceItemV1(BaseModel):
    """One producer-returned source item used for correction binding."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)
    matching_interactions: tuple[ExamAuthoringMatchingInteractionV1, ...] = ()


class ExamAuthoringCorrectionSourceStateV1(BaseModel):
    """Sanitized producer-returned state used for correction validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["exam_authoring_correction_source_state_v1"] = (
        "exam_authoring_correction_source_state_v1"
    )
    source_authoring_schema_version: ExamAuthoringIrSchemaVersion
    source_state_sha256: str = Field(min_length=1)
    items: tuple[ExamAuthoringCorrectionSourceItemV1, ...]


class ExamAuthoringCandidateLineageV1(BaseModel):
    """Bounded advisory-candidate lineage without raw provider data."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    completion_report_sha256: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    candidate_payload_digest: str = Field(min_length=1)
    provider_profile_id: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    prompt_template_version: str = Field(min_length=1)
    validation_state: Literal["valid"]


class ExamAuthoringCorrectionEntryBaseV1(BaseModel):
    """Common binding fields for every correction entry."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(min_length=1)
    entry_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)


class ExamAuthoringItemTextPatchOperationV1(BaseModel):
    """One visible text patch operation for future source-neutral correction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field: Literal[
        "item_title",
        "stem_html",
        "prompt_html",
        "body_html",
        "visible_option_text",
        "gap_prompt_text",
    ]
    value: str = Field(min_length=1)
    choice_id: str | None = Field(default=None, min_length=1)
    gap_id: str | None = Field(default=None, min_length=1)


class ExamAuthoringItemTextPatchCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Visible item text patch entry reserved for a later implementation slice."""

    kind: Literal["item_text_patch"]
    patches: tuple[ExamAuthoringItemTextPatchOperationV1, ...] = Field(min_length=1)


class ExamAuthoringPointCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Point correction entry reserved for unified runtime migration."""

    kind: Literal["point_correction"]
    max_score: int = Field(gt=0)


class ExamAuthoringManualChoiceAnswerKeyCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Manual choice answer-key entry reserved for unified runtime migration."""

    kind: Literal["manual_choice_answer_key"]
    interaction_id: str = Field(min_length=1)
    submission_origin: ExamAuthoringAnswerKeySubmissionOriginV1
    correct_choice_ids: tuple[str, ...] = Field(min_length=1)
    candidate_lineage: ExamAuthoringCandidateLineageV1 | None = None


class ExamAuthoringGapAnswerV1(BaseModel):
    """Accepted values for one source-bound gap."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    gap_id: str = Field(min_length=1)
    accepted_values: tuple[str, ...] = Field(min_length=1)


class ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1(
    ExamAuthoringCorrectionEntryBaseV1
):
    """Manual gap/open-cloze answer-key entry reserved for unified migration."""

    kind: Literal["manual_gap_open_cloze_answer_key"]
    interaction_id: str = Field(min_length=1)
    submission_origin: ExamAuthoringAnswerKeySubmissionOriginV1
    gap_answers: tuple[ExamAuthoringGapAnswerV1, ...] = Field(min_length=1)
    candidate_lineage: ExamAuthoringCandidateLineageV1 | None = None


class ExamAuthoringManualMatchingAnswerKeyCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Manual matching answer-key correction implemented by Task 330."""

    kind: Literal["manual_matching_answer_key"]
    item_type: Literal["matching"]
    interaction_id: str = Field(min_length=1)
    submission_origin: ExamAuthoringAnswerKeySubmissionOriginV1
    pairs: tuple[ExamAuthoringMatchingPairV1, ...] = Field(min_length=1)
    candidate_lineage: ExamAuthoringCandidateLineageV1 | None = None

    @model_validator(mode="after")
    def _validate_candidate_lineage(self) -> "ExamAuthoringManualMatchingAnswerKeyCorrectionV1":
        if self.submission_origin != "teacher_authored" and self.candidate_lineage is None:
            raise ValueError("advisory-origin matching corrections require candidate lineage")
        return self


class ExamAuthoringReviewDecisionCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Review decision entry reserved for unified runtime migration."""

    kind: Literal["review_decision"]
    decision: Literal["accept_current_state_for_export"]
    decision_id: str = Field(min_length=1)
    accepted_targets: tuple[ExamAuthoringCorrectionTargetV1, ...] = Field(min_length=1)
    note: str | None = Field(default=None, min_length=1)


class ExamAuthoringCandidateSuppressionCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Candidate suppression entry reserved for unified runtime migration."""

    kind: Literal["candidate_suppression"]
    candidate_lineage: ExamAuthoringCandidateLineageV1
    suppression_reason: Literal["teacher_rejected_candidate"]


ExamAuthoringCorrectionEntryV1: TypeAlias = Annotated[
    ExamAuthoringItemTextPatchCorrectionV1
    | ExamAuthoringPointCorrectionV1
    | ExamAuthoringManualChoiceAnswerKeyCorrectionV1
    | ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1
    | ExamAuthoringManualMatchingAnswerKeyCorrectionV1
    | ExamAuthoringReviewDecisionCorrectionV1
    | ExamAuthoringCandidateSuppressionCorrectionV1,
    Field(discriminator="kind"),
]


class ExamAuthoringCorrectionsApplyRequestV1(BaseModel):
    """Request body for applying a source-neutral correction batch."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_corrections_apply_request_v1"] = (
        "exam_authoring_corrections_apply_request_v1"
    )
    request_id: str = Field(min_length=1)
    source_binding: ExamAuthoringCorrectionSourceBindingV1
    source_authoring_state: ExamAuthoringCorrectionSourceStateV1
    corrections: tuple[ExamAuthoringCorrectionEntryV1, ...] = Field(min_length=1)
    requested_targets: tuple[ExamAuthoringCorrectionTargetV1, ...] = (
        "examnet_pdf",
        "qti_package",
    )


class ExamAuthoringEffectiveStateV1(BaseModel):
    """Effective authoring state projection after accepted corrections."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_effective_state_v1"] = (
        "exam_authoring_effective_state_v1"
    )
    effective_state_sha256: str = Field(min_length=1)
    items: tuple[ExamAuthoringCorrectionSourceItemV1, ...]


class ExamAuthoringCorrectionAcceptedEntryV1(BaseModel):
    """Accepted correction summary without raw submitted payloads."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entry_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    applied_fields: tuple[str, ...]
    effective_provenance: str | None = None


class ExamAuthoringCorrectionRejectedEntryV1(BaseModel):
    """Rejected correction summary without raw submitted payloads."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entry_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    reason_code: str = Field(min_length=1)
    message_key: str = Field(min_length=1)
    teacher_action: str = Field(min_length=1)
    retryable: bool


class ExamAuthoringCorrectionReportV1(BaseModel):
    """Accepted and rejected correction report for consumers."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_correction_report_v1"] = (
        "exam_authoring_correction_report_v1"
    )
    accepted_entries: tuple[ExamAuthoringCorrectionAcceptedEntryV1, ...]
    rejected_entries: tuple[ExamAuthoringCorrectionRejectedEntryV1, ...]


class ExamAuthoringCorrectionTargetReadinessRowV1(BaseModel):
    """Target readiness projection for corrected authoring state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target: ExamAuthoringCorrectionTargetV1
    readiness: ExamAuthoringCorrectionReadinessV1
    export_enabled: bool
    reason_code: str = Field(min_length=1)
    message_key: str = Field(min_length=1)
    item_id: str | None = Field(default=None, min_length=1)
    sequence: int | None = Field(default=None, ge=1)


class ExamAuthoringCorrectionTargetReadinessReportV1(BaseModel):
    """Source-neutral target readiness report for a correction batch."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["target_readiness_report_v1"] = "target_readiness_report_v1"
    targets: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]


class ExamAuthoringCorrectionArtifactAvailabilityRowV1(BaseModel):
    """Artifact availability projection for corrected authoring state."""

    model_config = ConfigDict(extra="forbid")

    artifact_key: ExamAuthoringCorrectionTargetV1
    availability: ExamAuthoringCorrectionArtifactAvailabilityV1
    unavailable_code: str | None = None


class ExamAuthoringCorrectionsApplyResultV1(BaseModel):
    """Producer-owned result returned after correction application."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_corrections_apply_result_v1"] = (
        "exam_authoring_corrections_apply_result_v1"
    )
    request_id: str = Field(min_length=1)
    source_binding: ExamAuthoringCorrectionSourceBindingV1
    effective_state: ExamAuthoringEffectiveStateV1
    correction_report: ExamAuthoringCorrectionReportV1
    target_readiness: ExamAuthoringCorrectionTargetReadinessReportV1
    artifact_availability: tuple[ExamAuthoringCorrectionArtifactAvailabilityRowV1, ...]
