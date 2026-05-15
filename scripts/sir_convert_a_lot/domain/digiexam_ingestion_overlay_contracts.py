"""DigiExam ingestion overlay and effective exam contracts.

Purpose:
    Define strict DTOs and value objects for source-bound teacher overlays,
    effective exam reporting, and overlay application reports.

Relationships:
    - Parsed by `domain.digiexam_ingestion_overlay`.
    - Emitted by `infrastructure.digiexam_migration_bundle_builder`.
    - Mirrors the public v2 artifact contract for Task 295.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from scripts.sir_convert_a_lot.domain.specs_v2 import ExamMigrationTargetV2


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


class DigiExamOverlayReviewDecision(BaseModel):
    """Teacher review decision that never creates answer-key evidence."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["accept_current_state_for_export"]
    decision_id: str = Field(min_length=1, max_length=120)
    accepted_targets: tuple[ExamMigrationTargetV2, ...] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=500)


class DigiExamIngestionOverlayItem(BaseModel):
    """One source-bound overlay entry for a DigiExam item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: DigiExamItemType
    source_item_fingerprint: str = Field(min_length=1)
    effective_item_patch: DigiExamOverlayEffectiveItemPatch | None = None
    manual_answer_key: DigiExamOverlayManualAnswerKey | None = None
    review_decision: DigiExamOverlayReviewDecision | None = None


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
class DigiExamEffectiveReviewDecision:
    """Applied review decision surfaced in effective item reporting."""

    kind: str
    decision_id: str
    accepted_targets: tuple[str, ...]
    note: str | None


@dataclass(frozen=True)
class DigiExamEffectiveAnswerKey:
    """Effective answer key surfaced without changing source IR provenance."""

    provenance: str
    correct_alternative_ids: tuple[int, ...]
    correct_gap_answers: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class DigiExamEffectiveItemPatchSummary:
    """Item-content patch summary surfaced without exposing raw overlay JSON."""

    changed_fields: tuple[str, ...]
    patched_alternative_ids: tuple[int, ...]
    patched_gap_ids: tuple[str, ...]


@dataclass(frozen=True)
class DigiExamEffectiveItem:
    """One effective item summary for the current effective-exam schema."""

    item_id: str
    sequence: int
    item_type: str
    source_item_fingerprint: str
    effective_answer_key: DigiExamEffectiveAnswerKey | None
    effective_item_patch: DigiExamEffectiveItemPatchSummary | None
    applied_overlay_entry_ids: tuple[str, ...]
    review_decisions: tuple[DigiExamEffectiveReviewDecision, ...]


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
    accepted_review_decisions: tuple[tuple[str, ExamMigrationTargetV2], ...]


def _reject_embedded_resources(value: str) -> None:
    lowered = value.lower()
    forbidden_fragments = ("base64,", "data:", "<script", "<iframe", "src=", "href=")
    if any(fragment in lowered for fragment in forbidden_fragments):
        raise ValueError("visible text patches must not carry embedded resources")
