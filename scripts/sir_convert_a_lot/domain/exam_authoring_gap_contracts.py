"""Source-neutral gap and open-cloze authoring contracts.

Purpose:
    Define reusable gap/open-cloze value objects and validators for
    ExamAuthoringIR v1 without depending on DigiExam parser DTOs or target
    exporter syntax.

Relationships:
    - Complements `domain.exam_authoring_ir_contracts`, which currently owns
      shared authoring provenance and matching interactions.
    - Consumed by source adapters such as `domain.digiexam_exam_authoring_adapter`.
    - Feeds target-profile validation before Exam.net PDF, QTI, or future
      authoring exporters claim automatic evaluation.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum

from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringSourceEvidence,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)


class ExamAuthoringGapNormalizationProfile(StrEnum):
    """Normalization profiles used for validation and target decisions."""

    EXACT_TRIM_CASE_SENSITIVE = "exact_trim_case_sensitive"
    TRIM_CASE_INSENSITIVE = "trim_case_insensitive"
    TRIM_CASE_PUNCTUATION_INSENSITIVE = "trim_case_punctuation_insensitive"


class ExamAuthoringGapPromptBindingKind(StrEnum):
    """Prompt/body binding kinds that stay source-neutral."""

    HTML_ATTRIBUTE = "html_attribute"
    SOURCE_LOCATOR = "source_locator"


class ExamAuthoringGapValidationIssueCode(StrEnum):
    """Stable validation issue codes for gap/open-cloze contracts."""

    DUPLICATE_GAP_ID = "duplicate_gap_open_cloze_gap_id"
    BLANK_GAP_ID = "blank_gap_open_cloze_gap_id"
    INVALID_DISPLAY_ORDER = "invalid_gap_open_cloze_display_order"
    DUPLICATE_DISPLAY_ORDER = "duplicate_gap_open_cloze_display_order"
    BLANK_PROMPT_BINDING = "blank_gap_open_cloze_prompt_binding"
    UNKNOWN_GAP_ID = "unknown_gap_open_cloze_gap_id"
    BLANK_ACCEPTED_VALUE = "blank_gap_open_cloze_accepted_value"
    DUPLICATE_NORMALIZED_ACCEPTED_VALUE = "duplicate_gap_open_cloze_normalized_accepted_value"
    MISSING_REQUIRED_ACCEPTED_VALUE = "missing_required_gap_open_cloze_accepted_value"
    ACCEPTED_VALUE_WITHOUT_PROVENANCE = "accepted_gap_open_cloze_value_without_provenance"
    ACCEPTED_VALUE_PROVENANCE_EVIDENCE_MISMATCH = (
        "accepted_gap_open_cloze_value_provenance_evidence_mismatch"
    )
    EXAMNET_PDF_NATIVE_GAP_SUPPORT_UNPROVEN = "examnet_pdf_gap_open_cloze_native_support_unproven"
    EXAMNET_PDF_MULTI_GAP_NOT_SUPPORTED = "examnet_pdf_multi_gap_open_cloze_not_supported"


@dataclass(frozen=True)
class ExamAuthoringGapPromptBinding:
    """One prompt/body locator for a gap placeholder."""

    kind: ExamAuthoringGapPromptBindingKind
    locator: str


@dataclass(frozen=True)
class ExamAuthoringGap:
    """One ordered source-neutral gap/open-cloze placeholder."""

    gap_id: str
    display_order: int
    prompt_binding: ExamAuthoringGapPromptBinding
    required_for_auto_evaluation: bool
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = ()


@dataclass(frozen=True)
class ExamAuthoringGapAcceptedValue:
    """One accepted value bound to a stable gap ID."""

    gap_id: str
    value: str
    provenance: ExamAuthoringAnswerKeyProvenance
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = ()


@dataclass(frozen=True)
class ExamAuthoringGapAnswerKey:
    """Gap/open-cloze answer key with derived source-neutral provenance."""

    accepted_values: tuple[ExamAuthoringGapAcceptedValue, ...]
    provenance: ExamAuthoringAnswerKeyProvenance = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provenance",
            summarize_exam_authoring_gap_answer_key_provenance(self.accepted_values),
        )


@dataclass(frozen=True)
class ExamAuthoringGapOpenClozeInteraction:
    """Source-neutral gap/open-cloze interaction contract."""

    schema_version: ExamAuthoringIrSchemaVersion
    interaction_id: str
    gaps: tuple[ExamAuthoringGap, ...]
    normalization_profile: ExamAuthoringGapNormalizationProfile
    answer_key: ExamAuthoringGapAnswerKey
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = ()


@dataclass(frozen=True)
class ExamAuthoringGapValidationIssue:
    """One validation issue with explicit contract/evaluation/export impact."""

    reason_code: ExamAuthoringGapValidationIssueCode
    message: str
    gap_id: str | None = None
    normalized_value: str | None = None
    blocks_contract: bool = True
    blocks_auto_evaluation: bool = True
    blocks_target_export: bool = False


@dataclass(frozen=True)
class ExamAuthoringGapValidationResult:
    """Validation result for a gap/open-cloze interaction or target profile."""

    valid: bool
    automatic_evaluation_ready: bool
    target_export_ready: bool
    issues: tuple[ExamAuthoringGapValidationIssue, ...]


def build_exam_authoring_gap_open_cloze_interaction(
    *,
    interaction_id: str,
    gaps: tuple[ExamAuthoringGap, ...],
    normalization_profile: ExamAuthoringGapNormalizationProfile,
    answer_key: ExamAuthoringGapAnswerKey,
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = (),
) -> ExamAuthoringGapOpenClozeInteraction:
    """Build a versioned source-neutral gap/open-cloze interaction."""

    return ExamAuthoringGapOpenClozeInteraction(
        schema_version=EXAM_AUTHORING_IR_SCHEMA_VERSION,
        interaction_id=interaction_id,
        gaps=gaps,
        normalization_profile=normalization_profile,
        answer_key=answer_key,
        evidence=evidence,
    )


def validate_exam_authoring_gap_open_cloze_interaction(
    interaction: ExamAuthoringGapOpenClozeInteraction,
) -> ExamAuthoringGapValidationResult:
    """Validate source-neutral gap structure and auto-evaluation readiness."""

    issues: list[ExamAuthoringGapValidationIssue] = []
    gap_ids = tuple(gap.gap_id for gap in interaction.gaps)
    display_orders = tuple(gap.display_order for gap in interaction.gaps)
    issues.extend(_gap_identity_issues(gap_ids))
    issues.extend(_display_order_issues(display_orders))
    issues.extend(_prompt_binding_issues(interaction.gaps))
    issues.extend(_accepted_value_issues(interaction))
    issues.extend(_missing_required_value_issues(interaction, gap_ids))
    return _validation_result(issues)


def validate_examnet_pdf_gap_open_cloze_profile(
    interaction: ExamAuthoringGapOpenClozeInteraction,
) -> ExamAuthoringGapValidationResult:
    """Validate current Exam.net PDF gap/open-cloze target constraints."""

    issues = list(validate_exam_authoring_gap_open_cloze_interaction(interaction).issues)
    issues.append(
        ExamAuthoringGapValidationIssue(
            reason_code=(
                ExamAuthoringGapValidationIssueCode.EXAMNET_PDF_NATIVE_GAP_SUPPORT_UNPROVEN
            ),
            message=(
                "Exam.net PDF may preserve gap intent only through governed degraded "
                "or manual target shapes until native gap import/export proof exists."
            ),
            blocks_contract=False,
            blocks_auto_evaluation=False,
            blocks_target_export=False,
        )
    )
    if len(interaction.gaps) != 1:
        issues.append(
            ExamAuthoringGapValidationIssue(
                reason_code=ExamAuthoringGapValidationIssueCode.EXAMNET_PDF_MULTI_GAP_NOT_SUPPORTED,
                message=(
                    "The current Exam.net PDF converter profile does not support "
                    "native multi-gap/open-cloze export."
                ),
                blocks_contract=False,
                blocks_auto_evaluation=False,
                blocks_target_export=True,
            )
        )
    return _validation_result(issues)


def summarize_exam_authoring_gap_answer_key_provenance(
    accepted_values: tuple[ExamAuthoringGapAcceptedValue, ...],
) -> ExamAuthoringAnswerKeyProvenance:
    """Return the aggregate answer-key provenance derived from values."""

    value_provenance = {accepted_value.provenance for accepted_value in accepted_values}
    if not value_provenance:
        return ExamAuthoringAnswerKeyProvenance.ABSENT
    if len(value_provenance) == 1:
        return next(iter(value_provenance))
    return ExamAuthoringAnswerKeyProvenance.MIXED


def normalize_exam_authoring_gap_value(
    value: str, profile: ExamAuthoringGapNormalizationProfile
) -> str:
    """Normalize one accepted value according to the interaction profile."""

    normalized = _normalize_whitespace(value)
    if profile in {
        ExamAuthoringGapNormalizationProfile.TRIM_CASE_INSENSITIVE,
        ExamAuthoringGapNormalizationProfile.TRIM_CASE_PUNCTUATION_INSENSITIVE,
    }:
        normalized = normalized.casefold()
    if profile == ExamAuthoringGapNormalizationProfile.TRIM_CASE_PUNCTUATION_INSENSITIVE:
        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.category(character).startswith("P")
        )
        normalized = _normalize_whitespace(normalized)
    return normalized


def _gap_identity_issues(gap_ids: tuple[str, ...]) -> tuple[ExamAuthoringGapValidationIssue, ...]:
    issues: list[ExamAuthoringGapValidationIssue] = []
    seen: set[str] = set()
    duplicates: set[str] = set()
    for gap_id in gap_ids:
        if gap_id.strip() == "":
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=ExamAuthoringGapValidationIssueCode.BLANK_GAP_ID,
                    message="Gap/open-cloze interaction contains a blank gap ID.",
                    gap_id=gap_id,
                )
            )
        if gap_id in seen:
            duplicates.add(gap_id)
        seen.add(gap_id)
    issues.extend(
        ExamAuthoringGapValidationIssue(
            reason_code=ExamAuthoringGapValidationIssueCode.DUPLICATE_GAP_ID,
            message="Gap/open-cloze interaction contains duplicate gap IDs.",
            gap_id=gap_id,
        )
        for gap_id in sorted(duplicates)
    )
    return tuple(issues)


def _display_order_issues(
    display_orders: tuple[int, ...],
) -> tuple[ExamAuthoringGapValidationIssue, ...]:
    issues: list[ExamAuthoringGapValidationIssue] = []
    seen: set[int] = set()
    duplicates: set[int] = set()
    for order in display_orders:
        if order < 1:
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=ExamAuthoringGapValidationIssueCode.INVALID_DISPLAY_ORDER,
                    message="Gap/open-cloze display order must be one-based.",
                )
            )
        if order in seen:
            duplicates.add(order)
        seen.add(order)
    issues.extend(
        ExamAuthoringGapValidationIssue(
            reason_code=ExamAuthoringGapValidationIssueCode.DUPLICATE_DISPLAY_ORDER,
            message="Gap/open-cloze interaction contains duplicate display orders.",
        )
        for _order in sorted(duplicates)
    )
    return tuple(issues)


def _prompt_binding_issues(
    gaps: tuple[ExamAuthoringGap, ...],
) -> tuple[ExamAuthoringGapValidationIssue, ...]:
    return tuple(
        ExamAuthoringGapValidationIssue(
            reason_code=ExamAuthoringGapValidationIssueCode.BLANK_PROMPT_BINDING,
            message="Gap/open-cloze prompt binding locator must not be blank.",
            gap_id=gap.gap_id,
        )
        for gap in gaps
        if gap.prompt_binding.locator.strip() == ""
    )


def _accepted_value_issues(
    interaction: ExamAuthoringGapOpenClozeInteraction,
) -> tuple[ExamAuthoringGapValidationIssue, ...]:
    issues: list[ExamAuthoringGapValidationIssue] = []
    known_gap_ids = frozenset(gap.gap_id for gap in interaction.gaps)
    normalized_by_gap: dict[str, set[str]] = {}
    for accepted_value in interaction.answer_key.accepted_values:
        normalized = normalize_exam_authoring_gap_value(
            accepted_value.value, interaction.normalization_profile
        )
        if accepted_value.gap_id not in known_gap_ids:
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=ExamAuthoringGapValidationIssueCode.UNKNOWN_GAP_ID,
                    message="Accepted value references an unknown gap ID.",
                    gap_id=accepted_value.gap_id,
                    normalized_value=normalized,
                )
            )
        if normalized == "":
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=ExamAuthoringGapValidationIssueCode.BLANK_ACCEPTED_VALUE,
                    message="Accepted value must not be blank after normalization.",
                    gap_id=accepted_value.gap_id,
                    normalized_value=normalized,
                )
            )
            continue
        if accepted_value.provenance == ExamAuthoringAnswerKeyProvenance.ABSENT:
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=ExamAuthoringGapValidationIssueCode.ACCEPTED_VALUE_WITHOUT_PROVENANCE,
                    message="Accepted value requires typed non-absent provenance.",
                    gap_id=accepted_value.gap_id,
                    normalized_value=normalized,
                )
            )
        issues.extend(_accepted_value_evidence_issues(accepted_value, normalized))
        seen_values = normalized_by_gap.setdefault(accepted_value.gap_id, set())
        if normalized in seen_values:
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=(
                        ExamAuthoringGapValidationIssueCode.DUPLICATE_NORMALIZED_ACCEPTED_VALUE
                    ),
                    message="Accepted values for a gap duplicate after normalization.",
                    gap_id=accepted_value.gap_id,
                    normalized_value=normalized,
                )
            )
        seen_values.add(normalized)
    return tuple(issues)


def _accepted_value_evidence_issues(
    accepted_value: ExamAuthoringGapAcceptedValue, normalized: str
) -> tuple[ExamAuthoringGapValidationIssue, ...]:
    issues: list[ExamAuthoringGapValidationIssue] = []
    for evidence in accepted_value.evidence:
        evidence_provenance = _known_evidence_provenance(evidence.source_family)
        if evidence_provenance is not None and evidence_provenance != accepted_value.provenance:
            issues.append(
                ExamAuthoringGapValidationIssue(
                    reason_code=(
                        ExamAuthoringGapValidationIssueCode.ACCEPTED_VALUE_PROVENANCE_EVIDENCE_MISMATCH
                    ),
                    message="Accepted value provenance contradicts known evidence origin.",
                    gap_id=accepted_value.gap_id,
                    normalized_value=normalized,
                )
            )
    return tuple(issues)


def _known_evidence_provenance(
    source_family: str,
) -> ExamAuthoringAnswerKeyProvenance | None:
    if source_family in {"digiexam_dxe", "digiexam_result_pdf_correct_labels"}:
        return ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED
    if source_family == "teacher_overlay":
        return ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED
    if source_family == "reviewed_completion":
        return ExamAuthoringAnswerKeyProvenance.REVIEWED
    return None


def _missing_required_value_issues(
    interaction: ExamAuthoringGapOpenClozeInteraction,
    gap_ids: tuple[str, ...],
) -> tuple[ExamAuthoringGapValidationIssue, ...]:
    accepted_gap_ids = frozenset(
        accepted_value.gap_id
        for accepted_value in interaction.answer_key.accepted_values
        if accepted_value.gap_id in gap_ids
        and accepted_value.provenance != ExamAuthoringAnswerKeyProvenance.ABSENT
        and normalize_exam_authoring_gap_value(
            accepted_value.value, interaction.normalization_profile
        )
        != ""
    )
    return tuple(
        ExamAuthoringGapValidationIssue(
            reason_code=ExamAuthoringGapValidationIssueCode.MISSING_REQUIRED_ACCEPTED_VALUE,
            message="Required gap has no trusted accepted value for automatic evaluation.",
            gap_id=gap.gap_id,
            blocks_contract=False,
            blocks_auto_evaluation=True,
        )
        for gap in interaction.gaps
        if gap.required_for_auto_evaluation and gap.gap_id not in accepted_gap_ids
    )


def _validation_result(
    issues: list[ExamAuthoringGapValidationIssue],
) -> ExamAuthoringGapValidationResult:
    valid = not any(issue.blocks_contract for issue in issues)
    automatic_evaluation_ready = valid and not any(issue.blocks_auto_evaluation for issue in issues)
    target_export_ready = valid and not any(issue.blocks_target_export for issue in issues)
    return ExamAuthoringGapValidationResult(
        valid=valid,
        automatic_evaluation_ready=automatic_evaluation_ready,
        target_export_ready=target_export_ready,
        issues=tuple(issues),
    )


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().split())
