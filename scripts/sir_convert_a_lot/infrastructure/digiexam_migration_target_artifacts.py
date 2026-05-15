"""DigiExam migration target artifact builders.

Purpose:
    Build target-specific Exam.net PDF and QTI artifacts for one DigiExam
    migration bundle without owning parser, overlay, manifest, or route
    orchestration.

Relationships:
    - Called by `infrastructure.digiexam_migration_bundle_builder`.
    - Uses domain PDF and QTI planners, then returns bundle artifact entries.
    - Keeps target-specific unavailable-code mapping out of the main bundle
      coordinator.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarning,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIntermediateExam
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    ARTIFACT_DEFINITIONS,
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import ExamNetQtiPackageStatus
from scripts.sir_convert_a_lot.domain.examnet_qti_package import build_examnet_qti_package_plan
from scripts.sir_convert_a_lot.domain.specs_v2 import ExamMigrationTargetV2
from scripts.sir_convert_a_lot.infrastructure.digiexam_examnet_pdf_renderer import (
    render_digiexam_examnet_pdf,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
    available_entry,
    failed_entry,
    json_ready,
    unavailable_entry,
)
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    write_examnet_qti_artifacts,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def build_examnet_pdf_artifact(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    exam: DigiExamIntermediateExam,
    accepted_current_state_item_ids: tuple[str, ...] = (),
) -> tuple[DigiExamMigrationArtifactEntry, tuple[DigiExamExamNetPdfWarning, ...]]:
    """Build the Exam.net PDF artifact and bundle entry."""

    pdf_path = artifact_path(artifacts_dir, DigiExamMigrationArtifactKey.EXAMNET_PDF)
    result = render_digiexam_examnet_pdf(
        exam=exam,
        output_pdf_path=pdf_path,
        work_dir=artifacts_dir / "examnet-pdf-work",
        accepted_current_state_item_ids=accepted_current_state_item_ids,
    )
    if result.status == DigiExamExamNetPdfStatus.SUCCESS:
        return (
            available_entry(
                job=job,
                key=DigiExamMigrationArtifactKey.EXAMNET_PDF,
                path=pdf_path,
            ),
            result.warnings,
        )
    return (
        unavailable_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.EXAMNET_PDF,
            unavailable_code=_pdf_unavailable_code(result.warnings),
        ),
        result.warnings,
    )


def build_qti_artifacts(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    exam: DigiExamIntermediateExam,
    accepted_current_state_item_ids: tuple[str, ...] = (),
) -> tuple[
    dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactEntry], list[object], list[str]
]:
    """Build QTI package/report artifacts and bundle entries."""

    adapter_result = build_examnet_qti_items_from_digiexam_ir(
        exam,
        accepted_current_state_item_ids=accepted_current_state_item_ids,
    )
    plan = build_examnet_qti_package_plan(
        package_name=Path(job.source_filename).stem,
        items=adapter_result.items,
    )
    written = write_examnet_qti_artifacts(
        plan=plan,
        output_dir=artifacts_dir,
        package_filename=ARTIFACT_DEFINITIONS[DigiExamMigrationArtifactKey.QTI_PACKAGE].filename,
        report_filename=ARTIFACT_DEFINITIONS[
            DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT
        ].filename,
    )
    entries: dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactEntry] = {}
    if plan.status == ExamNetQtiPackageStatus.PASSED and written.package_path is not None:
        entries[DigiExamMigrationArtifactKey.QTI_PACKAGE] = available_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.QTI_PACKAGE,
            path=written.package_path,
        )
    else:
        entries[DigiExamMigrationArtifactKey.QTI_PACKAGE] = failed_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.QTI_PACKAGE,
            unavailable_code="qti_validation_failed",
        )
    entries[DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT] = available_entry(
        job=job,
        key=DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT,
        path=written.report_path,
    )
    follow_ups = [
        json_ready(asdict(follow_up))
        for follow_up in (*adapter_result.manual_follow_ups, *plan.manual_follow_ups)
    ]
    return entries, follow_ups, list(plan.warnings)


def accepted_current_state_item_ids(
    accepted_review_decisions: tuple[tuple[str, ExamMigrationTargetV2], ...],
    target: ExamMigrationTargetV2,
) -> tuple[str, ...]:
    """Return accepted-current-state item IDs for one target."""

    return tuple(
        item_id
        for item_id, accepted_target in accepted_review_decisions
        if accepted_target == target
    )


def _pdf_unavailable_code(warnings: tuple[DigiExamExamNetPdfWarning, ...]) -> str:
    if not warnings:
        return "unsupported_target_shape"
    first_code = warnings[0].code.value
    if "asset" in first_code:
        return "embedded_asset_unavailable"
    if "answer_key" in first_code:
        return "manual_answer_key_required"
    if "parser" in first_code:
        return "blocked_ir"
    return "unsupported_target_shape"
