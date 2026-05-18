"""Source-neutral matching correction application contracts.

Purpose:
    Define the service-facing request, response, and application mapping for
    applying teacher-provided matching answer keys to `ExamAuthoringIR v1`
    interactions before target readiness is projected to consumers.

Relationships:
    - Consumes the Task 323 `ExamAuthoringMatchingManualAnswerKey` DTO.
    - Reuses `domain.exam_authoring_ir_contracts` for matching interaction
      validation and target-profile readiness.
    - Exposed by the v2 HTTP source-neutral matching apply route for
      Skriptoteket PR-0332 without widening DigiExam ingestion overlays.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringMatchingAnswerKey,
    ExamAuthoringMatchingChoice,
    ExamAuthoringMatchingInteraction,
    ExamAuthoringMatchingPair,
    ExamAuthoringSourceEvidence,
    validate_examnet_pdf_matching_profile,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_matching_manual_answer_key import (
    ExamAuthoringMatchingManualAnswerKey,
    apply_exam_authoring_matching_manual_answer_key,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)

ExamAuthoringMatchingTargetV1 = Literal["examnet_pdf", "qti_package"]
ExamAuthoringMatchingTargetReadinessV1 = Literal[
    "ready",
    "target_validation_failed",
    "unsupported_target_shape",
]
ExamAuthoringMatchingArtifactAvailabilityV1 = Literal["available", "unavailable"]


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


class ExamAuthoringMatchingManualAnswerKeyApplyRequest(BaseModel):
    """Request body for applying a matching manual answer key."""

    model_config = ConfigDict(extra="forbid")

    source_interaction: ExamAuthoringMatchingInteractionV1
    exam_authoring_matching_manual_answer_key: ExamAuthoringMatchingManualAnswerKey
    requested_targets: tuple[ExamAuthoringMatchingTargetV1, ...] = ("examnet_pdf", "qti_package")


class ExamAuthoringMatchingTargetReadinessRowV1(BaseModel):
    """Target readiness projection for a corrected matching interaction."""

    model_config = ConfigDict(extra="forbid")

    target: ExamAuthoringMatchingTargetV1
    readiness: ExamAuthoringMatchingTargetReadinessV1
    export_enabled: bool
    reason_code: str
    message_key: str


class ExamAuthoringMatchingArtifactAvailabilityRowV1(BaseModel):
    """Artifact availability projection for a corrected matching interaction."""

    model_config = ConfigDict(extra="forbid")

    artifact_key: ExamAuthoringMatchingTargetV1
    availability: ExamAuthoringMatchingArtifactAvailabilityV1
    unavailable_code: str | None = None


class ExamAuthoringMatchingManualAnswerKeyApplyResponse(BaseModel):
    """Producer-owned effective state returned after matching key application."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_matching_apply_result_v1"] = (
        "exam_authoring_matching_apply_result_v1"
    )
    effective_interaction: ExamAuthoringMatchingInteractionV1
    target_readiness: tuple[ExamAuthoringMatchingTargetReadinessRowV1, ...]
    artifact_availability: tuple[ExamAuthoringMatchingArtifactAvailabilityRowV1, ...]


def apply_matching_manual_answer_key_request(
    request_body: ExamAuthoringMatchingManualAnswerKeyApplyRequest,
) -> ExamAuthoringMatchingManualAnswerKeyApplyResponse:
    """Apply a request body and return producer-owned effective state."""

    source_interaction = _to_domain_interaction(request_body.source_interaction)
    effective_interaction = apply_exam_authoring_matching_manual_answer_key(
        submission=request_body.exam_authoring_matching_manual_answer_key,
        interaction=source_interaction,
        expected_source_item_fingerprint=request_body.source_interaction.source_item_fingerprint,
    )
    effective = _from_domain_interaction(
        effective_interaction,
        source_item_fingerprint=request_body.source_interaction.source_item_fingerprint,
    )
    readiness = tuple(
        _target_readiness(target=target, interaction=effective_interaction)
        for target in request_body.requested_targets
    )
    return ExamAuthoringMatchingManualAnswerKeyApplyResponse(
        effective_interaction=effective,
        target_readiness=readiness,
        artifact_availability=tuple(_artifact_availability(row) for row in readiness),
    )


