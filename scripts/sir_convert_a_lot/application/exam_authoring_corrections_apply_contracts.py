"""Source-neutral exam authoring correction application service.

Purpose:
    Apply source-bound correction batches for the unified exam-authoring
    correction route and project effective state, readiness, and reports.

Relationships:
    - Consumes DTOs from `application.exam_authoring_corrections_apply_models`.
    - Reuses `domain.exam_authoring_matching_manual_answer_key` and
      `domain.exam_authoring_ir_contracts` for matching-key validation.
    - Called by `interfaces.http_routes_exam_authoring_corrections_v2`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionAcceptedEntryV1,
    ExamAuthoringCorrectionArtifactAvailabilityRowV1,
    ExamAuthoringCorrectionEntryBaseV1,
    ExamAuthoringCorrectionRejectedEntryV1,
    ExamAuthoringCorrectionReportV1,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionsApplyResultV1,
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringCorrectionTargetReadinessReportV1,
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringCorrectionTargetV1,
    ExamAuthoringEffectiveStateV1,
    ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
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
    validate_examnet_pdf_matching_profile,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_matching_manual_answer_key import (
    ExamAuthoringMatchingManualAnswerKey,
    ExamAuthoringMatchingManualAnswerKeyError,
    apply_exam_authoring_matching_manual_answer_key,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
)


class ExamAuthoringCorrectionsApplyError(ValueError):
    """Typed failure raised before a correction batch can affect state."""

    def __init__(self, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def apply_exam_authoring_corrections_request(
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
) -> ExamAuthoringCorrectionsApplyResultV1:
    """Apply a correction batch and return producer-owned effective state."""

    _validate_request_binding(request_body)
    effective_items = list(request_body.source_authoring_state.items)
    accepted_entries: list[ExamAuthoringCorrectionAcceptedEntryV1] = []
    rejected_entries: list[ExamAuthoringCorrectionRejectedEntryV1] = []
    readiness_rows: list[ExamAuthoringCorrectionTargetReadinessRowV1] = []

    for correction in request_body.corrections:
        if isinstance(correction, ExamAuthoringManualMatchingAnswerKeyCorrectionV1):
            item_index, item = _bound_item(correction, effective_items)
            interaction = _matching_interaction(correction=correction, item=item)
            effective_interaction = _apply_matching_correction(
                correction=correction,
                interaction=interaction,
                expected_source_item_fingerprint=_expected_interaction_fingerprint(
                    item=item,
                    interaction=interaction,
                ),
            )
            effective_items[item_index] = _replace_matching_interaction(
                item=item,
                interaction_id=correction.interaction_id,
                effective_interaction=effective_interaction,
            )
            accepted_entries.append(_accepted_matching_entry(correction))
            readiness_rows.extend(
                _target_readiness_rows(
                    targets=request_body.requested_targets,
                    item=effective_items[item_index],
                    interaction=effective_interaction,
                )
            )
        else:
            rejected_entries.append(_unsupported_entry(correction))

    effective_state = _effective_state(effective_items)
    readiness_report = ExamAuthoringCorrectionTargetReadinessReportV1(
        targets=tuple(readiness_rows),
    )
    return ExamAuthoringCorrectionsApplyResultV1(
        request_id=request_body.request_id,
        source_binding=request_body.source_binding,
        effective_state=effective_state,
        correction_report=ExamAuthoringCorrectionReportV1(
            accepted_entries=tuple(accepted_entries),
            rejected_entries=tuple(rejected_entries),
        ),
        target_readiness=readiness_report,
        artifact_availability=tuple(_artifact_availability(row) for row in readiness_rows),
    )


def _validate_request_binding(request_body: ExamAuthoringCorrectionsApplyRequestV1) -> None:
    binding = request_body.source_binding
    state = request_body.source_authoring_state
    if binding.source_authoring_schema_version != state.source_authoring_schema_version:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_schema_version",
            "Correction source binding schema version does not match the source state.",
            {
                "submitted_schema_version": binding.source_authoring_schema_version,
                "expected_schema_version": state.source_authoring_schema_version,
            },
        )
    if binding.source_state_sha256 != state.source_state_sha256:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_source_state",
            "Correction source binding digest does not match the source state.",
            {
                "submitted_source_state_sha256": binding.source_state_sha256,
                "expected_source_state_sha256": state.source_state_sha256,
            },
        )


def _bound_item(
    correction: ExamAuthoringCorrectionEntryBaseV1,
    items: list[ExamAuthoringCorrectionSourceItemV1],
) -> tuple[int, ExamAuthoringCorrectionSourceItemV1]:
    for index, item in enumerate(items):
        if item.item_id == correction.item_id:
            _validate_item_binding(correction=correction, item=item)
            return index, item
    raise ExamAuthoringCorrectionsApplyError(
        "unknown_exam_authoring_item",
        "Correction references an unknown source item.",
        {"item_id": correction.item_id, "entry_id": correction.entry_id},
    )


def _validate_item_binding(
    *,
    correction: ExamAuthoringCorrectionEntryBaseV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> None:
    if correction.sequence != item.sequence:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_item_sequence",
            "Correction item sequence does not match the source item.",
            {"submitted_sequence": correction.sequence, "expected_sequence": item.sequence},
        )
    if correction.item_type != item.item_type:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_item_type",
            "Correction item type does not match the source item.",
            {"submitted_item_type": correction.item_type, "expected_item_type": item.item_type},
        )
    if (
        item.source_item_fingerprint is not None
        and correction.source_item_fingerprint != item.source_item_fingerprint
    ):
        raise ExamAuthoringCorrectionsApplyError(
            "stale_correction_source_item_fingerprint",
            "Correction source item fingerprint does not match the source item.",
            {
                "submitted_source_item_fingerprint": correction.source_item_fingerprint,
                "expected_source_item_fingerprint": item.source_item_fingerprint,
            },
        )


def _matching_interaction(
    *,
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringMatchingInteractionV1:
    for interaction in item.matching_interactions:
        if interaction.interaction_id == correction.interaction_id:
            return interaction
    raise ExamAuthoringCorrectionsApplyError(
        "unknown_matching_interaction_id",
        "Matching correction references an unknown interaction.",
        {
            "entry_id": correction.entry_id,
            "item_id": correction.item_id,
            "interaction_id": correction.interaction_id,
        },
    )


def _expected_interaction_fingerprint(
    *,
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteractionV1,
) -> str | None:
    return interaction.source_item_fingerprint or item.source_item_fingerprint


def _apply_matching_correction(
    *,
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
    interaction: ExamAuthoringMatchingInteractionV1,
    expected_source_item_fingerprint: str | None,
) -> ExamAuthoringMatchingInteractionV1:
    try:
        effective_interaction = apply_exam_authoring_matching_manual_answer_key(
            submission=_matching_submission(correction),
            interaction=_to_domain_interaction(interaction),
            expected_source_item_fingerprint=expected_source_item_fingerprint,
        )
    except ExamAuthoringMatchingManualAnswerKeyError as exc:
        raise ExamAuthoringCorrectionsApplyError(exc.code, str(exc), exc.details) from exc
    return _from_domain_interaction(
        effective_interaction,
        source_item_fingerprint=expected_source_item_fingerprint,
    )


def _matching_submission(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> ExamAuthoringMatchingManualAnswerKey:
    provenance: Literal["teacher_provided", "reviewed"]
    if correction.submission_origin == "accepted_advisory_candidate":
        provenance = "reviewed"
    else:
        provenance = "teacher_provided"
    return ExamAuthoringMatchingManualAnswerKey.model_validate(
        {
            "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
            "kind": "matching",
            "interaction_id": correction.interaction_id,
            "source_item_fingerprint": correction.source_item_fingerprint,
            "answer_key": {
                "provenance": provenance,
                "pairs": tuple(pair.model_dump(mode="json") for pair in correction.pairs),
            },
        }
    )


def _replace_matching_interaction(
    *,
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction_id: str,
    effective_interaction: ExamAuthoringMatchingInteractionV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    interactions = tuple(
        effective_interaction if interaction.interaction_id == interaction_id else interaction
        for interaction in item.matching_interactions
    )
    return item.model_copy(update={"matching_interactions": interactions})


def _accepted_matching_entry(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> ExamAuthoringCorrectionAcceptedEntryV1:
    provenance = (
        "reviewed"
        if correction.submission_origin == "accepted_advisory_candidate"
        else ("teacher_provided")
    )
    return ExamAuthoringCorrectionAcceptedEntryV1(
        entry_id=correction.entry_id,
        kind=correction.kind,
        item_id=correction.item_id,
        sequence=correction.sequence,
        applied_fields=("answer_key",),
        effective_provenance=provenance,
    )


def _unsupported_entry(
    correction: ExamAuthoringCorrectionEntryBaseV1,
) -> ExamAuthoringCorrectionRejectedEntryV1:
    return ExamAuthoringCorrectionRejectedEntryV1(
        entry_id=correction.entry_id,
        kind=correction.kind,
        item_id=correction.item_id,
        sequence=correction.sequence,
        reason_code="correction_kind_not_supported_in_initial_unified_route",
        message_key="exam_authoring.corrections.unsupported_in_initial_runtime",
        teacher_action="wait_for_supported_runtime_slice",
        retryable=False,
    )


def _effective_state(
    items: list[ExamAuthoringCorrectionSourceItemV1],
) -> ExamAuthoringEffectiveStateV1:
    item_payloads = tuple(item.model_dump(mode="json") for item in items)
    return ExamAuthoringEffectiveStateV1(
        effective_state_sha256=_stable_sha256(
            {
                "schema_version": "exam_authoring_effective_state_v1",
                "items": item_payloads,
            }
        ),
        items=tuple(items),
    )


def _stable_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _target_readiness_rows(
    *,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteractionV1,
) -> tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]:
    domain_interaction = _to_domain_interaction(interaction)
    return tuple(
        _target_readiness(target=target, item=item, interaction=domain_interaction)
        for target in targets
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


def _artifact_availability(
    readiness: ExamAuthoringCorrectionTargetReadinessRowV1,
) -> ExamAuthoringCorrectionArtifactAvailabilityRowV1:
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
