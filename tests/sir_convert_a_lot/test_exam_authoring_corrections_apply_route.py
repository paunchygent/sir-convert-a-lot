"""Tests for the unified exam authoring corrections apply route.

Purpose:
    Prove Task 330 exposes the unified source-neutral correction route, applies
    matching manual keys through it, and stops accepting the superseded Task 324
    matching-specific route.

Relationships:
    - Exercises `interfaces.http_routes_exam_authoring_corrections_v2`.
    - Reuses the Task 323 matching DTO/domain validation through the unified
      `manual_matching_answer_key` entry.
    - Protects ADR-0011's no-adapter/no-bridge hard cut.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_HEADERS = {
    "X-API-Key": "secret-key",
    "X-Correlation-ID": "corr_corrections_apply_v2",
}
_ROUTE = "/v2/exam-authoring/corrections/apply"
_OLD_ROUTE = "/v2/exam-authoring/matching/manual-answer-key/apply"


def test_corrections_apply_route_returns_effective_matching_state_and_readiness(
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
    assert payload["target_readiness"]["targets"] == [
        {
            "target": "examnet_pdf",
            "readiness": "ready",
            "export_enabled": True,
            "reason_code": "ready",
            "message_key": "exam_converter.target.matching.ready",
            "item_id": "item-001",
            "sequence": 1,
        },
        {
            "target": "qti_package",
            "readiness": "unsupported_target_shape",
            "export_enabled": False,
            "reason_code": "examnet_qti_matching_import_unproven",
            "message_key": "exam_converter.target.matching.qti_import_unproven",
            "item_id": "item-001",
            "sequence": 1,
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


def test_corrections_apply_route_reports_unsupported_non_matching_entries(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    payload["corrections"] = [
        {
            "entry_id": "corr-points-001",
            "kind": "point_correction",
            "item_id": "item-001",
            "sequence": 1,
            "item_type": "matching",
            "source_item_fingerprint": "sha256:item-001",
            "max_score": 2,
        }
    ]

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["correction_report"]["accepted_entries"] == []
    assert payload["correction_report"]["rejected_entries"] == [
        {
            "entry_id": "corr-points-001",
            "kind": "point_correction",
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


def test_superseded_task_324_matching_route_is_not_accepted(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(_OLD_ROUTE, headers=_API_HEADERS, json={})

    assert response.status_code == 404


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
        "schema_version": "exam_authoring_corrections_apply_request_v1",
        "request_id": "correction-request-001",
        "source_binding": {
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_state_sha256": "sha256:source-state",
            "source_bundle_id": "bundle-001",
            "source_file_sha256": "sha256:source-file",
        },
        "source_authoring_state": {
            "schema_version": "exam_authoring_correction_source_state_v1",
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_state_sha256": "sha256:source-state",
            "items": [
                {
                    "item_id": "item-001",
                    "sequence": 1,
                    "item_type": "matching",
                    "source_item_fingerprint": "sha256:item-001",
                    "matching_interactions": [
                        {
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
                        }
                    ],
                }
            ],
        },
        "corrections": [
            {
                "entry_id": "corr-matching-001",
                "kind": "manual_matching_answer_key",
                "item_id": "item-001",
                "sequence": 1,
                "item_type": "matching",
                "source_item_fingerprint": "sha256:item-001",
                "interaction_id": "matching-001",
                "submission_origin": "teacher_authored",
                "pairs": [{"source_id": "source-001", "target_id": "target-001"}],
            }
        ],
        "requested_targets": ["examnet_pdf", "qti_package"],
    }
