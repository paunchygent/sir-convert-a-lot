"""Correction apply source-job fail-closed route tests.

Purpose:
    Prove that source-bound correction apply cannot return exportable replay
    readiness when the producer job named by the signed source binding is gone
    or unauthorized.

Relationships:
    - Exercises `interfaces.http_routes_exam_authoring_corrections_v2` through
      the public FastAPI route.
    - Reuses DigiExam migration fixtures to obtain real producer-issued source
      bindings and source-state payloads.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _client,
    _headers,
    _IdentitySigner,
    _missing_answer_key_payload,
    _post_digiexam_job,
    _read_grants,
    _runtime_from_client,
)


def test_correction_apply_fails_closed_when_bound_source_job_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-correction-source-missing",
        idempotency_key="idem-correction-source-missing",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-correction-source-missing",
        grants=_read_grants(),
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
    choice_item = next(item for item in issued_state["items"] if item["choice_interactions"])
    choice_interaction = choice_item["choice_interactions"][0]
    runtime = _runtime_from_client(client)
    original_get_job = runtime.get_job

    def missing_bound_source_job(lookup_job_id: str) -> StoredJobV2 | None:
        if lookup_job_id == job_id:
            return None
        return original_get_job(lookup_job_id)

    monkeypatch.setattr(runtime, "get_job", missing_bound_source_job)

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-source-missing",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-choice-source-missing",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": choice_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": [choice_interaction["choices"][1]["choice_id"]],
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 409
    payload = apply_response.json()
    assert payload["error"]["code"] == "exam_authoring_correction_source_job_unavailable"
    assert payload["error"]["retryable"] is False
    rendered = apply_response.text
    assert "correction_replay_examnet_pdf" not in rendered
    assert "correction_replay_qti_package" not in rendered
    assert "source_state_signature" not in rendered


def test_correction_apply_wrong_owner_source_job_remains_access_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-correction-source-owner",
        idempotency_key="idem-correction-source-owner",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-correction-source-owner",
        grants=_read_grants(),
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
    choice_item = next(item for item in issued_state["items"] if item["choice_interactions"])
    choice_interaction = choice_item["choice_interactions"][0]
    runtime = _runtime_from_client(client)
    source_job = runtime.get_job(job_id)
    assert source_job is not None
    wrong_owner_job = replace(source_job, owner_api_key_scope="identity:v1:other-teacher")

    def wrong_owner_bound_source_job(lookup_job_id: str) -> StoredJobV2 | None:
        if lookup_job_id == job_id:
            return wrong_owner_job
        return runtime.get_job(lookup_job_id)

    monkeypatch.setattr(runtime, "get_job", wrong_owner_bound_source_job)

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-source-wrong-owner",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-choice-source-wrong-owner",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": choice_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": [choice_interaction["choices"][1]["choice_id"]],
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 403
    assert (
        apply_response.json()["error"]["code"] == "exam_authoring_correction_replay_access_denied"
    )


def test_correction_apply_missing_grant_source_job_remains_access_denied(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-correction-source-missing-grant",
        idempotency_key="idem-correction-source-missing-grant",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    issue_headers = _headers(
        identity,
        subject="teacher-correction-source-missing-grant",
        grants=_read_grants(),
    )
    issue_response = client.post(
        "/v2/exam-authoring/corrections/source-state/issue",
        headers=issue_headers,
        json={
            "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
            "job_id": job_id,
        },
    )
    assert issue_response.status_code == 200
    issued = issue_response.json()
    issued_state = issued["source_authoring_state"]
    choice_item = next(item for item in issued_state["items"] if item["choice_interactions"])
    choice_interaction = choice_item["choice_interactions"][0]

    apply_headers = _headers(
        identity,
        subject="teacher-correction-source-missing-grant",
        grants={"sir-convert:jobs:read-own"},
    )
    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=apply_headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-source-missing-grant",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-choice-source-missing-grant",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": choice_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": [choice_interaction["choices"][1]["choice_id"]],
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 403
    assert (
        apply_response.json()["error"]["code"] == "exam_authoring_correction_replay_access_denied"
    )
    rendered = apply_response.text
    assert "correction_replay_examnet_pdf" not in rendered
    assert "correction_replay_qti_package" not in rendered
    assert "source_state_signature" not in rendered


def test_correction_apply_rejects_stale_binding_before_source_job_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-correction-stale-binding",
        idempotency_key="idem-correction-stale-binding",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-correction-stale-binding",
        grants=_read_grants(),
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
    issued_state["source_state_sha256"] = "sha256:stale-source-state"
    choice_item = next(item for item in issued_state["items"] if item["choice_interactions"])
    choice_interaction = choice_item["choice_interactions"][0]
    runtime = _runtime_from_client(client)

    def source_job_lookup_must_not_run(lookup_job_id: str) -> StoredJobV2 | None:
        raise AssertionError(f"unexpected source-job lookup for {lookup_job_id}")

    monkeypatch.setattr(runtime, "get_job", source_job_lookup_must_not_run)

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-stale-before-lookup",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-choice-stale-before-lookup",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": choice_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": [choice_interaction["choices"][1]["choice_id"]],
                }
            ],
            "requested_targets": ["examnet_pdf"],
        },
    )

    assert apply_response.status_code == 422
    assert apply_response.json()["error"]["code"] == "stale_exam_authoring_source_state"


def test_correction_apply_valid_source_job_still_returns_replay_artifacts(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-correction-source-valid",
        idempotency_key="idem-correction-source-valid",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(
        identity,
        subject="teacher-correction-source-valid",
        grants=_read_grants(),
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
    choice_item = next(item for item in issued_state["items"] if item["choice_interactions"])
    choice_interaction = choice_item["choice_interactions"][0]

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-source-valid",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-choice-source-valid",
                    "kind": "manual_choice_answer_key",
                    "item_id": choice_item["item_id"],
                    "sequence": choice_item["sequence"],
                    "item_type": choice_item["item_type"],
                    "source_item_fingerprint": choice_item["source_item_fingerprint"],
                    "interaction_id": choice_interaction["interaction_id"],
                    "submission_origin": "teacher_authored",
                    "correct_choice_ids": [choice_interaction["choices"][1]["choice_id"]],
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 200
    payload = apply_response.json()
    assert payload["correction_report"]["rejected_entries"] == []
    readiness_by_target = {row["target"]: row for row in payload["target_readiness"]["targets"]}
    assert readiness_by_target["examnet_pdf"]["artifact_key"] == "correction_replay_examnet_pdf"
    assert readiness_by_target["qti_package"]["artifact_key"] == "correction_replay_qti_package"
    assert {
        row["artifact_key"]: row["availability"] for row in payload["artifact_availability"]
    } == {
        "examnet_pdf": "available",
        "qti_package": "available",
    }
