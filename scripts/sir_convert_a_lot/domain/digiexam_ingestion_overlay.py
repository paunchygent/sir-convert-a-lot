"""DigiExam ingestion overlay application service.

Purpose:
    Validate source-bound teacher overlays and apply accepted manual keys or
    review decisions to an effective renderer input without mutating source IR.

Relationships:
    - Consumes contracts from `domain.digiexam_ingestion_overlay_contracts`.
    - Uses `domain.digiexam_source_fingerprints` for source binding.
    - Feeds `infrastructure.digiexam_migration_bundle_builder`.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamGapAnswer,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_effective_item_patch import (
    apply_effective_item_patch,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamEffectiveAnswerKey,
    DigiExamEffectiveExam,
    DigiExamEffectiveItem,
    DigiExamEffectiveItemPatchSummary,
    DigiExamEffectiveReviewDecision,
    DigiExamIngestionOverlay,
    DigiExamIngestionOverlayAcceptedEntry,
    DigiExamIngestionOverlayError,
    DigiExamIngestionOverlayItem,
    DigiExamIngestionOverlayRejectedEntry,
    DigiExamIngestionOverlayReport,
    DigiExamOverlayApplicationResult,
    DigiExamOverlayChoiceManualAnswerKey,
    DigiExamOverlayGapFillManualAnswerKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    DigiExamIntermediateExam,
    DigiExamIrAnswerKey,
    DigiExamIrItem,
    DigiExamIrManualFollowUpReason,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    INGESTION_OVERLAY_REPORT_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import ExamMigrationTargetV2


def parse_and_apply_digiexam_ingestion_overlay(
    *,
    overlay_bytes: bytes,
    source_file_sha256: str,
    source_ir_sha256: str,
    source_exam: DigiExamIntermediateExam,
) -> DigiExamOverlayApplicationResult:
    """Validate and apply one overlay to a source exam."""

    overlay = _parse_overlay(overlay_bytes)
    overlay_sha256 = f"sha256:{hashlib.sha256(overlay_bytes).hexdigest()}"
    _validate_source_binding(
        overlay=overlay,
        source_file_sha256=source_file_sha256,
        source_ir_sha256=source_ir_sha256,
    )
    _validate_item_bindings(overlay=overlay, source_exam=source_exam)
    return _apply_overlay(
        overlay=overlay,
        overlay_sha256=overlay_sha256,
        source_file_sha256=source_file_sha256,
        source_ir_sha256=source_ir_sha256,
        source_exam=source_exam,
    )


def _parse_overlay(overlay_bytes: bytes) -> DigiExamIngestionOverlay:
    try:
        return DigiExamIngestionOverlay.model_validate_json(overlay_bytes)
    except ValidationError as exc:
        raise DigiExamIngestionOverlayError(
            "digiexam_ingestion_overlay_invalid",
            "DigiExam ingestion overlay failed schema validation.",
            {"errors": exc.errors(include_context=False)},
        ) from exc


def _validate_source_binding(
    *,
    overlay: DigiExamIngestionOverlay,
    source_file_sha256: str,
    source_ir_sha256: str,
) -> None:
    binding = overlay.source_binding
    if binding.source_file_sha256 != source_file_sha256:
        raise _binding_error("source_file_sha256", binding.source_file_sha256, source_file_sha256)
    if binding.source_ir_schema_version != DIGIEXAM_IR_SCHEMA_VERSION:
        raise _binding_error(
            "source_ir_schema_version",
            binding.source_ir_schema_version,
            DIGIEXAM_IR_SCHEMA_VERSION,
        )
    if binding.source_ir_sha256 != source_ir_sha256:
        raise _binding_error("source_ir_sha256", binding.source_ir_sha256, source_ir_sha256)


def _validate_item_bindings(
    *,
    overlay: DigiExamIngestionOverlay,
    source_exam: DigiExamIntermediateExam,
) -> None:
    items_by_id = {item.item_id: item for item in source_exam.items}
    seen_item_ids: set[str] = set()
    for entry in overlay.items:
        if entry.item_id in seen_item_ids:
            raise _item_error(entry, "duplicate_overlay_item", "Overlay item IDs must be unique.")
        seen_item_ids.add(entry.item_id)
        item = items_by_id.get(entry.item_id)
        if item is None:
            raise _item_error(entry, "unknown_item_id", "Overlay item does not exist in source IR.")
        if entry.sequence != item.sequence:
            raise _item_error(entry, "stale_item_sequence", "Overlay item sequence is stale.")
        if entry.item_type != item.item_type:
            raise _item_error(entry, "stale_item_type", "Overlay item type is stale.")
        if entry.source_item_fingerprint != source_item_fingerprint(item):
            raise _item_error(
                entry,
                "stale_source_item_fingerprint",
                "Overlay item fingerprint does not match source IR.",
            )


def _apply_overlay(
    *,
    overlay: DigiExamIngestionOverlay,
    overlay_sha256: str,
    source_file_sha256: str,
    source_ir_sha256: str,
    source_exam: DigiExamIntermediateExam,
) -> DigiExamOverlayApplicationResult:
    replacements: dict[str, DigiExamIrItem] = {}
    accepted: list[DigiExamIngestionOverlayAcceptedEntry] = []
    rejected: list[DigiExamIngestionOverlayRejectedEntry] = []
    effective_items: list[DigiExamEffectiveItem] = []
    accepted_reviews: list[tuple[str, ExamMigrationTargetV2]] = []
    answered_item_ids: set[str] = set()
    items_by_id = {item.item_id: item for item in source_exam.items}
    for entry in overlay.items:
        item = items_by_id[entry.item_id]
        applied_fields: list[str] = []
        review_decisions = _review_decisions(entry)
        accepted_reviews.extend((entry.item_id, target) for target in _review_targets(entry))
        patch_summary = None
        patch_result = apply_effective_item_patch(entry=entry, item=item)
        if patch_result.rejection is not None:
            rejected.append(
                _rejected(
                    entry,
                    patch_result.rejection.reason_code,
                    patch_result.rejection.message,
                )
            )
        if patch_result.application is not None:
            item = patch_result.application.item
            replacements[item.item_id] = item
            patch_summary = patch_result.application.summary
            applied_fields.append("effective_item_patch")
        replacement = _manual_key_replacement(entry=entry, item=item, rejected=rejected)
        if replacement is not None:
            replacements[item.item_id] = replacement
            applied_fields.append("manual_answer_key")
            answered_item_ids.add(item.item_id)
            item = replacement
        if review_decisions:
            applied_fields.append("review_decision")
        if applied_fields:
            accepted.append(_accepted(entry, tuple(applied_fields)))
        effective_items.append(
            _effective_item(
                item=item,
                applied=tuple(applied_fields),
                source_item_fingerprint=entry.source_item_fingerprint,
                patch_summary=patch_summary,
                review_decisions=review_decisions,
            )
        )
    effective_exam = _replace_exam_items(source_exam, replacements, answered_item_ids)
    return DigiExamOverlayApplicationResult(
        effective_exam_for_rendering=effective_exam,
        effective_exam_report=_effective_exam_report(
            source_file_sha256=source_file_sha256,
            source_ir_sha256=source_ir_sha256,
            overlay_sha256=overlay_sha256,
            items=tuple(effective_items),
        ),
        ingestion_overlay_report=DigiExamIngestionOverlayReport(
            schema_version=INGESTION_OVERLAY_REPORT_SCHEMA_VERSION,
            overlay_sha256=overlay_sha256,
            source_ir_sha256=source_ir_sha256,
            accepted_entries=tuple(accepted),
            rejected_entries=tuple(rejected),
        ),
        renderer_input_changed=bool(replacements),
        accepted_review_decisions=tuple(accepted_reviews),
    )


def _manual_key_replacement(
    *,
    entry: DigiExamIngestionOverlayItem,
    item: DigiExamIrItem,
    rejected: list[DigiExamIngestionOverlayRejectedEntry],
) -> DigiExamIrItem | None:
    key = entry.manual_answer_key
    if key is None:
        return None
    if isinstance(key, DigiExamOverlayChoiceManualAnswerKey):
        return _choice_replacement(entry=entry, item=item, key=key, rejected=rejected)
    return _gap_fill_replacement(entry=entry, item=item, key=key, rejected=rejected)


def _choice_replacement(
    *,
    entry: DigiExamIngestionOverlayItem,
    item: DigiExamIrItem,
    key: DigiExamOverlayChoiceManualAnswerKey,
    rejected: list[DigiExamIngestionOverlayRejectedEntry],
) -> DigiExamIrItem | None:
    if item.item_type not in _CHOICE_ITEM_TYPES:
        rejected.append(
            _rejected(entry, "answer_key_item_type_mismatch", "Choice key on non-choice item.")
        )
        return None
    valid_ids = {alternative.id for alternative in item.alternatives}
    if len(set(key.correct_alternative_ids)) != len(key.correct_alternative_ids):
        rejected.append(
            _rejected(entry, "duplicate_answer_id", "Choice key contains duplicate IDs.")
        )
        return None
    if any(alternative_id not in valid_ids for alternative_id in key.correct_alternative_ids):
        rejected.append(_rejected(entry, "unknown_answer_id", "Choice key references unknown IDs."))
        return None
    return replace(
        item,
        answer_key=DigiExamIrAnswerKey(
            provenance=DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY,
            correct_alternative_ids=key.correct_alternative_ids,
            correct_gap_answers=(),
        ),
    )


def _gap_fill_replacement(
    *,
    entry: DigiExamIngestionOverlayItem,
    item: DigiExamIrItem,
    key: DigiExamOverlayGapFillManualAnswerKey,
    rejected: list[DigiExamIngestionOverlayRejectedEntry],
) -> DigiExamIrItem | None:
    if item.item_type != DigiExamItemType.GAP_FILL:
        rejected.append(
            _rejected(entry, "answer_key_item_type_mismatch", "Gap key on non-gap item.")
        )
        return None
    valid_gap_ids = {gap.guid for gap in item.gaps}
    answers: list[DigiExamGapAnswer] = []
    for gap_answer in key.gap_answers:
        if gap_answer.gap_id not in valid_gap_ids:
            rejected.append(
                _rejected(entry, "unknown_gap_id", "Gap key references unknown gap IDs.")
            )
            return None
        answers.extend(
            DigiExamGapAnswer(guid=gap_answer.gap_id, value=value)
            for value in gap_answer.accepted_values
        )
    return replace(
        item,
        answer_key=DigiExamIrAnswerKey(
            provenance=DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY,
            correct_alternative_ids=(),
            correct_gap_answers=tuple(answers),
        ),
    )


def _replace_exam_items(
    source_exam: DigiExamIntermediateExam,
    replacements: dict[str, DigiExamIrItem],
    answered_item_ids: set[str],
) -> DigiExamIntermediateExam:
    if not replacements:
        return source_exam
    follow_ups = tuple(
        follow_up
        for follow_up in source_exam.manual_follow_ups
        if not (
            follow_up.item_id in answered_item_ids
            and follow_up.reason == DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
        )
    )
    return replace(
        source_exam,
        items=tuple(replacements.get(item.item_id, item) for item in source_exam.items),
        manual_follow_ups=follow_ups,
    )


def _effective_exam_report(
    *,
    source_file_sha256: str,
    source_ir_sha256: str,
    overlay_sha256: str,
    items: tuple[DigiExamEffectiveItem, ...],
) -> DigiExamEffectiveExam:
    return DigiExamEffectiveExam(
        schema_version=DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
        source_file_sha256=source_file_sha256,
        source_ir_schema_version=DIGIEXAM_IR_SCHEMA_VERSION,
        source_ir_sha256=source_ir_sha256,
        ingestion_overlay_sha256=overlay_sha256,
        answer_key_completion_report_sha256=None,
        items=items,
    )


def _effective_item(
    *,
    item: DigiExamIrItem,
    applied: tuple[str, ...],
    source_item_fingerprint: str,
    patch_summary: DigiExamEffectiveItemPatchSummary | None,
    review_decisions: tuple[DigiExamEffectiveReviewDecision, ...],
) -> DigiExamEffectiveItem:
    return DigiExamEffectiveItem(
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type.value,
        source_item_fingerprint=source_item_fingerprint,
        effective_answer_key=_effective_answer_key(item)
        if "manual_answer_key" in applied
        else None,
        effective_item_patch=patch_summary,
        applied_overlay_entry_ids=(item.item_id,) if applied else (),
        review_decisions=review_decisions,
    )


def _effective_answer_key(item: DigiExamIrItem) -> DigiExamEffectiveAnswerKey:
    return DigiExamEffectiveAnswerKey(
        provenance=item.answer_key.provenance.value,
        correct_alternative_ids=item.answer_key.correct_alternative_ids,
        correct_gap_answers=tuple(
            {"gap_id": answer.guid, "value": answer.value}
            for answer in item.answer_key.correct_gap_answers
        ),
    )


def _review_decisions(
    entry: DigiExamIngestionOverlayItem,
) -> tuple[DigiExamEffectiveReviewDecision, ...]:
    decision = entry.review_decision
    if decision is None:
        return ()
    return (
        DigiExamEffectiveReviewDecision(
            kind=decision.kind,
            decision_id=decision.decision_id,
            accepted_targets=tuple(target.value for target in decision.accepted_targets),
            note=decision.note,
        ),
    )


def _review_targets(entry: DigiExamIngestionOverlayItem) -> tuple[ExamMigrationTargetV2, ...]:
    if entry.review_decision is None:
        return ()
    return entry.review_decision.accepted_targets


def _binding_error(field: str, observed: object, expected: object) -> DigiExamIngestionOverlayError:
    return DigiExamIngestionOverlayError(
        "digiexam_ingestion_overlay_stale_source",
        "DigiExam ingestion overlay source binding does not match this conversion.",
        {"field": field, "observed": observed, "expected": expected},
    )


def _item_error(
    entry: DigiExamIngestionOverlayItem, code: str, message: str
) -> DigiExamIngestionOverlayError:
    return DigiExamIngestionOverlayError(
        f"digiexam_ingestion_overlay_{code}",
        message,
        {"item_id": entry.item_id, "sequence": entry.sequence},
    )


def _accepted(
    entry: DigiExamIngestionOverlayItem, applied_fields: tuple[str, ...]
) -> DigiExamIngestionOverlayAcceptedEntry:
    return DigiExamIngestionOverlayAcceptedEntry(
        item_id=entry.item_id,
        sequence=entry.sequence,
        applied_fields=applied_fields,
    )


def _rejected(
    entry: DigiExamIngestionOverlayItem, reason_code: str, message: str
) -> DigiExamIngestionOverlayRejectedEntry:
    return DigiExamIngestionOverlayRejectedEntry(
        item_id=entry.item_id,
        sequence=entry.sequence,
        reason_code=reason_code,
        message=message,
    )


_CHOICE_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
