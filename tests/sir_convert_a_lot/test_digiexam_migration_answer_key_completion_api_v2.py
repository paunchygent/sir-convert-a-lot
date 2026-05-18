"""API tests for DigiExam advisory answer-key completion behavior.

Purpose:
    Cover provider routing, advisory reports, review overlays, and vision
    assets for the DigiExam migration answer-key bounded context.

Relationships:
    - Exercises the v2 DigiExam migration route through shared API fixtures.
    - Keeps answer-key behavior out of the general migration bundle route tests.
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    answer_key_candidate_payload_digest,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamOverlayReviewedCompletionOutcome,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import DigiExamAnswerKeyCompletionModeV2
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMImageURLContentPart,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _choice_answer_payload,
    _client,
    _embedded_image_gap_payload,
    _headers,
    _IdentitySigner,
    _missing_answer_key_payload,
    _post_digiexam_job,
    _qwen36_vision_structured_llm_config,
    _read_grants,
    _reviewed_completion_overlay_bytes,
    _runtime_from_client,
    _structured_llm_config,
    _structured_llm_config_with_openai_fallback,
    _wait_for_terminal_job,
)


def test_digiexam_migration_default_artifact_route_does_not_call_structured_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    async def forbidden_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        provider_calls.append(profile.provider_id)
        raise AssertionError(f"Unexpected structured LLM call for {request.item_id}")

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        forbidden_provider_call,
    )
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-default-off",
        idempotency_key="idem-digiexam-bundle-no-llm-default",
        wait_seconds=20,
        targets=("examnet_pdf",),
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(identity, subject="teacher-llm-default-off", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    artifact_entries = {
        entry["artifact_key"]: entry for entry in manifest_response.json()["artifacts"]
    }
    assert artifact_entries["answer_key_completion_report"]["availability"] == "not_requested"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")
    assert provider_calls == []


def test_digiexam_migration_advisory_completion_report_does_not_mutate_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        provider_calls.append(f"{profile.provider_id}:{request.item_id}")
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
    client = _client(tmp_path, identity, structured_llm=_structured_llm_config())
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-advisory",
        idempotency_key="idem-digiexam-advisory-report",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    job_id = response.json()["job"]["job_id"]

    headers = _headers(identity, subject="teacher-llm-advisory", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    artifact_entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert provider_calls == ["local-structured:item-001"]
    assert artifact_entries["answer_key_completion_report"]["availability"] == "available"
    assert artifact_entries["effective_ir_json"]["availability"] == "not_requested"
    assert artifact_entries["examnet_pdf"]["availability"] == "unavailable"
    assert artifact_entries["examnet_pdf"]["unavailable_code"] == "manual_answer_key_required"
    assert artifact_entries["qti_package"]["availability"] == "unavailable"
    assert artifact_entries["qti_package"]["unavailable_code"] == "manual_answer_key_required"
    assert manifest["manual_follow_up"]["required"] is True

    source_ir = client.get(f"/v2/convert/jobs/{job_id}/artifacts/ir_json", headers=headers).json()
    qti_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_validation_report",
        headers=headers,
    ).json()
    completion_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/answer_key_completion_report",
        headers=headers,
    ).json()
    rendered_report = json.dumps(completion_report, ensure_ascii=False, sort_keys=True)

    assert source_ir["items"][0]["answer_key"]["provenance"] == "absent"
    assert qti_report["package_status"] == "blocked"
    assert qti_report["package_sha256"] is None
    assert qti_report["manual_follow_ups"][0]["reason_code"] == "manual_answer_key_required"
    assert completion_report["schema_version"] == ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION
    assert completion_report["items"][0]["decision_state"] == "suggested"
    assert completion_report["items"][0]["answer_payload"] == {
        "kind": "choice",
        "correct_alternative_ids": [2],
    }
    assert completion_report["items"][0]["candidate_payload_digest"].startswith("sha256:")
    assert "Choose the Greek letter" not in rendered_report
    assert "Alpha" not in rendered_report
    assert "Beta" not in rendered_report
    assert "source_provided" not in rendered_report
    assert "teacher_provided" not in rendered_report
    assert "reviewed" not in rendered_report


def test_digiexam_migration_admitted_provider_route_does_not_drift_after_hot_switch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        provider_calls.append(f"{profile.provider_id}:{request.item_id}")
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
    client = _client(
        tmp_path,
        identity,
        structured_llm=_structured_llm_config_with_openai_fallback(),
        run_jobs_on_submit=False,
    )
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-admission",
        idempotency_key="idem-digiexam-admission-route",
        wait_seconds=0,
        payload=_missing_answer_key_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )
    assert response.status_code == 202
    job_id = response.json()["job"]["job_id"]

    settings_headers = _headers(
        identity,
        subject="operator-llm-admission",
        grants={
            "sir-convert:structured-llm-settings:read",
            "sir-convert:structured-llm-settings:write",
        },
    )
    settings_response = client.put(
        "/v2/operator/structured-llm/provider-routing",
        headers=settings_headers,
        json={
            "version": 2,
            "active_provider_profile_id": "openai-gpt-5.4-mini-2026-03-17",
            "allowed_internal_route_classes": ["operator_api_only"],
            "remote_provider_authorized": True,
            "rollout_label": "openai-after-admission",
        },
    )
    assert settings_response.status_code == 200

    runtime_obj = _runtime_from_client(client)
    runtime_obj.run_job_async(job_id)
    _wait_for_terminal_job(runtime_obj, job_id)

    headers = _headers(identity, subject="teacher-llm-admission", grants=_read_grants())
    completion_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/answer_key_completion_report",
        headers=headers,
    ).json()
    rendered_report = json.dumps(completion_report, ensure_ascii=False, sort_keys=True)

    assert provider_calls == ["local-structured:item-001"]
    assert completion_report["provider_lineage"] == {
        "provider_family": "local_structured_llm",
        "provider_profile_id": "local-structured",
        "model": "local-model",
        "endpoint_kind": "chat_completions",
        "output_mode": "json_schema",
        "reasoning_effort": None,
        "text_verbosity": None,
        "settings_version": 1,
        "route_class": "operator_default",
        "route_decision": "active_provider_profile",
        "remote_provider_authorized": True,
    }
    assert "openai-gpt-5.4-mini-2026-03-17" not in rendered_report
    assert "Choose the Greek letter" not in rendered_report
    assert "Beta" not in rendered_report

    second_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-admission",
        idempotency_key="idem-digiexam-admission-route-openai",
        wait_seconds=0,
        payload=_missing_answer_key_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )
    assert second_response.status_code == 202
    second_job_id = second_response.json()["job"]["job_id"]
    runtime_obj.run_job_async(second_job_id)
    _wait_for_terminal_job(runtime_obj, second_job_id)

    second_report = client.get(
        f"/v2/convert/jobs/{second_job_id}/artifacts/answer_key_completion_report",
        headers=headers,
    ).json()
    assert provider_calls == [
        "local-structured:item-001",
        "openai-gpt-5.4-mini-2026-03-17:item-001",
    ]
    assert second_report["provider_lineage"] == {
        "provider_family": "openai_responses",
        "provider_profile_id": "openai-gpt-5.4-mini-2026-03-17",
        "model": "gpt-5.4-mini-2026-03-17",
        "endpoint_kind": "responses",
        "output_mode": "json_schema",
        "reasoning_effort": "none",
        "text_verbosity": "low",
        "settings_version": 2,
        "route_class": "operator_api_only",
        "route_decision": "active_provider_profile",
        "remote_provider_authorized": True,
    }


def test_digiexam_migration_advisory_completion_allows_valid_embedded_image_item(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_image_urls: list[str] = []
    provider_media_root = tmp_path / "provider-media"

    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        del profile
        content_parts = request.user_content_parts
        assert request.max_output_tokens == 4096
        assert len(content_parts) == 2
        image_part = content_parts[1]
        assert isinstance(image_part, StructuredLLMImageURLContentPart)
        provider_image_urls.append(image_part.url)
        return StructuredLLMResponse(
            content={
                "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild"]}],
            },
            finish_reason="stop",
        )

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        advisory_provider_call,
    )
    identity = _IdentitySigner()
    client = _client(
        tmp_path,
        identity,
        structured_llm=_qwen36_vision_structured_llm_config(
            vision_media_path=provider_media_root,
        ),
    )
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-vision-advisory",
        idempotency_key="idem-digiexam-vision-advisory-report",
        wait_seconds=20,
        payload=_embedded_image_gap_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-vision-advisory", grants=_read_grants())
    completion_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/answer_key_completion_report",
        headers=headers,
    ).json()
    rendered_report = json.dumps(completion_report, ensure_ascii=False, sort_keys=True)

    assert len(provider_image_urls) == 1
    assert provider_image_urls[0].startswith(f"file://{job_id}/item-001/assets/")
    assert provider_image_urls[0].endswith(".png")
    provider_relative_path = provider_image_urls[0].removeprefix("file://")
    assert (provider_media_root / provider_relative_path).is_file()
    assert completion_report["items"][0]["decision_state"] == "suggested"
    assert completion_report["items"][0]["answer_payload"] == {
        "kind": "gap_fill",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild"]}],
    }
    assert "content_base64" not in rendered_report
    assert "iVBORw0KGgo" not in rendered_report


def test_digiexam_migration_vision_provider_without_media_root_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    async def advisory_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        del request
        provider_calls.append(profile.provider_id)
        return StructuredLLMResponse(content={}, finish_reason="stop")

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        advisory_provider_call,
    )
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, structured_llm=_qwen36_vision_structured_llm_config())
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-vision-advisory",
        idempotency_key="idem-digiexam-vision-advisory-missing-media-root",
        wait_seconds=20,
        payload=_embedded_image_gap_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED
        ).value,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-vision-advisory", grants=_read_grants())
    completion_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/answer_key_completion_report",
        headers=headers,
    ).json()
    rendered_report = json.dumps(completion_report, ensure_ascii=False, sort_keys=True)

    assert provider_calls == []
    assert completion_report["items"][0]["decision_state"] == "manual_follow_up_required"
    assert completion_report["items"][0]["backend_failure_code"] == "unsupported_assets"
    assert "Look at the embedded prompt image" not in rendered_report


def test_digiexam_migration_reviewed_completion_apply_uses_overlay_without_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    async def forbidden_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        provider_calls.append(profile.provider_id)
        raise AssertionError(f"Unexpected structured LLM call for {request.item_id}")

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        forbidden_provider_call,
    )
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, structured_llm=_structured_llm_config())
    headers = _headers(identity, subject="teacher-llm-reviewed", grants=_read_grants())
    source_payload = _missing_answer_key_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-reviewed",
        idempotency_key="idem-reviewed-completion-baseline",
        wait_seconds=20,
        payload=source_payload,
    )
    assert baseline_response.status_code == 200
    baseline_job_id = baseline_response.json()["job"]["job_id"]
    baseline_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts",
        headers=headers,
    ).json()
    migration_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts/migration_manifest",
        headers=headers,
    ).json()
    answer_payload = _choice_answer_payload(2)

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-reviewed",
        idempotency_key="idem-reviewed-completion-apply",
        wait_seconds=20,
        payload=source_payload,
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW
        ).value,
        digiexam_ingestion_overlay=(
            "teacher-overlay.json",
            _reviewed_completion_overlay_bytes(
                baseline_manifest=baseline_manifest,
                item_summary=migration_manifest["item_summaries"][0],
                answer_payload=answer_payload,
                review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
                candidate_payload_digest=answer_key_candidate_payload_digest(answer_payload),
            ),
        ),
    )

    assert overlay_response.status_code == 200
    assert provider_calls == []
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    source_ir = client.get(f"/v2/convert/jobs/{job_id}/artifacts/ir_json", headers=headers).json()
    effective_ir = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/effective_ir_json",
        headers=headers,
    ).json()

    assert entries["answer_key_completion_report"]["availability"] == "not_requested"
    assert entries["effective_ir_json"]["availability"] == "available"
    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "available"
    assert source_ir["items"][0]["answer_key"]["provenance"] == "absent"
    assert effective_ir["answer_key_completion_report_sha256"] == "sha256:completion-report"
    effective_answer_key = effective_ir["items"][0]["effective_answer_key"]
    assert effective_answer_key["provenance"] == "reviewed"
    assert effective_answer_key["correct_alternative_ids"] == [2]
    assert effective_answer_key["lineage"]["candidate_id"] == "candidate-item-001"
    assert effective_answer_key["lineage"]["schema_version"] == (
        DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION
    )
    assert effective_answer_key["lineage"]["prompt_template_version"] == (
        CHOICE_PROMPT_TEMPLATE_VERSION
    )
    assert effective_answer_key["lineage"]["review_outcome"] == (
        DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value
    )


def test_digiexam_migration_reviewed_gap_completion_keeps_keys_in_pdf_and_qti(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def forbidden_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        del profile
        raise AssertionError(f"Unexpected structured LLM call for {request.item_id}")

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        forbidden_provider_call,
    )
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, structured_llm=_structured_llm_config())
    headers = _headers(identity, subject="teacher-gap-reviewed", grants=_read_grants())
    source_payload = _embedded_image_gap_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-gap-reviewed",
        idempotency_key="idem-reviewed-gap-baseline",
        wait_seconds=20,
        payload=source_payload,
    )
    baseline_job_id = baseline_response.json()["job"]["job_id"]
    baseline_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts",
        headers=headers,
    ).json()
    migration_manifest = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifacts/migration_manifest",
        headers=headers,
    ).json()
    answer_payload: dict[str, JsonValue] = {
        "kind": "gap_fill",
        "gap_answers": [{"gap_id": "gap-1", "accepted_values": ["bild", "foto"]}],
    }

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-gap-reviewed",
        idempotency_key="idem-reviewed-gap-apply",
        wait_seconds=20,
        payload=source_payload,
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW
        ).value,
        digiexam_ingestion_overlay=(
            "teacher-overlay.json",
            _reviewed_completion_overlay_bytes(
                baseline_manifest=baseline_manifest,
                item_summary=migration_manifest["item_summaries"][0],
                answer_payload=answer_payload,
                review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
                candidate_payload_digest=answer_key_candidate_payload_digest(answer_payload),
            ),
        ),
    )

    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "available"

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        item_xml = archive.read("items/item_001.xml").decode("utf-8")
    assert "textEntryInteraction" in item_xml
    assert "correctResponse" in item_xml
    assert "bild" in item_xml
    assert "foto" in item_xml

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        text = "\n".join(str(page.get_text("text", sort=True)) for page in document)
    assert "Typ: Fritext" in text
    assert "Correct answers" in text
    assert "bild" in text
    assert "foto" in text
    assert "Manuell bedömning" not in text


def test_digiexam_migration_reviewed_completion_apply_requires_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    async def forbidden_provider_call(
        self: HttpStructuredChatProvider,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del self
        provider_calls.append(profile.provider_id)
        raise AssertionError(f"Unexpected structured LLM call for {request.item_id}")

    monkeypatch.setattr(
        HttpStructuredChatProvider,
        "complete_structured_chat",
        forbidden_provider_call,
    )
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, structured_llm=_structured_llm_config())

    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-llm-reviewed-required",
        idempotency_key="idem-reviewed-completion-missing-overlay",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
        completion_mode=(
            DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW
        ).value,
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert (
        DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW.value
        in error["details"]["errors"][0]["msg"]
    )
    assert provider_calls == []
