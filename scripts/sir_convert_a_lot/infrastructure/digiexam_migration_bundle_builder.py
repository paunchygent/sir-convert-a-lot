"""DigiExam migration bundle execution for service API v2.

Purpose:
    Orchestrate the accepted `.dxe` parser, IR builder, Exam.net PDF renderer,
    QTI package writer, and deterministic bundle manifest into one terminal
    runtime artifact set.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for the
      `digiexam_dxe -> examnet_migration_bundle` route.
    - Writes named artifacts consumed by `interfaces.http_routes_job_artifacts_v2`.
    - Keeps API routing, auth, and generic job-store transitions outside the
      DigiExam target-building logic.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamParseStatus
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarning,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlayError,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
    build_digiexam_ir_manifest,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    ARTIFACT_DEFINITIONS,
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerExtractor,
    normalize_result_text,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_target_readiness import (
    build_digiexam_target_readiness_report,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import ExamNetQtiPackageStatus
from scripts.sir_convert_a_lot.domain.examnet_qti_package import build_examnet_qti_package_plan
from scripts.sir_convert_a_lot.domain.specs_v2 import (
    ExamMigrationTargetV2,
    normalized_exam_migration_targets_v2,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_answer_key_completion_runtime import (
    write_requested_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_examnet_pdf_renderer import (
    render_digiexam_examnet_pdf,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_job_companion_paths_v2 import (
    graded_result_pdf_path_for_upload,
    ingestion_overlay_path_for_upload,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
    available_entry,
    bundle_status,
    complete_entries,
    expires_at,
    failed_entry,
    json_bytes,
    json_ready,
    not_requested_entry,
    not_requested_qti_entries,
    unavailable_entry,
    write_json,
    write_manual_follow_up_report,
    write_warnings_report,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_pdf_text import DigiExamPdfTextExtractor
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    write_examnet_qti_artifacts,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


@dataclass(frozen=True)
class DigiExamMigrationBundleExecutionResult:
    """Runtime execution result for a terminal DigiExam migration bundle."""

    artifact_bytes: bytes
    warnings: tuple[str, ...]
    phase_timings_ms: dict[str, int]


def execute_digiexam_migration_bundle_job(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
) -> DigiExamMigrationBundleExecutionResult:
    """Build and persist all named artifacts for one DigiExam migration job."""

    started = time.perf_counter()
    artifacts_dir = job.artifact_path.parent
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    source_bytes = job.upload_path.read_bytes()
    source_file_sha256 = f"sha256:{hashlib.sha256(source_bytes).hexdigest()}"
    answer_evidence = _answer_evidence_for_job(job)

    parse_result = DigiExamDxeParser().parse_file(job.upload_path, answer_evidence=answer_evidence)
    if parse_result.status == DigiExamParseStatus.BLOCKED and not parse_result.items:
        raise ServiceError(
            status_code=422,
            code="digiexam_source_invalid",
            message="DigiExam `.dxe` source could not be parsed into exam items.",
            retryable=False,
            details={"warnings": [warning.message for warning in parse_result.warnings]},
        )

    exam = build_digiexam_intermediate_exam(parse_result)
    ir_manifest = build_digiexam_ir_manifest(exam)
    requested_targets = normalized_exam_migration_targets_v2(job.spec)

    ir_path = artifact_path(artifacts_dir, DigiExamMigrationArtifactKey.IR_JSON)
    write_json(ir_path, json_ready(asdict(exam)))
    source_ir_sha256 = _artifact_sha256(ir_path)
    effective_exam = exam
    effective_exam_sha256 = source_ir_sha256
    effective_ir_entry = None
    ingestion_overlay_report_entry = None
    overlay_result = None
    overlay_path = ingestion_overlay_path_for_upload(job.upload_path)
    if overlay_path.exists():
        try:
            overlay_result = parse_and_apply_digiexam_ingestion_overlay(
                overlay_bytes=overlay_path.read_bytes(),
                source_file_sha256=source_file_sha256,
                source_ir_sha256=source_ir_sha256,
                source_exam=exam,
            )
        except DigiExamIngestionOverlayError as exc:
            raise ServiceError(
                status_code=422,
                code=exc.code,
                message=str(exc),
                retryable=False,
                details=exc.details,
            ) from exc
        effective_exam = overlay_result.effective_exam_for_rendering
        overlay_report_path = artifact_path(
            artifacts_dir,
            DigiExamMigrationArtifactKey.INGESTION_OVERLAY_REPORT,
        )
        write_json(overlay_report_path, json_ready(asdict(overlay_result.ingestion_overlay_report)))
        ingestion_overlay_report_entry = available_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.INGESTION_OVERLAY_REPORT,
            path=overlay_report_path,
        )
        if overlay_result.renderer_input_changed:
            effective_ir_path = artifact_path(
                artifacts_dir,
                DigiExamMigrationArtifactKey.EFFECTIVE_IR_JSON,
            )
            write_json(effective_ir_path, json_ready(asdict(overlay_result.effective_exam_report)))
            effective_exam_sha256 = _artifact_sha256(effective_ir_path)
            effective_ir_entry = available_entry(
                job=job,
                key=DigiExamMigrationArtifactKey.EFFECTIVE_IR_JSON,
                path=effective_ir_path,
            )
    answer_key_completion_report_entry = write_requested_digiexam_answer_key_completion_report(
        job=job,
        artifacts_dir=artifacts_dir,
        exam=effective_exam,
        config=config,
    )
    migration_manifest_path = artifact_path(
        artifacts_dir, DigiExamMigrationArtifactKey.MIGRATION_MANIFEST
    )
    write_json(migration_manifest_path, json_ready(asdict(ir_manifest)))
    asset_summary_path = artifact_path(artifacts_dir, DigiExamMigrationArtifactKey.ASSET_SUMMARY)
    write_json(
        asset_summary_path,
        {
            "schema_version": "digiexam_asset_summary_v1",
            "source_filename": exam.source_filename,
            "asset_count": ir_manifest.asset_count,
            "assets": json_ready(tuple(asdict(asset) for asset in ir_manifest.asset_summaries)),
        },
    )

    if ExamMigrationTargetV2.EXAMNET_PDF in requested_targets:
        pdf_entry, pdf_warnings = _build_examnet_pdf_artifact(
            job=job, artifacts_dir=artifacts_dir, exam=effective_exam
        )
    else:
        pdf_entry = not_requested_entry(job=job, key=DigiExamMigrationArtifactKey.EXAMNET_PDF)
        pdf_warnings = ()

    if ExamMigrationTargetV2.QTI_PACKAGE in requested_targets:
        qti_entries, qti_follow_ups, qti_warnings = _build_qti_artifacts(
            job=job,
            artifacts_dir=artifacts_dir,
            exam=effective_exam,
            accepted_current_state_item_ids=(
                _accepted_current_state_item_ids(
                    overlay_result.accepted_review_decisions,
                    ExamMigrationTargetV2.QTI_PACKAGE,
                )
                if overlay_result is not None
                else ()
            ),
        )
    else:
        qti_entries = not_requested_qti_entries(job)
        qti_follow_ups = []
        qti_warnings = []
    manual_follow_up_path = artifact_path(
        artifacts_dir, DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT
    )
    manual_follow_up_count = write_manual_follow_up_report(
        path=manual_follow_up_path,
        exam_follow_ups=json_ready(
            tuple(asdict(entry) for entry in effective_exam.manual_follow_ups)
        ),
        qti_follow_ups=qti_follow_ups,
    )
    warnings_path = artifact_path(artifacts_dir, DigiExamMigrationArtifactKey.WARNINGS_REPORT)
    warning_messages = write_warnings_report(
        path=warnings_path,
        parser_warnings=json_ready(tuple(asdict(warning) for warning in parse_result.warnings)),
        pdf_warnings=json_ready(tuple(asdict(warning) for warning in pdf_warnings)),
        qti_warnings=qti_warnings,
    )
    target_readiness_path = artifact_path(
        artifacts_dir,
        DigiExamMigrationArtifactKey.TARGET_READINESS_REPORT,
    )
    target_readiness_entries = tuple(
        entry
        for entry in (pdf_entry, *qti_entries.values())
        if entry.artifact_key
        in {DigiExamMigrationArtifactKey.EXAMNET_PDF, DigiExamMigrationArtifactKey.QTI_PACKAGE}
    )
    write_json(
        target_readiness_path,
        asdict(
            build_digiexam_target_readiness_report(
                job_id=job.job_id,
                exam=effective_exam,
                entries=target_readiness_entries,
                source_ir_sha256=source_ir_sha256,
                effective_exam_sha256=effective_exam_sha256,
                accepted_review_decisions=(
                    overlay_result.accepted_review_decisions if overlay_result is not None else ()
                ),
            )
        ),
    )

    entries = complete_entries(
        job=job,
        artifacts_dir=artifacts_dir,
        pdf_entry=pdf_entry,
        qti_entries=qti_entries,
        effective_ir_entry=effective_ir_entry,
        ingestion_overlay_report_entry=ingestion_overlay_report_entry,
        answer_key_completion_report_entry=answer_key_completion_report_entry,
    )
    resolved_bundle_status = bundle_status(entries, manual_follow_up_count)
    manifest = {
        "schema_version": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        "job_id": job.job_id,
        "source": {
            "filename": job.source_filename,
            "sha256": source_file_sha256,
            "format": job.source_format.value,
        },
        "bundle_status": resolved_bundle_status.value,
        "retention": {"pin": job.spec.retention.pin, "expires_at": expires_at(job)},
        "artifacts": json_ready(tuple(asdict(entry) for entry in entries)),
        "manual_follow_up": {
            "required": manual_follow_up_count > 0,
            "artifact_key": DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT.value,
            "count": manual_follow_up_count,
        },
        "readiness": {
            "artifact_key": DigiExamMigrationArtifactKey.TARGET_READINESS_REPORT.value,
            "exportable_targets": _exportable_targets(entries),
            "review_required": manual_follow_up_count > 0,
        },
        "source_binding": {
            "source_ir_schema_version": exam.schema_version,
            "source_ir_sha256": source_ir_sha256,
            "effective_exam_schema_version": DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
            "effective_exam_sha256": effective_exam_sha256,
        },
        "warnings": {
            "artifact_key": DigiExamMigrationArtifactKey.WARNINGS_REPORT.value,
            "count": len(warning_messages),
        },
    }
    manifest_bytes = json_bytes(manifest)
    job.artifact_path.write_bytes(manifest_bytes)
    phase_timings_ms = {"digiexam_migration_bundle_ms": _elapsed_ms(started)}
    return DigiExamMigrationBundleExecutionResult(
        artifact_bytes=manifest_bytes,
        warnings=tuple(warning_messages),
        phase_timings_ms=phase_timings_ms,
    )


def _answer_evidence_for_job(job: StoredJobV2) -> DigiExamResultPdfAnswerEvidence | None:
    result_pdf_path = graded_result_pdf_path_for_upload(job.upload_path)
    if not result_pdf_path.exists():
        return None
    _, lines = DigiExamPdfTextExtractor().extract(result_pdf_path)
    delimiter = _infer_student_block_delimiter(tuple(line.text for line in lines))
    if delimiter is None:
        raise ServiceError(
            status_code=422,
            code="digiexam_result_pdf_unsafe_evidence",
            message="Sanitized graded-result PDF evidence could not be classified safely.",
            retryable=False,
        )
    return DigiExamResultPdfAnswerExtractor(student_block_delimiter=delimiter).extract(lines)


def _infer_student_block_delimiter(lines: tuple[str, ...]) -> str | None:
    counts: dict[str, int] = {}
    for line in lines:
        normalized = normalize_result_text(line)
        if normalized == "" or _looks_like_result_content(normalized):
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
    repeated = tuple((value, count) for value, count in counts.items() if count >= 2)
    if not repeated:
        return None
    return sorted(repeated, key=lambda entry: (-entry[1], entry[0]))[0][0]


def _looks_like_result_content(value: str) -> bool:
    markers = ("Svar", "Erhållen poäng", "Korrekt", "Fel svar", "Max poäng")
    return any(marker in value for marker in markers)


def _build_examnet_pdf_artifact(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    exam,
) -> tuple[DigiExamMigrationArtifactEntry, tuple[DigiExamExamNetPdfWarning, ...]]:
    pdf_path = artifact_path(artifacts_dir, DigiExamMigrationArtifactKey.EXAMNET_PDF)
    result = render_digiexam_examnet_pdf(
        exam=exam,
        output_pdf_path=pdf_path,
        work_dir=artifacts_dir / "examnet-pdf-work",
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


def _build_qti_artifacts(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    exam,
    accepted_current_state_item_ids: tuple[str, ...] = (),
) -> tuple[
    dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactEntry], list[object], list[str]
]:
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


def _accepted_current_state_item_ids(
    accepted_review_decisions: tuple[tuple[str, ExamMigrationTargetV2], ...],
    target: ExamMigrationTargetV2,
) -> tuple[str, ...]:
    return tuple(
        item_id
        for item_id, accepted_target in accepted_review_decisions
        if accepted_target == target
    )


def _exportable_targets(entries: tuple[DigiExamMigrationArtifactEntry, ...]) -> list[str]:
    target_keys = {
        DigiExamMigrationArtifactKey.EXAMNET_PDF,
        DigiExamMigrationArtifactKey.QTI_PACKAGE,
    }
    return [
        entry.artifact_key.value
        for entry in entries
        if entry.artifact_key in target_keys and entry.download_path is not None
    ]


def _artifact_sha256(path: Path) -> str:
    payload = path.read_bytes()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


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


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
