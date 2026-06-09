"""DigiExam reviewed answer-key completion application.

Purpose:
    Apply teacher-reviewed advisory answer-key candidates to effective exam
    summaries while keeping source parser provenance immutable.

Relationships:
    - Consumes reviewed choice candidate candidate payload digest semantics from
      `domain.digiexam_answer_key_completion_contracts`.
    - Consumes Markdown to DOCX route6 reviewed overlay fields from
      `domain.digiexam_ingestion_overlay_contracts`.
    - Called by `domain.digiexam_ingestion_overlay` after source binding and
      item binding have already been validated.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    answer_key_candidate_payload_digest,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_payloads import (
    validated_reviewed_answer_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamGapAnswer,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamEffectiveAnswerKey,
    DigiExamEffectiveAnswerKeyLineage,
    DigiExamEffectiveAnswerKeyProvenance,
    DigiExamIngestionOverlay,
    DigiExamIngestionOverlayError,
    DigiExamIngestionOverlayItem,
    DigiExamOverlayReviewedCompletionAnswerKey,
    DigiExamOverlayReviewedCompletionOutcome,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrAnswerKey,
    DigiExamIrItem,
)


@dataclass(frozen=True)
class DigiExamReviewedCompletionApplication:
    """Applied reviewed completion with renderer item and effective metadata."""

    item: DigiExamIrItem
    effective_answer_key: DigiExamEffectiveAnswerKey


def reviewed_completion_report_sha256(overlay: DigiExamIngestionOverlay) -> str | None:
    """Return the single reviewed completion report digest referenced by an overlay."""

    report_digests = {
        entry.reviewed_completion_answer_key.candidate_lineage.completion_report_sha256
        for entry in overlay.items
        if entry.reviewed_completion_answer_key is not None
    }
    if not report_digests:
        return None
    if len(report_digests) > 1:
        raise DigiExamIngestionOverlayError(
            "digiexam_reviewed_completion_multiple_reports",
            "Reviewed completion overlay must reference one completion report digest.",
            {"completion_report_sha256": sorted(report_digests)},
        )
    return next(iter(report_digests))


def reviewed_completion_replacement(
    *,
    entry: DigiExamIngestionOverlayItem,
    item: DigiExamIrItem,
) -> DigiExamReviewedCompletionApplication | None:
    """Apply a reviewed completion entry when present and semantically valid."""

    key = entry.reviewed_completion_answer_key
    if key is None:
        return None
    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        raise _item_error(
            entry,
            "source_bound_answer_key_exists",
            "Reviewed completion cannot overwrite source-bound answer evidence.",
        )
    payload = _reviewed_answer_payload(key)
    validated_payload = validated_reviewed_answer_payload(item=item, payload=payload)
    if validated_payload is None:
        raise _item_error(
            entry,
            "reviewed_completion_answer_key_invalid",
            "Reviewed completion answer key does not match source item structure.",
        )
    digest = answer_key_candidate_payload_digest(validated_payload)
    if (
        key.review_outcome == DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED
        and digest != key.candidate_lineage.candidate_payload_digest
    ):
        raise _item_error(
            entry,
            "reviewed_completion_candidate_digest_mismatch",
            "Accepted unchanged completion must match the candidate payload digest.",
        )
    effective_provenance = (
        DigiExamEffectiveAnswerKeyProvenance.REVIEWED
        if key.review_outcome == DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED
        else DigiExamEffectiveAnswerKeyProvenance.TEACHER_PROVIDED
    )
    replacement = replace(
        item,
        answer_key=DigiExamIrAnswerKey(
            provenance=DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY,
            correct_alternative_ids=_reviewed_choice_ids(validated_payload),
            correct_gap_answers=_reviewed_gap_answers(validated_payload),
        ),
    )
    return DigiExamReviewedCompletionApplication(
        item=replacement,
        effective_answer_key=effective_answer_key_for_item(
            replacement,
            provenance=effective_provenance,
            lineage=_effective_lineage(key),
        ),
    )


def effective_answer_key_for_item(
    item: DigiExamIrItem,
    *,
    provenance: DigiExamEffectiveAnswerKeyProvenance,
    lineage: DigiExamEffectiveAnswerKeyLineage | None,
) -> DigiExamEffectiveAnswerKey:
    """Build effective answer-key metadata from a renderer item answer key."""

    return DigiExamEffectiveAnswerKey(
        provenance=provenance.value,
        correct_alternative_ids=item.answer_key.correct_alternative_ids,
        correct_gap_answers=tuple(
            {"gap_id": answer.guid, "value": answer.value}
            for answer in item.answer_key.correct_gap_answers
        ),
        lineage=lineage,
    )


def _effective_lineage(
    key: DigiExamOverlayReviewedCompletionAnswerKey,
) -> DigiExamEffectiveAnswerKeyLineage:
    lineage = key.candidate_lineage
    return DigiExamEffectiveAnswerKeyLineage(
        completion_report_sha256=lineage.completion_report_sha256,
        candidate_id=lineage.candidate_id,
        candidate_payload_digest=lineage.candidate_payload_digest,
        provider_profile_id=lineage.provider_profile_id,
        schema_name=lineage.schema_name,
        schema_version=lineage.schema_version,
        prompt_template_version=lineage.prompt_template_version,
        validation_state=lineage.validation_state,
        review_decision_id=key.review_decision_id,
        review_outcome=key.review_outcome.value,
    )


def _reviewed_answer_payload(
    key: DigiExamOverlayReviewedCompletionAnswerKey,
) -> dict[str, JsonValue]:
    payload = key.answer_payload
    if payload.kind == "choice":
        return {
            "kind": "choice",
            "correct_alternative_ids": list(payload.correct_alternative_ids),
        }
    return {
        "kind": "gap_fill",
        "gap_answers": [
            {"gap_id": answer.gap_id, "accepted_values": list(answer.accepted_values)}
            for answer in payload.gap_answers
        ],
    }


def _reviewed_choice_ids(payload: dict[str, JsonValue]) -> tuple[int, ...]:
    ids = payload.get("correct_alternative_ids")
    if not isinstance(ids, list):
        return ()
    return tuple(identifier for identifier in ids if isinstance(identifier, int))


def _reviewed_gap_answers(payload: dict[str, JsonValue]) -> tuple[DigiExamGapAnswer, ...]:
    raw_gap_answers = payload.get("gap_answers")
    if not isinstance(raw_gap_answers, list):
        return ()
    answers: list[DigiExamGapAnswer] = []
    for raw_answer in raw_gap_answers:
        if not isinstance(raw_answer, dict):
            continue
        gap_id = raw_answer.get("gap_id")
        accepted_values = raw_answer.get("accepted_values")
        if not isinstance(gap_id, str) or not isinstance(accepted_values, list):
            continue
        answers.extend(
            DigiExamGapAnswer(guid=gap_id, value=value)
            for value in accepted_values
            if isinstance(value, str)
        )
    return tuple(answers)


def _item_error(
    entry: DigiExamIngestionOverlayItem, code: str, message: str
) -> DigiExamIngestionOverlayError:
    return DigiExamIngestionOverlayError(
        f"digiexam_ingestion_overlay_{code}",
        message,
        {"item_id": entry.item_id, "sequence": entry.sequence},
    )
