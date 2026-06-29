"""Source-neutral exam authoring correction application service.

Purpose:
    Apply source-bound correction batches for the unified exam-authoring
    correction route and project effective state, readiness, and reports.

Relationships:
    - Consumes DTOs from `application.exam_authoring_corrections_apply_models`.
    - Reuses matching and non-matching correction delegates for validation.
    - Called by `interfaces.http_routes_exam_authoring_corrections_v2`.
"""

from __future__ import annotations

from typing import Literal

from scripts.sir_convert_a_lot.application.exam_authoring_answer_key_review_projection import (
    build_answer_key_review_state_for_apply_result,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringMatchingInteractionV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_binding import (
    ExamAuthoringCorrectionsApplyBindingError,
    validate_correction_request_binding,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_integrity import (
    matching_answer_key_payload_digest,
    stable_json_sha256,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionAcceptedEntryV1,
    ExamAuthoringCorrectionEntryBaseV1,
    ExamAuthoringCorrectionRejectedEntryV1,
    ExamAuthoringCorrectionReportV1,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionsApplyResultV1,
    ExamAuthoringCorrectionTargetReadinessReportV1,
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringCorrectionTargetV1,
    ExamAuthoringEffectiveStateV1,
    ExamAuthoringItemTextPatchCorrectionV1,
    ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
    ExamAuthoringPointCorrectionV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_matching_dto_mapping import (
    from_domain_matching_interaction,
    to_domain_matching_interaction,
)
from scripts.sir_convert_a_lot.application.exam_authoring_matching_readiness import (
    artifact_availability_for_readiness,
    matching_target_readiness_rows,
)
from scripts.sir_convert_a_lot.application.exam_authoring_non_matching_corrections import (
    ExamAuthoringNonMatchingCorrectionError,
    prepare_non_matching_correction,
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
    *,
    source_state_signature_secret: str | None,
) -> ExamAuthoringCorrectionsApplyResultV1:
    """Apply a correction batch and return producer-owned effective state."""

    try:
        validate_correction_request_binding(
            request_body=request_body,
            source_state_signature_secret=source_state_signature_secret,
        )
    except ExamAuthoringCorrectionsApplyBindingError as exc:
        raise ExamAuthoringCorrectionsApplyError(exc.code, str(exc), exc.details) from exc
    source_items = list(request_body.source_authoring_state.items)
    effective_items = list(source_items)
    prepared_corrections: list[ExamAuthoringCorrectionEntryBaseV1] = []
    accepted_entries: list[ExamAuthoringCorrectionAcceptedEntryV1] = []
    readiness_rows: dict[_ReadinessKey, ExamAuthoringCorrectionTargetReadinessRowV1] = {}
    rejected_entries: list[ExamAuthoringCorrectionRejectedEntryV1] = []

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
            prepared_corrections.append(correction)
            accepted_entries.append(_accepted_matching_entry(correction))
            _record_readiness(
                readiness_rows,
                matching_target_readiness_rows(
                    targets=request_body.requested_targets,
                    item=effective_items[item_index],
                    interaction=effective_interaction,
                ),
            )
        elif isinstance(
            correction,
            (
                ExamAuthoringItemTextPatchCorrectionV1,
                ExamAuthoringPointCorrectionV1,
                ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
                ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
            ),
        ):
            item_index, item = _bound_item(correction, effective_items)
            try:
                prepared = prepare_non_matching_correction(
                    correction=correction,
                    item=item,
                    targets=request_body.requested_targets,
                )
            except ExamAuthoringNonMatchingCorrectionError as exc:
                raise ExamAuthoringCorrectionsApplyError(
                    exc.code,
                    str(exc),
                    exc.details,
                ) from exc
            effective_items[item_index] = prepared.effective_item
            prepared_corrections.append(correction)
            accepted_entries.append(prepared.accepted_entry)
            _record_readiness(readiness_rows, prepared.readiness_rows)
        else:
            rejected_entries.append(_unsupported_entry(correction))

    if rejected_entries:
        batch_rejections = tuple(
            _batch_blocked_entry(correction) for correction in prepared_corrections
        )
        return _result(
            request_body=request_body,
            effective_items=source_items,
            accepted_entries=(),
            rejected_entries=(*batch_rejections, *tuple(rejected_entries)),
            readiness_rows=(),
        )

    return _result(
        request_body=request_body,
        effective_items=effective_items,
        accepted_entries=tuple(accepted_entries),
        rejected_entries=(),
        readiness_rows=tuple(readiness_rows.values()),
    )


def _result(
    *,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    effective_items: list[ExamAuthoringCorrectionSourceItemV1],
    accepted_entries: tuple[ExamAuthoringCorrectionAcceptedEntryV1, ...],
    rejected_entries: tuple[ExamAuthoringCorrectionRejectedEntryV1, ...],
    readiness_rows: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...],
) -> ExamAuthoringCorrectionsApplyResultV1:
    """Build the route result after batch validation has settled."""

    effective_state = _effective_state(effective_items)
    correction_report = ExamAuthoringCorrectionReportV1(
        accepted_entries=accepted_entries,
        rejected_entries=rejected_entries,
    )
    target_readiness = ExamAuthoringCorrectionTargetReadinessReportV1(
        targets=readiness_rows,
    )
    return ExamAuthoringCorrectionsApplyResultV1(
        request_id=request_body.request_id,
        source_binding=request_body.source_binding,
        effective_state=effective_state,
        correction_report=correction_report,
        answer_key_review_state=build_answer_key_review_state_for_apply_result(
            request_body=request_body,
            effective_state=effective_state,
            effective_items=tuple(effective_items),
            accepted_entries=accepted_entries,
            rejected_entries=rejected_entries,
            readiness_rows=readiness_rows,
        ),
        target_readiness=target_readiness,
        artifact_availability=tuple(
            artifact_availability_for_readiness(row) for row in readiness_rows
        ),
    )


def _record_readiness(
    rows_by_key: dict[_ReadinessKey, ExamAuthoringCorrectionTargetReadinessRowV1],
    rows: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...],
) -> None:
    for row in rows:
        rows_by_key[(row.target, row.item_id, row.sequence)] = row


_ReadinessKey = tuple[ExamAuthoringCorrectionTargetV1, str | None, int | None]


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
            interaction=to_domain_matching_interaction(interaction),
            expected_source_item_fingerprint=expected_source_item_fingerprint,
        )
    except ExamAuthoringMatchingManualAnswerKeyError as exc:
        raise ExamAuthoringCorrectionsApplyError(exc.code, str(exc), exc.details) from exc
    return from_domain_matching_interaction(
        effective_interaction,
        source_item_fingerprint=expected_source_item_fingerprint,
    )


