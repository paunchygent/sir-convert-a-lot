"""API tests for Task 282 DigiExam migration bundle routes.

Purpose:
    Prove that the service API v2 runtime accepts authenticated DigiExam `.dxe`
    jobs, produces deterministic named artifacts, and enforces
    InternalIdentityContextV1 owner isolation.

Relationships:
    - Exercises `interfaces.http_api` through FastAPI TestClient.
    - Covers the runtime bundle builder, QTI package integration, named
      artifact routes, and identity-derived ownership.
"""

from __future__ import annotations

import base64
import json
import time
import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
    DigiExamAnswerKeyCompletionValidationState,
    answer_key_candidate_payload_digest,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamOverlayReviewedCompletionOutcome,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DIGIEXAM_IR_SCHEMA_VERSION
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.digiexam_target_readiness import (
    TARGET_READINESS_REPORT_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import DigiExamAnswerKeyCompletionModeV2
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
    StructuredLLMImageURLContentPart,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
    StructuredLLMProviderConnection,
)
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_KEY_ID = "gateway-identity-rs256-v1"
_API_KEY = "secret-key"
_FIXTURE_DIR = Path("inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types")
_EMBEDDED_IMAGE_DXE = _FIXTURE_DIR / "sanitized-embedded-image.dxe"
_ONEDRIVE_CORPUS_ROOT = Path("inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe")
_ITEM_013_DXE = _ONEDRIVE_CORPUS_ROOT / "1811577114-ekologiprov-v-49-25d-e.dxe"
_LIVE_CORPUS_DXE_FILENAMES = (
    "1776888013-ak7-lag-och-ratt.dxe",
    "1790207116-23c-atom-och-karnfysik-eca.dxe",
)
_MultipartFileValue = tuple[str | None, bytes | str, str | None]
_MultipartFormValue = tuple[str | None, str]
_MultipartValue = _MultipartFileValue | _MultipartFormValue


def test_digiexam_migration_bundle_route_produces_named_pdf_qti_and_reports(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-bundle-success",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value

    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    artifact_entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert manifest["schema_version"] == DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
    assert manifest["source"]["format"] == "digiexam_dxe"
    assert manifest["bundle_status"] == "partial"
    assert set(artifact_entries) == {
        "bundle_manifest",
        "examnet_pdf",
        "qti_package",
        "qti_validation_report",
        "ir_json",
        "effective_ir_json",
        "migration_manifest",
        "target_readiness_report",
        "ingestion_overlay_report",
        "answer_key_completion_report",
        "manual_follow_up_report",
        "warnings_report",
        "asset_summary",
    }
    assert artifact_entries["examnet_pdf"]["availability"] == "available"
    assert artifact_entries["qti_package"]["availability"] == "available"
    assert artifact_entries["qti_validation_report"]["availability"] == "available"
    assert artifact_entries["target_readiness_report"]["availability"] == "available"
    assert artifact_entries["effective_ir_json"]["availability"] == "not_requested"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        assert "imsmanifest.xml" in archive.namelist()
        assert "items/item_002.xml" in archive.namelist()

    report_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_validation_report",
        headers=headers,
    )
    assert report_response.status_code == 200
    assert report_response.json()["schema_version"] == "examnet_qti_validation_report_v1"
    readiness_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    )
    assert readiness_response.status_code == 200
    assert readiness_response.json()["schema_version"] == TARGET_READINESS_REPORT_SCHEMA_VERSION


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


