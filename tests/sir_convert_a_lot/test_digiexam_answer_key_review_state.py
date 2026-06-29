"""Tests for compact DigiExam answer-key review-state projection.

Purpose:
    Prove the Sir Convert-owned review-state projection schema rejects
    compatibility fields and emits item-addressable state for missing keys.

Relationships:
    - Exercises the public Pydantic DTO and projection builder consumed by
      migration bundles and correction apply results.
    - Complements route tests that prove named artifact and response exposure.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state import (
    DigiExamAnswerKeyReviewStateItemV1,
    DigiExamAnswerKeyReviewStateV1,
    build_digiexam_answer_key_review_state,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceStateV1,
)


def test_review_state_projection_reports_choice_and_gap_missing_key_reasons() -> None:
    report = build_digiexam_answer_key_review_state(
        source_state=ExamAuthoringCorrectionSourceStateV1.model_validate(
            {
                "schema_version": "exam_authoring_correction_source_state_v1",
                "source_authoring_schema_version": "exam_authoring_ir_v1",
                "source_state_sha256": "sha256:source-state",
                "items": [_choice_item(), _gap_item()],
            }
        )
    )

    items = {item.item_id: item for item in report.items}
    assert items["item-choice"].review_state == "validation_required"
    assert items["item-choice"].current_key_origin == "none"
    assert items["item-choice"].reasons == ("no_correct_choice_selected",)
    assert items["item-gap"].review_state == "validation_required"
    assert items["item-gap"].current_key_origin == "none"
    assert items["item-gap"].reasons == ("required_gap_accepted_values_missing",)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("review_state", "accepted_current_state"),
        ("current_key_origin", "legacy_reviewed"),
        ("reasons", ["needs_teacher_review_decision"]),
    ),
)
def test_review_state_schema_rejects_unknown_vocabularies(field: str, value: object) -> None:
    payload = _review_item_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DigiExamAnswerKeyReviewStateItemV1.model_validate(payload)


@pytest.mark.parametrize(
    "legacy_field",
    (
        "history",
        "review_decision",
        "accept_current_state_for_export",
    ),
)
def test_review_state_schema_rejects_legacy_compatibility_fields(legacy_field: str) -> None:
    payload = _review_item_payload()
    payload[legacy_field] = {"kind": "accept_current_state_for_export"}

    with pytest.raises(ValidationError):
        DigiExamAnswerKeyReviewStateItemV1.model_validate(payload)


def test_review_state_schema_accepts_only_bounded_top_level_shape() -> None:
    with pytest.raises(ValidationError):
        DigiExamAnswerKeyReviewStateV1.model_validate(
            {
                "schema_version": "digiexam_answer_key_review_state_v1",
                "items": [_review_item_payload()],
                "source_state_signature": "hmac-sha256:private",
            }
        )


def _review_item_payload() -> dict[str, object]:
    return {
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "choice_interaction_ids": ["choice-item-choice"],
        "choice_ids": ["choice-001", "choice-002"],
        "gap_interaction_ids": [],
        "gap_ids": [],
        "correction_affordances": ["manual_choice_answer_key"],
        "review_state": "validation_required",
        "current_key_origin": "none",
        "reasons": ["no_correct_choice_selected"],
        "message_key": "exam_converter.answer_key_review.no_correct_choice_selected",
        "provenance_detail": None,
        "replay_artifact_references": [],
    }


def _choice_item() -> dict[str, object]:
    return {
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "choice_interactions": [
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": "choice-item-choice",
                "interaction_kind": "single_choice",
                "choices": [
                    {"choice_id": "choice-001", "order": 1, "source_id": "1", "text": "Alpha"},
                    {"choice_id": "choice-002", "order": 2, "source_id": "2", "text": "Beta"},
                ],
                "min_correct_choices": 1,
                "max_correct_choices": 1,
                "answer_key": {"provenance": "absent", "correct_choice_ids": []},
                "evidence": [],
            }
        ],
    }


def _gap_item() -> dict[str, object]:
    return {
        "item_id": "item-gap",
        "sequence": 2,
        "item_type": "gap_fill",
        "source_item_fingerprint": "sha256:item-gap",
        "gap_open_cloze_interactions": [
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": "gap-item-gap",
                "gaps": [
                    {
                        "gap_id": "gap-1",
                        "display_order": 1,
                        "prompt_binding": {
                            "kind": "html_attribute",
                            "locator": "data-gap-id=gap-1",
                        },
                        "required_for_auto_evaluation": True,
                        "evidence": [],
                    }
                ],
                "normalization_profile": "exact_trim_case_sensitive",
                "answer_key": {"provenance": "absent", "accepted_values": []},
                "evidence": [],
            }
        ],
    }
