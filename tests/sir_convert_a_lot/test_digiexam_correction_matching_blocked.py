"""DigiExam matching-correction block regressions.

Purpose:
    Prove that DigiExam-issued correction source state cannot be used to unlock
    downstream matching corrections before a matching-capable producer exists.

Relationships:
    - Reuses the authenticated DigiExam service route helpers from the migration
      bundle API tests.
    - Guards Task 333 product sequencing: non-matching corrections may proceed,
      while `manual_matching_answer_key` remains blocked on Task 332.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.test_digiexam_migration_bundle_api_v2 import (
    _client,
    _headers,
    _IdentitySigner,
    _post_digiexam_job,
)


def test_digiexam_issued_source_state_rejects_matching_correction_without_readiness(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-matching-blocked-source-state",
        idempotency_key="idem-digiexam-matching-blocked-source-state",
        wait_seconds=20,
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]
    headers = _headers(
        identity,
        subject="teacher-matching-blocked-source-state",
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
    issued_state = issued["source_authoring_state"]
    assert sum(len(item["matching_interactions"]) for item in issued_state["items"]) == 0
    item = issued_state["items"][0]

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-digiexam-matching-blocked-001",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-matching-blocked-001",
                    "kind": "manual_matching_answer_key",
                    "item_id": item["item_id"],
                    "sequence": item["sequence"],
                    "item_type": "matching",
                    "source_item_fingerprint": item["source_item_fingerprint"],
                    "interaction_id": "matching-from-browser-draft",
                    "submission_origin": "teacher_authored",
                    "pairs": [
                        {
                            "source_id": "source-from-browser-draft",
                            "target_id": "target-from-browser-draft",
                        }
                    ],
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 422
    payload = apply_response.json()
    assert payload["error"]["code"] == "stale_exam_authoring_item_type"
    assert payload["error"]["details"] == {
        "submitted_item_type": "matching",
        "expected_item_type": item["item_type"],
    }
    assert "target_readiness" not in payload
    assert "artifact_availability" not in payload
    assert "source-from-browser-draft" not in apply_response.text
    assert "target-from-browser-draft" not in apply_response.text