def test_digiexam_migration_respects_examnet_pdf_only_target(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-examnet-pdf-only",
        wait_seconds=20,
        targets=("examnet_pdf",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "not_requested"
    assert entries["qti_validation_report"]["availability"] == "not_requested"

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 409
    assert qti_response.json()["error"]["code"] == "digiexam_artifact_not_requested"

    warnings_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/warnings_report",
        headers=headers,
    )
    assert warnings_response.status_code == 200
    assert warnings_response.json()["qti_warnings"] == []


def test_digiexam_migration_respects_qti_only_target(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-qti-only",
        wait_seconds=20,
        targets=("qti_package",),
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "not_requested"
    assert entries["qti_package"]["availability"] == "available"
    assert entries["qti_validation_report"]["availability"] == "available"

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 409
    assert pdf_response.json()["error"]["code"] == "digiexam_artifact_not_requested"


def test_digiexam_migration_result_metadata_matches_bundle_manifest(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-result-metadata",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=headers)

    assert manifest_response.status_code == 200
    assert result_response.status_code == 200
    manifest = manifest_response.json()
    result = result_response.json()["result"]
    metadata = result["conversion_metadata"]
    assert metadata["route_key"] == "digiexam_dxe_to_examnet_migration_bundle"
    assert metadata["bundle_schema_version"] == manifest["schema_version"]
    assert metadata["bundle_status"] == manifest["bundle_status"]
    assert metadata["source_sha256"] == manifest["source"]["sha256"]
    assert metadata["target_readiness_report_artifact_key"] == "target_readiness_report"
    assert metadata["manual_follow_up_required"] == manifest["manual_follow_up"]["required"]
    assert metadata["warning_count"] == manifest["warnings"]["count"]
    assert metadata["artifact_count"] == len(manifest["artifacts"])


def test_digiexam_migration_idempotency_includes_companion_digest(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    first_parity_pdf = _pdf_bytes("first parity")
    changed_parity_pdf = _pdf_bytes("changed parity")
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", first_parity_pdf),
    )
    assert response.status_code in {200, 202}

    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", first_parity_pdf),
    )
    assert replay.status_code in {200, 202}
    assert replay.headers["X-Idempotent-Replay"] == "true"

    conflict = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-digiexam-companion",
        parity_pdf=("student-view.pdf", changed_parity_pdf),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_digiexam_migration_unavailable_pdf_target_returns_named_artifact_error(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)

    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-unavailable-pdf-target",
        wait_seconds=20,
        payload=_missing_answer_key_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers)
    assert manifest_response.status_code == 200
    entries = {entry["artifact_key"]: entry for entry in manifest_response.json()["artifacts"]}
    assert entries["examnet_pdf"]["availability"] == "unavailable"
    assert entries["examnet_pdf"]["unavailable_code"] == "manual_answer_key_required"
    assert manifest_response.json()["manual_follow_up"]["required"] is True
    assert manifest_response.json()["readiness"]["review_required"] is True

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert artifact_response.status_code == 409
    assert artifact_response.json()["error"]["code"] == "manual_answer_key_required"
    readiness_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    )
    readiness_targets = readiness_response.json()["targets"]
    assert any(
        row["readiness"] == "needs_teacher_answer_key"
        and row["source_item_fingerprint"].startswith("sha256:")
        for row in readiness_targets
    )


def test_accept_current_state_enables_manual_unkeyed_qti_without_correct_response(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-accept-current-baseline",
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

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-accept-current-qti",
        wait_seconds=20,
        payload=source_payload,
        digiexam_ingestion_overlay=(
            "teacher-overlay.json",
            _accept_current_state_overlay_bytes(
                baseline_manifest=baseline_manifest,
                item_summary=migration_manifest["item_summaries"][0],
                target="qti_package",
            ),
        ),
    )
    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["qti_package"]["availability"] == "available"
    readiness = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    ).json()
    assert any(
        row["target"] == "qti_package"
        and row["readiness"] == "ready_after_accepted_current_state"
        and row["export_enabled"] is True
        for row in readiness["targets"]
    )

    qti_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/qti_package",
        headers=headers,
    )
    assert qti_response.status_code == 200
    with zipfile.ZipFile(BytesIO(qti_response.content)) as archive:
        item_xml = archive.read("items/item_001.xml").decode("utf-8")

    assert "choice_001" in item_xml
    assert "choice_002" in item_xml
    assert "correctResponse" not in item_xml
    assert "responseProcessing" not in item_xml


def test_accept_current_state_enables_manual_unkeyed_examnet_pdf_without_key_claims(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-accept-current-pdf-baseline",
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

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-accept-current-pdf",
        wait_seconds=20,
        payload=source_payload,
        digiexam_ingestion_overlay=(
            "teacher-overlay.json",
            _accept_current_state_overlay_bytes(
                baseline_manifest=baseline_manifest,
                item_summary=migration_manifest["item_summaries"][0],
                target="examnet_pdf",
            ),
        ),
    )
    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "available"
    readiness = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    ).json()
    assert any(
        row["target"] == "examnet_pdf"
        and row["readiness"] == "ready_after_accepted_current_state"
        and row["reason_code"] == "accepted_current_state_pdf_manual_unkeyed_profile"
        and row["export_enabled"] is True
        for row in readiness["targets"]
    )

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        text = "\n".join(str(page.get_text("text", sort=True)) for page in document)
    assert "Alpha" in text
    assert "Beta" in text
    assert "Correct answer" not in text
    assert "Correct answers" not in text


