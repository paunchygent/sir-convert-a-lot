"""Correction replay overlay translation for DigiExam rendering.

Purpose:
    Translate source-neutral exam-authoring correction requests into the
    DigiExam ingestion overlay payload used to render corrected replay
    artifacts.

Relationships:
    - Consumed by `infrastructure.correction_replay_artifact_writer`.
    - Bridges `exam_authoring_corrections_apply_models` DTOs to
      `domain.digiexam_ingestion_overlay_contracts`.
    - Keeps replay artifact rendering source-bound without introducing
      consumer-side artifact guesses.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCandidateLineageV1,
    ExamAuthoringCorrectionEntryV1,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionSourceItemV1,
    ExamAuthoringItemTextPatchCorrectionV1,
    ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
    ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
    ExamAuthoringPointCorrectionV1,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DIGIEXAM_IR_SCHEMA_VERSION
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class CorrectionReplayOverlayPayload:
    """DigiExam overlay payload plus the reviewed-completion mode flag."""

    has_reviewed_completion: bool
    payload: dict[str, object]


class CorrectionReplayOverlayBuildError(ValueError):
    """Raised when a correction batch cannot be rendered as a DigiExam overlay."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def build_correction_replay_overlay_payload(
    *,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    source_file_sha256: str,
    source_ir_sha256: str,
) -> CorrectionReplayOverlayPayload:
    """Build the DigiExam ingestion overlay payload for correction replay."""

    source_items = {item.item_id: item for item in request_body.source_authoring_state.items}
    item_payloads: dict[str, dict[str, object]] = {}
    has_reviewed_completion = False
    for correction in request_body.corrections:
        if not _renderable_correction(correction):
            continue
        source_item = source_items.get(correction.item_id)
        if source_item is None:
            raise CorrectionReplayOverlayBuildError("correction_replay_unknown_source_item")
        payload = item_payloads.setdefault(
            correction.item_id,
            _base_overlay_item(correction=correction, source_item=source_item),
        )
        has_reviewed_completion = (
            _apply_overlay_field(payload=payload, correction=correction, source_item=source_item)
            or has_reviewed_completion
        )
    if not item_payloads:
        raise CorrectionReplayOverlayBuildError("correction_replay_no_renderable_corrections")
    return CorrectionReplayOverlayPayload(
        has_reviewed_completion=has_reviewed_completion,
        payload={
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": source_file_sha256,
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": source_ir_sha256,
            },
            "items": list(item_payloads.values()),
        },
    )


def _renderable_correction(correction: ExamAuthoringCorrectionEntryV1) -> bool:
    return isinstance(
        correction,
        (
            ExamAuthoringItemTextPatchCorrectionV1,
            ExamAuthoringManualChoiceAnswerKeyCorrectionV1,
            ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1,
            ExamAuthoringPointCorrectionV1,
        ),
    )


def _base_overlay_item(
    *,
    correction: ExamAuthoringCorrectionEntryV1,
    source_item: ExamAuthoringCorrectionSourceItemV1,
) -> dict[str, object]:
    source_item_fingerprint = correction.source_item_fingerprint
    if source_item_fingerprint is None:
        raise CorrectionReplayOverlayBuildError("correction_replay_source_item_fingerprint_missing")
    return {
        "item_id": correction.item_id,
        "sequence": correction.sequence,
        "item_type": source_item.item_type,
        "source_item_fingerprint": source_item_fingerprint,
    }


def _apply_overlay_field(
    *,
    payload: dict[str, object],
    correction: ExamAuthoringCorrectionEntryV1,
    source_item: ExamAuthoringCorrectionSourceItemV1,
) -> bool:
    if isinstance(correction, ExamAuthoringItemTextPatchCorrectionV1):
        payload["effective_item_patch"] = _item_patch_payload(
            correction=correction,
            source_item=source_item,
        )
        return False
    if isinstance(correction, ExamAuthoringManualChoiceAnswerKeyCorrectionV1):
        return _set_answer_key_payload(
            payload=payload,
            correction=correction,
            answer_payload={
                "kind": "choice",
                "correct_alternative_ids": [
                    _alternative_id_for_choice(source_item=source_item, choice_id=choice_id)
                    for choice_id in correction.correct_choice_ids
                ],
            },
        )
    if isinstance(correction, ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1):
        return _set_answer_key_payload(
            payload=payload,
            correction=correction,
            answer_payload={
                "kind": "gap_fill",
                "gap_answers": [
                    {
                        "gap_id": answer.gap_id,
                        "accepted_values": list(answer.accepted_values),
                    }
                    for answer in correction.gap_answers
                ],
            },
        )
    if isinstance(correction, ExamAuthoringPointCorrectionV1):
        payload["point_correction"] = {
            "kind": "item_points",
            "max_score": correction.max_score,
        }
        return False
    return False


