"""Source-neutral matching manual answer-key producer contracts.

Purpose:
    Define the producer-ready DTO and application boundary for teacher-provided
    matching answer keys that target `ExamAuthoringIR v1` interactions.

Relationships:
    - Reuses `domain.exam_authoring_ir_contracts` for matching semantics and
      validation.
    - Exposed through `application.openapi_contracts_v2` for downstream
      Skriptoteket type generation.
    - Stays separate from DigiExam-specific ingestion overlays because `.dxe`
      sources do not carry canonical matching items.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringMatchingAnswerKey,
    ExamAuthoringMatchingInteraction,
    ExamAuthoringMatchingPair,
    ExamAuthoringMatchingValidationIssue,
    validate_exam_authoring_matching_interaction,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)

ExamAuthoringMatchingManualAnswerKeyProvenance: TypeAlias = Literal[
    "absent",
    "source_provided",
    "teacher_provided",
    "reviewed",
]


class ExamAuthoringMatchingManualAnswerKeyError(ValueError):
    """Typed failure raised before a matching manual key can affect IR."""

    def __init__(self, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


class ExamAuthoringMatchingManualAnswerKeyPair(BaseModel):
    """One submitted source-to-target matching answer pair."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)


class ExamAuthoringMatchingManualAnswerKeyPayload(BaseModel):
    """Whole-key matching answer payload with source-neutral provenance."""

    model_config = ConfigDict(extra="forbid")

    provenance: ExamAuthoringMatchingManualAnswerKeyProvenance
    pairs: tuple[ExamAuthoringMatchingManualAnswerKeyPair, ...] = ()

    @model_validator(mode="after")
    def _validate_pair_provenance(self) -> Self:
        if self.provenance == "absent" and self.pairs:
            raise ValueError("absent matching provenance cannot carry directed pairs")
        if self.provenance != "absent" and not self.pairs:
            raise ValueError("trusted matching provenance requires at least one directed pair")
        return self


class ExamAuthoringMatchingManualAnswerKey(BaseModel):
    """Source-neutral matching manual answer-key submission."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: ExamAuthoringIrSchemaVersion = EXAM_AUTHORING_IR_SCHEMA_VERSION
    kind: Literal["matching"]
    interaction_id: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)
    answer_key: ExamAuthoringMatchingManualAnswerKeyPayload


def parse_exam_authoring_matching_manual_answer_key_json(
    payload: bytes,
) -> ExamAuthoringMatchingManualAnswerKey:
    """Parse one matching manual answer-key submission from JSON bytes."""

    try:
        return ExamAuthoringMatchingManualAnswerKey.model_validate_json(payload)
    except ValidationError as exc:
        raise ExamAuthoringMatchingManualAnswerKeyError(
            "exam_authoring_matching_manual_answer_key_invalid",
            "Matching manual answer-key submission failed schema validation.",
            {"errors": exc.errors(include_context=False)},
        ) from exc


def apply_exam_authoring_matching_manual_answer_key(
    *,
    submission: ExamAuthoringMatchingManualAnswerKey,
    interaction: ExamAuthoringMatchingInteraction,
    expected_source_item_fingerprint: str | None = None,
) -> ExamAuthoringMatchingInteraction:
    """Validate and apply a matching manual key to one neutral interaction."""

    _validate_submission_binding(
        submission=submission,
        interaction=interaction,
        expected_source_item_fingerprint=expected_source_item_fingerprint,
    )
    updated = replace(
        interaction,
        answer_key=ExamAuthoringMatchingAnswerKey(
            provenance=ExamAuthoringAnswerKeyProvenance(submission.answer_key.provenance),
            pairs=tuple(
                ExamAuthoringMatchingPair(
                    source_id=pair.source_id,
                    target_id=pair.target_id,
                )
                for pair in submission.answer_key.pairs
            ),
        ),
    )
    validation = validate_exam_authoring_matching_interaction(updated)
    if not validation.valid:
        raise ExamAuthoringMatchingManualAnswerKeyError(
            "exam_authoring_matching_manual_answer_key_rejected",
            "Matching manual answer-key submission failed neutral IR validation.",
            {"issues": tuple(_issue_payload(issue) for issue in validation.issues)},
        )
    return updated


def _validate_submission_binding(
    *,
    submission: ExamAuthoringMatchingManualAnswerKey,
    interaction: ExamAuthoringMatchingInteraction,
    expected_source_item_fingerprint: str | None,
) -> None:
    if submission.schema_version != interaction.schema_version:
        raise ExamAuthoringMatchingManualAnswerKeyError(
            "stale_exam_authoring_schema_version",
            "Matching manual answer-key schema version does not match the interaction.",
            {
                "submitted_schema_version": submission.schema_version,
                "expected_schema_version": interaction.schema_version,
            },
        )
    if submission.interaction_id != interaction.interaction_id:
        raise ExamAuthoringMatchingManualAnswerKeyError(
            "stale_matching_interaction_id",
            "Matching manual answer-key interaction ID does not match the source interaction.",
            {
                "submitted_interaction_id": submission.interaction_id,
                "expected_interaction_id": interaction.interaction_id,
            },
        )
    if (
        expected_source_item_fingerprint is not None
        and submission.source_item_fingerprint != expected_source_item_fingerprint
    ):
        raise ExamAuthoringMatchingManualAnswerKeyError(
            "stale_matching_source_item_fingerprint",
            "Matching manual answer-key source fingerprint does not match the source item.",
            {
                "submitted_source_item_fingerprint": submission.source_item_fingerprint,
                "expected_source_item_fingerprint": expected_source_item_fingerprint,
            },
        )


def _issue_payload(issue: ExamAuthoringMatchingValidationIssue) -> dict[str, str | None]:
    return {
        "reason_code": issue.reason_code.value,
        "message": issue.message,
        "source_id": issue.source_id,
        "target_id": issue.target_id,
    }
