"""DigiExam ingestion overlay and effective exam contracts.

Purpose:
    Define strict DTOs and value objects for source-bound teacher overlays,
    effective exam reporting, and overlay application reports.

Relationships:
    - Parsed by `domain.digiexam_ingestion_overlay`.
    - Emitted by `infrastructure.digiexam_migration_bundle_builder`.
    - Mirrors the public v2 artifact contract for DigiExam ingestion overlay.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIntermediateExam
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DigiExamEffectiveExamSchemaVersion,
    DigiExamIngestionOverlaySchemaVersion,
    DigiExamIntermediateExamSchemaVersion,
    IngestionOverlayReportSchemaVersion,
)


class DigiExamIngestionOverlayError(ValueError):
    """Typed overlay failure raised before target rendering."""

    def __init__(self, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


class DigiExamOverlaySourceBinding(BaseModel):
    """Source binding required for a trusted overlay."""

    model_config = ConfigDict(extra="forbid")

    source_file_sha256: str
    source_ir_schema_version: DigiExamIntermediateExamSchemaVersion
    source_ir_sha256: str


class DigiExamOverlayChoiceManualAnswerKey(BaseModel):
    """Manual answer key for source choice items."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice"]
    correct_alternative_ids: tuple[int, ...] = Field(min_length=1)


class DigiExamOverlayGapAnswer(BaseModel):
    """Manual accepted values for one source gap."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str = Field(min_length=1)
    accepted_values: tuple[str, ...] = Field(min_length=1)

    @field_validator("accepted_values")
    @classmethod
    def _validate_accepted_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(entry.strip() for entry in value)
        if any(entry == "" for entry in normalized):
            raise ValueError("gap accepted values must not be blank")
        return normalized


class DigiExamOverlayGapFillManualAnswerKey(BaseModel):
    """Manual answer key for source gap-fill items."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["gap_fill"]
    gap_answers: tuple[DigiExamOverlayGapAnswer, ...] = Field(min_length=1)


DigiExamOverlayManualAnswerKey = Annotated[
    DigiExamOverlayChoiceManualAnswerKey | DigiExamOverlayGapFillManualAnswerKey,
    Field(discriminator="kind"),
]


class DigiExamOverlayReviewedCompletionOutcome(StrEnum):
    """Teacher review outcomes for applying an advisory candidate."""

    ACCEPTED_UNCHANGED = "accepted_unchanged"
    TEACHER_EDITED = "teacher_edited"


class DigiExamOverlayReviewedCompletionCandidateLineage(BaseModel):
    """Bounded lineage for a reviewed advisory answer-key candidate."""

    model_config = ConfigDict(extra="forbid")

    completion_report_sha256: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1, max_length=160)
    candidate_payload_digest: str = Field(min_length=1)
    provider_profile_id: str = Field(min_length=1, max_length=160)
    schema_name: str = Field(min_length=1, max_length=160)
    schema_version: str = Field(min_length=1, max_length=160)
    prompt_template_version: str = Field(min_length=1, max_length=160)
    validation_state: Literal["valid"]


class DigiExamOverlayReviewedChoiceAnswerPayload(BaseModel):
    """Reviewed choice answer payload using reviewed choice candidate candidate semantics."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice"]
    correct_alternative_ids: tuple[int, ...] = Field(min_length=1)


class DigiExamOverlayReviewedGapFillAnswerPayload(BaseModel):
    """Reviewed gap-fill answer payload using gap-fill candidate candidate semantics."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["gap_fill"]
    gap_answers: tuple[DigiExamOverlayGapAnswer, ...] = Field(min_length=1)


DigiExamOverlayReviewedCompletionAnswerPayload = Annotated[
    DigiExamOverlayReviewedChoiceAnswerPayload | DigiExamOverlayReviewedGapFillAnswerPayload,
    Field(discriminator="kind"),
]