def test_accept_current_state_enables_manual_unkeyed_examnet_pdf_for_item_013_multigap(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _item_013_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-item-013-pdf-baseline",
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

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-item-013-pdf",
        wait_seconds=20,
        payload=source_payload,
        digiexam_ingestion_overlay=(
            "teacher-overlay.json",
            _accept_current_state_overlay_bytes(
                baseline_manifest=baseline_manifest,
                item_summary=migration_manifest["item_summaries"][0],
                target="examnet_pdf",
            ),
        ),
    )
    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

    assert entries["examnet_pdf"]["availability"] == "available"
    readiness = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    ).json()
    assert any(
        row["target"] == "examnet_pdf"
        and row["readiness"] == "ready_after_accepted_current_state"
        and row["export_enabled"] is True
        for row in readiness["targets"]
    )
    warnings = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/warnings_report",
        headers=headers,
    ).json()
    warning_codes = {
        warning["code"]
        for warning in warnings["examnet_pdf_warnings"]
        if warning["blocking"] is False
    }
    assert "manual_unkeyed_gap_open_cloze_rendered" in warning_codes
    assert "examnet_pdf_multi_gap_open_cloze_degraded" in warning_codes

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        text = "\n".join(str(page.get_text("text", sort=True)) for page in document)
        has_image = any(page.get_images(full=True) for page in document)
    assert has_image
    assert text.count("____") >= 5
    assert "Lucka 1" in text
    assert "Lucka 5" in text
    assert "Correct answers" not in text


def test_digiexam_migration_applies_source_bound_teacher_overlay(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()

    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-baseline",
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
    item_summary = migration_manifest["item_summaries"][0]
    overlay_bytes = json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": baseline_manifest["source"]["sha256"],
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": baseline_manifest["source_binding"]["source_ir_sha256"],
            },
            "items": [
                {
                    "item_id": item_summary["item_id"],
                    "sequence": item_summary["sequence"],
                    "item_type": item_summary["item_type"],
                    "source_item_fingerprint": item_summary["source_item_fingerprint"],
                    "manual_answer_key": {
                        "kind": "choice",
                        "correct_alternative_ids": [2],
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")

    overlay_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-manual-key",
        wait_seconds=20,
        payload=source_payload,
        digiexam_ingestion_overlay=("teacher-overlay.json", overlay_bytes),
    )

    assert overlay_response.status_code == 200
    job_id = overlay_response.json()["job"]["job_id"]
    manifest = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=headers).json()
    entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    assert entries["effective_ir_json"]["availability"] == "available"
    assert entries["ingestion_overlay_report"]["availability"] == "available"
    assert entries["examnet_pdf"]["availability"] == "available"
    assert entries["qti_package"]["availability"] == "available"

    source_ir = client.get(f"/v2/convert/jobs/{job_id}/artifacts/ir_json", headers=headers).json()
    effective_ir = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/effective_ir_json",
        headers=headers,
    ).json()
    overlay_report = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/ingestion_overlay_report",
        headers=headers,
    ).json()
    readiness = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/target_readiness_report",
        headers=headers,
    ).json()

    assert source_ir["items"][0]["answer_key"]["provenance"] == "absent"
    assert effective_ir["items"][0]["effective_answer_key"]["provenance"] == "teacher_provided"
    assert effective_ir["items"][0]["effective_answer_key"]["lineage"] is None
    assert overlay_report["accepted_entries"][0]["applied_fields"] == ["manual_answer_key"]
    assert overlay_report["rejected_entries"] == []
    assert {row["target"]: row["export_enabled"] for row in readiness["targets"]} == {
        "examnet_pdf": True,
        "qti_package": True,
    }


