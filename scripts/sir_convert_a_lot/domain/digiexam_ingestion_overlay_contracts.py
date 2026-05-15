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
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIntermediateExam
from scripts.sir_convert_a_lot.domain.specs_v2 import ExamMigrationTargetV2

DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION: Literal["digiexam_ingestion_overlay_v1"] = (
    "digiexam_ingestion_overlay_v1"
)
DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION: Literal["digiexam_effective_exam_v1"] = (
    "digiexam_effective_exam_v1"
)
INGESTION_OVERLAY_REPORT_SCHEMA_VERSION: Literal["ingestion_overlay_report_v1"] = (
    "ingestion_overlay_report_v1"
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
    source_ir_schema_version: Literal["digiexam_intermediate_exam_v2"]
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


class DigiExamOverlayMatchingPair(BaseModel):
    """Contract-level matching pair kept unsupported until exact IR fields exist."""

    model_config = ConfigDict(extra="forbid")

    left_id: str = Field(min_length=1)
    right_id: str = Field(min_length=1)


class DigiExamOverlayMatchingManualAnswerKey(BaseModel):
    """Manual matching answer key accepted at DTO level but not applied yet."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["matching"]
    matching_pairs: tuple[DigiExamOverlayMatchingPair, ...] = Field(min_length=1)


DigiExamOverlayManualAnswerKey = Annotated[
    DigiExamOverlayChoiceManualAnswerKey
    | DigiExamOverlayGapFillManualAnswerKey
    | DigiExamOverlayMatchingManualAnswerKey,
    Field(discriminator="kind"),
]


class DigiExamOverlayChoiceAlternativeOverride(BaseModel):
    """Bounded alternative text patch parsed but not applied in Task 295."""

    model_config = ConfigDict(extra="forbid")

    alternative_id: int
    text: str = Field(min_length=1, max_length=500)


class DigiExamOverlayChoiceItemPatch(BaseModel):
    """Bounded choice item patch parsed but not applied in Task 295."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice"]
    alternative_overrides: tuple[DigiExamOverlayChoiceAlternativeOverride, ...] = ()


DigiExamOverlayEffectiveItemPatch = Annotated[
    DigiExamOverlayChoiceItemPatch,
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

    schema_version: Literal["digiexam_ingestion_overlay_v1"]
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
class DigiExamEffectiveItem:
    """One effective item summary for `digiexam_effective_exam_v1`."""

    item_id: str
    sequence: int
    item_type: str
    source_item_fingerprint: str
    effective_answer_key: DigiExamEffectiveAnswerKey | None
    applied_overlay_entry_ids: tuple[str, ...]
    review_decisions: tuple[DigiExamEffectiveReviewDecision, ...]


@dataclass(frozen=True)
class DigiExamEffectiveExam:
    """Effective exam artifact payload consumed by review consumers."""

    schema_version: Literal["digiexam_effective_exam_v1"]
    source_file_sha256: str
    source_ir_schema_version: Literal["digiexam_intermediate_exam_v2"]
    source_ir_sha256: str
    ingestion_overlay_sha256: str | None
    answer_key_completion_report_sha256: str | None
    items: tuple[DigiExamEffectiveItem, ...]


@dataclass(frozen=True)
class DigiExamIngestionOverlayReport:
    """Overlay application report that excludes raw overlay JSON."""

    schema_version: Literal["ingestion_overlay_report_v1"]
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