class DigiExamOverlayReviewedCompletionAnswerKey(BaseModel):
    """Teacher-reviewed advisory answer key applied only to effective IR."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice", "gap_fill"]
    review_decision_id: str = Field(min_length=1, max_length=120)
    review_outcome: DigiExamOverlayReviewedCompletionOutcome
    candidate_lineage: DigiExamOverlayReviewedCompletionCandidateLineage
    answer_payload: DigiExamOverlayReviewedCompletionAnswerPayload

    @model_validator(mode="after")
    def _validate_payload_kind(self) -> Self:
        if self.kind != self.answer_payload.kind:
            raise ValueError("reviewed completion kind must match answer_payload.kind")
        return self


class DigiExamOverlayVisibleTextPatch(BaseModel):
    """Shared visible item text patch fields for effective renderer input."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    prompt_html: str | None = Field(default=None, min_length=1, max_length=8000)
    prompt_lines: tuple[str, ...] | None = Field(default=None, max_length=20)

    @field_validator("title", "prompt_html")
    @classmethod
    def _validate_text_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            raise ValueError("visible text patches must not be blank")
        _reject_embedded_resources(normalized)
        return normalized

    @field_validator("prompt_lines")
    @classmethod
    def _validate_prompt_lines(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if value is None:
            return None
        normalized = tuple(line.strip() for line in value)
        if not normalized or any(line == "" for line in normalized):
            raise ValueError("prompt lines must contain non-blank entries")
        for line in normalized:
            _reject_embedded_resources(line)
        return normalized


class DigiExamOverlayChoiceAlternativeOverride(BaseModel):
    """Bounded alternative text patch for effective choice items."""

    model_config = ConfigDict(extra="forbid")

    alternative_id: int
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        normalized = value.strip()
        _reject_embedded_resources(normalized)
        return normalized


class DigiExamOverlayChoiceItemPatch(DigiExamOverlayVisibleTextPatch):
    """Bounded choice item patch applied only to the effective IR."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice"]
    alternative_overrides: tuple[DigiExamOverlayChoiceAlternativeOverride, ...] = ()

    @model_validator(mode="after")
    def _require_patch_content(self) -> Self:
        if (
            self.title is None
            and self.prompt_html is None
            and self.prompt_lines is None
            and not self.alternative_overrides
        ):
            raise ValueError("choice item patch must contain at least one visible edit")
        return self


class DigiExamOverlayGapFillItemPatch(DigiExamOverlayVisibleTextPatch):
    """Bounded gap-fill item patch applied only to the effective IR."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["gap_fill"]

    @model_validator(mode="after")
    def _require_patch_content(self) -> Self:
        if self.title is None and self.prompt_html is None and self.prompt_lines is None:
            raise ValueError("gap-fill item patch must contain at least one visible edit")
        return self


DigiExamOverlayEffectiveItemPatch = Annotated[
    DigiExamOverlayChoiceItemPatch | DigiExamOverlayGapFillItemPatch,
    Field(discriminator="kind"),
]


class DigiExamOverlayPointCorrection(BaseModel):
    """Bounded item point correction applied only to effective renderer input."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["item_points"]
    max_score: int = Field(gt=0, strict=True)


class DigiExamIngestionOverlayItem(BaseModel):
    """One source-bound overlay entry for a DigiExam item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: DigiExamItemType
    source_item_fingerprint: str = Field(min_length=1)
    effective_item_patch: DigiExamOverlayEffectiveItemPatch | None = None
    manual_answer_key: DigiExamOverlayManualAnswerKey | None = None
    reviewed_completion_answer_key: DigiExamOverlayReviewedCompletionAnswerKey | None = None
    point_correction: DigiExamOverlayPointCorrection | None = None

    @model_validator(mode="after")
    def _validate_answer_key_source(self) -> Self:
        if self.manual_answer_key is not None and self.reviewed_completion_answer_key is not None:
            raise ValueError("manual_answer_key and reviewed_completion_answer_key are exclusive")
        return self


class DigiExamIngestionOverlay(BaseModel):
    """Top-level source-bound ingestion overlay."""

    model_config = ConfigDict(extra="forbid")

    schema_version: DigiExamIngestionOverlaySchemaVersion
    source_binding: DigiExamOverlaySourceBinding
    items: tuple[DigiExamIngestionOverlayItem, ...] = Field(min_length=1)


@dataclass(frozen=True)
class DigiExamIngestionOverlayAcceptedEntry:
    """Accepted overlay fields for one source item."""

    item_id: str
    sequence: int
    applied_fields: tuple[str, ...]


@dataclass(frozen=True)
class DigiExamIngestionOverlayRejectedEntry:
    """Rejected overlay field or item with a typed reason."""

    item_id: str
    sequence: int
    reason_code: str
    message: str


@dataclass(frozen=True)
class DigiExamEffectiveAnswerKey:
    """Effective answer key surfaced without changing source IR provenance."""

    provenance: str
    correct_alternative_ids: tuple[int, ...]
    correct_gap_answers: tuple[dict[str, str], ...]
    lineage: "DigiExamEffectiveAnswerKeyLineage | None" = None


@dataclass(frozen=True)
class DigiExamEffectiveAnswerKeyLineage:
    """Bounded reviewed-completion lineage surfaced in effective IR."""

    completion_report_sha256: str
    candidate_id: str
    candidate_payload_digest: str
    provider_profile_id: str
    schema_name: str
    schema_version: str
    prompt_template_version: str
    validation_state: str
    review_decision_id: str
    review_outcome: str


class DigiExamEffectiveAnswerKeyProvenance(StrEnum):
    """Effective answer-key provenance states separate from parser evidence."""

    REVIEWED = "reviewed"
    TEACHER_PROVIDED = "teacher_provided"


@dataclass(frozen=True)
class DigiExamEffectiveItemPatchSummary:
    """Item-content patch summary surfaced without exposing raw overlay JSON."""

    changed_fields: tuple[str, ...]
    patched_alternative_ids: tuple[int, ...]
    patched_gap_ids: tuple[str, ...]


@dataclass(frozen=True)
class DigiExamEffectivePointCorrection:
    """Applied item point correction surfaced for producer-state projection."""

    kind: str
    source_max_score: int | None
    effective_max_score: int
    source_item_fingerprint: str


@dataclass(frozen=True)
class DigiExamEffectiveItem:
    """One effective item summary for the current effective-exam schema."""

    item_id: str
    sequence: int
    item_type: str
    source_item_fingerprint: str
    effective_answer_key: DigiExamEffectiveAnswerKey | None
    effective_item_patch: DigiExamEffectiveItemPatchSummary | None
    effective_point_correction: DigiExamEffectivePointCorrection | None
    applied_overlay_entry_ids: tuple[str, ...]


@dataclass(frozen=True)
class DigiExamEffectiveExam:
    """Effective exam artifact payload consumed by review consumers."""

    schema_version: DigiExamEffectiveExamSchemaVersion
    source_file_sha256: str
    source_ir_schema_version: DigiExamIntermediateExamSchemaVersion
    source_ir_sha256: str
    ingestion_overlay_sha256: str | None
    answer_key_completion_report_sha256: str | None
    items: tuple[DigiExamEffectiveItem, ...]


@dataclass(frozen=True)
class DigiExamIngestionOverlayReport:
    """Overlay application report that excludes raw overlay JSON."""

    schema_version: IngestionOverlayReportSchemaVersion
    overlay_sha256: str
    source_ir_sha256: str
    accepted_entries: tuple[DigiExamIngestionOverlayAcceptedEntry, ...]
    rejected_entries: tuple[DigiExamIngestionOverlayRejectedEntry, ...]


@dataclass(frozen=True)
class DigiExamOverlayApplicationResult:
    """Effective renderer state and reports after overlay processing."""

    effective_exam_for_rendering: DigiExamIntermediateExam
    effective_exam_report: DigiExamEffectiveExam
    ingestion_overlay_report: DigiExamIngestionOverlayReport
    renderer_input_changed: bool


def _reject_embedded_resources(value: str) -> None:
    lowered = value.lower()
    forbidden_fragments = ("base64,", "data:", "<script", "<iframe", "src=", "href=")
    if any(fragment in lowered for fragment in forbidden_fragments):
        raise ValueError("visible text patches must not carry embedded resources")
