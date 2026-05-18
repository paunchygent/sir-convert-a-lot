"""Source-neutral exam authoring correction application contracts.

Purpose:
    Define the runtime request, response, and first correction application
    boundary for the unified exam-authoring correction apply route.

Relationships:
    - Implements the accepted ADR-0011 route contract for service API v2.
    - Reuses `domain.exam_authoring_matching_manual_answer_key` and
      `domain.exam_authoring_ir_contracts` for matching-key validation.
    - Exposed by `interfaces.http_routes_exam_authoring_corrections_v2` and
      published through the generated OpenAPI snapshot for downstream consumers.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringMatchingAnswerKey,
    ExamAuthoringMatchingChoice,
    ExamAuthoringMatchingInteraction,
    ExamAuthoringMatchingPair,
    ExamAuthoringSourceEvidence,
    validate_examnet_pdf_matching_profile,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_matching_manual_answer_key import (
    ExamAuthoringMatchingManualAnswerKey,
    ExamAuthoringMatchingManualAnswerKeyError,
    apply_exam_authoring_matching_manual_answer_key,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
    ExamAuthoringIrSchemaVersion,
)

ExamAuthoringCorrectionTargetV1 = Literal["examnet_pdf", "qti_package"]
ExamAuthoringCorrectionReadinessV1 = Literal[
    "ready",
    "target_validation_failed",
    "unsupported_target_shape",
]
ExamAuthoringCorrectionArtifactAvailabilityV1 = Literal["available", "unavailable"]
ExamAuthoringAnswerKeySubmissionOriginV1 = Literal[
    "teacher_authored",
    "accepted_advisory_candidate",
    "teacher_edited_advisory_candidate",
]


class ExamAuthoringCorrectionsApplyError(ValueError):
    """Typed failure raised before a correction batch can affect state."""

    def __init__(self, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


class ExamAuthoringCorrectionSourceBindingV1(BaseModel):
    """Request-level binding to the producer-returned authoring state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_authoring_schema_version: ExamAuthoringIrSchemaVersion
    source_state_sha256: str = Field(min_length=1)
    source_bundle_id: str | None = Field(default=None, min_length=1)
    source_file_sha256: str | None = Field(default=None, min_length=1)


class ExamAuthoringSourceEvidenceV1(BaseModel):
    """Source-neutral evidence reference for an authoring interaction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_family: str = Field(min_length=1)
    source_id: str | None = Field(default=None, min_length=1)
    locator: str | None = Field(default=None, min_length=1)


class ExamAuthoringMatchingChoiceV1(BaseModel):
    """One ordered source or target choice in a matching interaction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    choice_id: str = Field(min_length=1)
    order: int
    text: str = Field(min_length=1)
    match_min: int
    match_max: int


class ExamAuthoringMatchingPairV1(BaseModel):
    """One directed source-to-target matching pair."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)


class ExamAuthoringMatchingAnswerKeyV1(BaseModel):
    """Source-neutral matching answer key for effective authoring state."""

    model_config = ConfigDict(extra="forbid")

    provenance: Literal["absent", "source_provided", "teacher_provided", "reviewed", "mixed"]
    pairs: tuple[ExamAuthoringMatchingPairV1, ...] = ()


class ExamAuthoringMatchingInteractionV1(BaseModel):
    """Source-neutral matching interaction carried by a producer state surface."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: ExamAuthoringIrSchemaVersion = EXAM_AUTHORING_IR_SCHEMA_VERSION
    interaction_id: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)
    source_choices: tuple[ExamAuthoringMatchingChoiceV1, ...]
    target_choices: tuple[ExamAuthoringMatchingChoiceV1, ...]
    min_associations: int
    max_associations: int
    answer_key: ExamAuthoringMatchingAnswerKeyV1
    evidence: tuple[ExamAuthoringSourceEvidenceV1, ...] = ()


class ExamAuthoringCorrectionSourceItemV1(BaseModel):
    """One producer-returned source item used for correction binding."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)
    matching_interactions: tuple[ExamAuthoringMatchingInteractionV1, ...] = ()


class ExamAuthoringCorrectionSourceStateV1(BaseModel):
    """Sanitized producer-returned state used for correction validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["exam_authoring_correction_source_state_v1"] = (
        "exam_authoring_correction_source_state_v1"
    )
    source_authoring_schema_version: ExamAuthoringIrSchemaVersion
    source_state_sha256: str = Field(min_length=1)
    items: tuple[ExamAuthoringCorrectionSourceItemV1, ...]


