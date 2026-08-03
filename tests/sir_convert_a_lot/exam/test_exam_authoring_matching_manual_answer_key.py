"""Tests for source-neutral matching manual answer-key submissions.

Purpose:
    Prove that HTML to PDF route3 exposes a producer-ready matching key DTO and
    validation boundary without reintroducing DigiExam-specific matching
    overlays.

Relationships:
    - Exercises `domain.exam_authoring_matching_manual_answer_key`.
    - Reuses `domain.exam_authoring_ir_contracts` as the neutral matching
      authority.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringMatchingAnswerKey,
    ExamAuthoringMatchingChoice,
    ExamAuthoringMatchingInteraction,
    ExamAuthoringMatchingPair,
    build_exam_authoring_matching_interaction,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_matching_manual_answer_key import (
    ExamAuthoringMatchingManualAnswerKey,
    ExamAuthoringMatchingManualAnswerKeyError,
    apply_exam_authoring_matching_manual_answer_key,
    parse_exam_authoring_matching_manual_answer_key_json,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
)


def test_matching_manual_answer_key_applies_to_source_neutral_interaction() -> None:
    submission = ExamAuthoringMatchingManualAnswerKey.model_validate(
        {
            "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
            "kind": "matching",
            "interaction_id": "matching-001",
            "source_item_fingerprint": "sha256:item",
            "answer_key": {
                "provenance": "teacher_provided",
                "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
            },
        }
    )

    updated = apply_exam_authoring_matching_manual_answer_key(
        submission=submission,
        interaction=_empty_matching_interaction(),
        expected_source_item_fingerprint="sha256:item",
    )

    assert updated.schema_version == EXAM_AUTHORING_IR_SCHEMA_VERSION
    assert updated.answer_key.provenance == ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED
    assert updated.answer_key.pairs == (
        ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),
    )


def test_matching_manual_answer_key_rejects_retired_left_right_aliases() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExamAuthoringMatchingManualAnswerKey.model_validate(
            {
                "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
                "kind": "matching",
                "interaction_id": "matching-001",
                "answer_key": {
                    "provenance": "teacher_provided",
                    "pairs": [{"left_id": "source-001", "right_id": "target-001"}],
                },
            }
        )

    error_locations = {tuple(error["loc"]) for error in exc_info.value.errors()}

    assert ("answer_key", "pairs", 0, "source_id") in error_locations
    assert ("answer_key", "pairs", 0, "target_id") in error_locations
    assert ("answer_key", "pairs", 0, "left_id") in error_locations
    assert ("answer_key", "pairs", 0, "right_id") in error_locations


def test_matching_manual_answer_key_rejects_absent_pairs_and_mixed_provenance() -> None:
    base = {
        "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
        "kind": "matching",
        "interaction_id": "matching-001",
        "answer_key": {
            "provenance": "absent",
            "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
        },
    }

    with pytest.raises(ValidationError, match="absent matching provenance"):
        ExamAuthoringMatchingManualAnswerKey.model_validate(base)

    mixed = {
        **base,
        "answer_key": {"provenance": "mixed", "pairs": []},
    }
    with pytest.raises(ValidationError):
        ExamAuthoringMatchingManualAnswerKey.model_validate(mixed)


def test_matching_manual_answer_key_rejects_unknown_ids_before_application() -> None:
    submission = ExamAuthoringMatchingManualAnswerKey.model_validate(
        {
            "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
            "kind": "matching",
            "interaction_id": "matching-001",
            "answer_key": {
                "provenance": "teacher_provided",
                "pairs": [{"source_id": "source-404", "target_id": "target-404"}],
            },
        }
    )

    with pytest.raises(ExamAuthoringMatchingManualAnswerKeyError) as exc_info:
        apply_exam_authoring_matching_manual_answer_key(
            submission=submission,
            interaction=_empty_matching_interaction(),
        )

    assert exc_info.value.code == "exam_authoring_matching_manual_answer_key_rejected"
    issues = exc_info.value.details["issues"]
    assert isinstance(issues, tuple)
    assert {issue["reason_code"] for issue in issues if isinstance(issue, dict)} >= {
        "unknown_matching_source_id",
        "unknown_matching_target_id",
    }


def test_matching_manual_answer_key_rejects_stale_source_binding() -> None:
    submission = ExamAuthoringMatchingManualAnswerKey.model_validate(
        {
            "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
            "kind": "matching",
            "interaction_id": "matching-001",
            "source_item_fingerprint": "sha256:stale",
            "answer_key": {
                "provenance": "teacher_provided",
                "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
            },
        }
    )

    with pytest.raises(ExamAuthoringMatchingManualAnswerKeyError) as exc_info:
        apply_exam_authoring_matching_manual_answer_key(
            submission=submission,
            interaction=_empty_matching_interaction(),
            expected_source_item_fingerprint="sha256:item",
        )

    assert exc_info.value.code == "stale_matching_source_item_fingerprint"


def test_matching_manual_answer_key_json_parser_reports_schema_errors() -> None:
    with pytest.raises(ExamAuthoringMatchingManualAnswerKeyError) as exc_info:
        parse_exam_authoring_matching_manual_answer_key_json(
            b'{"kind":"matching","interaction_id":"matching-001","answer_key":{}}'
        )

    assert exc_info.value.code == "exam_authoring_matching_manual_answer_key_invalid"
    assert "errors" in exc_info.value.details


def _empty_matching_interaction() -> ExamAuthoringMatchingInteraction:
    return build_exam_authoring_matching_interaction(
        interaction_id="matching-001",
        source_choices=(
            ExamAuthoringMatchingChoice(
                choice_id="source-001",
                order=1,
                text="Source 1",
                match_min=1,
                match_max=1,
            ),
        ),
        target_choices=(
            ExamAuthoringMatchingChoice(
                choice_id="target-001",
                order=1,
                text="Target 1",
                match_min=1,
                match_max=1,
            ),
        ),
        min_associations=1,
        max_associations=1,
        answer_key=ExamAuthoringMatchingAnswerKey(
            provenance=ExamAuthoringAnswerKeyProvenance.ABSENT,
            pairs=(),
        ),
    )
