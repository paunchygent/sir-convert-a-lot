"""Behavior tests for DigiExam idempotent replay artifact compatibility.

Purpose:
    Prove Service API v2 refuses strict replay for stale succeeded DigiExam
    migration jobs whose persisted terminal artifacts no longer satisfy the
    current route contract.

Relationships:
    - Exercises the public `POST /v2/convert/jobs` route through the Task 375
      idempotency replay service seam.
    - Builds persisted DigiExam bundle artifacts matching
      `docs/converters/digiexam-migration-service-api-artifact-contract.md`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    ARTIFACT_DEFINITIONS,
    REQUIRED_ARTIFACT_KEYS,
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
    DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    TARGET_READINESS_REPORT_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
    json_bytes,
    public_artifact_filename,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from tests.sir_convert_a_lot.exam.digiexam_migration_bundle_api_fixtures import (
    _client,
    _IdentitySigner,
    _post_digiexam_job,
    _runtime_from_client,
)


def test_legacy_digiexam_success_missing_review_state_report_admits_service_reattempt(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-task-376-legacy",
        idempotency_key="idem-task-376-legacy",
    )
    runtime = _runtime_from_client(client)
    old_job_id = _job_id_from_response(first.json())
    _mark_digiexam_succeeded(
        runtime=runtime,
        job_id=old_job_id,
        bundle=_BundleShape(include_answer_key_review_state=False),
    )

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-task-376-legacy",
        idempotency_key="idem-task-376-legacy",
    )

    assert replay.status_code == 202
    assert replay.headers["X-Idempotent-Replay"] == "false"
    payload = replay.json()
    new_job_id = _job_id_from_response(payload)
    assert new_job_id != old_job_id
    assert payload["idempotency"]["state"] == "service_reattempt"
    assert payload["idempotency"]["reason"] == "terminal_artifact_contract_incompatible"
    assert payload["idempotency"]["reattempt_of_job_id"] == old_job_id
    assert payload["idempotency"]["previous_attempts"] == [
        {
            "job_id": old_job_id,
            "status": JobStatus.SUCCEEDED.value,
            "failure_retryable": None,
        }
    ]


def test_digiexam_success_missing_available_artifact_bytes_admits_service_reattempt(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-task-376-missing-bytes",
        idempotency_key="idem-task-376-missing-bytes",
    )
    runtime = _runtime_from_client(client)
    old_job_id = _job_id_from_response(first.json())
    _mark_digiexam_succeeded(
        runtime=runtime,
        job_id=old_job_id,
        bundle=_BundleShape(
            missing_available_artifact=DigiExamMigrationArtifactKey.WARNINGS_REPORT
        ),
    )

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-task-376-missing-bytes",
        idempotency_key="idem-task-376-missing-bytes",
    )

    assert replay.status_code == 202
    assert replay.headers["X-Idempotent-Replay"] == "false"
    payload = replay.json()
    assert payload["idempotency"]["state"] == "service_reattempt"
    assert payload["idempotency"]["reason"] == "terminal_artifact_contract_incompatible"
    assert payload["idempotency"]["reattempt_of_job_id"] == old_job_id


def test_digiexam_success_with_schema_version_drift_admits_service_reattempt(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-task-376-schema-drift",
        idempotency_key="idem-task-376-schema-drift",
    )
    runtime = _runtime_from_client(client)
    old_job_id = _job_id_from_response(first.json())
    _mark_digiexam_succeeded(
        runtime=runtime,
        job_id=old_job_id,
        bundle=_BundleShape(source_ir_schema_version="digiexam_intermediate_exam_v2"),
    )

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-task-376-schema-drift",
        idempotency_key="idem-task-376-schema-drift",
    )

    assert replay.status_code == 202
    assert replay.headers["X-Idempotent-Replay"] == "false"
    payload = replay.json()
    assert payload["idempotency"]["state"] == "service_reattempt"
    assert payload["idempotency"]["reason"] == "terminal_artifact_contract_incompatible"
    assert payload["idempotency"]["reattempt_of_job_id"] == old_job_id


@pytest.mark.parametrize(
    ("bundle_status", "manual_follow_up_required", "target_availability"),
    [
        ("complete", False, DigiExamMigrationArtifactAvailability.AVAILABLE),
        ("partial", True, DigiExamMigrationArtifactAvailability.UNAVAILABLE),
        ("needs_review", True, DigiExamMigrationArtifactAvailability.UNAVAILABLE),
        ("failed", True, DigiExamMigrationArtifactAvailability.FAILED),
    ],
)
def test_compatible_digiexam_terminal_success_remains_strict_replay(
    tmp_path: Path,
    bundle_status: str,
    manual_follow_up_required: bool,
    target_availability: DigiExamMigrationArtifactAvailability,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first = _post_digiexam_job(
        client=client,
        identity=identity,
        subject=f"teacher-task-376-compatible-{bundle_status}",
        idempotency_key=f"idem-task-376-compatible-{bundle_status}",
    )
    runtime = _runtime_from_client(client)
    old_job_id = _job_id_from_response(first.json())
    _mark_digiexam_succeeded(
        runtime=runtime,
        job_id=old_job_id,
        bundle=_BundleShape(
            bundle_status=bundle_status,
            manual_follow_up_required=manual_follow_up_required,
            target_availability=target_availability,
        ),
    )

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject=f"teacher-task-376-compatible-{bundle_status}",
        idempotency_key=f"idem-task-376-compatible-{bundle_status}",
    )

    assert replay.status_code == 200
    assert replay.headers["X-Idempotent-Replay"] == "true"
    payload = replay.json()
    assert _job_id_from_response(payload) == old_job_id
    assert payload["idempotency"]["state"] == "strict_replay"
    assert payload["idempotency"]["reason"] is None


@dataclass(frozen=True)
class _BundleShape:
    include_answer_key_review_state: bool = True
    missing_available_artifact: DigiExamMigrationArtifactKey | None = None
    source_ir_schema_version: str = DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION
    effective_exam_schema_version: str = DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION
    bundle_status: str = "complete"
    manual_follow_up_required: bool = False
    target_availability: DigiExamMigrationArtifactAvailability = (
        DigiExamMigrationArtifactAvailability.AVAILABLE
    )


def _mark_digiexam_succeeded(
    *,
    runtime: ServiceRuntimeV2,
    job_id: str,
    bundle: _BundleShape,
) -> None:
    job = runtime.get_job(job_id)
    assert job is not None
    manifest_bytes = _write_bundle_artifacts(job=job, bundle=bundle)
    assert runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=manifest_bytes,
        pipeline_used="digiexam_migration_bundle_v3",
        backend_used="test",
        acceleration_used=None,
        options_fingerprint="sha256:task-376-digiexam",
        warnings=[],
    )


def _write_bundle_artifacts(*, job: StoredJobV2, bundle: _BundleShape) -> bytes:
    artifacts_dir = job.artifact_path.parent
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    source_ir_sha256 = "sha256:source-ir-task-376"
    effective_exam_sha256 = "sha256:effective-exam-task-376"
    entries = [
        _artifact_entry(
            job=job,
            key=key,
            bundle=bundle,
            source_ir_sha256=source_ir_sha256,
            effective_exam_sha256=effective_exam_sha256,
        )
        for key in REQUIRED_ARTIFACT_KEYS
        if bundle.include_answer_key_review_state
        or key != DigiExamMigrationArtifactKey.ANSWER_KEY_REVIEW_STATE_REPORT
    ]
    manifest: dict[str, object] = {
        "schema_version": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        "job_id": job.job_id,
        "source": {
            "filename": job.source_filename,
            "sha256": "sha256:source-upload-task-376",
            "format": "digiexam_dxe",
        },
        "bundle_status": bundle.bundle_status,
        "retention": {"pin": False, "expires_at": None},
        "artifacts": entries,
        "manual_follow_up": {
            "required": bundle.manual_follow_up_required,
            "artifact_key": "manual_follow_up_report",
            "count": 1 if bundle.manual_follow_up_required else 0,
        },
        "readiness": {
            "artifact_key": "target_readiness_report",
            "exportable_targets": (
                ["examnet_pdf"]
                if bundle.target_availability == DigiExamMigrationArtifactAvailability.AVAILABLE
                else []
            ),
            "review_required": bundle.manual_follow_up_required,
        },
        "source_binding": {
            "source_ir_schema_version": bundle.source_ir_schema_version,
            "source_ir_sha256": source_ir_sha256,
            "effective_exam_schema_version": bundle.effective_exam_schema_version,
            "effective_exam_sha256": effective_exam_sha256,
        },
        "warnings": {"artifact_key": "warnings_report", "count": 0},
    }
    if bundle.include_answer_key_review_state:
        manifest["answer_key_review_state"] = {"artifact_key": "answer_key_review_state_report"}
    return json_bytes(manifest)


def _artifact_entry(
    *,
    job: StoredJobV2,
    key: DigiExamMigrationArtifactKey,
    bundle: _BundleShape,
    source_ir_sha256: str,
    effective_exam_sha256: str,
) -> dict[str, object]:
    definition = ARTIFACT_DEFINITIONS[key]
    availability = _availability_for_key(key=key, bundle=bundle)
    entry: dict[str, object] = {
        "artifact_key": key.value,
        "filename": public_artifact_filename(job=job, key=key),
        "content_type": definition.content_type,
        "availability": availability.value,
    }
    if availability == DigiExamMigrationArtifactAvailability.AVAILABLE:
        payload = _artifact_bytes(
            job=job,
            key=key,
            source_ir_sha256=source_ir_sha256,
            effective_exam_sha256=effective_exam_sha256,
        )
        if key != DigiExamMigrationArtifactKey.BUNDLE_MANIFEST:
            path = artifact_path(job.artifact_path.parent, key)
            if key != bundle.missing_available_artifact:
                path.write_bytes(payload)
            entry["size_bytes"] = len(payload)
            entry["sha256"] = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        entry["download_path"] = f"/v2/convert/jobs/{job.job_id}/artifacts/{key.value}"
        return entry
    entry["unavailable_code"] = "target_validation_failed"
    return entry


def _availability_for_key(
    *,
    key: DigiExamMigrationArtifactKey,
    bundle: _BundleShape,
) -> DigiExamMigrationArtifactAvailability:
    if key in {
        DigiExamMigrationArtifactKey.EXAMNET_PDF,
        DigiExamMigrationArtifactKey.QTI_PACKAGE,
        DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT,
    }:
        return bundle.target_availability
    if key in {
        DigiExamMigrationArtifactKey.EFFECTIVE_IR_JSON,
        DigiExamMigrationArtifactKey.INGESTION_OVERLAY_REPORT,
        DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT,
    }:
        return DigiExamMigrationArtifactAvailability.NOT_REQUESTED
    return DigiExamMigrationArtifactAvailability.AVAILABLE


def _artifact_bytes(
    *,
    job: StoredJobV2,
    key: DigiExamMigrationArtifactKey,
    source_ir_sha256: str,
    effective_exam_sha256: str,
) -> bytes:
    if key == DigiExamMigrationArtifactKey.TARGET_READINESS_REPORT:
        return json_bytes(
            {
                "schema_version": TARGET_READINESS_REPORT_SCHEMA_VERSION,
                "job_id": job.job_id,
                "source_ir_sha256": source_ir_sha256,
                "effective_exam_sha256": effective_exam_sha256,
                "targets": [
                    {
                        "target": "examnet_pdf",
                        "readiness": "ready",
                        "export_enabled": True,
                        "artifact_key": "examnet_pdf",
                        "reason_code": "target_available",
                        "teacher_action": "none",
                        "retryable": False,
                        "message_key": "exam_converter.target.ready",
                    }
                ],
            }
        )
    if key == DigiExamMigrationArtifactKey.ANSWER_KEY_REVIEW_STATE_REPORT:
        return json_bytes({"schema_version": ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION, "items": []})
    if key == DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT:
        return b"# Manuell uppfoljning\n\nInga manuella atgarder kravs.\n"
    return json_bytes({"artifact_key": key.value, "job_id": job.job_id})


def _job_id_from_response(payload: dict[str, object]) -> str:
    job = payload["job"]
    assert isinstance(job, dict)
    job_id = job["job_id"]
    assert isinstance(job_id, str)
    return job_id