def _target_readiness(
    *,
    target: ExamAuthoringMatchingTargetV1,
    interaction: ExamAuthoringMatchingInteraction,
) -> ExamAuthoringMatchingTargetReadinessRowV1:
    if target == "qti_package":
        return ExamAuthoringMatchingTargetReadinessRowV1(
            target=target,
            readiness="unsupported_target_shape",
            export_enabled=False,
            reason_code="examnet_qti_matching_import_unproven",
            message_key="exam_converter.target.matching.qti_import_unproven",
        )

    validation = validate_examnet_pdf_matching_profile(interaction)
    if validation.valid:
        return ExamAuthoringMatchingTargetReadinessRowV1(
            target=target,
            readiness="ready",
            export_enabled=True,
            reason_code="ready",
            message_key="exam_converter.target.matching.ready",
        )
    return ExamAuthoringMatchingTargetReadinessRowV1(
        target=target,
        readiness="target_validation_failed",
        export_enabled=False,
        reason_code=";".join(issue.reason_code.value for issue in validation.issues),
        message_key="exam_converter.target.matching.validation_failed",
    )


def _artifact_availability(
    readiness: ExamAuthoringMatchingTargetReadinessRowV1,
) -> ExamAuthoringMatchingArtifactAvailabilityRowV1:
    if readiness.export_enabled:
        return ExamAuthoringMatchingArtifactAvailabilityRowV1(
            artifact_key=readiness.target,
            availability="available",
        )
    return ExamAuthoringMatchingArtifactAvailabilityRowV1(
        artifact_key=readiness.target,
        availability="unavailable",
        unavailable_code=readiness.reason_code,
    )


def _to_domain_interaction(
    interaction: ExamAuthoringMatchingInteractionV1,
) -> ExamAuthoringMatchingInteraction:
    return ExamAuthoringMatchingInteraction(
        schema_version=interaction.schema_version,
        interaction_id=interaction.interaction_id,
        source_choices=tuple(_to_domain_choice(choice) for choice in interaction.source_choices),
        target_choices=tuple(_to_domain_choice(choice) for choice in interaction.target_choices),
        min_associations=interaction.min_associations,
        max_associations=interaction.max_associations,
        answer_key=ExamAuthoringMatchingAnswerKey(
            provenance=ExamAuthoringAnswerKeyProvenance(interaction.answer_key.provenance),
            pairs=tuple(
                ExamAuthoringMatchingPair(source_id=pair.source_id, target_id=pair.target_id)
                for pair in interaction.answer_key.pairs
            ),
        ),
        evidence=tuple(
            ExamAuthoringSourceEvidence(
                source_family=evidence.source_family,
                source_id=evidence.source_id,
                locator=evidence.locator,
            )
            for evidence in interaction.evidence
        ),
    )


def _from_domain_interaction(
    interaction: ExamAuthoringMatchingInteraction,
    *,
    source_item_fingerprint: str | None,
) -> ExamAuthoringMatchingInteractionV1:
    return ExamAuthoringMatchingInteractionV1(
        schema_version=interaction.schema_version,
        interaction_id=interaction.interaction_id,
        source_item_fingerprint=source_item_fingerprint,
        source_choices=tuple(_from_domain_choice(choice) for choice in interaction.source_choices),
        target_choices=tuple(_from_domain_choice(choice) for choice in interaction.target_choices),
        min_associations=interaction.min_associations,
        max_associations=interaction.max_associations,
        answer_key=ExamAuthoringMatchingAnswerKeyV1(
            provenance=interaction.answer_key.provenance.value,
            pairs=tuple(
                ExamAuthoringMatchingPairV1(source_id=pair.source_id, target_id=pair.target_id)
                for pair in interaction.answer_key.pairs
            ),
        ),
        evidence=tuple(
            ExamAuthoringSourceEvidenceV1(
                source_family=evidence.source_family,
                source_id=evidence.source_id,
                locator=evidence.locator,
            )
            for evidence in interaction.evidence
        ),
    )


def _to_domain_choice(choice: ExamAuthoringMatchingChoiceV1) -> ExamAuthoringMatchingChoice:
    return ExamAuthoringMatchingChoice(
        choice_id=choice.choice_id,
        order=choice.order,
        text=choice.text,
        match_min=choice.match_min,
        match_max=choice.match_max,
    )


def _from_domain_choice(choice: ExamAuthoringMatchingChoice) -> ExamAuthoringMatchingChoiceV1:
    return ExamAuthoringMatchingChoiceV1(
        choice_id=choice.choice_id,
        order=choice.order,
        text=choice.text,
        match_min=choice.match_min,
        match_max=choice.match_max,
    )
