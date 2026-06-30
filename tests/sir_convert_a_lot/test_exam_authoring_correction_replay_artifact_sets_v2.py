"""Correction replay artifact-set behavior tests.

Purpose:
    Prove that source-bound correction replay artifacts are immutable,
    request-scoped, and downloaded only through verified artifact-set
    references.

Relationships:
    - Exercises `interfaces.http_routes_exam_authoring_corrections_v2` through
      the public correction apply route.
    - Exercises the nested correction replay artifact route registered with
      the v2 job artifact routes.
    - Reuses DigiExam migration fixtures to obtain producer-issued source
      bindings and real replay-rendered PDF bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _client,
    _headers,
    _IdentitySigner,
    _missing_answer_key_payload,
    _post_digiexam_job,
    _read_grants,
    _runtime_from_client,
)


def test_correction_replay_artifact_sets_do_not_alias_later_requests(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers, job_id, issued = _source_state_bundle(
        client=client,
        identity=identity,
        subject="teacher-correction-artifact-sets",
    )
    choice_item, choice_interaction, choices = _choice_context(issued)
    first_choice_id = choices[0]["choice_id"]
    second_choice_id = choices[1]["choice_id"]

    first_apply = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=_apply_body(
            request_id="correction-request-artifact-set-first",
            issued=issued,
            choice_item=choice_item,
            choice_interaction=choice_interaction,
            correct_choice_id=first_choice_id,
        ),
    )
    assert first_apply.status_code == 200
    first_reference = _artifact_reference(first_apply.json(), target="examnet_pdf")
    first_download = _download_reference(client, headers=headers, reference=first_reference)
    assert first_download.status_code == 200
    assert first_download.content.startswith(b"%PDF")

    second_apply = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=_apply_body(
            request_id="correction-request-artifact-set-second",
            issued=issued,
            choice_item=choice_item,
            choice_interaction=choice_interaction,
            correct_choice_id=second_choice_id,
        ),
    )
    assert second_apply.status_code == 200
    second_reference = _artifact_reference(second_apply.json(), target="examnet_pdf")
    second_download = _download_reference(client, headers=headers, reference=second_reference)

    assert second_download.status_code == 200
    assert first_reference["artifact_set_id"] != second_reference["artifact_set_id"]
    assert first_reference["content_sha256"] != second_reference["content_sha256"]
    assert first_download.content != second_download.content
    first_redownload = _download_reference(client, headers=headers, reference=first_reference)
    assert first_redownload.status_code == 200
    assert first_redownload.content == first_download.content
    assert first_redownload.content != second_download.content


def test_duplicate_normalized_correction_replay_reuses_verified_artifact_set(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers, _job_id, issued = _source_state_bundle(
        client=client,
        identity=identity,
        subject="teacher-correction-artifact-duplicate",
    )
    choice_item, choice_interaction, choices = _choice_context(issued)
    correct_choice_id = choices[1]["choice_id"]
    body = _apply_body(
        request_id="correction-request-artifact-set-duplicate",
        issued=issued,
        choice_item=choice_item,
        choice_interaction=choice_interaction,
        correct_choice_id=correct_choice_id,
    )

    first_apply = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=body,
    )
    second_apply = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=body,
    )

    assert first_apply.status_code == 200
    assert second_apply.status_code == 200
    first_reference = _artifact_reference(first_apply.json(), target="examnet_pdf")
    second_reference = _artifact_reference(second_apply.json(), target="examnet_pdf")
    assert first_reference == second_reference


def test_reusing_request_id_with_different_normalized_content_conflicts(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers, _job_id, issued = _source_state_bundle(
        client=client,
        identity=identity,
        subject="teacher-correction-artifact-conflict",
    )
    choice_item, choice_interaction, choices = _choice_context(issued)

    first_apply = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=_apply_body(
            request_id="correction-request-artifact-set-conflict",
            issued=issued,
            choice_item=choice_item,
            choice_interaction=choice_interaction,
            correct_choice_id=choices[0]["choice_id"],
        ),
    )
    conflict_apply = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=_apply_body(
            request_id="correction-request-artifact-set-conflict",
            issued=issued,
            choice_item=choice_item,
            choice_interaction=choice_interaction,
            correct_choice_id=choices[1]["choice_id"],
        ),
    )

    assert first_apply.status_code == 200
    assert conflict_apply.status_code == 409
    assert (
        conflict_apply.json()["error"]["code"]
        == "exam_authoring_correction_replay_request_conflict"
    )


def test_correction_replay_artifact_route_fails_closed_for_missing_and_mismatched_references(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers, job_id, issued = _source_state_bundle(
        client=client,
        identity=identity,
        subject="teacher-correction-artifact-mismatch",
    )
    choice_item, choice_interaction, choices = _choice_context(issued)

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json=_apply_body(
            request_id="correction-request-artifact-set-mismatch",
            issued=issued,
            choice_item=choice_item,
            choice_interaction=choice_interaction,
            correct_choice_id=choices[1]["choice_id"],
        ),
    )
    assert apply_response.status_code == 200
    reference = _artifact_reference(apply_response.json(), target="examnet_pdf")

    missing_set = client.get(
        f"/v2/convert/jobs/{job_id}/correction-replays/missing-set/artifacts/"
        f"{reference['artifact_key']}",
        headers=headers,
        params={"content_sha256": reference["content_sha256"]},
    )
    wrong_key = client.get(
        f"/v2/convert/jobs/{job_id}/correction-replays/{reference['artifact_set_id']}/"
        "artifacts/correction_replay_qti_package",
        headers=headers,
        params={"content_sha256": reference["content_sha256"]},
    )
    wrong_hash = client.get(
        f"/v2/convert/jobs/{job_id}/correction-replays/{reference['artifact_set_id']}/"
        f"artifacts/{reference['artifact_key']}",
        headers=headers,
        params={"content_sha256": "sha256:wrong-content"},
    )

    runtime = _runtime_from_client(client)
    job = runtime.get_job(job_id)
    assert job is not None
    manifest_path = (
        job.artifact_path.parent
        / "correction-replays"
        / str(reference["artifact_set_id"])
        / "manifest.json"
    )
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["job_id"] = "jobv2_wrong"
    manifest_path.write_text(json.dumps(manifest_payload, sort_keys=True), encoding="utf-8")
    wrong_job_binding = _download_reference(client, headers=headers, reference=reference)

    assert missing_set.status_code == 404
    assert missing_set.json()["error"]["code"] == "correction_replay_artifact_set_not_found"
    assert wrong_key.status_code == 409
    assert wrong_key.json()["error"]["code"] == "correction_replay_artifact_reference_mismatch"
    assert wrong_hash.status_code == 409
    assert wrong_hash.json()["error"]["code"] == "correction_replay_artifact_reference_mismatch"
    assert wrong_job_binding.status_code == 409
    assert (
        wrong_job_binding.json()["error"]["code"] == "correction_replay_artifact_reference_mismatch"
    )


def _source_state_bundle(
    *,
    client: TestClient,
    identity: _IdentitySigner,
    subject: str,
) -> tuple[dict[str, str], str, dict[str, object]]:
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject=subject,
        idempotency_key=f"idem-{subject}",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf", "qti_package"),
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = str(response.json()["job"]["job_id"])
    headers = _headers(identity, subject=subject, grants=_read_grants())
    issue_response = client.post(
        "/v2/exam-authoring/corrections/source-state/issue",
        headers=headers,
        json={
            "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
            "job_id": job_id,
        },
    )
    assert issue_response.status_code == 200
    return headers, job_id, issue_response.json()


def _apply_body(
    *,
    request_id: str,
    issued: dict[str, object],
    choice_item: dict[str, object],
    choice_interaction: dict[str, object],
    correct_choice_id: object,
) -> dict[str, object]:
    return {
        "schema_version": "exam_authoring_corrections_apply_request_v1",
        "request_id": request_id,
        "source_binding": issued["source_binding"],
        "source_authoring_state": issued["source_authoring_state"],
        "corrections": [
            {
                "entry_id": f"{request_id}-choice",
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
        "requested_targets": ["examnet_pdf"],
    }


def _choice_context(
    issued: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
    issued_state = _json_object(issued["source_authoring_state"])
    items = _json_object_list(issued_state["items"])
    for item in items:
        interactions = _json_object_list(item["choice_interactions"])
        if not interactions:
            continue
        interaction = interactions[0]
        return item, interaction, _json_object_list(interaction["choices"])
    raise AssertionError("expected a choice interaction in issued source state")


def _artifact_reference(payload: dict[str, object], *, target: str) -> dict[str, object]:
    target_readiness = payload["target_readiness"]
    assert isinstance(target_readiness, dict)
    rows = target_readiness["targets"]
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        if row.get("target") != target:
            continue
        reference = row.get("artifact_reference")
        assert isinstance(reference, dict)
        assert reference["schema_version"] == "correction_replay_artifact_reference_v1"
        assert reference["target"] == target
        source_binding = _json_object(payload["source_binding"])
        assert reference["job_id"] == source_binding["source_bundle_id"]
        assert str(reference["artifact_set_id"])
        assert str(reference["artifact_key"]).startswith("correction_replay_")
        assert str(reference["content_sha256"]).startswith("sha256:")
        assert reference["request_id"] == payload["request_id"]
        assert str(reference["source_binding_digest"]).startswith("sha256:")
        assert str(reference["source_state_sha256"]).startswith("sha256:")
        assert str(reference["correction_payload_digest"]).startswith("sha256:")
        assert str(reference["target_set_digest"]).startswith("sha256:")
        assert str(reference["replay_profile_version"])
        assert str(reference["created_at"])
        return {str(key): value for key, value in reference.items()}
    raise AssertionError(f"missing artifact reference for target {target}")


def _json_object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


def _json_object_list(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    return [_json_object(item) for item in value]


def _download_reference(
    client: TestClient,
    *,
    headers: dict[str, str],
    reference: dict[str, object],
) -> Response:
    response = client.get(
        f"/v2/convert/jobs/{reference['job_id']}/correction-replays/"
        f"{reference['artifact_set_id']}/artifacts/{reference['artifact_key']}",
        headers=headers,
        params={"content_sha256": reference["content_sha256"]},
    )
    assert isinstance(response, Response)
    return response
