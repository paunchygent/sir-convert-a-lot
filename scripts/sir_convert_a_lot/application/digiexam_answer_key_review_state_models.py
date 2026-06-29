"""DTOs for compact DigiExam answer-key review-state projection.

Purpose:
    Publish strict Pydantic models and typed builder inputs for the
    `digiexam_answer_key_review_state_v1` producer contract.

Relationships:
    - Consumed by `application.digiexam_answer_key_review_state` for projection
      building.
    - Re-exported through OpenAPI and correction apply responses for
      Skriptoteket contract generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
    AnswerKeyReviewStateSchemaVersion,
)

DigiExamAnswerKeyReviewStateCodeV1: TypeAlias = Literal[
    "review_required",
    "review_complete",
    "teacher_modified",
    "validation_required",
]
DigiExamAnswerKeyOriginCodeV1: TypeAlias = Literal[
    "none",
    "source_provided",
    "reviewed_advisory",
    "teacher_authored",
    "teacher_edited_advisory",
    "mixed",
]
DigiExamAnswerKeyReviewReasonCodeV1: TypeAlias = Literal[
    "source_answer_key_present",
    "advisory_candidate_pending",
    "reviewed_advisory_accepted",
    "teacher_answer_key_present",
    "teacher_edited_advisory_candidate",
    "manual_answer_key_required",
    "no_correct_choice_selected",
    "required_gap_accepted_values_missing",
    "unsupported_item_type",
    "unsupported_target_shape",
    "target_validation_failed",
    "provider_unavailable",
    "correction_rejected",
    "stale_source_state",
    "replay_artifact_unavailable",
    "matching_source_state_unavailable",
]
DigiExamAnswerKeyCorrectionAffordanceV1: TypeAlias = Literal[
    "item_text_patch",
    "point_correction",
    "manual_choice_answer_key",
    "manual_gap_open_cloze_answer_key",
    "manual_matching_answer_key",
]
DigiExamAnswerKeyReviewSubmissionOriginV1: TypeAlias = Literal[
    "teacher_authored",
    "accepted_advisory_candidate",
    "teacher_edited_advisory_candidate",
]


@dataclass(frozen=True)
class DigiExamAnswerKeyReviewAdvisoryCandidateInput:
    """Bounded advisory row consumed by the compact projection builder."""

    item_id: str
    sequence: int
    candidate_id: str
    candidate_payload_digest: str
    provider_profile_id: str
    schema_name: str
    schema_version: str
    prompt_template_version: str
    validation_state: str


@dataclass(frozen=True)
class DigiExamAnswerKeyReviewCorrectionOutcomeInput:
    """Accepted or rejected correction outcome consumed by the projection."""

    item_id: str
    sequence: int
    accepted: bool
    submission_origin: DigiExamAnswerKeyReviewSubmissionOriginV1 | None = None


@dataclass(frozen=True)
class DigiExamAnswerKeyReviewTargetReadinessInput:
    """Target-readiness row subset needed by the compact projection."""

    target: str
    export_enabled: bool
    reason_code: str
    item_id: str | None = None
    sequence: int | None = None
    artifact_key: str | None = None


class DigiExamAnswerKeyReviewProvenanceDetailV1(BaseModel):
    """Bounded detail-only advisory lineage without raw provider data."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str = Field(min_length=1)
    candidate_payload_digest: str = Field(min_length=1)
    provider_profile_id: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    prompt_template_version: str = Field(min_length=1)
    validation_state: Literal["valid"]


class DigiExamAnswerKeyReviewReplayArtifactReferenceV1(BaseModel):
    """Replay-scoped target artifact reference returned after correction rendering."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target: Literal["examnet_pdf", "qti_package"]
    artifact_key: Literal["correction_replay_examnet_pdf", "correction_replay_qti_package"]


class DigiExamAnswerKeyReviewStateItemV1(BaseModel):
    """One item-addressable answer-key review-state row."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)
    choice_interaction_ids: tuple[str, ...] = ()
    choice_ids: tuple[str, ...] = ()
    gap_interaction_ids: tuple[str, ...] = ()
    gap_ids: tuple[str, ...] = ()
    correction_affordances: tuple[DigiExamAnswerKeyCorrectionAffordanceV1, ...] = ()
    review_state: DigiExamAnswerKeyReviewStateCodeV1
    current_key_origin: DigiExamAnswerKeyOriginCodeV1
    reasons: tuple[DigiExamAnswerKeyReviewReasonCodeV1, ...] = Field(min_length=1)
    message_key: str = Field(min_length=1)
    provenance_detail: DigiExamAnswerKeyReviewProvenanceDetailV1 | None = None
    replay_artifact_references: tuple[DigiExamAnswerKeyReviewReplayArtifactReferenceV1, ...] = ()


class DigiExamAnswerKeyReviewStateV1(BaseModel):
    """Top-level compact review-state report for DigiExam answer keys."""

    model_config = ConfigDict(extra="forbid")

    schema_version: AnswerKeyReviewStateSchemaVersion = ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION
    items: tuple[DigiExamAnswerKeyReviewStateItemV1, ...]