class ExamAuthoringCandidateLineageV1(BaseModel):
    """Bounded advisory-candidate lineage without raw provider data."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    completion_report_sha256: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    candidate_payload_digest: str = Field(min_length=1)
    provider_profile_id: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    prompt_template_version: str = Field(min_length=1)
    validation_state: Literal["valid"]


class ExamAuthoringCorrectionEntryBaseV1(BaseModel):
    """Common binding fields for every correction entry."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(min_length=1)
    entry_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str | None = Field(default=None, min_length=1)


class ExamAuthoringItemTextPatchOperationV1(BaseModel):
    """One visible text patch operation for future source-neutral correction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field: Literal[
        "item_title",
        "stem_html",
        "prompt_html",
        "body_html",
        "visible_option_text",
        "gap_prompt_text",
    ]
    value: str = Field(min_length=1)
    choice_id: str | None = Field(default=None, min_length=1)
    gap_id: str | None = Field(default=None, min_length=1)


class ExamAuthoringItemTextPatchCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Visible item text patch entry reserved for a later implementation slice."""

    kind: Literal["item_text_patch"]
    patches: tuple[ExamAuthoringItemTextPatchOperationV1, ...] = Field(min_length=1)


class ExamAuthoringPointCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Point correction entry reserved for unified runtime migration."""

    kind: Literal["point_correction"]
    max_score: int = Field(gt=0)


class ExamAuthoringManualChoiceAnswerKeyCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Manual choice answer-key entry reserved for unified runtime migration."""

    kind: Literal["manual_choice_answer_key"]
    interaction_id: str = Field(min_length=1)
    submission_origin: ExamAuthoringAnswerKeySubmissionOriginV1
    correct_choice_ids: tuple[str, ...] = Field(min_length=1)
    candidate_lineage: ExamAuthoringCandidateLineageV1 | None = None


class ExamAuthoringGapAnswerV1(BaseModel):
    """Accepted values for one source-bound gap."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    gap_id: str = Field(min_length=1)
    accepted_values: tuple[str, ...] = Field(min_length=1)


class ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Manual gap/open-cloze answer-key entry reserved for unified migration."""

    kind: Literal["manual_gap_open_cloze_answer_key"]
    interaction_id: str = Field(min_length=1)
    submission_origin: ExamAuthoringAnswerKeySubmissionOriginV1
    gap_answers: tuple[ExamAuthoringGapAnswerV1, ...] = Field(min_length=1)
    candidate_lineage: ExamAuthoringCandidateLineageV1 | None = None


class ExamAuthoringManualMatchingAnswerKeyCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Manual matching answer-key correction implemented by this hard cut."""

    kind: Literal["manual_matching_answer_key"]
    item_type: Literal["matching"]
    interaction_id: str = Field(min_length=1)
    submission_origin: ExamAuthoringAnswerKeySubmissionOriginV1
    pairs: tuple[ExamAuthoringMatchingPairV1, ...] = Field(min_length=1)
    candidate_lineage: ExamAuthoringCandidateLineageV1 | None = None

    @model_validator(mode="after")
    def _validate_candidate_lineage(self) -> "ExamAuthoringManualMatchingAnswerKeyCorrectionV1":
        if self.submission_origin != "teacher_authored" and self.candidate_lineage is None:
            raise ValueError("advisory-origin matching corrections require candidate lineage")
        return self


class ExamAuthoringReviewDecisionCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Review decision entry reserved for unified runtime migration."""

    kind: Literal["review_decision"]
    decision: Literal["accept_current_state_for_export"]
    decision_id: str = Field(min_length=1)
    accepted_targets: tuple[ExamAuthoringCorrectionTargetV1, ...] = Field(min_length=1)
    note: str | None = Field(default=None, min_length=1)


class ExamAuthoringCandidateSuppressionCorrectionV1(ExamAuthoringCorrectionEntryBaseV1):
    """Candidate suppression entry reserved for unified runtime migration."""

    kind: Literal["candidate_suppression"]
    candidate_lineage: ExamAuthoringCandidateLineageV1
    suppression_reason: Literal["teacher_rejected_candidate"]


ExamAuthoringCorrectionEntryV1: TypeAlias = Annotated[
    ExamAuthoringItemTextPatchCorrectionV1
    | ExamAuthoringPointCorrectionV1
    | ExamAuthoringManualChoiceAnswerKeyCorrectionV1
    | ExamAuthoringManualGapOpenClozeAnswerKeyCorrectionV1
    | ExamAuthoringManualMatchingAnswerKeyCorrectionV1
    | ExamAuthoringReviewDecisionCorrectionV1
    | ExamAuthoringCandidateSuppressionCorrectionV1,
    Field(discriminator="kind"),
]


