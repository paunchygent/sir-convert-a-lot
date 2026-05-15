"""Tests for source-neutral ExamAuthoringIR matching contracts.

Purpose:
    Prove that Task 307 extracts matching interaction semantics into a
    source-neutral authoring contract without requiring DigiExam matching
    parser fixtures.

Relationships:
    - Exercises `domain.exam_authoring_ir_contracts` as the first
      `ExamAuthoringIR v1` slice.
    - Keeps DigiExam `.dxe` matching out of the parser/adapter contract while
      preserving QTI-permissive and Exam.net PDF target-profile validation.
"""

from __future__ import annotations

from dataclasses import asdict

from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringMatchingAnswerKey,
    ExamAuthoringMatchingChoice,
    ExamAuthoringMatchingInteraction,
    ExamAuthoringMatchingPair,
    ExamAuthoringMatchingValidationIssueCode,
    build_exam_authoring_matching_interaction,
    validate_exam_authoring_matching_interaction,
    validate_examnet_pdf_matching_profile,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
)


def test_matching_contract_serializes_with_source_neutral_schema_version() -> None:
    interaction = _matching_interaction(
        pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),)
    )

    payload = asdict(interaction)

    assert payload["schema_version"] == EXAM_AUTHORING_IR_SCHEMA_VERSION
    assert payload["source_choices"][0]["choice_id"] == "source-001"
    assert payload["target_choices"][1]["choice_id"] == "target-002"
    assert "digiexam" not in repr(payload).lower()


def test_matching_contract_allows_qti_permissive_reused_targets() -> None:
    interaction = _matching_interaction(
        pairs=(
            ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),
            ExamAuthoringMatchingPair(source_id="source-002", target_id="target-001"),
        )
    )

    neutral_result = validate_exam_authoring_matching_interaction(interaction)
    examnet_pdf_result = validate_examnet_pdf_matching_profile(interaction)

    assert neutral_result.valid is True
    assert examnet_pdf_result.valid is False
    assert {issue.reason_code for issue in examnet_pdf_result.issues} == {
        ExamAuthoringMatchingValidationIssueCode.EXAMNET_PDF_REPEATED_TARGET_NOT_SUPPORTED
    }


def test_matching_contract_allows_unmatched_target_distractors() -> None:
    interaction = _matching_interaction(
        pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
        min_associations=1,
        max_associations=1,
    )

    neutral_result = validate_exam_authoring_matching_interaction(interaction)
    examnet_pdf_result = validate_examnet_pdf_matching_profile(interaction)

    assert neutral_result.valid is True
    assert examnet_pdf_result.valid is True


def test_matching_contract_rejects_duplicate_pairs_and_unknown_ids() -> None:
    interaction = _matching_interaction(
        pairs=(
            ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),
            ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),
            ExamAuthoringMatchingPair(source_id="source-404", target_id="target-404"),
        ),
        min_associations=1,
        max_associations=0,
    )

    result = validate_exam_authoring_matching_interaction(interaction)

    assert result.valid is False
    assert {issue.reason_code for issue in result.issues} >= {
        ExamAuthoringMatchingValidationIssueCode.DUPLICATE_PAIR,
        ExamAuthoringMatchingValidationIssueCode.UNKNOWN_SOURCE_ID,
        ExamAuthoringMatchingValidationIssueCode.UNKNOWN_TARGET_ID,
    }


def test_matching_contract_rejects_association_limit_violations() -> None:
    interaction = _matching_interaction(
        pairs=(
            ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),
            ExamAuthoringMatchingPair(source_id="source-001", target_id="target-002"),
        ),
        min_associations=1,
        max_associations=0,
    )

    result = validate_exam_authoring_matching_interaction(interaction)

    assert result.valid is False
    assert ExamAuthoringMatchingValidationIssueCode.SOURCE_ASSOCIATION_LIMIT_EXCEEDED in {
        issue.reason_code for issue in result.issues
    }


def test_matching_contract_rejects_invalid_interaction_bounds() -> None:
    negative_minimum = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            min_associations=-1,
            max_associations=1,
        )
    )
    negative_maximum = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            min_associations=0,
            max_associations=-1,
        )
    )
    impossible_bounds = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            min_associations=2,
            max_associations=1,
        )
    )

    assert {result.valid for result in (negative_minimum, negative_maximum, impossible_bounds)} == {
        False
    }
    assert all(
        ExamAuthoringMatchingValidationIssueCode.INVALID_INTERACTION_BOUNDS
        in {issue.reason_code for issue in result.issues}
        for result in (negative_minimum, negative_maximum, impossible_bounds)
    )


