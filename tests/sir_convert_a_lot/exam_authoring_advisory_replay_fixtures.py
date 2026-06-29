"""Fixtures for advisory candidate preservation replay tests.

Purpose:
    Build sanitized correction-apply payloads and DigiExam source fixtures for
    Task 374 advisory candidate preservation tests.

Relationships:
    - Feeds route tests in
      `test_exam_authoring_correction_apply_advisory_replay`.
    - Reuses correction apply digest helpers so source-state signatures match
      runtime validation.
"""

from __future__ import annotations

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    answer_key_candidate_payload_digest,
)
from tests.sir_convert_a_lot.exam_authoring_corrections_apply_fixtures import (
    candidate_lineage,
    refresh_source_state_digest,
)


def apply_payload_with_advisory_candidates() -> dict[str, object]:
    """Return a signed source-state apply payload with advisory siblings."""

    payload: dict[str, object] = {
        "schema_version": "exam_authoring_corrections_apply_request_v1",
        "request_id": "correction-request-preserve-advisory-siblings",
        "source_binding": {
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_state_sha256": "sha256:placeholder",
            "source_state_signature": "hmac-sha256:placeholder",
            "source_bundle_id": "bundle-preserve-advisory",
            "source_file_sha256": "sha256:source-file",
        },
        "source_authoring_state": {
            "schema_version": "exam_authoring_correction_source_state_v1",
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_state_sha256": "sha256:placeholder",
            "items": [
                _choice_item(item_id="choice-accept", sequence=1),
                _choice_item(item_id="choice-pending", sequence=2),
                _gap_item(item_id="gap-pending", sequence=3, item_type="gap_fill"),
                _gap_item(item_id="open-cloze-pending", sequence=4, item_type="open_cloze"),
                _choice_item(item_id="choice-missing", sequence=5),
                _free_writing_item(),
            ],
            "advisory_answer_key_candidates": [
                _candidate("choice-accept", 1, choice_digest([2])),
                _candidate("choice-pending", 2, choice_digest([1])),
                _candidate("gap-pending", 3, gap_digest("gap-pending-gap-1", "fotosyntes")),
                _candidate(
                    "open-cloze-pending",
                    4,
                    gap_digest("open-cloze-pending-gap-1", "cellandning"),
                ),
                _candidate("free-writing", 6, choice_digest([2])),
            ],
        },
        "corrections": [
            {
                "entry_id": "corr-choice-accept",
                "kind": "manual_choice_answer_key",
                "item_id": "choice-accept",
                "sequence": 1,
                "item_type": "single_choice",
                "source_item_fingerprint": "sha256:choice-accept",
                "interaction_id": "choice-choice-accept",
                "submission_origin": "accepted_advisory_candidate",
                "correct_choice_ids": ["choice-002"],
                "candidate_lineage": candidate_lineage(candidate_payload_digest=choice_digest([2])),
            }
        ],
        "requested_targets": ["examnet_pdf", "qti_package"],
    }
    refresh_source_state_digest(payload)
    return payload


def expected_detail(item_id: str) -> dict[str, str]:
    """Return expected bounded pending advisory provenance detail."""

    return {
        "candidate_id": f"candidate-{item_id}",
        "candidate_payload_digest": {
            "choice-pending": choice_digest([1]),
            "gap-pending": gap_digest("gap-pending-gap-1", "fotosyntes"),
            "open-cloze-pending": gap_digest("open-cloze-pending-gap-1", "cellandning"),
        }[item_id],
        "provider_profile_id": "local-structured",
        "schema_name": "digiexam_answer_key_decision_v1",
        "schema_version": "digiexam_answer_key_decision_v1",
        "prompt_template_version": "digiexam_answer_key_prompt_v1",
        "validation_state": "valid",
    }


def multi_missing_choice_payload() -> dict[str, object]:
    """Return a DigiExam-like source with three missing choice keys."""

    return {
        "exams": [
            {
                "questions": [
                    _digiexam_missing_choice(question_id=1, title="Single one"),
                    _digiexam_missing_choice(question_id=2, title="Single two"),
                    _digiexam_missing_choice(question_id=3, title="Single three"),
                ]
            }
        ]
    }


def choice_digest(correct_ids: list[int]) -> str:
    """Return the canonical advisory digest for a choice candidate."""

    correct_alternative_ids: list[JsonValue] = [choice_id for choice_id in correct_ids]
    return answer_key_candidate_payload_digest(
        {"kind": "choice", "correct_alternative_ids": correct_alternative_ids}
    )


def gap_digest(gap_id: str, accepted_value: str) -> str:
    """Return the canonical advisory digest for a gap/open-cloze candidate."""

    return answer_key_candidate_payload_digest(
        {
            "kind": "gap_fill",
            "gap_answers": [{"gap_id": gap_id, "accepted_values": [accepted_value]}],
        }
    )


def _choice_item(*, item_id: str, sequence: int) -> dict[str, object]:
    return {
        "item_id": item_id,
        "sequence": sequence,
        "item_type": "single_choice",
        "source_item_fingerprint": f"sha256:{item_id}",
        "max_score": 1,
        "choice_interactions": [
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": f"choice-{item_id}",
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


def _gap_item(*, item_id: str, sequence: int, item_type: str) -> dict[str, object]:
    gap_id = f"{item_id}-gap-1"
    return {
        "item_id": item_id,
        "sequence": sequence,
        "item_type": item_type,
        "source_item_fingerprint": f"sha256:{item_id}",
        "max_score": 1,
        "gap_open_cloze_interactions": [
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": f"gap-{item_id}",
                "gaps": [
                    {
                        "gap_id": gap_id,
                        "display_order": 1,
                        "prompt_binding": {
                            "kind": "html_attribute",
                            "locator": f"data-gap-id={gap_id}",
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


def _free_writing_item() -> dict[str, object]:
    return {
        "item_id": "free-writing",
        "sequence": 6,
        "item_type": "free_text",
        "source_item_fingerprint": "sha256:free-writing",
        "max_score": 4,
    }


def _digiexam_missing_choice(*, question_id: int, title: str) -> dict[str, object]:
    return {
        "id": question_id,
        "title": title,
        "about": "",
        "bodyHTML": "<p>Choose the Greek letter.</p>",
        "images": [],
        "maxScore": 2,
        "type": 1,
        "alternatives": [
            {"id": 1, "title": "Alpha", "about": "", "right": False},
            {"id": 2, "title": "Beta", "about": "", "right": False},
        ],
    }


def _candidate(item_id: str, sequence: int, digest: str) -> dict[str, object]:
    return {
        "item_id": item_id,
        "sequence": sequence,
        "candidate_id": f"candidate-{item_id}",
        "candidate_payload_digest": digest,
        "provider_profile_id": "local-structured",
        "schema_name": "digiexam_answer_key_decision_v1",
        "schema_version": "digiexam_answer_key_decision_v1",
        "prompt_template_version": "digiexam_answer_key_prompt_v1",
        "validation_state": "valid",
    }
