"""Tests for non-matching correction apply runtime non-matching correction apply runtime.

Purpose:
    Prove DigiExam-backed point, choice, gap/open-cloze, and item-text
    corrections apply through the unified source-neutral correction route.

Relationships:
    - Exercises `application.exam_authoring_non_matching_corrections` through
      the FastAPI v2 route.
    - Reuses signed source-state helpers from the unified apply route fixtures.
    - Protects PR-0332 sequencing while matching remains blocked on matching correction block.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    answer_key_candidate_payload_digest,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    API_HEADERS as _API_HEADERS,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    ROUTE as _ROUTE,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    build_client as _client,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    candidate_lineage as _candidate_lineage,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    refresh_source_state_digest as _refresh_source_state_digest,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    request_payload as _request_payload,
)


def test_non_matching_entries_apply_and_recompute_effective_state(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = _non_matching_payload(
        [
            _item_text_patch(),
            _point_correction(),
            _choice_answer_key(),
            _gap_answer_key(),
        ]
    )

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    result = response.json()
    accepted = result["correction_report"]["accepted_entries"]
    assert [entry["kind"] for entry in accepted] == [
        "item_text_patch",
        "point_correction",
        "manual_choice_answer_key",
        "manual_gap_open_cloze_answer_key",
    ]
    assert result["correction_report"]["rejected_entries"] == []
    choice_item = _result_item(result, "item-choice")
    assert choice_item["title"] == "Repaired title"
    assert choice_item["prompt_html"] == "<p>Repaired prompt</p>"
    assert choice_item["prompt_lines"] == ["Repaired prompt"]
    assert choice_item["max_score"] == 4
    choice_interaction = _first_mapping(choice_item["choice_interactions"])
    choices = choice_interaction["choices"]
    assert isinstance(choices, list)
    choice = choices[1]
    assert isinstance(choice, dict)
    assert choice["text"] == "Repaired option"
    assert choice_interaction["answer_key"] == {
        "provenance": "teacher_provided",
        "correct_choice_ids": ["choice-002"],
    }
    gap_item = _result_item(result, "item-gap")
    gap_interaction = _first_mapping(gap_item["gap_open_cloze_interactions"])
    assert gap_interaction["answer_key"] == {
        "provenance": "teacher_provided",
        "accepted_values": [
            {
                "gap_id": "gap-1",
                "value": "fotosyntes",
                "provenance": "teacher_provided",
                "evidence": [],
            }
        ],
    }
    assert all(row["readiness"] == "ready" for row in result["target_readiness"]["targets"])
    assert all(row["availability"] == "available" for row in result["artifact_availability"])


def test_non_matching_choice_advisory_candidate_digest_mismatch_rejected(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    correction = _choice_answer_key()
    correction["submission_origin"] = "accepted_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest="sha256:not-the-choice-payload"
    )
    payload = _non_matching_payload([correction])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "advisory_candidate_payload_digest_mismatch"
    assert "Repaired option" not in response.text


def test_non_matching_gap_teacher_edited_candidate_allows_digest_drift(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    correction = _gap_answer_key()
    correction["submission_origin"] = "teacher_edited_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest="sha256:original-gap-candidate"
    )
    payload = _non_matching_payload([correction])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    accepted = response.json()["correction_report"]["accepted_entries"]
    assert accepted[0]["effective_provenance"] == "teacher_provided"


def test_non_matching_unknown_nested_ids_reject_before_readiness(tmp_path: Path) -> None:
    client = _client(tmp_path)
    correction = _choice_answer_key()
    correction["correct_choice_ids"] = ["choice-404"]
    payload = _non_matching_payload([correction])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "unknown_choice_answer_id"
    assert "Alpha" not in response.text
    assert "Beta" not in response.text


def test_non_matching_mixed_unsupported_batch_fails_closed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = _non_matching_payload([_point_correction(), _candidate_suppression()])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["correction_report"]["accepted_entries"] == []
    assert [entry["reason_code"] for entry in result["correction_report"]["rejected_entries"]] == [
        "correction_batch_contains_rejected_entries",
        "correction_kind_not_supported_in_initial_unified_route",
    ]
    assert _result_item(result, "item-choice")["max_score"] == 2
    assert result["target_readiness"]["targets"] == []
    assert result["artifact_availability"] == []


def test_non_matching_choice_advisory_candidate_digest_match_is_reviewed(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    correction = _choice_answer_key()
    correction["submission_origin"] = "accepted_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest=answer_key_candidate_payload_digest(
            {"kind": "choice", "correct_alternative_ids": [2]}
        )
    )
    payload = _non_matching_payload([correction])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    accepted = response.json()["correction_report"]["accepted_entries"]
    assert accepted[0]["effective_provenance"] == "reviewed"


def test_non_matching_gap_advisory_candidate_digest_mismatch_rejected(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    correction = _gap_answer_key()
    correction["submission_origin"] = "accepted_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest=answer_key_candidate_payload_digest(
            {
                "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
                "kind": "gap_fill",
            }
        )
    )
    correction["gap_answers"] = [{"gap_id": "gap-1", "accepted_values": ["cellandning"]}]
    payload = _non_matching_payload([correction])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "advisory_candidate_payload_digest_mismatch"


def test_non_matching_gap_advisory_candidate_digest_match_is_reviewed(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    correction = _gap_answer_key()
    correction["submission_origin"] = "accepted_advisory_candidate"
    correction["candidate_lineage"] = _candidate_lineage(
        candidate_payload_digest=answer_key_candidate_payload_digest(
            {
                "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
                "kind": "gap_fill",
            }
        )
    )
    payload = _non_matching_payload([correction])

    response = client.post(_ROUTE, headers=_API_HEADERS, json=payload)

    assert response.status_code == 200
    accepted = response.json()["correction_report"]["accepted_entries"]
    assert accepted[0]["effective_provenance"] == "reviewed"


def _non_matching_payload(corrections: list[dict[str, object]]) -> dict[str, object]:
    payload = _request_payload()
    payload["source_authoring_state"] = {
        "schema_version": "exam_authoring_correction_source_state_v1",
        "source_authoring_schema_version": "exam_authoring_ir_v1",
        "source_state_sha256": "sha256:placeholder",
        "items": [_choice_source_item(), _gap_source_item()],
    }
    payload["source_binding"] = {
        "source_authoring_schema_version": "exam_authoring_ir_v1",
        "source_state_sha256": "sha256:placeholder",
        "source_state_signature": "hmac-sha256:placeholder",
        "source_bundle_id": "bundle-non-matching",
        "source_file_sha256": "sha256:source-file",
    }
    payload["corrections"] = corrections
    _refresh_source_state_digest(payload)
    return payload


def _choice_source_item() -> dict[str, object]:
    return {
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "title": "Original title",
        "prompt_html": "<p>Original prompt</p>",
        "prompt_lines": ["Original prompt"],
        "max_score": 2,
        "choice_interactions": [
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": "choice-item-choice",
                "interaction_kind": "single_choice",
                "choices": [
                    {"choice_id": "choice-001", "order": 1, "source_id": "1", "text": "Alpha"},
                    {"choice_id": "choice-002", "order": 2, "source_id": "2", "text": "Beta"},
                ],
                "min_correct_choices": 1,
                "max_correct_choices": 1,
                "answer_key": {"provenance": "absent", "correct_choice_ids": []},
                "evidence": [],
            }
        ],
    }


def _gap_source_item() -> dict[str, object]:
    return {
        "item_id": "item-gap",
        "sequence": 2,
        "item_type": "gap_fill",
        "source_item_fingerprint": "sha256:item-gap",
        "title": "Gap title",
        "prompt_html": "<p>Fotosyntes sker i ____.</p>",
        "prompt_lines": ["Fotosyntes sker i ____."],
        "max_score": 1,
        "gap_open_cloze_interactions": [
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": "gap-item-gap",
                "gaps": [
                    {
                        "gap_id": "gap-1",
                        "display_order": 1,
                        "prompt_binding": {
                            "kind": "html_attribute",
                            "locator": "data-gap-id=gap-1",
                        },
                        "required_for_auto_evaluation": True,
                        "evidence": [],
                    }
                ],
                "normalization_profile": "exact_trim_case_sensitive",
                "answer_key": {"provenance": "absent", "accepted_values": []},
                "evidence": [],
            }
        ],
    }


def _item_text_patch() -> dict[str, object]:
    return {
        "entry_id": "corr-text-001",
        "kind": "item_text_patch",
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "patches": [
            {"field": "item_title", "value": "Repaired title"},
            {"field": "prompt_html", "value": "<p>Repaired prompt</p>"},
            {"field": "prompt_lines", "value": "Repaired prompt"},
            {
                "field": "visible_option_text",
                "choice_id": "choice-002",
                "value": "Repaired option",
            },
        ],
    }


def _point_correction() -> dict[str, object]:
    return {
        "entry_id": "corr-point-001",
        "kind": "point_correction",
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "max_score": 4,
    }


def _choice_answer_key() -> dict[str, object]:
    return {
        "entry_id": "corr-choice-001",
        "kind": "manual_choice_answer_key",
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "interaction_id": "choice-item-choice",
        "submission_origin": "teacher_authored",
        "correct_choice_ids": ["choice-002"],
    }


def _gap_answer_key() -> dict[str, object]:
    return {
        "entry_id": "corr-gap-001",
        "kind": "manual_gap_open_cloze_answer_key",
        "item_id": "item-gap",
        "sequence": 2,
        "item_type": "gap_fill",
        "source_item_fingerprint": "sha256:item-gap",
        "interaction_id": "gap-item-gap",
        "submission_origin": "teacher_authored",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["fotosyntes"]}],
    }


def _candidate_suppression() -> dict[str, object]:
    return {
        "entry_id": "corr-suppression-001",
        "kind": "candidate_suppression",
        "item_id": "item-choice",
        "sequence": 1,
        "item_type": "single_choice",
        "source_item_fingerprint": "sha256:item-choice",
        "candidate_lineage": _candidate_lineage(
            candidate_payload_digest="sha256:suppressed-candidate"
        ),
        "suppression_reason": "teacher_rejected_candidate",
    }


def _result_item(result: dict[str, object], item_id: str) -> dict[str, object]:
    effective_state = result["effective_state"]
    assert isinstance(effective_state, dict)
    items = effective_state["items"]
    assert isinstance(items, list)
    for item in items:
        assert isinstance(item, dict)
        if item["item_id"] == item_id:
            return item
    raise AssertionError(f"missing result item {item_id}")


def _first_mapping(value: object) -> dict[str, object]:
    assert isinstance(value, list)
    first = value[0]
    assert isinstance(first, dict)
    return first