def test_matching_contract_rejects_invalid_source_choice_bounds() -> None:
    negative_minimum = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            source_choice_bounds=(-1, 1),
        )
    )
    negative_maximum = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            source_choice_bounds=(0, -1),
        )
    )
    impossible_bounds = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            source_choice_bounds=(2, 1),
        )
    )

    assert {result.valid for result in (negative_minimum, negative_maximum, impossible_bounds)} == {
        False
    }
    assert all(
        ExamAuthoringMatchingValidationIssueCode.INVALID_SOURCE_BOUNDS
        in {issue.reason_code for issue in result.issues}
        for result in (negative_minimum, negative_maximum, impossible_bounds)
    )


def test_matching_contract_rejects_invalid_target_choice_bounds() -> None:
    negative_minimum = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            target_choice_bounds=(-1, 1),
        )
    )
    negative_maximum = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            target_choice_bounds=(0, -1),
        )
    )
    impossible_bounds = validate_exam_authoring_matching_interaction(
        _matching_interaction(
            pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
            target_choice_bounds=(2, 1),
        )
    )

    assert {result.valid for result in (negative_minimum, negative_maximum, impossible_bounds)} == {
        False
    }
    assert all(
        ExamAuthoringMatchingValidationIssueCode.INVALID_TARGET_BOUNDS
        in {issue.reason_code for issue in result.issues}
        for result in (negative_minimum, negative_maximum, impossible_bounds)
    )


def test_matching_contract_rejects_mixed_provenance_without_pair_provenance() -> None:
    interaction = _matching_interaction(
        pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
        min_associations=1,
        max_associations=1,
        provenance=ExamAuthoringAnswerKeyProvenance.MIXED,
    )

    result = validate_exam_authoring_matching_interaction(interaction)

    assert result.valid is False
    assert ExamAuthoringMatchingValidationIssueCode.MIXED_PROVENANCE_WITHOUT_PAIR_PROVENANCE in {
        issue.reason_code for issue in result.issues
    }


def test_matching_contract_rejects_absent_provenance_with_pairs() -> None:
    interaction = _matching_interaction(
        pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
        min_associations=1,
        max_associations=1,
        provenance=ExamAuthoringAnswerKeyProvenance.ABSENT,
    )

    result = validate_exam_authoring_matching_interaction(interaction)

    assert result.valid is False
    assert ExamAuthoringMatchingValidationIssueCode.ABSENT_PROVENANCE_WITH_PAIRS in {
        issue.reason_code for issue in result.issues
    }


def test_matching_contract_allows_reviewed_whole_key_provenance() -> None:
    interaction = _matching_interaction(
        pairs=(ExamAuthoringMatchingPair(source_id="source-001", target_id="target-001"),),
        min_associations=1,
        max_associations=1,
        provenance=ExamAuthoringAnswerKeyProvenance.REVIEWED,
    )

    result = validate_exam_authoring_matching_interaction(interaction)

    assert result.valid is True
    assert result.issues == ()


def _matching_interaction(
    *,
    pairs: tuple[ExamAuthoringMatchingPair, ...],
    min_associations: int = 2,
    max_associations: int = 2,
    source_choice_bounds: tuple[int, int] = (1, 1),
    target_choice_bounds: tuple[int, int] = (0, 0),
    provenance: ExamAuthoringAnswerKeyProvenance = (
        ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED
    ),
) -> ExamAuthoringMatchingInteraction:
    source_min, source_max = source_choice_bounds
    target_min, target_max = target_choice_bounds
    return build_exam_authoring_matching_interaction(
        interaction_id="matching-001",
        source_choices=(
            ExamAuthoringMatchingChoice(
                choice_id="source-001",
                order=1,
                text="Författare 1",
                match_min=source_min,
                match_max=source_max,
            ),
            ExamAuthoringMatchingChoice(
                choice_id="source-002",
                order=2,
                text="Författare 2",
                match_min=0,
                match_max=1,
            ),
        ),
        target_choices=(
            ExamAuthoringMatchingChoice(
                choice_id="target-001",
                order=1,
                text="Romantiken",
                match_min=target_min,
                match_max=target_max,
            ),
            ExamAuthoringMatchingChoice(
                choice_id="target-002",
                order=2,
                text="Realismen",
                match_min=0,
                match_max=0,
            ),
        ),
        min_associations=min_associations,
        max_associations=max_associations,
        answer_key=ExamAuthoringMatchingAnswerKey(
            provenance=provenance,
            pairs=pairs,
        ),
    )
