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
    DigiExamAnswerKeyReviewReplayArtifactReferenceV1,
    DigiExamAnswerKeyReviewTargetReadinessInput,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_replay_artifacts import (
    ExamAuthoringCorrectionReplayArtifactDefinition,
    replay_artifact_definition_for_target,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_replay_overlay import (
    CorrectionReplayOverlayBuildError,
    build_correction_replay_overlay_payload,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionArtifactAvailabilityRowV1,
    ExamAuthoringCorrectionReplayArtifactReferenceV1,
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
from scripts.sir_convert_a_lot.infrastructure.correction_replay_artifact_sets import (
    CorrectionReplayArtifactResolution,
    CorrectionReplayRenderedArtifact,
    artifact_set_dir,
    build_correction_replay_artifact_set_identity,
    find_verified_duplicate_artifact_set,
    references_by_target_from_manifest,
    resolve_correction_replay_artifact,
    write_correction_replay_artifact_set_manifest,
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
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class _ReplayRenderOutcome:
    artifact_references_by_target: dict[
        ExamAuthoringCorrectionTargetV1,
        ExamAuthoringCorrectionReplayArtifactReferenceV1,
    ]
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
            artifact_references_by_target={},
            unavailable_codes_by_target={target: exc.code for target in targets},
        )
    return _with_replay_artifact_references(result=result, outcome=outcome)


def resolve_exam_authoring_correction_replay_artifact(
    *,
    job: StoredJobV2,
    artifact_set_id: str,
    artifact_key: str,
    content_sha256: str,
) -> CorrectionReplayArtifactResolution:
    """Resolve one nested correction replay artifact for download."""

    return resolve_correction_replay_artifact(
        job=job,
        artifact_set_id=artifact_set_id,
        artifact_key=artifact_key,
        content_sha256=content_sha256,
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
    identity = build_correction_replay_artifact_set_identity(
        job=job,
        request_body=request_body,
        targets=targets,
    )
    duplicate_manifest = find_verified_duplicate_artifact_set(
        job=job,
        identity=identity,
        targets=targets,
    )
    if duplicate_manifest is not None:
        return _ReplayRenderOutcome(
            artifact_references_by_target=references_by_target_from_manifest(duplicate_manifest),
            unavailable_codes_by_target={},
        )
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
    rendered_artifacts: list[CorrectionReplayRenderedArtifact] = []
    unavailable_codes: dict[ExamAuthoringCorrectionTargetV1, str] = {}
    set_dir = artifact_set_dir(job=job, artifact_set_id=identity.artifact_set_id)
    for target in targets:
        definition = replay_artifact_definition_for_target(target)
        final_path = set_dir / definition.filename
        unavailable_code = _write_target_artifact(
            job=job,
            target=target,
            definition=definition,
            applied=applied,
            final_path=final_path,
            work_dir=set_dir / f"work-{target}",
        )
        if unavailable_code is None:
            rendered_artifacts.append(
                CorrectionReplayRenderedArtifact(definition=definition, path=final_path)
            )
        else:
            unavailable_codes[target] = unavailable_code
    manifest = write_correction_replay_artifact_set_manifest(
        job=job,
        identity=identity,
        rendered_artifacts=tuple(rendered_artifacts),
    )
    return _ReplayRenderOutcome(
        artifact_references_by_target=references_by_target_from_manifest(manifest),
        unavailable_codes_by_target=unavailable_codes,
    )


def _write_target_artifact(
    *,
    job: StoredJobV2,
    target: ExamAuthoringCorrectionTargetV1,
    definition: ExamAuthoringCorrectionReplayArtifactDefinition,
    applied: DigiExamOverlayApplicationResult,
    final_path: Path,
    work_dir: Path,
) -> str | None:
    work_dir.mkdir(parents=True, exist_ok=True)
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
                        artifact_reference=(
                            DigiExamAnswerKeyReviewReplayArtifactReferenceV1.model_validate(
                                row.artifact_reference.model_dump(mode="json")
                            )
                            if row.artifact_reference is not None
                            else None
                        ),
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
    artifact_reference = outcome.artifact_references_by_target.get(row.target)
    if artifact_reference is not None and row.export_enabled:
        return row.model_copy(
            update={
                "artifact_key": artifact_reference.artifact_key,
                "artifact_reference": artifact_reference,
            }
        )
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
    artifact_reference = outcome.artifact_references_by_target.get(row.artifact_key)
    if artifact_reference is not None:
        return row.model_copy(
            update={
                "availability": "available",
                "unavailable_code": None,
                "artifact_reference": artifact_reference,
            }
        )
    unavailable_code = outcome.unavailable_codes_by_target.get(row.artifact_key)
    if unavailable_code is not None:
        return row.model_copy(
            update={
                "availability": "unavailable",
                "unavailable_code": unavailable_code,
            }
        )
    return row
