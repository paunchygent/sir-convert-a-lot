"""Source-state DTOs for unified exam-authoring corrections.

Purpose:
    Define the sanitized producer-state surface that correction consumers echo
    when requesting source-neutral exam-authoring corrections.

Relationships:
    - Consumed by `application.exam_authoring_corrections_apply_models` as the
      request and result source-state boundary.
    - Produced by `application.exam_authoring_correction_source_state_projection`
      from source-owned runtime state.
    - Validated and signed by the source-state issuer before downstream
      consumers can apply corrections.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)

ExamAuthoringAnswerKeyProvenanceV1 = Literal[
    "absent",
    "source_provided",
    "teacher_provided",
    "reviewed",
    "mixed",
]


class ExamAuthoringCorrectionSourceBindingV1(BaseModel):
    """Request-level binding to the producer-returned authoring state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_authoring_schema_version: ExamAuthoringIrSchemaVersion
    source_state_sha256: str = Field(min_length=1)
    source_state_signature: str = Field(min_length=1)
    source_bundle_id: str | None = Field(default=None, min_length=1)
    source_file_sha256: str | None = Field(default=None, min_length=1)


class ExamAuthoringSourceEvidenceV1(BaseModel):
    """Source-neutral evidence reference for an authoring interaction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_family: str = Field(min_length=1)
    source_id: str | None = Field(default=None, min_length=1)
    locator: str | None = Field(default=None, min_length=1)


class ExamAuthoringChoiceOptionV1(BaseModel):
    """One source-owned visible option in a choice interaction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    choice_id: str = Field(min_length=1)
    source_id: str | None = Field(default=None, min_length=1)
    order: int = Field(ge=1)
    text: str = Field(min_length=1)


class ExamAuthoringChoiceAnswerKeyV1(BaseModel):
    """Current source-owned choice answer-key state."""

    model_config = ConfigDict(extra="forbid")

    provenance: ExamAuthoringAnswerKeyProvenanceV1
    correct_choice_ids: tuple[str, ...] = ()


class ExamAuthoringChoiceInteractionV1(BaseModel):
    """Source-neutral choice interaction carried by source state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: ExamAuthoringIrSchemaVersion = EXAM_AUTHORING_IR_SCHEMA_VERSION
    interaction_id: str = Field(min_length=1)
    interaction_kind: Literal["single_choice", "multiple_choice", "multiple_response"]
    choices: tuple[ExamAuthoringChoiceOptionV1, ...]
    min_correct_choices: int = Field(ge=0)
    max_correct_choices: int = Field(ge=0)
    answer_key: ExamAuthoringChoiceAnswerKeyV1
    evidence: tuple[ExamAuthoringSourceEvidenceV1, ...] = ()


class ExamAuthoringGapPromptBindingV1(BaseModel):
    """One source-owned prompt/body locator for a gap placeholder."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal["html_attribute", "source_locator"]
    locator: str = Field(min_length=1)


class ExamAuthoringGapV1(BaseModel):
    """One source-owned gap/open-cloze placeholder."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str = Field(min_length=1)
    display_order: int = Field(ge=1)
    prompt_binding: ExamAuthoringGapPromptBindingV1
    required_for_auto_evaluation: bool
    evidence: tuple[ExamAuthoringSourceEvidenceV1, ...] = ()


class ExamAuthoringGapAcceptedValueV1(BaseModel):
    """One current accepted value bound to a source-owned gap."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    gap_id: str = Field(min_length=1)
    value: str = Field(min_length=1)
    provenance: ExamAuthoringAnswerKeyProvenanceV1
    evidence: tuple[ExamAuthoringSourceEvidenceV1, ...] = ()


class ExamAuthoringGapAnswerKeyV1(BaseModel):
    """Current source-owned gap/open-cloze answer-key state."""

    model_config = ConfigDict(extra="forbid")

    provenance: ExamAuthoringAnswerKeyProvenanceV1
    accepted_values: tuple[ExamAuthoringGapAcceptedValueV1, ...] = ()


class ExamAuthoringGapOpenClozeInteractionV1(BaseModel):
    """Source-neutral gap/open-cloze interaction carried by source state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: ExamAuthoringIrSchemaVersion = EXAM_AUTHORING_IR_SCHEMA_VERSION
    interaction_id: str = Field(min_length=1)
    gaps: tuple[ExamAuthoringGapV1, ...]
    normalization_profile: str = Field(min_length=1)
    answer_key: ExamAuthoringGapAnswerKeyV1
    evidence: tuple[ExamAuthoringSourceEvidenceV1, ...] = ()


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

    provenance: ExamAuthoringAnswerKeyProvenanceV1
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
    title: str | None = Field(default=None, min_length=1)
    prompt_html: str | None = Field(default=None, min_length=1)
    prompt_lines: tuple[str, ...] = ()
    max_score: int | None = Field(default=None, ge=0)
    choice_interactions: tuple[ExamAuthoringChoiceInteractionV1, ...] = ()
    gap_open_cloze_interactions: tuple[ExamAuthoringGapOpenClozeInteractionV1, ...] = ()
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


class ExamAuthoringCorrectionSourceStateIssueRequestV1(BaseModel):
    """Producer request for issuing a signed correction source-state bundle."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_correction_source_state_issue_request_v1"] = (
        "exam_authoring_correction_source_state_issue_request_v1"
    )
    job_id: str = Field(min_length=1)
    expected_source_state_sha256: str | None = Field(default=None, min_length=1)


class ExamAuthoringCorrectionSourceStateIssueResultV1(BaseModel):
    """Signed source-state bundle that downstream consumers can echo."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_correction_source_state_issue_result_v1"] = (
        "exam_authoring_correction_source_state_issue_result_v1"
    )
    source_binding: ExamAuthoringCorrectionSourceBindingV1
    source_authoring_state: ExamAuthoringCorrectionSourceStateV1