class ExamAuthoringCorrectionsApplyRequestV1(BaseModel):
    """Request body for applying a source-neutral correction batch."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_corrections_apply_request_v1"] = (
        "exam_authoring_corrections_apply_request_v1"
    )
    request_id: str = Field(min_length=1)
    source_binding: ExamAuthoringCorrectionSourceBindingV1
    source_authoring_state: ExamAuthoringCorrectionSourceStateV1
    corrections: tuple[ExamAuthoringCorrectionEntryV1, ...] = Field(min_length=1)
    requested_targets: tuple[ExamAuthoringCorrectionTargetV1, ...] = (
        "examnet_pdf",
        "qti_package",
    )


class ExamAuthoringEffectiveStateV1(BaseModel):
    """Effective authoring state projection after accepted corrections."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_effective_state_v1"] = (
        "exam_authoring_effective_state_v1"
    )
    effective_state_sha256: str = Field(min_length=1)
    items: tuple[ExamAuthoringCorrectionSourceItemV1, ...]


class ExamAuthoringCorrectionAcceptedEntryV1(BaseModel):
    """Accepted correction summary without raw submitted payloads."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entry_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    applied_fields: tuple[str, ...]
    effective_provenance: str | None = None


class ExamAuthoringCorrectionRejectedEntryV1(BaseModel):
    """Rejected correction summary without raw submitted payloads."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entry_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    reason_code: str = Field(min_length=1)
    message_key: str = Field(min_length=1)
    teacher_action: str = Field(min_length=1)
    retryable: bool


class ExamAuthoringCorrectionReportV1(BaseModel):
    """Accepted and rejected correction report for consumers."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_correction_report_v1"] = (
        "exam_authoring_correction_report_v1"
    )
    accepted_entries: tuple[ExamAuthoringCorrectionAcceptedEntryV1, ...]
    rejected_entries: tuple[ExamAuthoringCorrectionRejectedEntryV1, ...]


class ExamAuthoringCorrectionTargetReadinessRowV1(BaseModel):
    """Target readiness projection for corrected authoring state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target: ExamAuthoringCorrectionTargetV1
    readiness: ExamAuthoringCorrectionReadinessV1
    export_enabled: bool
    reason_code: str = Field(min_length=1)
    message_key: str = Field(min_length=1)
    item_id: str | None = Field(default=None, min_length=1)
    sequence: int | None = Field(default=None, ge=1)


class ExamAuthoringCorrectionTargetReadinessReportV1(BaseModel):
    """Source-neutral target readiness report for a correction batch."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["target_readiness_report_v1"] = "target_readiness_report_v1"
    targets: tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]


class ExamAuthoringCorrectionArtifactAvailabilityRowV1(BaseModel):
    """Artifact availability projection for corrected authoring state."""

    model_config = ConfigDict(extra="forbid")

    artifact_key: ExamAuthoringCorrectionTargetV1
    availability: ExamAuthoringCorrectionArtifactAvailabilityV1
    unavailable_code: str | None = None


class ExamAuthoringCorrectionsApplyResultV1(BaseModel):
    """Producer-owned result returned after correction application."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["exam_authoring_corrections_apply_result_v1"] = (
        "exam_authoring_corrections_apply_result_v1"
    )
    request_id: str = Field(min_length=1)
    source_binding: ExamAuthoringCorrectionSourceBindingV1
    effective_state: ExamAuthoringEffectiveStateV1
    correction_report: ExamAuthoringCorrectionReportV1
    target_readiness: ExamAuthoringCorrectionTargetReadinessReportV1
    artifact_availability: tuple[ExamAuthoringCorrectionArtifactAvailabilityRowV1, ...]


