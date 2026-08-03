"""Hard-cut and validation privacy tests for correction apply routes.

Purpose:
    Keep the unified correction route privacy envelope and HTML to PDF route4 route
    removal proof separate from family-specific apply runtime tests.

Relationships:
    - Exercises `interfaces.http_routes_exam_authoring_corrections_v2`.
    - Protects ADR-0011.s route-removal decision.
    - Complements matching and non-matching correction route test modules.
"""

from __future__ import annotations

from pathlib import Path

from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    API_HEADERS as _API_HEADERS,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    OLD_ROUTE as _OLD_ROUTE,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    ROUTE as _ROUTE,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    build_client as _client,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    request_payload as _request_payload,
)


def test_corrections_apply_route_validation_error_does_not_echo_raw_payload(
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
    item["student_result_data"] = "SECRET_STUDENT_ANSWER"

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    response_text = response.text
    assert "SECRET_STUDENT_ANSWER" not in response_text
    assert '"input"' not in response_text
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["errors"][0]["loc"] == [
        "body",
        "source_authoring_state",
        "items",
        0,
        "student_result_data",
    ]


def test_superseded_matching_route_is_not_accepted(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(_OLD_ROUTE, headers=_API_HEADERS, json={})

    assert response.status_code == 404


def test_corrections_apply_rejects_legacy_review_decision_entry(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = _request_payload()
    payload["corrections"] = [
        {
            "entry_id": "corr-review-decision-001",
            "kind": "review_decision",
            "item_id": "item-001",
            "sequence": 1,
            "item_type": "matching",
            "source_item_fingerprint": "sha256:item-001",
            "decision": "accept_current_state_for_export",
        }
    ]

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
