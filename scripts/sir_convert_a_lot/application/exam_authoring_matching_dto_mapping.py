"""Matching DTO mapping for exam authoring correction application.

Purpose:
    Convert between unified correction-route matching DTOs and the domain
    matching interaction contracts used for validation and target readiness.

Relationships:
    - Used by `application.exam_authoring_corrections_apply_contracts`.
    - Keeps HTTP/application DTO projection separate from matching domain
      validation and answer-key application.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringMatchingAnswerKeyV1,
    ExamAuthoringMatchingChoiceV1,
    ExamAuthoringMatchingInteractionV1,
    ExamAuthoringMatchingPairV1,
    ExamAuthoringSourceEvidenceV1,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringMatchingAnswerKey,
    ExamAuthoringMatchingChoice,
    ExamAuthoringMatchingInteraction,
    ExamAuthoringMatchingPair,
    ExamAuthoringSourceEvidence,
)


def to_domain_matching_interaction(
    interaction: ExamAuthoringMatchingInteractionV1,
) -> ExamAuthoringMatchingInteraction:
    """Convert a correction-route matching DTO to the domain contract."""

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


def from_domain_matching_interaction(
    interaction: ExamAuthoringMatchingInteraction,
    *,
    source_item_fingerprint: str | None,
) -> ExamAuthoringMatchingInteractionV1:
    """Convert a domain matching interaction to the correction-route DTO."""

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