def test_digiexam_migration_idempotency_includes_ingestion_overlay_digest(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())
    source_payload = _missing_answer_key_payload()
    baseline_response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest-baseline",
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
    first_overlay = _choice_overlay_bytes(
        baseline_manifest=baseline_manifest,
        item_summary=migration_manifest["item_summaries"][0],
        correct_id=2,
    )
    changed_overlay = _choice_overlay_bytes(
        baseline_manifest=baseline_manifest,
        item_summary=migration_manifest["item_summaries"][0],
        correct_id=1,
    )

    first = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest",
        digiexam_ingestion_overlay=("teacher-overlay.json", first_overlay),
        payload=source_payload,
    )
    assert first.status_code in {200, 202}
    replay = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest",
        digiexam_ingestion_overlay=("teacher-overlay.json", first_overlay),
        payload=source_payload,
    )
    assert replay.status_code in {200, 202}
    assert replay.headers["X-Idempotent-Replay"] == "true"
    conflict = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-overlay-digest",
        digiexam_ingestion_overlay=("teacher-overlay.json", changed_overlay),
        payload=source_payload,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_digiexam_migration_bundle_downloads_embedded_image_pdf(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-embedded-image",
        wait_seconds=20,
        payload=_embedded_image_payload(),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    pdf_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers=headers,
    )
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as document:
        assert document.page_count == 1
        page = document[0]
        assert page.get_images(full=True)
        assert "Look at the embedded prompt image." in str(page.get_text("text", sort=True))


def test_digiexam_migration_live_onedrive_dxe_corpus_subset(tmp_path: Path) -> None:
    missing = [
        filename
        for filename in _LIVE_CORPUS_DXE_FILENAMES
        if not (_ONEDRIVE_CORPUS_ROOT / filename).exists()
    ]
    if missing:
        pytest.skip(f"local raw OneDrive `.dxe` validation files are not present: {missing}")

    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(identity, subject="teacher-1", grants=_read_grants())

    for index, filename in enumerate(_LIVE_CORPUS_DXE_FILENAMES, start=1):
        source_path = _ONEDRIVE_CORPUS_ROOT / filename
        response = _post_digiexam_job(
            client=client,
            identity=identity,
            subject="teacher-1",
            idempotency_key=f"idem-onedrive-corpus-{index}",
            wait_seconds=20,
            source_file=(filename, source_path.read_bytes()),
        )
        assert response.status_code == 200
        job_id = response.json()["job"]["job_id"]

        manifest_response = client.get(
            f"/v2/convert/jobs/{job_id}/artifacts",
            headers=headers,
        )
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()
        entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}

        assert manifest["schema_version"] == DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
        assert manifest["source"]["filename"] == filename
        assert manifest["source"]["format"] == "digiexam_dxe"
        assert manifest["bundle_status"] in {"complete", "partial", "needs_review", "failed"}
        assert entries["qti_validation_report"]["availability"] == "available"
        assert entries["target_readiness_report"]["availability"] == "available"
        assert entries["manual_follow_up_report"]["availability"] == "available"
        assert entries["asset_summary"]["availability"] == "available"


def test_digiexam_migration_rejects_wrong_identity_audience(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = _headers(
        identity,
        subject="teacher-1",
        grants={"sir-convert:jobs:create"},
        audience="skriptoteket",
    )
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-wrong-audience",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_invalid_internal_identity"
    assert response.json()["error"]["details"]["reason"] == "invalid_internal_identity_audience"


def test_digiexam_migration_user_owner_cannot_be_read_by_another_user(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-cross-owner",
        wait_seconds=20,
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]

    other_headers = _headers(identity, subject="teacher-2", grants=_read_grants())
    status_response = client.get(f"/v2/convert/jobs/{job_id}", headers=other_headers)
    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=other_headers,
    )

    assert status_response.status_code == 403
    assert status_response.json()["error"]["code"] == "job_access_denied"
    assert artifact_response.status_code == 403
    assert artifact_response.json()["error"]["code"] == "artifact_access_denied"