def _item_patch_payload(
    *,
    correction: ExamAuthoringItemTextPatchCorrectionV1,
    source_item: ExamAuthoringCorrectionSourceItemV1,
) -> dict[str, object]:
    if source_item.item_type not in {
        "single_choice",
        "multiple_choice",
        "multiple_response",
        "gap_fill",
    }:
        raise CorrectionReplayOverlayBuildError("correction_replay_item_patch_not_renderable")
    payload: dict[str, object] = {
        "kind": "gap_fill" if source_item.item_type == "gap_fill" else "choice"
    }
    alternative_overrides: list[dict[str, object]] = []
    for patch in correction.patches:
        if patch.field == "item_title":
            payload["title"] = patch.value
        elif patch.field == "prompt_html":
            payload["prompt_html"] = patch.value
        elif patch.field == "prompt_lines":
            payload["prompt_lines"] = [line for line in patch.value.splitlines() if line.strip()]
        elif patch.field == "visible_option_text" and patch.choice_id is not None:
            alternative_overrides.append(
                {
                    "alternative_id": _alternative_id_for_choice(
                        source_item=source_item,
                        choice_id=patch.choice_id,
                    ),
                    "text": patch.value,
                }
            )
        else:
            raise CorrectionReplayOverlayBuildError("correction_replay_item_patch_not_renderable")
    if alternative_overrides:
        payload["alternative_overrides"] = alternative_overrides
    return payload


def _set_answer_key_payload(
    *,
    payload: dict[str, object],
    correction: (
        ExamAuthoringManualChoiceAnswerKeyCorrectionV1
        | ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1
    ),
    answer_payload: dict[str, object],
) -> bool:
    if correction.submission_origin == "teacher_authored":
        payload["manual_answer_key"] = answer_payload
        return False
    lineage = correction.candidate_lineage
    if lineage is None:
        raise CorrectionReplayOverlayBuildError("correction_replay_candidate_lineage_missing")
    payload["reviewed_completion_answer_key"] = {
        "kind": answer_payload["kind"],
        "review_decision_id": correction.entry_id,
        "review_outcome": (
            "accepted_unchanged"
            if correction.submission_origin == "accepted_advisory_candidate"
            else "teacher_edited"
        ),
        "candidate_lineage": _candidate_lineage_payload(lineage),
        "answer_payload": answer_payload,
    }
    return True


def _candidate_lineage_payload(lineage: ExamAuthoringCandidateLineageV1) -> dict[str, object]:
    return {
        "completion_report_sha256": lineage.completion_report_sha256,
        "candidate_id": lineage.candidate_id,
        "candidate_payload_digest": lineage.candidate_payload_digest,
        "provider_profile_id": lineage.provider_profile_id,
        "schema_name": lineage.schema_name,
        "schema_version": lineage.schema_version,
        "prompt_template_version": lineage.prompt_template_version,
        "validation_state": lineage.validation_state,
    }


def _alternative_id_for_choice(
    *,
    source_item: ExamAuthoringCorrectionSourceItemV1,
    choice_id: str,
) -> int:
    for interaction in source_item.choice_interactions:
        for choice in interaction.choices:
            if choice.choice_id == choice_id and choice.source_id is not None:
                try:
                    return int(choice.source_id)
                except ValueError as exc:
                    raise CorrectionReplayOverlayBuildError(
                        "correction_replay_choice_source_id_not_renderable"
                    ) from exc
    raise CorrectionReplayOverlayBuildError("correction_replay_unknown_choice_id")
