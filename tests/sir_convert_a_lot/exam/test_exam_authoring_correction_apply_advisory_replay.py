"""Correction-apply replay tests for preserved advisory answer-key candidates.

Purpose:
    Prove that source-neutral correction apply keeps first-pass advisory
    answer-key candidates for untouched keyed siblings after one advisory
    candidate is accepted.

Relationships:
    - Exercises the FastAPI correction apply route through the shared source
      binding fixtures.
    - Protects the `digiexam_answer_key_review_state_v1` producer projection
      consumed by Skriptoteket after correction replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state import (
    attach_digiexam_answer_key_review_replay_references,
)
from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state_models import (
    DigiExamAnswerKeyReviewReplayArtifactReferenceV1,
    DigiExamAnswerKeyReviewStateV1,
    DigiExamAnswerKeyReviewTargetReadinessInput,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import DigiExamAnswerKeyCompletionModeV2
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)
from tests.sir_convert_a_lot.exam.digiexam_migration_bundle_api_fixtures import (
    _client as build_digiexam_client,
)
from tests.sir_convert_a_lot.exam.digiexam_migration_bundle_api_fixtures import (
    _headers as digiexam_headers,
)
from tests.sir_convert_a_lot.exam.digiexam_migration_bundle_api_fixtures import (
    _IdentitySigner,
    _missing_answer_key_payload,
    _post_digiexam_job,
    _read_grants,
    _structured_llm_config,
)
from tests.sir_convert_a_lot.exam.exam_authoring_advisory_replay_fixtures import (
    apply_payload_with_advisory_candidates,
    expected_detail,
    multi_missing_choice_payload,
)
from tests.sir_convert_a_lot.exam.exam_authoring_corrections_apply_fixtures import (
    API_HEADERS,
    ROUTE,
    build_client,
    candidate_lineage,
)


def test_apply_preserves_untouched_advisory_candidates_after_sibling_accept(
    tmp_path: Path,
) -> None:
    client = build_client(tmp_path)
    payload = apply_payload_with_advisory_candidates()

    response = client.post(ROUTE, headers=API_HEADERS, json=payload)

    assert response.status_code == 200
    result = response.json()
    review_items = {item["item_id"]: item for item in result["answer_key_review_state"]["items"]}
    accepted = review_items["choice-accept"]
    assert accepted["review_state"] == "review_complete"
    assert accepted["current_key_origin"] == "reviewed_advisory"
    assert accepted["reasons"] == ["reviewed_advisory_accepted"]
    assert accepted["provenance_detail"] is None

    for item_id in ("choice-pending", "gap-pending", "open-cloze-pending"):
        pending = review_items[item_id]
        assert pending["review_state"] == "review_required"
        assert pending["current_key_origin"] == "none"
        assert pending["reasons"] == ["advisory_candidate_pending"]
        assert pending["provenance_detail"] == expected_detail(item_id)

    missing = review_items["choice-missing"]
    assert missing["review_state"] == "validation_required"
    assert missing["current_key_origin"] == "none"
    assert missing["reasons"] == ["no_correct_choice_selected"]
    assert missing["provenance_detail"] is None
    free_writing = review_items["free-writing"]
    assert free_writing["review_state"] == "review_complete"
    assert free_writing["current_key_origin"] == "none"
    assert free_writing["reasons"] == ["answer_key_not_applicable"]
    assert free_writing["provenance_detail"] is None

    rendered = response.text
    assert "raw_provider_prompt" not in rendered
    assert "raw_provider_response" not in rendered
    assert "/Users/" not in rendered
    assert "session-" not in rendered
    assert "credential" not in rendered


def test_replay_reference_attachment_preserves_pending_advisory_sibling_state(
    tmp_path: Path,
) -> None:
    client = build_client(tmp_path)
    payload = apply_payload_with_advisory_candidates()
    response = client.post(ROUTE, headers=API_HEADERS, json=payload)
    assert response.status_code == 200
    review_state = DigiExamAnswerKeyReviewStateV1.model_validate(
        response.json()["answer_key_review_state"]
    )

    replayed = attach_digiexam_answer_key_review_replay_references(
        report=review_state,
        target_readiness=(
            DigiExamAnswerKeyReviewTargetReadinessInput(
                target="examnet_pdf",
                export_enabled=True,
                reason_code="ready",
                item_id="choice-pending",
                sequence=2,
                artifact_key="correction_replay_examnet_pdf",
                artifact_reference=_review_replay_reference(
                    artifact_key="correction_replay_examnet_pdf",
                    target="examnet_pdf",
                    content_sha256="sha256:pdf",
                ),
            ),
            DigiExamAnswerKeyReviewTargetReadinessInput(
                target="qti_package",
                export_enabled=True,
                reason_code="ready",
                item_id="choice-pending",
                sequence=2,
                artifact_key="correction_replay_qti_package",
                artifact_reference=_review_replay_reference(
                    artifact_key="correction_replay_qti_package",
                    target="qti_package",
                    content_sha256="sha256:qti",
                ),
            ),
        ),
    )

    items = {item.item_id: item for item in replayed.items}
    pending = items["choice-pending"]
    assert pending.review_state == "review_required"
    assert pending.current_key_origin == "none"
    assert pending.reasons == ("advisory_candidate_pending",)
    assert pending.provenance_detail is not None
    assert [reference.artifact_key for reference in pending.replay_artifact_references] == [
        "correction_replay_examnet_pdf",
        "correction_replay_qti_package",
    ]
    accepted = items["choice-accept"]
    assert accepted.review_state == "review_complete"
    assert accepted.replay_artifact_references == ()


def _review_replay_reference(
    *,
    artifact_key: str,
    target: str,
    content_sha256: str,
) -> DigiExamAnswerKeyReviewReplayArtifactReferenceV1:
    return DigiExamAnswerKeyReviewReplayArtifactReferenceV1.model_validate(
        {
            "schema_version": "correction_replay_artifact_reference_v1",
            "job_id": "jobv2_review_state",
            "artifact_set_id": "crset_review_state",
            "artifact_key": artifact_key,
            "target": target,
            "content_sha256": content_sha256,
            "request_id": "correction-request-review-state",
            "source_binding_digest": "sha256:source-binding",
            "source_state_sha256": "sha256:source-state",
            "correction_payload_digest": "sha256:correction-payload",
            "target_set_digest": "sha256:target-set",
            "replay_profile_version": "digiexam_correction_replay_v1",
            "created_at": "2026-06-30T00:00:00Z",
        }
    )


def test_source_state_issue_returns_bounded_first_pass_advisory_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self, request, profile
        return StructuredLLMResponse(
            content={
                "decision_state": "answered",
                "correct_alternative_ids": [2],
                "manual_follow_up_code": None,
            },
            finish_reason="stop",
        )

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        advisory_provider_call,
    )
    identity = _IdentitySigner()
    client = build_digiexam_client(
        tmp_path,
        identity,
        structured_llm=_structured_llm_config(),
    )
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-source-state-advisory",
        idempotency_key="idem-source-state-advisory-context",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = digiexam_headers(
        identity,
        subject="teacher-source-state-advisory",
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
    candidates = issued_state["advisory_answer_key_candidates"]
    assert len(candidates) == 1
    [candidate] = candidates
    assert candidate == {
        "item_id": candidate["item_id"],
        "sequence": candidate["sequence"],
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_digest": candidate["candidate_payload_digest"],
        "provider_profile_id": "local-structured",
        "schema_name": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        "schema_version": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        "prompt_template_version": CHOICE_PROMPT_TEMPLATE_VERSION,
        "validation_state": "valid",
    }
    assert candidate["candidate_payload_digest"].startswith("sha256:")
    assert issued["source_binding"]["source_state_sha256"] == issued_state["source_state_sha256"]

    rendered = issue_response.text
    assert "raw_provider_prompt" not in rendered
    assert "raw_provider_response" not in rendered
    assert "source_state_signature" in rendered
    assert "/Users/" not in rendered
    assert "session-" not in rendered
    assert "student" not in rendered


def test_source_state_issue_to_apply_preserves_advisory_siblings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self, request, profile
        return StructuredLLMResponse(
            content={
                "decision_state": "answered",
                "correct_alternative_ids": [2],
                "manual_follow_up_code": None,
            },
            finish_reason="stop",
        )

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        advisory_provider_call,
    )
    identity = _IdentitySigner()
    client = build_digiexam_client(
        tmp_path,
        identity,
        structured_llm=_structured_llm_config(),
    )
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-issue-apply-advisory",
        idempotency_key="idem-issue-apply-advisory-siblings",
        wait_seconds=20,
        payload=multi_missing_choice_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = digiexam_headers(
        identity,
        subject="teacher-issue-apply-advisory",
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
    candidates_by_item = {
        candidate["item_id"]: candidate
        for candidate in issued_state["advisory_answer_key_candidates"]
    }
    assert len(candidates_by_item) == 3
    choice_items = [item for item in issued_state["items"] if item["choice_interactions"]]
    accepted_item = choice_items[0]
    accepted_candidate = candidates_by_item[accepted_item["item_id"]]

    apply_response = client.post(
        "/v2/exam-authoring/corrections/apply",
        headers=headers,
        json={
            "schema_version": "exam_authoring_corrections_apply_request_v1",
            "request_id": "correction-request-issue-apply-advisory-siblings",
            "source_binding": issued["source_binding"],
            "source_authoring_state": issued_state,
            "corrections": [
                {
                    "entry_id": "corr-issue-apply-advisory-accepted",
                    "kind": "manual_choice_answer_key",
                    "item_id": accepted_item["item_id"],
                    "sequence": accepted_item["sequence"],
                    "item_type": accepted_item["item_type"],
                    "source_item_fingerprint": accepted_item["source_item_fingerprint"],
                    "interaction_id": accepted_item["choice_interactions"][0]["interaction_id"],
                    "submission_origin": "accepted_advisory_candidate",
                    "correct_choice_ids": ["choice-002"],
                    "candidate_lineage": candidate_lineage(
                        candidate_payload_digest=accepted_candidate["candidate_payload_digest"]
                    ),
                }
            ],
            "requested_targets": ["examnet_pdf", "qti_package"],
        },
    )

    assert apply_response.status_code == 200
    review_items = {
        item["item_id"]: item for item in apply_response.json()["answer_key_review_state"]["items"]
    }
    accepted_review = review_items[accepted_item["item_id"]]
    assert accepted_review["review_state"] == "review_complete"
    assert accepted_review["current_key_origin"] == "reviewed_advisory"
    assert accepted_review["reasons"] == ["reviewed_advisory_accepted"]
    untouched_ids = {item["item_id"] for item in choice_items[1:]}
    for item_id in untouched_ids:
        pending = review_items[item_id]
        assert pending["review_state"] == "review_required"
        assert pending["current_key_origin"] == "none"
        assert pending["reasons"] == ["advisory_candidate_pending"]
        assert (
            pending["provenance_detail"]["candidate_id"]
            == (candidates_by_item[item_id]["candidate_id"])
        )