def apply_exam_authoring_corrections_request(
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
) -> ExamAuthoringCorrectionsApplyResultV1:
    """Apply a correction batch and return producer-owned effective state."""

    _validate_request_binding(request_body)
    effective_items = list(request_body.source_authoring_state.items)
    accepted_entries: list[ExamAuthoringCorrectionAcceptedEntryV1] = []
    rejected_entries: list[ExamAuthoringCorrectionRejectedEntryV1] = []
    readiness_rows: list[ExamAuthoringCorrectionTargetReadinessRowV1] = []

    for correction in request_body.corrections:
        if isinstance(correction, ExamAuthoringManualMatchingAnswerKeyCorrectionV1):
            item_index, item = _bound_item(correction, effective_items)
            interaction = _matching_interaction(correction=correction, item=item)
            effective_interaction = _apply_matching_correction(
                correction=correction,
                interaction=interaction,
                expected_source_item_fingerprint=_expected_interaction_fingerprint(
                    item=item,
                    interaction=interaction,
                ),
            )
            effective_items[item_index] = _replace_matching_interaction(
                item=item,
                interaction_id=correction.interaction_id,
                effective_interaction=effective_interaction,
            )
            accepted_entries.append(_accepted_matching_entry(correction))
            readiness_rows.extend(
                _target_readiness_rows(
                    targets=request_body.requested_targets,
                    item=effective_items[item_index],
                    interaction=effective_interaction,
                )
            )
        else:
            rejected_entries.append(_unsupported_entry(correction))

    effective_state = _effective_state(effective_items)
    readiness_report = ExamAuthoringCorrectionTargetReadinessReportV1(
        targets=tuple(readiness_rows),
    )
    return ExamAuthoringCorrectionsApplyResultV1(
        request_id=request_body.request_id,
        source_binding=request_body.source_binding,
        effective_state=effective_state,
        correction_report=ExamAuthoringCorrectionReportV1(
            accepted_entries=tuple(accepted_entries),
            rejected_entries=tuple(rejected_entries),
        ),
        target_readiness=readiness_report,
        artifact_availability=tuple(_artifact_availability(row) for row in readiness_rows),
    )


def _validate_request_binding(request_body: ExamAuthoringCorrectionsApplyRequestV1) -> None:
    binding = request_body.source_binding
    state = request_body.source_authoring_state
    if binding.source_authoring_schema_version != state.source_authoring_schema_version:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_schema_version",
            "Correction source binding schema version does not match the source state.",
            {
                "submitted_schema_version": binding.source_authoring_schema_version,
                "expected_schema_version": state.source_authoring_schema_version,
            },
        )
    if binding.source_state_sha256 != state.source_state_sha256:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_source_state",
            "Correction source binding digest does not match the source state.",
            {
                "submitted_source_state_sha256": binding.source_state_sha256,
                "expected_source_state_sha256": state.source_state_sha256,
            },
        )


def _bound_item(
    correction: ExamAuthoringCorrectionEntryBaseV1,
    items: list[ExamAuthoringCorrectionSourceItemV1],
) -> tuple[int, ExamAuthoringCorrectionSourceItemV1]:
    for index, item in enumerate(items):
        if item.item_id == correction.item_id:
            _validate_item_binding(correction=correction, item=item)
            return index, item
    raise ExamAuthoringCorrectionsApplyError(
        "unknown_exam_authoring_item",
        "Correction references an unknown source item.",
        {"item_id": correction.item_id, "entry_id": correction.entry_id},
    )


def _validate_item_binding(
    *,
    correction: ExamAuthoringCorrectionEntryBaseV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> None:
    if correction.sequence != item.sequence:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_item_sequence",
            "Correction item sequence does not match the source item.",
            {"submitted_sequence": correction.sequence, "expected_sequence": item.sequence},
        )
    if correction.item_type != item.item_type:
        raise ExamAuthoringCorrectionsApplyError(
            "stale_exam_authoring_item_type",
            "Correction item type does not match the source item.",
            {"submitted_item_type": correction.item_type, "expected_item_type": item.item_type},
        )
    if (
        item.source_item_fingerprint is not None
        and correction.source_item_fingerprint != item.source_item_fingerprint
    ):
        raise ExamAuthoringCorrectionsApplyError(
            "stale_correction_source_item_fingerprint",
            "Correction source item fingerprint does not match the source item.",
            {
                "submitted_source_item_fingerprint": correction.source_item_fingerprint,
                "expected_source_item_fingerprint": item.source_item_fingerprint,
            },
        )


def _matching_interaction(
    *,
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
    item: ExamAuthoringCorrectionSourceItemV1,
) -> ExamAuthoringMatchingInteractionV1:
    for interaction in item.matching_interactions:
        if interaction.interaction_id == correction.interaction_id:
            return interaction
    raise ExamAuthoringCorrectionsApplyError(
        "unknown_matching_interaction_id",
        "Matching correction references an unknown interaction.",
        {
            "entry_id": correction.entry_id,
            "item_id": correction.item_id,
            "interaction_id": correction.interaction_id,
        },
    )


