"""API tests for DigiExam migration bundle routes.

Purpose:
    Prove that the service API v2 runtime accepts authenticated DigiExam `.dxe`
    jobs, produces deterministic named artifacts, and enforces
    InternalIdentityContextV1 owner isolation.

Relationships:
    - Exercises `interfaces.http_api` through FastAPI TestClient.
    - Covers the runtime bundle builder, QTI package integration, named
      artifact routes, and identity-derived ownership.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest

from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_target_readiness import (
    TARGET_READINESS_REPORT_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _LIVE_CORPUS_DXE_FILENAMES,
    _ONEDRIVE_CORPUS_ROOT,
    _client,
    _embedded_image_payload,
    _headers,
    _IdentitySigner,
    _missing_answer_key_payload,
    _pdf_bytes,
    _post_digiexam_job,
    _read_grants,
)


def test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-bundle-success",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value

    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    artifact_entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    source_stem = Path(manifest["source"]["filename"]).stem

    assert manifest["schema_version"] == DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
    assert manifest["source"]["format"] == "digiexam_dxe"
    assert manifest["bundle_status"] == "partial"
    assert f"{source_stem}-artifact-bundle.json" in manifest_response.headers["content-disposition"]
    assert set(artifact_entries) == {
        "bundle_manifest",
        "examnet_pdf",
        "qti_package",
        "qti_validation_report",
        "ir_json",
        "effective_ir_json",
        "migration_manifest",
        "target_readiness_report",
        "ingestion_overlay_report",
        "answer_key_completion_report",
        "manual_follow_up_report",
        "warnings_report",
        "asset_summary",
    }
    assert artifact_entries["examnet_pdf"]["availability"] == "available"
    assert artifact_entries["examnet_pdf"]["filename"] == f"{source_stem}.pdf"
    assert artifact_entries["qti_package"]["availability"] == "available"
    assert artifact_entries["qti_package"]["filename"] == f"{source_stem}.zip"
    assert artifact_entries["qti_validation_report"]["availability"] == "available"
    assert artifact_entries["qti_validation_report"]["filename"] == (
        f"{source_stem}-qti-validation-report.json"
    )
    assert artifact_entries["target_readiness_report"]["availability"] == "available"
    assert artifact_entries["effective_ir_json"]["availability"] == "not_requested"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert f"{source_stem}.pdf" in pdf_response.headers["content-disposition"]
    assert pdf_response.content.startswith(b"%PDF")

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 200
    assert f"{source_stem}.zip" in qti_response.headers["content-disposition"]
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        assert "imsmanifest.xml" in archive.namelist()
        assert "items/item_002.xml" in archive.namelist()
        manifest_xml = archive.read("imsmanifest.xml").decode("utf-8")
        assert 'identifier="examnet_qti_package"' in manifest_xml

    report_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_validation_report",
        headers=headers,
    )
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["schema_version"] == "examnet_qti_validation_report_v1"
    assert report["package_filename"] == f"{source_stem}.zip"
    readiness_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    )
    assert readiness_response.status_code == 200
    assert readiness_response.json()["schema_version"] == TARGET_READINESS_REPORT_SCHEMA_VERSION


def test_digiexam_migration_respects_examnet_pdf_only_target(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-examnet-pdf-only",
        wait_seconds=20,
        targets=("examnet_pdf",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "not_requested"
    assert entries["qti_validation_report"]["availability"] == "not_requested"

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 409
    assert qti_response.json()["error"]["code"] == "digiexam_artifact_not_requested"

    warnings_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/warnings_report",
        headers=headers,
    )
    assert warnings_response.status_code == 200
    assert warnings_response.json()["qti_warnings"] == []


def test_digiexam_migration_respects_qti_only_target(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-qti-only",
        wait_seconds=20,
        targets=("qti_package",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "not_requested"
    assert entries["qti_package"]["availability"] == "available"
    assert entries["qti_validation_report"]["availability"] == "available"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 409
    assert pdf_response.json()["error"]["code"] == "digiexam_artifact_not_requested"


def test_digiexam_migration_result_metadata_matches_bundle_manifest(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-result-metadata",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=headers)

    assert manifest_response.status_code == 200
    assert result_response.status_code == 200
    manifest = manifest_response.json()
    result = result_response.json()["result"]
    metadata = result["conversion_metadata"]
    assert metadata["route_key"] == "digiexam_dxe_to_examnet_migration_bundle"
    assert metadata["bundle_schema_version"] == manifest["schema_version"]
    assert metadata["bundle_status"] == manifest["bundle_status"]
    assert metadata["source_sha256"] == manifest["source"]["sha256"]
    assert metadata["target_readiness_report_artifact_key"] == "target_readiness_report"
    assert metadata["manual_follow_up_required"] == manifest["manual_follow_up"]["required"]
    assert metadata["warning_count"] == manifest["warnings"]["count"]
    assert metadata["artifact_count"] == len(manifest["artifacts"])


def test_digiexam_migration_idempotency_includes_companion_digest(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    first_parity_pdf = _pdf_bytes("first parity")
    changed_parity_pdf = _pdf_bytes("changed parity")
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", first_parity_pdf),
    )
    assert response.status_code in {200, 202}

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", first_parity_pdf),
    )
    assert replay.status_code in {200, 202}
    assert replay.headers["X-Idempotent-Replay"] == "true"

    conflict = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", changed_parity_pdf),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_digiexam_migration_unavailable_pdf_target_returns_named_artifact_error(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)

    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-unavailable-pdf-target",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    entries = {entry["artifact_key"]: entry for entry in manifest_response.json()["artifacts"]}
    assert entries["examnet_pdf"]["availability"] == "unavailable"
    assert entries["examnet_pdf"]["unavailable_code"] == "manual_answer_key_required"
    assert entries["qti_package"]["availability"] == "unavailable"
    assert entries["qti_package"]["unavailable_code"] == "manual_answer_key_required"
    assert manifest_response.json()["manual_follow_up"]["required"] is True
    assert manifest_response.json()["readiness"]["review_required"] is True

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert artifact_response.status_code == 409
    assert artifact_response.json()["error"]["code"] == "manual_answer_key_required"
    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 409
    assert qti_response.json()["error"]["code"] == "manual_answer_key_required"
    readiness_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    )
    assert readiness_response.status_code == 200
    removed_readiness_values = {
        "ready_after_accepted_current_state",
        "needs_teacher_review_decision",
        "accepted_current_state_manual_unkeyed_profile",
        "accepted_current_state_pdf_manual_unkeyed_profile",
    }
    for removed_value in removed_readiness_values:
        assert removed_value not in readiness_response.text
    readiness_targets = readiness_response.json()["targets"]
    assert any(
        row["readiness"] == "needs_teacher_answer_key"
        and row["source_item_fingerprint"].startswith("sha256:")
        for row in readiness_targets
    )


def test_digiexam_migration_bundle_downloads_embedded_image_pdf(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-embedded-image",
        wait_seconds=20,
        payload=_embedded_image_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        assert document.page_count == 1
        page = document[0]
        assert page.get_images(full=True)
        assert "Look at the embedded prompt image." in str(page.get_text("text", sort=True))


def test_digiexam_migration_live_onedrive_dxe_corpus_subset(tmp_path: Path) -> None:
    missing = [
        filename
        for filename in _LIVE_CORPUS_DXE_FILENAMES
        if not (_ONEDRIVE_CORPUS_ROOT / filename).exists()
    ]
    if missing:
        pytest.skip(f"local raw OneDrive `.dxe` validation files are not present: {missing}")

    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    for index, filename in enumerate(_LIVE_CORPUS_DXE_FILENAMES, start=1):
        source_path = _ONEDRIVE_CORPUS_ROOT / filename
        response = _post_digiexam_job(
            client=client,
            identity=identity,
            subject="teacher-1",
            idempotency_key=f"idem-onedrive-corpus-{index}",
            wait_seconds=20,
            source_file=(filename, source_path.read_bytes()),
        )
        assert response.status_code == 200
        job_id = response.json()["job"]["job_id"]

        manifest_response = client.get(
            f"/v2/convert/jobs/{job_id}/artifacts",
            headers=headers,
        )
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()
        entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

        assert manifest["schema_version"] == DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
        assert manifest["source"]["filename"] == filename
        assert manifest["source"]["format"] == "digiexam_dxe"
        assert manifest["bundle_status"] in {"complete", "partial", "needs_review", "failed"}
        assert entries["qti_validation_report"]["availability"] == "available"
        assert entries["target_readiness_report"]["availability"] == "available"
        assert entries["manual_follow_up_report"]["availability"] == "available"
        assert entries["asset_summary"]["availability"] == "available"
