"""Tests for the source-neutral matching apply route.

Purpose:
    Prove Task 324 exposes a request-body route for applying matching manual
    answer keys and returns producer-owned effective/readiness state.

Relationships:
    - Exercises `interfaces.http_routes_exam_authoring_matching_v2`.
    - Reuses the Task 323 `ExamAuthoringMatchingManualAnswerKey` DTO.
    - Keeps matching submit separate from DigiExam ingestion overlays.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_HEADERS = {
    "X-API-Key": "secret-key",
    "X-Correlation-ID": "corr_matching_apply_v2",
}
_ROUTE = "/v2/exam-authoring/matching/manual-answer-key/apply"


def test_matching_apply_route_returns_effective_state_and_readiness(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(_ROUTE, headers=_API_HEADERS, json=_request_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "exam_authoring_matching_apply_result_v1"
    assert payload["effective_interaction"]["answer_key"] == {
        "provenance": "teacher_provided",
        "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
    }
    assert payload["effective_interaction"]["source_item_fingerprint"] == "sha256:item-001"
    assert payload["target_readiness"] == [
        {
            "target": "examnet_pdf",
            "readiness": "ready",
            "export_enabled": True,
            "reason_code": "ready",
            "message_key": "exam_converter.target.matching.ready",
        },
        {
            "target": "qti_package",
            "readiness": "unsupported_target_shape",
            "export_enabled": False,
            "reason_code": "examnet_qti_matching_import_unproven",
            "message_key": "exam_converter.target.matching.qti_import_unproven",
        },
    ]
    assert payload["artifact_availability"] == [
        {
            "artifact_key": "examnet_pdf",
            "availability": "available",
            "unavailable_code": None,
        },
        {
            "artifact_key": "qti_package",
            "availability": "unavailable",
            "unavailable_code": "examnet_qti_matching_import_unproven",
        },
    ]


def test_matching_apply_route_fails_closed_on_missing_source_fingerprint(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    matching_key = payload["exam_authoring_matching_manual_answer_key"]
    if isinstance(matching_key, dict):
        matching_key.pop("source_item_fingerprint")

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "stale_matching_source_item_fingerprint"
    assert error["details"] == {
        "submitted_source_item_fingerprint": None,
        "expected_source_item_fingerprint": "sha256:item-001",
    }


def test_matching_apply_route_allows_unfingerprinted_neutral_interactions(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    source_interaction = payload["source_interaction"]
    matching_key = payload["exam_authoring_matching_manual_answer_key"]
    if isinstance(source_interaction, dict):
        source_interaction.pop("source_item_fingerprint")
    if isinstance(matching_key, dict):
        matching_key.pop("source_item_fingerprint")

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    assert response.json()["effective_interaction"]["source_item_fingerprint"] is None


def test_matching_apply_route_rejects_unknown_pairs_before_target_readiness(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    matching_key = payload["exam_authoring_matching_manual_answer_key"]
    if isinstance(matching_key, dict):
        matching_key["answer_key"] = {
            "provenance": "teacher_provided",
            "pairs": [{"source_id": "source-404", "target_id": "target-001"}],
        }

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


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    return TestClient(app)


def _request_payload() -> dict[str, object]:
    return {
        "source_interaction": {
            "schema_version": "exam_authoring_ir_v1",
            "interaction_id": "matching-001",
            "source_item_fingerprint": "sha256:item-001",
            "source_choices": [
                {
                    "choice_id": "source-001",
                    "order": 1,
                    "text": "Source term",
                    "match_min": 1,
                    "match_max": 1,
                }
            ],
            "target_choices": [
                {
                    "choice_id": "target-001",
                    "order": 1,
                    "text": "Target explanation",
                    "match_min": 0,
                    "match_max": 1,
                },
                {
                    "choice_id": "target-002",
                    "order": 2,
                    "text": "Distraktor",
                    "match_min": 0,
                    "match_max": 1,
                },
            ],
            "min_associations": 1,
            "max_associations": 1,
            "answer_key": {
                "provenance": "absent",
                "pairs": [],
            },
            "evidence": [
                {
                    "source_family": "examnet_pdf",
                    "source_id": "item-001",
                    "locator": "page=1",
                }
            ],
        },
        "exam_authoring_matching_manual_answer_key": {
            "schema_version": "exam_authoring_ir_v1",
            "kind": "matching",
            "interaction_id": "matching-001",
            "source_item_fingerprint": "sha256:item-001",
            "answer_key": {
                "provenance": "teacher_provided",
                "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
            },
        },
        "requested_targets": ["examnet_pdf", "qti_package"],
    }
