"""Shared payload helpers for correction apply route tests.

Purpose:
    Build canonical source-bound correction apply requests for route-level
    contract tests without duplicating producer-state digest setup.

Relationships:
    - Used by correction apply route tests and Review 24 remediation
      regressions.
    - Mirrors the application integrity helpers used by the runtime route.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_issuer import (
    correction_source_state_artifact_path_for_job,
    write_exam_authoring_correction_source_state_artifact,
)
from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceBindingV1,
    ExamAuthoringCorrectionSourceStateV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_integrity import (
    source_state_authority_signature,
    source_state_content_digest,
    stable_json_sha256,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from scripts.sir_convert_a_lot.interfaces.http_app_state import ensure_runtime_state_v2

API_HEADERS = {
    "X-API-Key": "secret-key",
    "X-Correlation-ID": "corr_corrections_apply_v2",
}
ROUTE = "/v2/exam-authoring/corrections/apply"
ISSUE_ROUTE = "/v2/exam-authoring/corrections/source-state/issue"
OLD_ROUTE = "/v2/exam-authoring/matching/manual-answer-key/apply"
SOURCE_STATE_SIGNATURE_SECRET = "test-source-state-signature-secret"


def build_client(tmp_path: Path) -> TestClient:
    """Build a correction route test client with deterministic auth."""

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            exam_authoring_source_state_signature_secret=SOURCE_STATE_SIGNATURE_SECRET,
        )
    )
    return TestClient(app)


def request_payload() -> dict[str, object]:
    """Return a valid source-bound matching correction request."""

    payload: dict[str, object] = {
        "schema_version": "exam_authoring_corrections_apply_request_v1",
        "request_id": "correction-request-001",
        "source_binding": {
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_state_sha256": "sha256:placeholder",
            "source_state_signature": "hmac-sha256:placeholder",
            "source_bundle_id": "bundle-001",
            "source_file_sha256": "sha256:source-file",
        },
        "source_authoring_state": {
            "schema_version": "exam_authoring_correction_source_state_v1",
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_state_sha256": "sha256:placeholder",
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
                            "answer_key": {"provenance": "absent", "pairs": []},
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
    refresh_source_state_digest(payload)
    return payload


def source_state_issue_payload(job_id: str) -> dict[str, object]:
    """Return a producer source-state issuance request for a stored job."""

    return {
        "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
        "job_id": job_id,
    }


def seed_source_state_job(client: TestClient) -> str:
    """Seed a succeeded server-owned job with a source-state artifact."""

    app = client.app
    assert isinstance(app, FastAPI)
    runtime_obj = ensure_runtime_state_v2(
        app,
        utc_now_iso="2026-05-18T00:00:00Z",
    )
    assert isinstance(runtime_obj, ServiceRuntimeV2)
    job_id = "jobv2_correction_source_state_001"
    source_bytes = b"# Server-owned source state\n"
    runtime_obj.job_store.create_job(
        job_id=job_id,
        spec=JobSpecV2.model_validate(
            {
                "api_version": "v2",
                "source": {"kind": "upload", "filename": "source.md", "format": "md"},
                "conversion": {
                    "output_format": "pdf",
                    "template": None,
                    "css_filenames": [],
                    "reference_docx_filename": None,
                },
                "retention": {"pin": False},
            }
        ),
        upload_bytes=source_bytes,
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    assert runtime_obj.job_store.claim_queued_job(job_id)
    runtime_obj.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"# Converted artifact\n",
        pipeline_used="test-source-state-producer",
        backend_used=None,
        acceleration_used=None,
        options_fingerprint="sha256:test-options",
        warnings=[],
    )
    job = runtime_obj.get_job(job_id)
    assert job is not None
    payload = request_payload()
    source_state = payload["source_authoring_state"]
    assert isinstance(source_state, dict)
    source_state["source_state_sha256"] = "sha256:server-side-placeholder"
    write_exam_authoring_correction_source_state_artifact(
        path=correction_source_state_artifact_path_for_job(job),
        source_state=ExamAuthoringCorrectionSourceStateV1.model_validate(source_state),
    )
    return job_id


def refresh_source_state_digest(
    payload: dict[str, object],
    *,
    refresh_signature: bool = True,
) -> None:
    """Replace source-state digest placeholders with the canonical content digest."""

    source_state = payload["source_authoring_state"]
    assert isinstance(source_state, dict)
    state = ExamAuthoringCorrectionSourceStateV1.model_validate(source_state)
    digest = source_state_content_digest(state)
    source_state["source_state_sha256"] = digest
    source_binding = payload["source_binding"]
    assert isinstance(source_binding, dict)
    source_binding["source_state_sha256"] = digest
    if refresh_signature:
        refresh_source_state_signature(payload)


def refresh_source_state_signature(payload: dict[str, object]) -> None:
    """Replace the source-state authority signature with server truth."""

    source_binding = payload["source_binding"]
    assert isinstance(source_binding, dict)
    binding = ExamAuthoringCorrectionSourceBindingV1.model_validate(source_binding)
    source_binding["source_state_signature"] = source_state_authority_signature(
        binding=binding,
        secret=SOURCE_STATE_SIGNATURE_SECRET,
    )


def first_correction(payload: dict[str, object]) -> dict[str, object]:
    """Return the first correction entry from a mutable request payload."""

    corrections = payload["corrections"]
    assert isinstance(corrections, list)
    correction = corrections[0]
    assert isinstance(correction, dict)
    return correction


def candidate_lineage(*, candidate_payload_digest: str) -> dict[str, object]:
    """Return bounded advisory candidate lineage for matching corrections."""

    return {
        "completion_report_sha256": "sha256:completion-report",
        "candidate_id": "candidate-item-001",
        "candidate_payload_digest": candidate_payload_digest,
        "provider_profile_id": "local-structured",
        "schema_name": "exam_authoring_matching_answer_key_decision_v1",
        "schema_version": "exam_authoring_matching_answer_key_decision_v1",
        "prompt_template_version": "exam_authoring_matching_answer_key_prompt_v1",
        "validation_state": "valid",
    }


def matching_candidate_digest(pairs: list[dict[str, str]]) -> str:
    """Return the canonical digest for a matching advisory answer-key payload."""

    return stable_json_sha256({"kind": "matching", "pairs": tuple(pairs)})
