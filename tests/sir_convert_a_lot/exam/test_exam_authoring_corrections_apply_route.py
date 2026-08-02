"""Tests for the unified exam authoring corrections apply route.

Purpose:
    Prove unified correction route exposes the unified source-neutral correction route, applies
    matching manual keys through it, and preserves signed source-state binding
    rules for the initial matching implementation.

Relationships:
    - Exercises `interfaces.http_routes_exam_authoring_corrections_v2`.
    - Reuses the HTML to PDF route3 matching DTO/domain validation through the unified
      `manual_matching_answer_key` entry.
    - Complements hard-cut and non-matching correction route test modules.
"""

from __future__ import annotations

from pathlib import Path

from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    API_HEADERS as _API_HEADERS,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    ISSUE_ROUTE as _ISSUE_ROUTE,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    ROUTE as _ROUTE,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    build_client as _client,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    candidate_lineage as _candidate_lineage,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    first_correction as _first_correction,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    matching_candidate_digest as _matching_candidate_digest,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    refresh_source_state_digest as _refresh_source_state_digest,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    request_payload as _request_payload,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    seed_source_state_job as _seed_source_state_job,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    source_state_issue_payload as _source_state_issue_payload,
)


def test_corrections_apply_route_returns_effective_matching_state_without_artifacts(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)

    response = client.post(_ROUTE, headers=_API_HEADERS, json=_request_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "exam_authoring_corrections_apply_result_v1"
    assert payload["request_id"] == "correction-request-001"
    assert payload["correction_report"]["accepted_entries"] == [
        {
            "entry_id": "corr-matching-001",
            "kind": "manual_matching_answer_key",
            "item_id": "item-001",
            "sequence": 1,
            "applied_fields": ["answer_key"],
            "effective_provenance": "teacher_provided",
        }
    ]
    assert payload["correction_report"]["rejected_entries"] == []
    effective_item = payload["effective_state"]["items"][0]
    effective_interaction = effective_item["matching_interactions"][0]
    assert effective_interaction["answer_key"] == {
        "provenance": "teacher_provided",
        "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
    }
    assert effective_interaction["source_item_fingerprint"] == "sha256:item-001"
    assert payload["target_readiness"]["targets"] == []
    assert payload["artifact_availability"] == []


def test_correction_source_state_issue_route_returns_echoable_signed_bundle(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    job_id = _seed_source_state_job(client)

    issue_response = client.post(
        _ISSUE_ROUTE,
        headers=_API_HEADERS,
        json=_source_state_issue_payload(job_id),
    )

    assert issue_response.status_code == 200
    issued = issue_response.json()
    assert issued["schema_version"] == "exam_authoring_correction_source_state_issue_result_v1"
    issued_binding = issued["source_binding"]
    issued_state = issued["source_authoring_state"]
    assert issued_binding["source_state_sha256"] == issued_state["source_state_sha256"]
    assert issued_binding["source_bundle_id"] == job_id
    assert issued_binding["source_state_sha256"] != "sha256:server-side-placeholder"
    assert issued_binding["source_state_signature"].startswith("hmac-sha256:")

    apply_payload = _request_payload()
    apply_payload["source_binding"] = issued_binding
    apply_payload["source_authoring_state"] = issued_state
    apply_response = client.post(_ROUTE, headers=_API_HEADERS, json=apply_payload)

    assert apply_response.status_code == 200
    accepted = apply_response.json()["correction_report"]["accepted_entries"]
    assert accepted[0]["kind"] == "manual_matching_answer_key"


def test_correction_source_state_issue_route_rejects_caller_supplied_forged_state(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    job_id = _seed_source_state_job(client)
    issue_payload = _source_state_issue_payload(job_id)
    forged_apply_payload = _request_payload()
    source_state = forged_apply_payload["source_authoring_state"]
    assert isinstance(source_state, dict)
    items = source_state["items"]
    assert isinstance(items, list)
    item = items[0]
    assert isinstance(item, dict)
    interactions = item["matching_interactions"]
    assert isinstance(interactions, list)
    interaction = interactions[0]
    assert isinstance(interaction, dict)
    source_choices = interaction["source_choices"]
    assert isinstance(source_choices, list)
    choice = source_choices[0]
    assert isinstance(choice, dict)
    choice["choice_id"] = "browser-local-source"
    issue_payload["source_authoring_state"] = source_state

    issue_response = client.post(_ISSUE_ROUTE, headers=_API_HEADERS, json=issue_payload)

    assert issue_response.status_code == 422
    error = issue_response.json()["error"]
    assert error["code"] == "validation_error"
    assert "browser-local-source" not in issue_response.text


def test_corrections_apply_route_rejects_mutated_source_state_digest(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    source_state = payload["source_authoring_state"]
    assert isinstance(source_state, dict)
    items = source_state["items"]
    assert isinstance(items, list)
    item = items[0]
    assert isinstance(item, dict)
    interactions = item["matching_interactions"]
    assert isinstance(interactions, list)
    interaction = interactions[0]
    assert isinstance(interaction, dict)
    source_choices = interaction["source_choices"]
    assert isinstance(source_choices, list)
    choice = source_choices[0]
    assert isinstance(choice, dict)
    choice["choice_id"] = "browser-local-source"
    corrections = payload["corrections"]
    assert isinstance(corrections, list)
    correction = corrections[0]
    assert isinstance(correction, dict)
    correction["pairs"] = [{"source_id": "browser-local-source", "target_id": "target-001"}]

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "stale_exam_authoring_source_state_digest"
    assert "browser-local-source" not in response.text


def test_corrections_apply_route_rejects_forged_source_state_authority(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    source_state = payload["source_authoring_state"]
    assert isinstance(source_state, dict)
    items = source_state["items"]
    assert isinstance(items, list)
    item = items[0]
    assert isinstance(item, dict)
    interactions = item["matching_interactions"]
    assert isinstance(interactions, list)
    interaction = interactions[0]
    assert isinstance(interaction, dict)
    source_choices = interaction["source_choices"]
    assert isinstance(source_choices, list)
    choice = source_choices[0]
    assert isinstance(choice, dict)
    choice["choice_id"] = "browser-local-source"
    correction = _first_correction(payload)
    correction["pairs"] = [{"source_id": "browser-local-source", "target_id": "target-001"}]
    _refresh_source_state_digest(payload, refresh_signature=False)

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "stale_exam_authoring_source_state_authority"
    assert "browser-local-source" not in response.text


def test_corrections_apply_route_fails_closed_on_missing_source_fingerprint(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    corrections = payload["corrections"]
    assert isinstance(corrections, list)
    correction = corrections[0]
    assert isinstance(correction, dict)
    correction.pop("source_item_fingerprint")

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "stale_correction_source_item_fingerprint"
    assert error["details"] == {
        "submitted_source_item_fingerprint": None,
        "expected_source_item_fingerprint": "sha256:item-001",
    }


def test_corrections_apply_route_rejects_unknown_pairs_before_target_readiness(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    corrections = payload["corrections"]
    assert isinstance(corrections, list)
    correction = corrections[0]
    assert isinstance(correction, dict)
    correction["pairs"] = [{"source_id": "source-404", "target_id": "target-001"}]

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "exam_authoring_matching_manual_answer_key_rejected"
    issues = error["details"]["issues"]
    assert {
        "reason_code": "unknown_matching_source_id",
        "message": "Matching key references an unknown source choice.",
        "source_id": "source-404",
        "target_id": "target-001",
    } in issues
    assert {
        "reason_code": "matching_source_association_limit_exceeded",
        "message": "Matching key violates source choice association bounds.",
        "source_id": "source-001",
        "target_id": None,
    } in issues


def test_corrections_apply_route_accepts_advisory_candidate_digest_match(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    correction = _first_correction(payload)
    correction["submission_origin"] = "accepted_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest=_matching_candidate_digest(
            [{"source_id": "source-001", "target_id": "target-001"}]
        )
    )

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    accepted = response.json()["correction_report"]["accepted_entries"]
    assert accepted[0]["effective_provenance"] == "reviewed"


def test_corrections_apply_route_rejects_advisory_candidate_digest_mismatch(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    correction = _first_correction(payload)
    correction["submission_origin"] = "accepted_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest="sha256:wrong-candidate-payload"
    )

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "advisory_candidate_payload_digest_mismatch"
    assert error["details"]["candidate_id"] == "candidate-item-001"
    assert "source-001" not in response.text
    assert "target-001" not in response.text


def test_corrections_apply_route_allows_teacher_edited_advisory_candidate_digest_drift(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    correction = _first_correction(payload)
    correction["submission_origin"] = "teacher_edited_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest="sha256:original-advisory-candidate"
    )

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    accepted = response.json()["correction_report"]["accepted_entries"]
    assert accepted[0]["effective_provenance"] == "teacher_provided"


def test_corrections_apply_route_rejects_missing_advisory_lineage_without_raw_input(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    correction = _first_correction(payload)
    correction["submission_origin"] = "accepted_advisory_candidate"

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert '"input"' not in response.text
    assert "source-001" not in response.text
    assert "target-001" not in response.text


def test_corrections_apply_route_reports_unsupported_candidate_suppression_entries(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    payload["corrections"] = [
        {
            "entry_id": "corr-suppression-001",
            "kind": "candidate_suppression",
            "item_id": "item-001",
            "sequence": 1,
            "item_type": "matching",
            "source_item_fingerprint": "sha256:item-001",
            "candidate_lineage": _candidate_lineage(
                candidate_payload_digest="sha256:suppressed-candidate"
            ),
            "suppression_reason": "teacher_rejected_candidate",
        }
    ]

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["correction_report"]["accepted_entries"] == []
    assert payload["correction_report"]["rejected_entries"] == [
        {
            "entry_id": "corr-suppression-001",
            "kind": "candidate_suppression",
            "item_id": "item-001",
            "sequence": 1,
            "reason_code": "correction_kind_not_supported_in_initial_unified_route",
            "message_key": "exam_authoring.corrections.unsupported_in_initial_runtime",
            "teacher_action": "wait_for_supported_runtime_slice",
            "retryable": False,
        }
    ]
    assert payload["target_readiness"]["targets"] == []
    assert payload["artifact_availability"] == []


def test_corrections_apply_route_blocks_artifacts_for_mixed_rejected_batch(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    corrections = payload["corrections"]
    assert isinstance(corrections, list)
    corrections.append(
        {
            "entry_id": "corr-suppression-001",
            "kind": "candidate_suppression",
            "item_id": "item-001",
            "sequence": 1,
            "item_type": "matching",
            "source_item_fingerprint": "sha256:item-001",
            "candidate_lineage": _candidate_lineage(
                candidate_payload_digest="sha256:suppressed-candidate"
            ),
            "suppression_reason": "teacher_rejected_candidate",
        }
    )

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["correction_report"]["accepted_entries"] == []
    assert response_payload["correction_report"]["rejected_entries"] == [
        {
            "entry_id": "corr-matching-001",
            "kind": "manual_matching_answer_key",
            "item_id": "item-001",
            "sequence": 1,
            "reason_code": "correction_batch_contains_rejected_entries",
            "message_key": "exam_authoring.corrections.batch_contains_rejected_entries",
            "teacher_action": "resolve_rejected_entries_and_retry_batch",
            "retryable": True,
        },
        {
            "entry_id": "corr-suppression-001",
            "kind": "candidate_suppression",
            "item_id": "item-001",
            "sequence": 1,
            "reason_code": "correction_kind_not_supported_in_initial_unified_route",
            "message_key": "exam_authoring.corrections.unsupported_in_initial_runtime",
            "teacher_action": "wait_for_supported_runtime_slice",
            "retryable": False,
        },
    ]
    assert response_payload["target_readiness"]["targets"] == []
    assert response_payload["artifact_availability"] == []
    effective_interaction = response_payload["effective_state"]["items"][0][
        "matching_interactions"
    ][0]
    assert effective_interaction["answer_key"] == {"provenance": "absent", "pairs": []}
