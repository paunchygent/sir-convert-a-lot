"""API tests for DigiExam correction source-state and overlay behavior.

Purpose:
    Cover source-state emission, teacher overlays, point corrections, and
    overlay idempotency in the DigiExam correction bounded context.

Relationships:
    - Exercises the v2 DigiExam migration route through shared API fixtures.
    - Complements source-neutral correction/apply contract tests.
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf

from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DIGIEXAM_IR_SCHEMA_VERSION
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _choice_overlay_bytes,
    _client,
    _embedded_image_gap_payload,
    _headers,
    _IdentitySigner,
    _missing_answer_key_payload,
    _point_correction_overlay_bytes,
    _post_digiexam_job,
    _qti_maxscore,
    _read_grants,
)


def test_digiexam_migration_job_emits_correction_source_state_for_issuer(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-source-state",
        idempotency_key="idem-digiexam-correction-source-state",
        wait_seconds=20,
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-source-state",
        grants={"sir-convert:artifacts:read-own"},
    )
    issue_response = client.post(
        "/v2/exam-authoring/corrections/source-state/issue",
        headers=headers,
        json={
            "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
            "job_id": job_id,
        },
    )

    assert issue_response.status_code == 200
    issued = issue_response.json()
    issued_binding = issued["source_binding"]
    issued_state = issued["source_authoring_state"]
    assert issued_binding["source_bundle_id"] == job_id
    assert issued_binding["source_state_sha256"] == issued_state["source_state_sha256"]
    assert issued_binding["source_state_signature"].startswith("hmac-sha256:")
    assert issued_binding["source_file_sha256"].startswith("sha256:")
    assert issued_state["items"]
    first_item = issued_state["items"][0]
    assert first_item["source_item_fingerprint"].startswith("sha256:")
    assert first_item["title"] == "Essay"
    assert first_item["prompt_html"] == "<p>Explain the water cycle.</p>"
    assert first_item["max_score"] == 3
    choice_item = next(item for item in issued_state["items"] if item["item_id"] == "item-002")
    assert choice_item["choice_interactions"] == [
        {
            "schema_version": "exam_authoring_ir_v1",
            "interaction_id": "choice-item-002",
            "interaction_kind": "single_choice",
            "choices": [
                {
                    "choice_id": "choice-001",
                    "source_id": "1",
                    "order": 1,
                    "text": "Alpha",
                },
                {
                    "choice_id": "choice-002",
                    "source_id": "2",
                    "order": 2,
                    "text": "Beta",
                },
            ],
            "min_correct_choices": 1,
            "max_correct_choices": 1,
            "answer_key": {
                "provenance": "source_provided",
                "correct_choice_ids": ["choice-002"],
            },
            "evidence": [
                {
                    "source_family": "digiexam_dxe",
                    "source_id": "item-002",
                    "locator": "items[1].alternatives",
                }
            ],
        }
    ]
    assert sum(len(item["matching_interactions"]) for item in issued_state["items"]) == 0

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-real-producer-001",
            "source_binding": issued_binding,
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-text-real-producer-001",
                    "kind": "item_text_patch",
                    "item_id": first_item["item_id"],
                    "sequence": first_item["sequence"],
                    "item_type": first_item["item_type"],
                    "source_item_fingerprint": first_item["source_item_fingerprint"],
                    "patches": [
                        {"field": "item_title", "value": "Essay repaired by teacher"},
                        {"field": "prompt_html", "value": "<p>Explain evaporation.</p>"},
                    ],
                },
                {
                    "entry_id": "corr-points-real-producer-001",
                    "kind": "point_correction",
                    "item_id": first_item["item_id"],
                    "sequence": first_item["sequence"],
                    "item_type": first_item["item_type"],
                    "source_item_fingerprint": first_item["source_item_fingerprint"],
                    "max_score": 2,
                },
                {
                    "entry_id": "corr-choice-real-producer-001",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": "choice-item-002",
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": ["choice-001"],
                },
            ],
            "requested_targets": ["examnet_pdf"],
        },
    )

    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["correction_report"]["rejected_entries"] == []
    accepted = apply_payload["correction_report"]["accepted_entries"]
    assert [entry["kind"] for entry in accepted] == [
        "item_text_patch",
        "point_correction",
        "manual_choice_answer_key",
    ]
    effective_first = next(
        item
        for item in apply_payload["effective_state"]["items"]
        if item["item_id"] == first_item["item_id"]
    )
    assert effective_first["title"] == "Essay repaired by teacher"
    assert effective_first["prompt_html"] == "<p>Explain evaporation.</p>"
    assert effective_first["max_score"] == 2
    effective_choice = next(
        item
        for item in apply_payload["effective_state"]["items"]
        if item["item_id"] == choice_item["item_id"]
    )
    assert effective_choice["choice_interactions"][0]["answer_key"] == {
        "provenance": "teacher_provided",
        "correct_choice_ids": ["choice-001"],
    }


def test_digiexam_migration_job_emits_gap_correction_source_state_for_issuer(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-gap-source-state",
        idempotency_key="idem-digiexam-gap-correction-source-state",
        wait_seconds=20,
        payload=_embedded_image_gap_payload(),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-gap-source-state",
        grants={"sir-convert:artifacts:read-own"},
    )
    issue_response = client.post(
        "/v2/exam-authoring/corrections/source-state/issue",
        headers=headers,
        json={
            "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
            "job_id": job_id,
        },
    )

    assert issue_response.status_code == 200
    issued = issue_response.json()
    issued_binding = issued["source_binding"]
    issued_state = issued["source_authoring_state"]
    gap_item = next(
        item
        for item in issued_state["items"]
        if item["item_type"] == "gap_fill" and item["gap_open_cloze_interactions"]
    )
    gap_interaction = gap_item["gap_open_cloze_interactions"][0]
    assert gap_interaction["interaction_id"] == f"gap-{gap_item['item_id']}"
    assert gap_interaction["normalization_profile"] == "exact_trim_case_sensitive"
    assert gap_interaction["gaps"]
    assert gap_interaction["gaps"][0]["gap_id"]
    assert gap_interaction["gaps"][0]["prompt_binding"]["locator"]
    assert gap_interaction["answer_key"]["provenance"] in {
        "absent",
        "source_provided",
        "teacher_provided",
        "reviewed",
        "mixed",
    }

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-real-producer-gap-001",
            "source_binding": issued_binding,
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-gap-real-producer-001",
                    "kind": "manual_gap_open_cloze_answer_key",
                    "item_id": gap_item["item_id"],
                    "sequence": gap_item["sequence"],
                    "item_type": gap_item["item_type"],
                    "source_item_fingerprint": gap_item["source_item_fingerprint"],
                    "interaction_id": gap_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "gap_answers": [
                        {
                            "gap_id": gap_interaction["gaps"][0]["gap_id"],
                            "accepted_values": ["bild"],
                        }
                    ],
                }
            ],
            "requested_targets": ["examnet_pdf"],
        },
    )

    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["correction_report"]["rejected_entries"] == []
    assert apply_payload["correction_report"]["accepted_entries"][0]["kind"] == (
        "manual_gap_open_cloze_answer_key"
    )


def test_digiexam_correction_apply_returns_downloadable_replay_artifacts(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-correction-replay-artifacts",
        idempotency_key="idem-digiexam-correction-replay-artifacts",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-correction-replay-artifacts",
        grants={"sir-convert:artifacts:read-own"},
    )
    issue_response = client.post(
        "/v2/exam-authoring/corrections/source-state/issue",
        headers=headers,
        json={
            "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
            "job_id": job_id,
        },
    )
    assert issue_response.status_code == 200
    issued = issue_response.json()
    issued_binding = issued["source_binding"]
    issued_state = issued["source_authoring_state"]
    choice_item = next(item for item in issued_state["items"] if item["choice_interactions"])
    choice_interaction = choice_item["choice_interactions"][0]
    correct_choice_id = choice_interaction["choices"][1]["choice_id"]

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-replay-artifacts-001",
            "source_binding": issued_binding,
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-choice-replay-artifacts-001",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": choice_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": [correct_choice_id],
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload["correction_report"]["rejected_entries"] == []
    readiness_by_target = {
        row["target"]: row for row in apply_payload["target_readiness"]["targets"]
    }
    assert readiness_by_target["examnet_pdf"]["export_enabled"] is True
    assert readiness_by_target["examnet_pdf"]["artifact_key"] == "correction_replay_examnet_pdf"
    assert readiness_by_target["qti_package"]["export_enabled"] is True
    assert readiness_by_target["qti_package"]["artifact_key"] == "correction_replay_qti_package"
    pdf_reference = readiness_by_target["examnet_pdf"]["artifact_reference"]
    qti_reference = readiness_by_target["qti_package"]["artifact_reference"]
    availability_by_target = {
        row["artifact_key"]: row["availability"] for row in apply_payload["artifact_availability"]
    }
    assert availability_by_target == {
        "examnet_pdf": "available",
        "qti_package": "available",
    }

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/correction-replays/"
        f"{pdf_reference['artifact_set_id']}/artifacts/{pdf_reference['artifact_key']}",
        headers=headers,
        params={"content_sha256": pdf_reference["content_sha256"]},
    )
    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/correction-replays/"
        f"{qti_reference['artifact_set_id']}/artifacts/{qti_reference['artifact_key']}",
        headers=headers,
        params={"content_sha256": qti_reference["content_sha256"]},
    )

    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")
    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        assert "imsmanifest.xml" in archive.namelist()


def test_digiexam_migration_applies_source_bound_teacher_overlay(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-baseline",
        wait_seconds=20,
        payload=source_payload,
    )
    assert baseline_response.status_code == 200
    baseline_job_id = baseline_response.json()["job"]["job_id"]
    baseline_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts",
        headers=headers,
    ).json()
    migration_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts/migration_manifest",
        headers=headers,
    ).json()
    item_summary = migration_manifest["item_summaries"][0]
    overlay_bytes = json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": baseline_manifest["source"]["sha256"],
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": baseline_manifest["source_binding"]["source_ir_sha256"],
            },
            "items": [
                {
                    "item_id": item_summary["item_id"],
                    "sequence": item_summary["sequence"],
                    "item_type": item_summary["item_type"],
                    "source_item_fingerprint": item_summary["source_item_fingerprint"],
                    "manual_answer_key": {
                        "kind": "choice",
                        "correct_alternative_ids": [2],
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-manual-key",
        wait_seconds=20,
        payload=source_payload,
        digiexam_ingestion_overlay=("teacher-overlay.json", overlay_bytes),
    )

    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    assert entries["effective_ir_json"]["availability"] == "available"
    assert entries["ingestion_overlay_report"]["availability"] == "available"
    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "available"

    source_ir = client.get(f"/v2/convert/jobs/{job_id}/artifacts/ir_json", headers=headers).json()
    effective_ir = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/effective_ir_json",
        headers=headers,
    ).json()
    overlay_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/ingestion_overlay_report",
        headers=headers,
    ).json()
    readiness = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    ).json()

    assert source_ir["items"][0]["answer_key"]["provenance"] == "absent"
    assert effective_ir["items"][0]["effective_answer_key"]["provenance"] == "teacher_provided"
    assert effective_ir["items"][0]["effective_answer_key"]["lineage"] is None
    assert overlay_report["accepted_entries"][0]["applied_fields"] == ["manual_answer_key"]
    assert overlay_report["rejected_entries"] == []
    assert {row["target"]: row["export_enabled"] for row in readiness["targets"]} == {
        "examnet_pdf": True,
        "qti_package": True,
    }


def test_digiexam_migration_applies_point_correction_to_effective_pdf_and_qti(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-point-correction-baseline",
        wait_seconds=20,
        payload=source_payload,
    )
    baseline_job_id = baseline_response.json()["job"]["job_id"]
    baseline_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts",
        headers=headers,
    ).json()
    migration_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts/migration_manifest",
        headers=headers,
    ).json()
    item_summary = migration_manifest["item_summaries"][0]

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-point-correction-apply",
        wait_seconds=20,
        payload=source_payload,
        digiexam_ingestion_overlay=(
            "teacher-overlay.json",
            _point_correction_overlay_bytes(
                baseline_manifest=baseline_manifest,
                item_summary=item_summary,
                correct_id=2,
                max_score=6,
            ),
        ),
    )

    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    assert entries["effective_ir_json"]["availability"] == "available"
    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "available"

    source_ir = client.get(f"/v2/convert/jobs/{job_id}/artifacts/ir_json", headers=headers).json()
    effective_ir = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/effective_ir_json",
        headers=headers,
    ).json()
    overlay_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/ingestion_overlay_report",
        headers=headers,
    ).json()
    readiness = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    ).json()
    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )

    assert source_ir["items"][0]["max_score"] == 2
    assert effective_ir["items"][0]["effective_point_correction"] == {
        "kind": "item_points",
        "source_max_score": 2,
        "effective_max_score": 6,
        "source_item_fingerprint": item_summary["source_item_fingerprint"],
    }
    assert effective_ir["items"][0]["effective_answer_key"]["provenance"] == "teacher_provided"
    assert overlay_report["accepted_entries"][0]["applied_fields"] == [
        "point_correction",
        "manual_answer_key",
    ]
    assert {row["target"]: row["readiness"] for row in readiness["targets"]} == {
        "examnet_pdf": "ready",
        "qti_package": "ready",
    }
    assert all(row["item_id"] is None for row in readiness["targets"])

    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        pdf_text = "\n".join(str(page.get_text("text", sort=True)) for page in document)
    assert "Poängvärde: 6" in pdf_text

    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        item_xml = archive.read("items/item_001.xml").decode("utf-8")
    assert _qti_maxscore(item_xml) == "6"


def test_digiexam_migration_idempotency_includes_ingestion_overlay_digest(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()
    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest-baseline",
        wait_seconds=20,
        payload=source_payload,
    )
    baseline_job_id = baseline_response.json()["job"]["job_id"]
    baseline_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts",
        headers=headers,
    ).json()
    migration_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts/migration_manifest",
        headers=headers,
    ).json()
    first_overlay = _choice_overlay_bytes(
        baseline_manifest=baseline_manifest,
        item_summary=migration_manifest["item_summaries"][0],
        correct_id=2,
    )
    changed_overlay = _choice_overlay_bytes(
        baseline_manifest=baseline_manifest,
        item_summary=migration_manifest["item_summaries"][0],
        correct_id=1,
    )

    first = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest",
        digiexam_ingestion_overlay=("teacher-overlay.json", first_overlay),
        payload=source_payload,
    )
    assert first.status_code in {200, 202}
    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest",
        digiexam_ingestion_overlay=("teacher-overlay.json", first_overlay),
        payload=source_payload,
    )
    assert replay.status_code in {200, 202}
    assert replay.headers["X-Idempotent-Replay"] == "true"
    conflict = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest",
        digiexam_ingestion_overlay=("teacher-overlay.json", changed_overlay),
        payload=source_payload,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"
