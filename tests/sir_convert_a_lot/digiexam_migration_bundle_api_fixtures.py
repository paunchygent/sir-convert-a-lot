"""Shared fixtures for DigiExam migration bundle API tests.

Purpose:
    Provide authenticated clients, payload builders, overlays, and structured
    LLM configs used by bounded DigiExam migration API test modules.

Relationships:
    - Supports route, artifact, answer-key, correction, and access-control
      tests without keeping all behavior in one mega-test module.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from xml.etree import ElementTree

import pymupdf
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
    DigiExamAnswerKeyCompletionValidationState,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DIGIEXAM_IR_SCHEMA_VERSION
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import DigiExamAnswerKeyCompletionModeV2
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMTextVerbosity,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
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
    run_jobs_on_submit: bool = True,
) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            gpu_available=False,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            run_jobs_on_submit=run_jobs_on_submit,
            internal_identity_public_keys={_KEY_ID: identity.public_key_pem},
            structured_llm=structured_llm or StructuredLLMRuntimeConfig(),
            exam_authoring_source_state_signature_secret="test-source-state-signature-secret",
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


def _wait_for_terminal_job(runtime: ServiceRuntimeV2, job_id: str) -> None:
    deadline = time.monotonic() + 5.0
    current = runtime.get_job(job_id)
    while current is not None and current.status not in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
        if time.monotonic() > deadline:
            raise AssertionError(f"Job {job_id} did not reach a terminal state")
        time.sleep(0.05)
        current = runtime.get_job(job_id)
    assert current is not None
    assert current.status == JobStatus.SUCCEEDED


def _runtime_from_client(client: TestClient) -> ServiceRuntimeV2:
    app_state = getattr(getattr(client, "app"), "state", None)
    runtime_obj = getattr(app_state, "runtime_v2", None)
    assert isinstance(runtime_obj, ServiceRuntimeV2)
    return runtime_obj


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


def _structured_llm_config_with_openai_fallback() -> StructuredLLMRuntimeConfig:
    local_profile = StructuredLLMProviderProfile(
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
    openai_profile = StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.4-mini-2026-03-17",
        model="gpt-5.4-mini-2026-03-17",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=400000,
        max_output_tokens=4096,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
        reasoning_effort=StructuredLLMReasoningEffort.NONE,
        text_verbosity=StructuredLLMTextVerbosity.LOW,
    )
    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(primary=local_profile, fallback=openai_profile),
        connections={
            local_profile.provider_id: StructuredLLMProviderConnection(
                provider_id=local_profile.provider_id,
                base_url="http://127.0.0.1:8123",
            ),
            openai_profile.provider_id: StructuredLLMProviderConnection(
                provider_id=openai_profile.provider_id,
                base_url="https://api.openai.com",
                api_key="test-token",
            ),
        },
        remote_providers_enabled=True,
        remote_fallback_policy_authorized=True,
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


def _point_correction_overlay_bytes(
    *,
    baseline_manifest: dict[str, object],
    item_summary: dict[str, object],
    correct_id: int,
    max_score: int,
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
                    "point_correction": {
                        "kind": "item_points",
                        "max_score": max_score,
                    },
                    "manual_answer_key": {
                        "kind": "choice",
                        "correct_alternative_ids": [correct_id],
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")


def _qti_maxscore(item_xml: str) -> str | None:
    root = ElementTree.fromstring(item_xml)
    namespace = {"qti": "http://www.imsglobal.org/xsd/imsqti_v2p1"}
    for outcome in root.findall("qti:outcomeDeclaration", namespace):
        if outcome.attrib.get("identifier") != "MAXSCORE":
            continue
        value = outcome.find("qti:defaultValue/qti:value", namespace)
        return value.text if value is not None else None
    return None


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
