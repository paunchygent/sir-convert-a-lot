"""DigiExam target-readiness reporting for migration bundles.

Purpose:
    Build the Sir Convert-owned target-readiness report that downstream
    consumers use to decide whether PDF and QTI export actions can be enabled.

Relationships:
    - Consumes the DigiExam source IR and bundle artifact entries.
    - Produced by `infrastructure.digiexam_migration_bundle_builder`.
    - Mirrors the target-readiness artifact contract in converter docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from scripts.sir_convert_a_lot.domain.digiexam_exam_authoring_adapter import (
    build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrManualFollowUpReason,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    TARGET_READINESS_REPORT_SCHEMA_VERSION,
    TargetReadinessReportSchemaVersion,
)
from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_gap_contracts import (
    validate_examnet_pdf_gap_open_cloze_profile,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import ExamMigrationTargetV2

GAP_OPEN_CLOZE_TARGET_CHOICE_TEACHER_ACTION: Final = (
    "choose_degraded_manual_free_text_or_omit_or_manual_recreation"
)
GAP_OPEN_CLOZE_UNSUPPORTED_TARGET_MESSAGE_KEY: Final = (
    "exam_converter.target.gap_open_cloze.unsupported_target_shape"
)


class DigiExamTargetReadiness(StrEnum):
    """Consumer-facing readiness classes for export targets."""

    READY = "ready"
    READY_AFTER_ACCEPTED_CURRENT_STATE = "ready_after_accepted_current_state"
    NEEDS_TEACHER_ANSWER_KEY = "needs_teacher_answer_key"
    NEEDS_TEACHER_REVIEW_DECISION = "needs_teacher_review_decision"
    UNSUPPORTED_TARGET_SHAPE = "unsupported_target_shape"
    TARGET_VALIDATION_FAILED = "target_validation_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    NOT_REQUESTED = "not_requested"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True)
class DigiExamTargetReadinessRow:
    """One target or target/item readiness decision."""

    target: str
    readiness: DigiExamTargetReadiness
    export_enabled: bool
    artifact_key: str | None
    reason_code: str
    teacher_action: str
    retryable: bool
    message_key: str
    item_id: str | None = None
    sequence: int | None = None
    source_item_fingerprint: str | None = None


@dataclass(frozen=True)
class DigiExamTargetReadinessReport:
    """Top-level target-readiness report persisted as a named artifact."""

    schema_version: TargetReadinessReportSchemaVersion
    job_id: str
    source_ir_sha256: str
    effective_exam_sha256: str
    targets: tuple[DigiExamTargetReadinessRow, ...]


def build_digiexam_target_readiness_report(
    *,
    job_id: str,
    exam: DigiExamIntermediateExam,
    entries: tuple[DigiExamMigrationArtifactEntry, ...],
    source_ir_sha256: str,
    effective_exam_sha256: str,
    accepted_review_decisions: tuple[tuple[str, ExamMigrationTargetV2], ...] = (),
) -> DigiExamTargetReadinessReport:
    """Build readiness rows for the PDF and QTI migration targets."""

    entries_by_key = {entry.artifact_key: entry for entry in entries}
    fingerprints = {item.item_id: source_item_fingerprint(item) for item in exam.items}
    missing_answer_key_item_ids = {
        follow_up.item_id
        for follow_up in exam.manual_follow_ups
        if follow_up.reason == DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    }
    rows: list[DigiExamTargetReadinessRow] = []
    for key in (
        DigiExamMigrationArtifactKey.EXAMNET_PDF,
        DigiExamMigrationArtifactKey.QTI_PACKAGE,
    ):
        entry = entries_by_key[key]
        rows.extend(
            _rows_for_target(
                entry=entry,
                exam=exam,
                fingerprints=fingerprints,
                missing_answer_key_item_ids=missing_answer_key_item_ids,
                accepted_review_item_ids={
                    item_id
                    for item_id, target in accepted_review_decisions
                    if target.value == entry.artifact_key.value
                },
            )
        )
    return DigiExamTargetReadinessReport(
        schema_version=TARGET_READINESS_REPORT_SCHEMA_VERSION,
        job_id=job_id,
        source_ir_sha256=source_ir_sha256,
        effective_exam_sha256=effective_exam_sha256,
        targets=tuple(rows),
    )


def _rows_for_target(
    *,
    entry: DigiExamMigrationArtifactEntry,
    exam: DigiExamIntermediateExam,
    fingerprints: dict[str, str],
    missing_answer_key_item_ids: set[str],
    accepted_review_item_ids: set[str],
) -> tuple[DigiExamTargetReadinessRow, ...]:
    target = entry.artifact_key.value
    if entry.availability == DigiExamMigrationArtifactAvailability.AVAILABLE:
        accepted_missing_item_ids = accepted_review_item_ids.intersection(
            missing_answer_key_item_ids
        )
        if target == DigiExamMigrationArtifactKey.QTI_PACKAGE.value and accepted_missing_item_ids:
            item_by_id = {item.item_id: item for item in exam.items}
            return tuple(
                _accepted_current_state_row(
                    target=target,
                    item_id=item_id,
                    sequence=item_by_id[item_id].sequence,
                    source_item_fingerprint=fingerprints[item_id],
                )
                for item_id in sorted(accepted_missing_item_ids)
                if item_id in item_by_id
            )
        return (
            DigiExamTargetReadinessRow(
                target=target,
                readiness=DigiExamTargetReadiness.READY,
                export_enabled=True,
                artifact_key=target,
                reason_code="target_available",
                teacher_action="none",
                retryable=False,
                message_key="exam_converter.target.ready",
            ),
        )
    if entry.availability == DigiExamMigrationArtifactAvailability.NOT_REQUESTED:
        return (_target_row(entry, DigiExamTargetReadiness.NOT_REQUESTED, "none", False),)
    if entry.availability == DigiExamMigrationArtifactAvailability.NOT_IMPLEMENTED:
        return (_target_row(entry, DigiExamTargetReadiness.NOT_IMPLEMENTED, "none", False),)
    if entry.availability == DigiExamMigrationArtifactAvailability.FAILED:
        return (
            _target_row(
                entry,
                DigiExamTargetReadiness.TARGET_VALIDATION_FAILED,
                "retry_after_fix",
                True,
            ),
        )
    if entry.unavailable_code == "manual_answer_key_required" and missing_answer_key_item_ids:
        item_by_id = {item.item_id: item for item in exam.items}
        return tuple(
            _missing_key_row(
                target=target,
                item_id=item_id,
                sequence=item_by_id[item_id].sequence,
                source_item_fingerprint=fingerprints[item_id],
                accepted_current_state=item_id in accepted_review_item_ids,
            )
            for item_id in sorted(missing_answer_key_item_ids)
            if item_id in item_by_id
        )
    if entry.unavailable_code == "provider_unavailable":
        return (
            _target_row(entry, DigiExamTargetReadiness.PROVIDER_UNAVAILABLE, "retry_later", True),
        )
    if entry.unavailable_code == "unsupported_target_shape":
        gap_rows = _unsupported_gap_open_cloze_rows(
            target=target,
            exam=exam,
            fingerprints=fingerprints,
        )
        if gap_rows:
            return gap_rows
    return (
        _target_row(
            entry,
            DigiExamTargetReadiness.UNSUPPORTED_TARGET_SHAPE,
            "manual_target_creation_required",
            False,
        ),
    )


def _unsupported_gap_open_cloze_rows(
    *,
    target: str,
    exam: DigiExamIntermediateExam,
    fingerprints: dict[str, str],
) -> tuple[DigiExamTargetReadinessRow, ...]:
    if target != DigiExamMigrationArtifactKey.EXAMNET_PDF.value:
        return ()
    interactions = build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir(exam)
    item_by_id = {item.item_id: item for item in exam.items}
    rows: list[DigiExamTargetReadinessRow] = []
    for interaction in interactions:
        validation = validate_examnet_pdf_gap_open_cloze_profile(interaction)
        if validation.target_export_ready:
            continue
        item = item_by_id.get(interaction.interaction_id)
        if item is None:
            continue
        rows.append(
            DigiExamTargetReadinessRow(
                target=target,
                readiness=DigiExamTargetReadiness.UNSUPPORTED_TARGET_SHAPE,
                export_enabled=False,
                artifact_key=None,
                reason_code=DigiExamTargetReadiness.UNSUPPORTED_TARGET_SHAPE.value,
                teacher_action=GAP_OPEN_CLOZE_TARGET_CHOICE_TEACHER_ACTION,
                retryable=False,
                message_key=GAP_OPEN_CLOZE_UNSUPPORTED_TARGET_MESSAGE_KEY,
                item_id=item.item_id,
                sequence=item.sequence,
                source_item_fingerprint=fingerprints[item.item_id],
            )
        )
    return tuple(rows)


def _accepted_current_state_row(
    *,
    target: str,
    item_id: str,
    sequence: int,
    source_item_fingerprint: str,
) -> DigiExamTargetReadinessRow:
    return DigiExamTargetReadinessRow(
        target=target,
        readiness=DigiExamTargetReadiness.READY_AFTER_ACCEPTED_CURRENT_STATE,
        export_enabled=True,
        artifact_key=target,
        reason_code="accepted_current_state_manual_unkeyed_profile",
        teacher_action="review_after_import",
        retryable=False,
        message_key="exam_converter.target.ready_after_accepted_current_state",
        item_id=item_id,
        sequence=sequence,
        source_item_fingerprint=source_item_fingerprint,
    )


def _missing_key_row(
    *,
    target: str,
    item_id: str,
    sequence: int,
    source_item_fingerprint: str,
    accepted_current_state: bool,
) -> DigiExamTargetReadinessRow:
    if accepted_current_state:
        return DigiExamTargetReadinessRow(
            target=target,
            readiness=DigiExamTargetReadiness.UNSUPPORTED_TARGET_SHAPE,
            export_enabled=False,
            artifact_key=None,
            reason_code="accepted_current_state_not_renderable",
            teacher_action="manual_target_creation_required",
            retryable=False,
            message_key="exam_converter.target.accepted_current_state_not_renderable",
            item_id=item_id,
            sequence=sequence,
            source_item_fingerprint=source_item_fingerprint,
        )
    return DigiExamTargetReadinessRow(
        target=target,
        readiness=DigiExamTargetReadiness.NEEDS_TEACHER_ANSWER_KEY,
        export_enabled=False,
        artifact_key=None,
        reason_code="manual_answer_key_required",
        teacher_action="supply_answer_key_overlay",
        retryable=False,
        message_key="exam_converter.target.needs_teacher_answer_key",
        item_id=item_id,
        sequence=sequence,
        source_item_fingerprint=source_item_fingerprint,
    )


def _target_row(
    entry: DigiExamMigrationArtifactEntry,
    readiness: DigiExamTargetReadiness,
    teacher_action: str,
    retryable: bool,
) -> DigiExamTargetReadinessRow:
    return DigiExamTargetReadinessRow(
        target=entry.artifact_key.value,
        readiness=readiness,
        export_enabled=False,
        artifact_key=None,
        reason_code=entry.unavailable_code or readiness.value,
        teacher_action=teacher_action,
        retryable=retryable,
        message_key=f"exam_converter.target.{readiness.value}",
    )
