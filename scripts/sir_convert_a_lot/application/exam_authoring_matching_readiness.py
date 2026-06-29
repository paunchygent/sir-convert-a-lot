"""Matching correction target-readiness projection.

Purpose:
    Build target readiness and artifact availability rows for source-neutral
    matching answer-key corrections after effective state has been applied.

Relationships:
    - Used by `exam_authoring_corrections_apply_contracts` for matching entries.
    - Reuses the source-neutral matching domain validator and correction apply
      response DTOs.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringMatchingInteractionV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionArtifactAvailabilityRowV1,
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringCorrectionTargetV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_matching_dto_mapping import (
    to_domain_matching_interaction,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringMatchingInteraction,
    validate_examnet_pdf_matching_profile,
)


def matching_target_readiness_rows(
    *,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteractionV1,
) -> tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]:
    """Return target readiness rows for a corrected matching interaction."""

    domain_interaction = to_domain_matching_interaction(interaction)
    return tuple(
        _target_readiness(target=target, item=item, interaction=domain_interaction)
        for target in targets
    )


def artifact_availability_for_readiness(
    readiness: ExamAuthoringCorrectionTargetReadinessRowV1,
) -> ExamAuthoringCorrectionArtifactAvailabilityRowV1:
    """Project artifact availability from one target-readiness row."""

    if readiness.export_enabled:
        return ExamAuthoringCorrectionArtifactAvailabilityRowV1(
            artifact_key=readiness.target,
            availability="available",
        )
    return ExamAuthoringCorrectionArtifactAvailabilityRowV1(
        artifact_key=readiness.target,
        availability="unavailable",
        unavailable_code=readiness.reason_code,
    )


def _target_readiness(
    *,
    target: ExamAuthoringCorrectionTargetV1,
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteraction,
) -> ExamAuthoringCorrectionTargetReadinessRowV1:
    if target == "qti_package":
        return ExamAuthoringCorrectionTargetReadinessRowV1(
            target=target,
            readiness="unsupported_target_shape",
            export_enabled=False,
            reason_code="examnet_qti_matching_import_unproven",
            message_key="exam_converter.target.matching.qti_import_unproven",
            item_id=item.item_id,
            sequence=item.sequence,
        )
    validation = validate_examnet_pdf_matching_profile(interaction)
    if validation.valid:
        return ExamAuthoringCorrectionTargetReadinessRowV1(
            target=target,
            readiness="ready",
            export_enabled=True,
            reason_code="ready",
            message_key="exam_converter.target.matching.ready",
            item_id=item.item_id,
            sequence=item.sequence,
        )
    return ExamAuthoringCorrectionTargetReadinessRowV1(
        target=target,
        readiness="target_validation_failed",
        export_enabled=False,
        reason_code=";".join(issue.reason_code.value for issue in validation.issues),
        message_key="exam_converter.target.matching.validation_failed",
        item_id=item.item_id,
        sequence=item.sequence,
    )
