"""Focused migration-manifest projection tests for answer-key completion."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.answer_key_token_lease_contracts import (
    AnswerKeyTokenLeaseError,
    AnswerKeyTokenLeaseFailureCode,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)
from tests.sir_convert_a_lot.exam.digiexam_migration_bundle_api_fixtures import (
    _client,
    _headers,
    _IdentitySigner,
    _missing_answer_key_payload,
    _post_digiexam_job,
    _read_grants,
    _structured_llm_config,
)


@pytest.mark.parametrize(
    ("failure_code", "expected_status"),
    (
        (
            AnswerKeyTokenLeaseFailureCode.DAILY_TOKEN_LEASE_EXHAUSTED,
            "daily_token_lease_exhausted",
        ),
        (
            AnswerKeyTokenLeaseFailureCode.TOKEN_LEASE_LEDGER_UNAVAILABLE,
            "token_lease_ledger_unavailable",
        ),
    ),
)
def test_manifest_projects_lease_failure_without_blocking_deterministic_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_code: AnswerKeyTokenLeaseFailureCode,
    expected_status: str,
) -> None:
    async def lease_refusal(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self, request, profile
        raise AnswerKeyTokenLeaseError(
            failure_code=failure_code,
            message="Token lease unavailable.",
            utc_day="2026-08-29",
            requested_tokens=100,
            available_tokens=0,
        )

    monkeypatch.setattr(HttpStructuredChatProvider, "complete_structured_chat", lease_refusal)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, structured_llm=_structured_llm_config())
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-lease-status",
        idempotency_key=f"idem-{failure_code.value}",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        completion_mode="local_llm_suggest_missing_machine_marked",
        targets=("examnet_pdf",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-lease-status", grants=_read_grants())
    artifact_manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in artifact_manifest["artifacts"]}
    assert entries["ir_json"]["availability"] == "available"
    assert entries["migration_manifest"]["availability"] == "available"
    assert artifact_manifest["answer_key_completion"] == {
        "artifact_key": "answer_key_completion_report",
        "status": expected_status,
        "failure_codes": [failure_code.value],
    }


def test_source_evidence_mode_keeps_completion_not_requested(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-source-evidence",
        idempotency_key="idem-source-evidence",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        targets=("examnet_pdf",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-source-evidence", grants=_read_grants())
    artifact_manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()

    entries = {entry["artifact_key"]: entry for entry in artifact_manifest["artifacts"]}
    assert entries["answer_key_completion_report"]["availability"] == "not_requested"
    assert artifact_manifest["answer_key_completion"] == {
        "artifact_key": "answer_key_completion_report",
        "status": "not_requested",
        "failure_codes": [],
    }