def _expected_interaction_fingerprint(
    *,
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteractionV1,
) -> str | None:
    return interaction.source_item_fingerprint or item.source_item_fingerprint


def _apply_matching_correction(
    *,
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
    interaction: ExamAuthoringMatchingInteractionV1,
    expected_source_item_fingerprint: str | None,
) -> ExamAuthoringMatchingInteractionV1:
    try:
        effective_interaction = apply_exam_authoring_matching_manual_answer_key(
            submission=_matching_submission(correction),
            interaction=_to_domain_interaction(interaction),
            expected_source_item_fingerprint=expected_source_item_fingerprint,
        )
    except ExamAuthoringMatchingManualAnswerKeyError as exc:
        raise ExamAuthoringCorrectionsApplyError(exc.code, str(exc), exc.details) from exc
    return _from_domain_interaction(
        effective_interaction,
        source_item_fingerprint=expected_source_item_fingerprint,
    )


def _matching_submission(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> ExamAuthoringMatchingManualAnswerKey:
    provenance: Literal["teacher_provided", "reviewed"]
    if correction.submission_origin == "accepted_advisory_candidate":
        provenance = "reviewed"
    else:
        provenance = "teacher_provided"
    return ExamAuthoringMatchingManualAnswerKey.model_validate(
        {
            "schema_version": EXAM_AUTHORING_IR_SCHEMA_VERSION,
            "kind": "matching",
            "interaction_id": correction.interaction_id,
            "source_item_fingerprint": correction.source_item_fingerprint,
            "answer_key": {
                "provenance": provenance,
                "pairs": tuple(pair.model_dump(mode="json") for pair in correction.pairs),
            },
        }
    )


def _replace_matching_interaction(
    *,
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction_id: str,
    effective_interaction: ExamAuthoringMatchingInteractionV1,
) -> ExamAuthoringCorrectionSourceItemV1:
    interactions = tuple(
        effective_interaction if interaction.interaction_id == interaction_id else interaction
        for interaction in item.matching_interactions
    )
    return item.model_copy(update={"matching_interactions": interactions})


def _accepted_matching_entry(
    correction: ExamAuthoringManualMatchingAnswerKeyCorrectionV1,
) -> ExamAuthoringCorrectionAcceptedEntryV1:
    provenance = (
        "reviewed"
        if correction.submission_origin == "accepted_advisory_candidate"
        else ("teacher_provided")
    )
    return ExamAuthoringCorrectionAcceptedEntryV1(
        entry_id=correction.entry_id,
        kind=correction.kind,
        item_id=correction.item_id,
        sequence=correction.sequence,
        applied_fields=("answer_key",),
        effective_provenance=provenance,
    )


def _unsupported_entry(
    correction: ExamAuthoringCorrectionEntryBaseV1,
) -> ExamAuthoringCorrectionRejectedEntryV1:
    return ExamAuthoringCorrectionRejectedEntryV1(
        entry_id=correction.entry_id,
        kind=correction.kind,
        item_id=correction.item_id,
        sequence=correction.sequence,
        reason_code="correction_kind_not_supported_in_initial_unified_route",
        message_key="exam_authoring.corrections.unsupported_in_initial_runtime",
        teacher_action="wait_for_supported_runtime_slice",
        retryable=False,
    )


def _effective_state(
    items: list[ExamAuthoringCorrectionSourceItemV1],
) -> ExamAuthoringEffectiveStateV1:
    item_payloads = tuple(item.model_dump(mode="json") for item in items)
    return ExamAuthoringEffectiveStateV1(
        effective_state_sha256=_stable_sha256(
            {
                "schema_version": "exam_authoring_effective_state_v1",
                "items": item_payloads,
            }
        ),
        items=tuple(items),
    )


def _stable_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _target_readiness_rows(
    *,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteractionV1,
) -> tuple[ExamAuthoringCorrectionTargetReadinessRowV1, ...]:
    domain_interaction = _to_domain_interaction(interaction)
    return tuple(
        _target_readiness(target=target, item=item, interaction=domain_interaction)
        for target in targets
    )


def _target_readiness(
    *,
    target: ExamAuthoringCorrectionTargetV1,
    item: ExamAuthoringCorrectionSourceItemV1,
    interaction: ExamAuthoringMatchingInteraction,
) -> ExamAuthoringCorrectionTargetReadinessRowV1:
    if target == "qti_package":
        return ExamAuthoringCorrectionTargetReadinessRowV1(
            target=target,
            readiness="unsupported_target_shape",
            export_enabled=False,
            reason_code="examnet_qti_matching_import_unproven",
            message_key="exam_converter.target.matching.qti_import_unproven",
            item_id=item.item_id,
            sequence=item.sequence,
        )

    validation = validate_examnet_pdf_matching_profile(interaction)
    if validation.valid:
        return ExamAuthoringCorrectionTargetReadinessRowV1(
            target=target,
            readiness="ready",
            export_enabled=True,
            reason_code="ready",
            message_key="exam_converter.target.matching.ready",
            item_id=item.item_id,
            sequence=item.sequence,
        )
    return ExamAuthoringCorrectionTargetReadinessRowV1(
        target=target,
        readiness="target_validation_failed",
        export_enabled=False,
        reason_code=";".join(issue.reason_code.value for issue in validation.issues),
        message_key="exam_converter.target.matching.validation_failed",
        item_id=item.item_id,
        sequence=item.sequence,
    )


def _artifact_availability(
    readiness: ExamAuthoringCorrectionTargetReadinessRowV1,
) -> ExamAuthoringCorrectionArtifactAvailabilityRowV1:
    if readiness.export_enabled:
        return ExamAuthoringCorrectionArtifactAvailabilityRowV1(
            artifact_key=readiness.target,
            availability="available",
        )
    return ExamAuthoringCorrectionArtifactAvailabilityRowV1(
        artifact_key=readiness.target,
        availability="unavailable",
        unavailable_code=readiness.reason_code,
    )


def _to_domain_interaction(
    interaction: ExamAuthoringMatchingInteractionV1,
) -> ExamAuthoringMatchingInteraction:
    return ExamAuthoringMatchingInteraction(
        schema_version=interaction.schema_version,
        interaction_id=interaction.interaction_id,
        source_choices=tuple(_to_domain_choice(choice) for choice in interaction.source_choices),
        target_choices=tuple(_to_domain_choice(choice) for choice in interaction.target_choices),
        min_associations=interaction.min_associations,
        max_associations=interaction.max_associations,
        answer_key=ExamAuthoringMatchingAnswerKey(
            provenance=ExamAuthoringAnswerKeyProvenance(interaction.answer_key.provenance),
            pairs=tuple(
                ExamAuthoringMatchingPair(source_id=pair.source_id, target_id=pair.target_id)
                for pair in interaction.answer_key.pairs
            ),
        ),
        evidence=tuple(
            ExamAuthoringSourceEvidence(
                source_family=evidence.source_family,
                source_id=evidence.source_id,
                locator=evidence.locator,
            )
            for evidence in interaction.evidence
        ),
    )


def _from_domain_interaction(
    interaction: ExamAuthoringMatchingInteraction,
    *,
    source_item_fingerprint: str | None,
) -> ExamAuthoringMatchingInteractionV1:
    return ExamAuthoringMatchingInteractionV1(
        schema_version=interaction.schema_version,
        interaction_id=interaction.interaction_id,
        source_item_fingerprint=source_item_fingerprint,
        source_choices=tuple(_from_domain_choice(choice) for choice in interaction.source_choices),
        target_choices=tuple(_from_domain_choice(choice) for choice in interaction.target_choices),
        min_associations=interaction.min_associations,
        max_associations=interaction.max_associations,
        answer_key=ExamAuthoringMatchingAnswerKeyV1(
            provenance=interaction.answer_key.provenance.value,
            pairs=tuple(
                ExamAuthoringMatchingPairV1(source_id=pair.source_id, target_id=pair.target_id)
                for pair in interaction.answer_key.pairs
            ),
        ),
        evidence=tuple(
            ExamAuthoringSourceEvidenceV1(
                source_family=evidence.source_family,
                source_id=evidence.source_id,
                locator=evidence.locator,
            )
            for evidence in interaction.evidence
        ),
    )


def _to_domain_choice(choice: ExamAuthoringMatchingChoiceV1) -> ExamAuthoringMatchingChoice:
    return ExamAuthoringMatchingChoice(
        choice_id=choice.choice_id,
        order=choice.order,
        text=choice.text,
        match_min=choice.match_min,
        match_max=choice.match_max,
    )


def _from_domain_choice(choice: ExamAuthoringMatchingChoice) -> ExamAuthoringMatchingChoiceV1:
    return ExamAuthoringMatchingChoiceV1(
        choice_id=choice.choice_id,
        order=choice.order,
        text=choice.text,
        match_min=choice.match_min,
        match_max=choice.match_max,
    )
