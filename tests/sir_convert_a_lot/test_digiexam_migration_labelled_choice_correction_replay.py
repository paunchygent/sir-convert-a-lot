"""Correction replay tests for source-labelled DigiExam choice options.

Purpose:
    Prove that source-visible multiple-choice labels no longer block
    teacher-corrected Exam.net PDF replay artifacts.

Relationships:
    - Exercises the v2 DigiExam migration and correction API fixtures.
    - Complements renderer-domain tests by proving downloadable replay
      artifacts at the service boundary.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _client,
    _headers,
    _IdentitySigner,
    _post_digiexam_job,
)


def test_digiexam_correction_replay_pdf_downloads_with_source_labelled_options(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-labelled-choice-replay",
        idempotency_key="idem-labelled-choice-replay",
        wait_seconds=20,
        payload=_labelled_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-labelled-choice-replay",
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
            "request_id": "correction-request-labelled-choice-replay-001",
            "source_binding": issued_binding,
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-labelled-choice-replay-001",
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
    pdf_reference = readiness_by_target["examnet_pdf"]["artifact_reference"]
    qti_reference = readiness_by_target["qti_package"]["artifact_reference"]
    review_item = apply_payload["answer_key_review_state"]["items"][0]
    assert review_item["review_state"] == "teacher_modified"
    assert review_item["current_key_origin"] == "teacher_authored"
    assert [
        (reference["target"], reference["artifact_key"], reference["artifact_set_id"])
        for reference in review_item["replay_artifact_references"]
    ] == [
        ("examnet_pdf", "correction_replay_examnet_pdf", pdf_reference["artifact_set_id"]),
        ("qti_package", "correction_replay_qti_package", qti_reference["artifact_set_id"]),
    ]

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
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        pdf_text = "\n".join(str(page.get_text("text", sort=True)) for page in document)
    assert "Alpha" in pdf_text
    assert "Beta" in pdf_text
    assert "Correct answer: Beta" in pdf_text
    assert "A. Alpha" not in pdf_text
    assert "B. Beta" not in pdf_text

    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        assert "imsmanifest.xml" in archive.namelist()


def _labelled_missing_answer_key_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Single without key",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "A. Alpha", "about": "", "right": False},
                            {"id": 2, "title": "B. Beta", "about": "", "right": False},
                        ],
                    }
                ]
            }
        ]
    }
