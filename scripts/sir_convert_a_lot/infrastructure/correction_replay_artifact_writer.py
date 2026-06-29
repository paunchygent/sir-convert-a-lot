"""Correction replay artifact rendering for Exam Converter consumers.

Purpose:
    Render source-bound correction apply results into job-owned replay artifacts
    and attach the resulting artifact keys to target readiness rows.

Relationships:
    - Called by `interfaces.http_routes_exam_authoring_corrections_v2` after the
      unified correction application service accepts a batch.
    - Reuses the DigiExam ingestion overlay and target renderers that produce
      first-pass Exam.net PDF/QTI artifacts.
    - Emits artifact keys defined by
      `application.exam_authoring_correction_replay_artifacts` for
      HuleEdu/Skriptoteket download authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state import (
    attach_digiexam_answer_key_review_replay_references,
)
from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state_models import (
    DigiExamAnswerKeyReviewTargetReadinessInput,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_replay_artifacts import (
    ExamAuthoringCorrectionReplayArtifactDefinition,
    replay_artifact_definition_for_key,
    replay_artifact_definition_for_target,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_replay_overlay import (
    CorrectionReplayOverlayBuildError,
    build_correction_replay_overlay_payload,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionArtifactAvailabilityRowV1,
    ExamAuthoringCorrectionsApplyRequestV1,
    ExamAuthoringCorrectionsApplyResultV1,
    ExamAuthoringCorrectionTargetReadinessReportV1,
    ExamAuthoringCorrectionTargetReadinessRowV1,
    ExamAuthoringCorrectionTargetV1,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlayError,
    DigiExamOverlayApplicationResult,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
    json_bytes,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_source_loader import (
    load_digiexam_migration_source_exam,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_target_artifacts import (
    build_examnet_pdf_artifact,
    build_qti_artifacts,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class ReplayArtifactResolution:
    """Filesystem and response metadata for one replay artifact key."""

    content_type: str
    filename: str
    path: Path


@dataclass(frozen=True)
class _ReplayRenderOutcome:
    artifact_keys_by_target: dict[ExamAuthoringCorrectionTargetV1, str]
    unavailable_codes_by_target: dict[ExamAuthoringCorrectionTargetV1, str]


def write_exam_authoring_correction_replay_artifacts(
    *,
    job: StoredJobV2,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    result: ExamAuthoringCorrectionsApplyResultV1,
) -> ExamAuthoringCorrectionsApplyResultV1:
    """Write corrected replay artifacts and return result rows with artifact keys."""

    targets = _targets_requiring_replay_artifacts(result)
    if not targets or result.correction_report.rejected_entries:
        return result
    try:
        outcome = _render_replay_artifacts(
            job=job,
            request_body=request_body,
            targets=targets,
        )
    except (CorrectionReplayOverlayBuildError, DigiExamIngestionOverlayError) as exc:
        outcome = _ReplayRenderOutcome(
            artifact_keys_by_target={},
            unavailable_codes_by_target={target: exc.code for target in targets},
        )
    return _with_replay_artifact_references(result=result, outcome=outcome)


def resolve_exam_authoring_correction_replay_artifact(
    *,
    job: StoredJobV2,
    artifact_key: str,
) -> ReplayArtifactResolution | None:
    """Resolve one persisted correction replay artifact key for download."""

    definition = replay_artifact_definition_for_key(artifact_key)
    if definition is None:
        return None
    path = _replay_artifact_path(job=job, definition=definition)
    if not path.exists():
        raise ServiceError(
            status_code=404,
            code="digiexam_artifact_not_found",
            message="Named correction replay artifact has not been created for this job.",
            retryable=False,
            details={"artifact_key": artifact_key},
        )
    return ReplayArtifactResolution(
        content_type=definition.content_type,
        filename=definition.filename,
        path=path,
    )


def _targets_requiring_replay_artifacts(
    result: ExamAuthoringCorrectionsApplyResultV1,
) -> tuple[ExamAuthoringCorrectionTargetV1, ...]:
    targets: list[ExamAuthoringCorrectionTargetV1] = []
    for row in result.target_readiness.targets:
        if row.export_enabled and row.target not in targets:
            targets.append(row.target)
    return tuple(targets)


def _render_replay_artifacts(
    *,
    job: StoredJobV2,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    targets: tuple[ExamAuthoringCorrectionTargetV1, ...],
) -> _ReplayRenderOutcome:
    loaded_source = load_digiexam_migration_source_exam(job)
    overlay = build_correction_replay_overlay_payload(
        request_body=request_body,
        source_file_sha256=loaded_source.source_file_sha256,
        source_ir_sha256=loaded_source.source_ir_sha256,
    )
    overlay_bytes = json_bytes(overlay.payload)
    applied = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=overlay_bytes,
        source_file_sha256=loaded_source.source_file_sha256,
        source_ir_sha256=loaded_source.source_ir_sha256,
        source_exam=loaded_source.exam,
        allow_reviewed_completion=overlay.has_reviewed_completion,
    )
    artifact_keys: dict[ExamAuthoringCorrectionTargetV1, str] = {}
    unavailable_codes: dict[ExamAuthoringCorrectionTargetV1, str] = {}
    for target in targets:
        definition = replay_artifact_definition_for_target(target)
        unavailable_code = _write_target_artifact(
            job=job,
            target=target,
            definition=definition,
            applied=applied,
        )
        if unavailable_code is None:
            artifact_keys[target] = definition.artifact_key
        else:
            unavailable_codes[target] = unavailable_code
    return _ReplayRenderOutcome(
        artifact_keys_by_target=artifact_keys,
        unavailable_codes_by_target=unavailable_codes,
    )


def _write_target_artifact(
    *,
    job: StoredJobV2,
    target: ExamAuthoringCorrectionTargetV1,
    definition: ExamAuthoringCorrectionReplayArtifactDefinition,
    applied: DigiExamOverlayApplicationResult,
) -> str | None:
    work_dir = _replay_work_dir(job=job, target=target)
    work_dir.mkdir(parents=True, exist_ok=True)
    final_path = _replay_artifact_path(job=job, definition=definition)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if target == "examnet_pdf":
        entry, _warnings = build_examnet_pdf_artifact(
            job=job,
            artifacts_dir=work_dir,
            exam=applied.effective_exam_for_rendering,
        )
        if entry.availability == DigiExamMigrationArtifactAvailability.AVAILABLE:
            artifact_path(work_dir, DigiExamMigrationArtifactKey.EXAMNET_PDF).replace(final_path)
            return None
        final_path.unlink(missing_ok=True)
        return entry.unavailable_code or "correction_replay_examnet_pdf_unavailable"

    entries, _qti_follow_ups, _qti_warnings = build_qti_artifacts(
        job=job,
        artifacts_dir=work_dir,
        exam=applied.effective_exam_for_rendering,
    )
    entry = entries[DigiExamMigrationArtifactKey.QTI_PACKAGE]
    if entry.availability == DigiExamMigrationArtifactAvailability.AVAILABLE:
        artifact_path(work_dir, DigiExamMigrationArtifactKey.QTI_PACKAGE).replace(final_path)
        return None
    final_path.unlink(missing_ok=True)
    return entry.unavailable_code or "correction_replay_qti_package_unavailable"


def _with_replay_artifact_references(
    *,
    result: ExamAuthoringCorrectionsApplyResultV1,
    outcome: _ReplayRenderOutcome,
) -> ExamAuthoringCorrectionsApplyResultV1:
    target_readiness = ExamAuthoringCorrectionTargetReadinessReportV1(
        targets=tuple(
            _readiness_with_artifact_reference(row=row, outcome=outcome)
            for row in result.target_readiness.targets
        )
    )
    return result.model_copy(
        update={
            "target_readiness": target_readiness,
            "answer_key_review_state": attach_digiexam_answer_key_review_replay_references(
                report=result.answer_key_review_state,
                target_readiness=tuple(
                    DigiExamAnswerKeyReviewTargetReadinessInput(
                        target=row.target,
                        export_enabled=row.export_enabled,
                        reason_code=row.reason_code,
                        item_id=row.item_id,
                        sequence=row.sequence,
                        artifact_key=row.artifact_key,
                    )
                    for row in target_readiness.targets
                ),
            ),
            "artifact_availability": tuple(
                _availability_with_rendering(row=row, outcome=outcome)
                for row in result.artifact_availability
            ),
        }
    )


def _readiness_with_artifact_reference(
    *,
    row: ExamAuthoringCorrectionTargetReadinessRowV1,
    outcome: _ReplayRenderOutcome,
) -> ExamAuthoringCorrectionTargetReadinessRowV1:
    artifact_key = outcome.artifact_keys_by_target.get(row.target)
    if artifact_key is not None and row.export_enabled:
        return row.model_copy(update={"artifact_key": artifact_key})
    unavailable_code = outcome.unavailable_codes_by_target.get(row.target)
    if unavailable_code is not None and row.export_enabled:
        return row.model_copy(
            update={
                "artifact_key": None,
                "export_enabled": False,
                "readiness": "target_validation_failed",
                "reason_code": unavailable_code,
                "message_key": "exam_converter.target.correction_replay_artifact_unavailable",
            }
        )
    return row


def _availability_with_rendering(
    *,
    row: ExamAuthoringCorrectionArtifactAvailabilityRowV1,
    outcome: _ReplayRenderOutcome,
) -> ExamAuthoringCorrectionArtifactAvailabilityRowV1:
    if row.artifact_key in outcome.artifact_keys_by_target:
        return row.model_copy(update={"availability": "available", "unavailable_code": None})
    unavailable_code = outcome.unavailable_codes_by_target.get(row.artifact_key)
    if unavailable_code is not None:
        return row.model_copy(
            update={
                "availability": "unavailable",
                "unavailable_code": unavailable_code,
            }
        )
    return row


def _replay_artifact_path(
    *,
    job: StoredJobV2,
    definition: ExamAuthoringCorrectionReplayArtifactDefinition,
) -> Path:
    return _replay_artifacts_dir(job) / definition.filename


def _replay_work_dir(*, job: StoredJobV2, target: ExamAuthoringCorrectionTargetV1) -> Path:
    return _replay_artifacts_dir(job) / f"work-{target}"


def _replay_artifacts_dir(job: StoredJobV2) -> Path:
    return job.artifact_path.parent / "correction-replay"
