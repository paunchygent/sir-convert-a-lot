"""Source-neutral exam authoring interaction contracts.

Purpose:
    Define reusable authoring IR value objects shared by source adapters and
    target validators/exporters, beginning with matching interactions.

Relationships:
    - Owns the Task 307 first-slice matching contract extracted from
      DigiExam-named adapter contracts.
    - Feeds future Exam.net PDF, teacher-authored DOCX/Markdown, QTI, and
      Exam.net PDF target-profile validators without depending on DigiExam
      parser shapes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)

_MatchingChoiceSide = Literal["source", "target"]


class ExamAuthoringAnswerKeyProvenance(StrEnum):
    """Source-neutral answer-key provenance states."""

    ABSENT = "absent"
    SOURCE_PROVIDED = "source_provided"
    TEACHER_PROVIDED = "teacher_provided"
    REVIEWED = "reviewed"


class ExamAuthoringMatchingValidationIssueCode(StrEnum):
    """Stable validation issue codes for matching interaction contracts."""

    DUPLICATE_SOURCE_ID = "duplicate_matching_source_id"
    DUPLICATE_TARGET_ID = "duplicate_matching_target_id"
    BLANK_SOURCE_ID = "blank_matching_source_id"
    BLANK_TARGET_ID = "blank_matching_target_id"
    DUPLICATE_PAIR = "duplicate_matching_pair"
    UNKNOWN_SOURCE_ID = "unknown_matching_source_id"
    UNKNOWN_TARGET_ID = "unknown_matching_target_id"
    ASSOCIATION_COUNT_OUT_OF_BOUNDS = "matching_association_count_out_of_bounds"
    SOURCE_ASSOCIATION_LIMIT_EXCEEDED = "matching_source_association_limit_exceeded"
    TARGET_ASSOCIATION_LIMIT_EXCEEDED = "matching_target_association_limit_exceeded"
    EXAMNET_PDF_REPEATED_SOURCE_NOT_SUPPORTED = "examnet_pdf_matching_repeated_source_not_supported"
    EXAMNET_PDF_REPEATED_TARGET_NOT_SUPPORTED = "examnet_pdf_matching_repeated_target_not_supported"


@dataclass(frozen=True)
class ExamAuthoringSourceEvidence:
    """Optional source evidence that does not assume one source format."""

    source_family: str
    source_id: str | None
    locator: str | None


@dataclass(frozen=True)
class ExamAuthoringMatchingChoice:
    """One ordered source or target choice in a matching interaction."""

    choice_id: str
    order: int
    text: str
    match_min: int
    match_max: int


@dataclass(frozen=True)
class ExamAuthoringMatchingPair:
    """One directed source-to-target answer association."""

    source_id: str
    target_id: str


@dataclass(frozen=True)
class ExamAuthoringMatchingAnswerKey:
    """Matching answer key with source-neutral provenance."""

    provenance: ExamAuthoringAnswerKeyProvenance
    pairs: tuple[ExamAuthoringMatchingPair, ...]


@dataclass(frozen=True)
class ExamAuthoringMatchingInteraction:
    """Source-neutral matching interaction with QTI-compatible bounds."""

    schema_version: ExamAuthoringIrSchemaVersion
    interaction_id: str
    source_choices: tuple[ExamAuthoringMatchingChoice, ...]
    target_choices: tuple[ExamAuthoringMatchingChoice, ...]
    min_associations: int
    max_associations: int
    answer_key: ExamAuthoringMatchingAnswerKey
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = ()


@dataclass(frozen=True)
class ExamAuthoringMatchingValidationIssue:
    """One source-neutral matching contract validation issue."""

    reason_code: ExamAuthoringMatchingValidationIssueCode
    message: str
    source_id: str | None = None
    target_id: str | None = None


@dataclass(frozen=True)
class ExamAuthoringMatchingValidationResult:
    """Validation result for a matching interaction or target profile."""

    valid: bool
    issues: tuple[ExamAuthoringMatchingValidationIssue, ...]


def build_exam_authoring_matching_interaction(
    *,
    interaction_id: str,
    source_choices: tuple[ExamAuthoringMatchingChoice, ...],
    target_choices: tuple[ExamAuthoringMatchingChoice, ...],
    min_associations: int,
    max_associations: int,
    answer_key: ExamAuthoringMatchingAnswerKey,
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = (),
) -> ExamAuthoringMatchingInteraction:
    """Build a versioned source-neutral matching interaction."""

    return ExamAuthoringMatchingInteraction(
        schema_version=EXAM_AUTHORING_IR_SCHEMA_VERSION,
        interaction_id=interaction_id,
        source_choices=source_choices,
        target_choices=target_choices,
        min_associations=min_associations,
        max_associations=max_associations,
        answer_key=answer_key,
        evidence=evidence,
    )


def validate_exam_authoring_matching_interaction(
    interaction: ExamAuthoringMatchingInteraction,
) -> ExamAuthoringMatchingValidationResult:
    """Validate source-neutral matching structure and association bounds."""

    issues: list[ExamAuthoringMatchingValidationIssue] = []
    source_ids = tuple(choice.choice_id for choice in interaction.source_choices)
    target_ids = tuple(choice.choice_id for choice in interaction.target_choices)
    issues.extend(_duplicate_choice_issues("source", source_ids))
    issues.extend(_duplicate_choice_issues("target", target_ids))
    issues.extend(_blank_choice_issues("source", source_ids))
    issues.extend(_blank_choice_issues("target", target_ids))
    issues.extend(_duplicate_pair_issues(interaction.answer_key.pairs))

    valid_source_ids = frozenset(source_ids)
    valid_target_ids = frozenset(target_ids)
    for pair in interaction.answer_key.pairs:
        if pair.source_id not in valid_source_ids:
            issues.append(
                ExamAuthoringMatchingValidationIssue(
                    reason_code=ExamAuthoringMatchingValidationIssueCode.UNKNOWN_SOURCE_ID,
                    message="Matching key references an unknown source choice.",
                    source_id=pair.source_id,
                    target_id=pair.target_id,
                )
            )
        if pair.target_id not in valid_target_ids:
            issues.append(
                ExamAuthoringMatchingValidationIssue(
                    reason_code=ExamAuthoringMatchingValidationIssueCode.UNKNOWN_TARGET_ID,
                    message="Matching key references an unknown target choice.",
                    source_id=pair.source_id,
                    target_id=pair.target_id,
                )
            )

    pair_count = len(interaction.answer_key.pairs)
    if not _within_bounds(pair_count, interaction.min_associations, interaction.max_associations):
        issues.append(
            ExamAuthoringMatchingValidationIssue(
                reason_code=(
                    ExamAuthoringMatchingValidationIssueCode.ASSOCIATION_COUNT_OUT_OF_BOUNDS
                ),
                message="Matching pair count violates interaction association bounds.",
            )
        )

    source_counts = _counts(pair.source_id for pair in interaction.answer_key.pairs)
    target_counts = _counts(pair.target_id for pair in interaction.answer_key.pairs)
    for choice in interaction.source_choices:
        if not _within_bounds(
            source_counts.get(choice.choice_id, 0),
            choice.match_min,
            choice.match_max,
        ):
            issues.append(
                ExamAuthoringMatchingValidationIssue(
                    reason_code=(
                        ExamAuthoringMatchingValidationIssueCode.SOURCE_ASSOCIATION_LIMIT_EXCEEDED
                    ),
                    message="Matching key violates source choice association bounds.",
                    source_id=choice.choice_id,
                )
            )
    for choice in interaction.target_choices:
        if not _within_bounds(
            target_counts.get(choice.choice_id, 0),
            choice.match_min,
            choice.match_max,
        ):
            issues.append(
                ExamAuthoringMatchingValidationIssue(
                    reason_code=(
                        ExamAuthoringMatchingValidationIssueCode.TARGET_ASSOCIATION_LIMIT_EXCEEDED
                    ),
                    message="Matching key violates target choice association bounds.",
                    target_id=choice.choice_id,
                )
            )

    return ExamAuthoringMatchingValidationResult(valid=not issues, issues=tuple(issues))


def validate_examnet_pdf_matching_profile(
    interaction: ExamAuthoringMatchingInteraction,
) -> ExamAuthoringMatchingValidationResult:
    """Validate the current Exam.net PDF matching profile constraints."""

    issues = list(validate_exam_authoring_matching_interaction(interaction).issues)
    source_ids = tuple(pair.source_id for pair in interaction.answer_key.pairs)
    target_ids = tuple(pair.target_id for pair in interaction.answer_key.pairs)
    if len(set(source_ids)) != len(source_ids):
        issues.append(
            ExamAuthoringMatchingValidationIssue(
                reason_code=(
                    ExamAuthoringMatchingValidationIssueCode.EXAMNET_PDF_REPEATED_SOURCE_NOT_SUPPORTED
                ),
                message=(
                    "Exam.net PDF matching does not support one source matched to several targets."
                ),
            )
        )
    if len(set(target_ids)) != len(target_ids):
        issues.append(
            ExamAuthoringMatchingValidationIssue(
                reason_code=(
                    ExamAuthoringMatchingValidationIssueCode.EXAMNET_PDF_REPEATED_TARGET_NOT_SUPPORTED
                ),
                message=(
                    "Exam.net PDF matching does not support one target matched "
                    "from several sources."
                ),
            )
        )
    return ExamAuthoringMatchingValidationResult(valid=not issues, issues=tuple(issues))


def _duplicate_choice_issues(
    side: _MatchingChoiceSide, choice_ids: tuple[str, ...]
) -> tuple[ExamAuthoringMatchingValidationIssue, ...]:
    reason_code = (
        ExamAuthoringMatchingValidationIssueCode.DUPLICATE_SOURCE_ID
        if side == "source"
        else ExamAuthoringMatchingValidationIssueCode.DUPLICATE_TARGET_ID
    )
    return tuple(
        ExamAuthoringMatchingValidationIssue(
            reason_code=reason_code,
            message=f"Matching interaction contains duplicate {side} choice IDs.",
            source_id=choice_id if side == "source" else None,
            target_id=choice_id if side == "target" else None,
        )
        for choice_id in _duplicates(choice_ids)
    )


def _blank_choice_issues(
    side: _MatchingChoiceSide, choice_ids: tuple[str, ...]
) -> tuple[ExamAuthoringMatchingValidationIssue, ...]:
    reason_code = (
        ExamAuthoringMatchingValidationIssueCode.BLANK_SOURCE_ID
        if side == "source"
        else ExamAuthoringMatchingValidationIssueCode.BLANK_TARGET_ID
    )
    return tuple(
        ExamAuthoringMatchingValidationIssue(
            reason_code=reason_code,
            message=f"Matching interaction contains blank {side} choice IDs.",
        )
        for choice_id in choice_ids
        if choice_id.strip() == ""
    )


def _duplicate_pair_issues(
    pairs: tuple[ExamAuthoringMatchingPair, ...],
) -> tuple[ExamAuthoringMatchingValidationIssue, ...]:
    seen: set[tuple[str, str]] = set()
    issues: list[ExamAuthoringMatchingValidationIssue] = []
    for pair in pairs:
        key = (pair.source_id, pair.target_id)
        if key in seen:
            issues.append(
                ExamAuthoringMatchingValidationIssue(
                    reason_code=ExamAuthoringMatchingValidationIssueCode.DUPLICATE_PAIR,
                    message="Matching key contains a duplicate source-target pair.",
                    source_id=pair.source_id,
                    target_id=pair.target_id,
                )
            )
        seen.add(key)
    return tuple(issues)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(duplicates)


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _within_bounds(value: int, minimum: int, maximum: int) -> bool:
    if value < minimum:
        return False
    return maximum == 0 or value <= maximum