def test_digiexam_migration_rejects_api_key_only_user_originated_create(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-api-key-only",
        headers={
            "X-API-Key": _API_KEY,
            "Idempotency-Key": "idem-api-key-only",
            "X-Correlation-ID": "corr-api-key-only",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_invalid_internal_identity"


def test_digiexam_migration_rejects_generic_resources_companion(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    response = _post_digiexam_job(
        client=client,
        identity=identity,
        subject="teacher-1",
        idempotency_key="idem-generic-resource",
        extra_files=[("resources", ("resources.zip", b"not-a-real-zip", "application/zip"))],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "digiexam_companion_unsupported"
    assert response.json()["error"]["details"]["unsupported_parts"] == ["resources"]


class _IdentitySigner:
    """Small RS256 test signer matching HuleEdu InternalIdentityContextV1."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self._private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def headers(
        self,
        *,
        subject: str,
        grants: set[str],
        audience: str = "sir-convert-a-lot",
    ) -> dict[str, str]:
        now = int(time.time())
        payload = {
            "context_version": 1,
            "iss": "api_gateway_service",
            "aud": audience,
            "sub": subject,
            "session_id": f"session-{subject}",
            "org_id": "org-1",
            "tenant_id": None,
            "roles": ["teacher"],
            "grants": sorted(grants),
            "policy_version": "2026-04-09",
            "iat": now,
            "exp": now + 60,
            "jti": f"ctx-{subject}-{now}",
            "source_app": "skriptoteket",
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "realm_subject_id": subject,
        }
        encoded = _b64url(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        signature = self._private_key.sign(
            encoded.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "X-HuleEdu-Identity-Context-Version": "1",
            "X-HuleEdu-Identity-Context": encoded,
            "X-HuleEdu-Identity-Key-Id": _KEY_ID,
            "X-HuleEdu-Identity-Signature": f"rs256={_b64url(signature)}",
        }


def _client(
    tmp_path: Path,
    identity: _IdentitySigner,
    *,
    structured_llm: StructuredLLMRuntimeConfig | None = None,
) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            gpu_available=False,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            internal_identity_public_keys={_KEY_ID: identity.public_key_pem},
            structured_llm=structured_llm or StructuredLLMRuntimeConfig(),
        )
    )
    return TestClient(app)


def _headers(
    identity: _IdentitySigner,
    *,
    subject: str,
    grants: set[str],
    audience: str = "sir-convert-a-lot",
) -> dict[str, str]:
    headers = {
        "X-API-Key": _API_KEY,
        "X-Correlation-ID": f"corr-{subject}",
    }
    headers.update(identity.headers(subject=subject, grants=grants, audience=audience))
    return headers


def _post_digiexam_job(
    *,
    client: TestClient,
    identity: _IdentitySigner,
    subject: str,
    idempotency_key: str,
    wait_seconds: int = 0,
    parity_pdf: tuple[str, bytes] | None = None,
    digiexam_ingestion_overlay: tuple[str, bytes] | None = None,
    extra_files: list[tuple[str, _MultipartFileValue]] | None = None,
    payload: dict[str, object] | None = None,
    source_file: tuple[str, bytes] | None = None,
    headers: dict[str, str] | None = None,
    targets: tuple[str, ...] = ("examnet_pdf", "qti_package"),
    completion_mode: str = DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY.value,
) -> Response:
    request_headers = headers or _headers(
        identity,
        subject=subject,
        grants={"sir-convert:jobs:create"},
    )
    request_headers["Idempotency-Key"] = idempotency_key
    file_name = source_file[0] if source_file is not None else "exam.dxe"
    file_bytes = (
        source_file[1]
        if source_file is not None
        else json.dumps(payload or _digiexam_payload()).encode("utf-8")
    )
    spec = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": file_name, "format": "digiexam_dxe"},
        "conversion": {
            "output_format": "examnet_migration_bundle",
            "targets": list(targets),
            "artifact_language": "sv",
        },
        "digiexam_migration_options": {
            "parity_pdf_filename": parity_pdf[0] if parity_pdf is not None else None,
            "ingestion_overlay_filename": (
                digiexam_ingestion_overlay[0] if digiexam_ingestion_overlay is not None else None
            ),
            "ingestion_overlay_policy": (
                "apply_teacher_overlay" if digiexam_ingestion_overlay is not None else "none"
            ),
            "result_pdf_usage": "correct_machine_marked_answers_only",
            "manual_follow_up_policy": "emit_item_addressable_report",
            "completion_mode": completion_mode,
            "remote_provider_policy": "forbidden",
        },
        "retention": {"pin": False},
    }
    files: list[tuple[str, _MultipartValue]] = [
        (
            "file",
            (
                file_name,
                file_bytes,
                "application/octet-stream",
            ),
        ),
        ("job_spec", (None, json.dumps(spec))),
    ]
    if parity_pdf is not None:
        files.append(("parity_pdf", (parity_pdf[0], parity_pdf[1], "application/pdf")))
    if digiexam_ingestion_overlay is not None:
        files.append(
            (
                "digiexam_ingestion_overlay",
                (
                    digiexam_ingestion_overlay[0],
                    digiexam_ingestion_overlay[1],
                    "application/json",
                ),
            )
        )
    if extra_files is not None:
        files.extend(extra_files)
    return client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers=request_headers,
        files=files,
    )


def _structured_llm_config() -> StructuredLLMRuntimeConfig:
    profile = StructuredLLMProviderProfile(
        provider_id="local-structured",
        model="local-model",
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=4096,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
    )
    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(primary=profile),
        connections={
            profile.provider_id: StructuredLLMProviderConnection(
                provider_id=profile.provider_id,
                base_url="http://127.0.0.1:8123",
            )
        },
    )


def _qwen36_vision_structured_llm_config(
    *,
    vision_media_path: Path | None = None,
) -> StructuredLLMRuntimeConfig:
    profile = StructuredLLMProviderProfile(
        provider_id="qwen36-local-vision",
        model="qwen3.6-27b-q6k",
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=32768,
        max_output_tokens=4096,
        temperature=0.15,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=True,
        ),
    )
    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(primary=profile),
        connections={
            profile.provider_id: StructuredLLMProviderConnection(
                provider_id=profile.provider_id,
                base_url="http://127.0.0.1:8123",
            )
        },
        vision_media_path=vision_media_path,
    )


def _read_grants() -> set[str]:
    return {"sir-convert:jobs:read-own", "sir-convert:artifacts:read-own"}


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _choice_overlay_bytes(
    *,
    baseline_manifest: dict[str, object],
    item_summary: dict[str, object],
    correct_id: int,
) -> bytes:
    source = baseline_manifest["source"]
    source_binding = baseline_manifest["source_binding"]
    if not isinstance(source, dict) or not isinstance(source_binding, dict):
        raise RuntimeError("baseline manifest has no source binding")
    return json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": source["sha256"],
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": source_binding["source_ir_sha256"],
            },
            "items": [
                {
                    "item_id": item_summary["item_id"],
                    "sequence": item_summary["sequence"],
                    "item_type": item_summary["item_type"],
                    "source_item_fingerprint": item_summary["source_item_fingerprint"],
                    "manual_answer_key": {
                        "kind": "choice",
                        "correct_alternative_ids": [correct_id],
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")


def _accept_current_state_overlay_bytes(
    *,
    baseline_manifest: dict[str, object],
    item_summary: dict[str, object],
    target: str,
) -> bytes:
    source = baseline_manifest["source"]
    source_binding = baseline_manifest["source_binding"]
    if not isinstance(source, dict) or not isinstance(source_binding, dict):
        raise RuntimeError("baseline manifest has no source binding")
    return json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": source["sha256"],
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": source_binding["source_ir_sha256"],
            },
            "items": [
                {
                    "item_id": item_summary["item_id"],
                    "sequence": item_summary["sequence"],
                    "item_type": item_summary["item_type"],
                    "source_item_fingerprint": item_summary["source_item_fingerprint"],
                    "review_decision": {
                        "kind": "accept_current_state_for_export",
                        "decision_id": "accept-qti-current-state",
                        "accepted_targets": [target],
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")


def _reviewed_completion_overlay_bytes(
    *,
    baseline_manifest: dict[str, object],
    item_summary: dict[str, object],
    answer_payload: dict[str, JsonValue],
    review_outcome: str,
    candidate_payload_digest: str,
) -> bytes:
    source = baseline_manifest["source"]
    source_binding = baseline_manifest["source_binding"]
    if not isinstance(source, dict) or not isinstance(source_binding, dict):
        raise RuntimeError("baseline manifest has no source binding")
    kind = answer_payload.get("kind")
    if not isinstance(kind, str):
        raise RuntimeError("reviewed completion answer payload kind must be a string")
    schema_version = _answer_payload_schema_version(kind)
    prompt_template_version = _answer_payload_prompt_template_version(kind)
    return json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": source["sha256"],
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": source_binding["source_ir_sha256"],
            },
            "items": [
                {
                    "item_id": item_summary["item_id"],
                    "sequence": item_summary["sequence"],
                    "item_type": item_summary["item_type"],
                    "source_item_fingerprint": item_summary["source_item_fingerprint"],
                    "reviewed_completion_answer_key": {
                        "kind": kind,
                        "review_decision_id": "review-decision-001",
                        "review_outcome": review_outcome,
                        "candidate_lineage": {
                            "completion_report_sha256": "sha256:completion-report",
                            "candidate_id": "candidate-item-001",
                            "candidate_payload_digest": candidate_payload_digest,
                            "provider_profile_id": "local-structured",
                            "schema_name": schema_version,
                            "schema_version": schema_version,
                            "prompt_template_version": prompt_template_version,
                            "validation_state": (
                                DigiExamAnswerKeyCompletionValidationState.VALID.value
                            ),
                        },
                        "answer_payload": answer_payload,
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")


def _answer_payload_schema_version(kind: str) -> str:
    if kind == "gap_fill":
        return DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION
    return DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION


def _answer_payload_prompt_template_version(kind: str) -> str:
    if kind == "gap_fill":
        return GAP_FILL_PROMPT_TEMPLATE_VERSION
    return CHOICE_PROMPT_TEMPLATE_VERSION


def _choice_answer_payload(correct_id: int) -> dict[str, JsonValue]:
    return {"kind": "choice", "correct_alternative_ids": [correct_id]}


def _pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    try:
        page = doc.new_page()
        if page is None:
            raise RuntimeError("PyMuPDF returned no page")
        page.insert_text((72, 72), text, fontsize=12)
        return bytes(doc.tobytes())
    finally:
        doc.close()


def _digiexam_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Essay",
                        "about": "",
                        "bodyHTML": "<p>Explain the water cycle.</p>",
                        "images": [],
                        "maxScore": 3,
                        "type": 0,
                    },
                    {
                        "id": 2,
                        "title": "Single",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Multiple",
                        "about": "",
                        "bodyHTML": "<p>Choose the ordinal words.</p>",
                        "images": [],
                        "maxScore": 4,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "First", "about": "", "right": True},
                            {"id": 2, "title": "Between", "about": "", "right": False},
                            {"id": 3, "title": "Third", "about": "", "right": True},
                        ],
                    },
                ]
            }
        ]
    }


def _missing_answer_key_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Single without key",
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
                ]
            }
        ]
    }


def _embedded_image_payload() -> dict[str, object]:
    loaded_payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    if not isinstance(loaded_payload, dict):
        raise RuntimeError("Embedded image fixture has no root object")
    payload = {str(key): value for key, value in loaded_payload.items()}
    exams = payload["exams"]
    if not isinstance(exams, list):
        raise RuntimeError("Embedded image fixture has no exams list")
    exam = exams[0]
    if not isinstance(exam, dict):
        raise RuntimeError("Embedded image fixture has no exam object")
    questions = exam["questions"]
    if not isinstance(questions, list):
        raise RuntimeError("Embedded image fixture has no questions list")
    question = questions[0]
    if not isinstance(question, dict):
        raise RuntimeError("Embedded image fixture has no question object")
    question["title"] = "Embedded image prompt"
    question["about"] = "Look at the embedded prompt image."
    question["bodyHTML"] = (
        "<p>Look at the embedded prompt image.</p>"
        '<p><img data-image-id="0" class="fr-fic fr-dib" /></p>'
    )
    question["type"] = 0
    question["blanks"] = []
    return payload


def _embedded_image_gap_payload() -> dict[str, object]:
    loaded_payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    if not isinstance(loaded_payload, dict):
        raise RuntimeError("Embedded image fixture has no root object")
    return {str(key): value for key, value in loaded_payload.items()}


def _item_013_payload() -> dict[str, object]:
    loaded_payload = json.loads(_ITEM_013_DXE.read_text(encoding="utf-8"))
    if not isinstance(loaded_payload, dict):
        raise RuntimeError("Item 013 fixture has no root object")
    payload = {str(key): value for key, value in loaded_payload.items()}
    exams = payload["exams"]
    if not isinstance(exams, list):
        raise RuntimeError("Item 013 fixture has no exams list")
    exam = exams[0]
    if not isinstance(exam, dict):
        raise RuntimeError("Item 013 fixture has no exam object")
    questions = exam["questions"]
    if not isinstance(questions, list):
        raise RuntimeError("Item 013 fixture has no questions list")
    exam["questions"] = [questions[12]]
    return payload