def _matching_submission(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> ExamAuthoringMatchingManualAnswerKey:
    _validate_matching_candidate_digest(correction)
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


def _validate_matching_candidate_digest(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> None:
    if correction.submission_origin != "accepted_advisory_candidate":
        return
    if correction.candidate_lineage is None:
        raise ExamAuthoringCorrectionsApplyError(
            "advisory_candidate_lineage_missing",
            "Accepted advisory matching correction requires candidate lineage.",
            {"entry_id": correction.entry_id},
        )
    submitted_digest = matching_answer_key_payload_digest(correction)
    expected_digest = correction.candidate_lineage.candidate_payload_digest
    if submitted_digest != expected_digest:
        raise ExamAuthoringCorrectionsApplyError(
            "advisory_candidate_payload_digest_mismatch",
            "Accepted advisory matching correction must match the candidate payload digest.",
            {
                "entry_id": correction.entry_id,
                "candidate_id": correction.candidate_lineage.candidate_id,
                "submitted_candidate_payload_digest": submitted_digest,
                "expected_candidate_payload_digest": expected_digest,
            },
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


def _batch_blocked_entry(
    correction: ExamAuthoringCorrectionEntryBaseV1,
) -> ExamAuthoringCorrectionRejectedEntryV1:
    return ExamAuthoringCorrectionRejectedEntryV1(
        entry_id=correction.entry_id,
        kind=correction.kind,
        item_id=correction.item_id,
        sequence=correction.sequence,
        reason_code="correction_batch_contains_rejected_entries",
        message_key="exam_authoring.corrections.batch_contains_rejected_entries",
        teacher_action="resolve_rejected_entries_and_retry_batch",
        retryable=True,
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
    return stable_json_sha256(payload)
