"""Tests for Story 58 live replay proof retention.

Purpose:
    Prove the Story 58 proof runner records live Service API replay outcomes
    as redacted operational evidence instead of retaining payloads or faking
    unsafe production setup.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.story58_live_replay_proof`.
    - Protects Story 58 closeout evidence for Tasks 375-378 without changing
      Service API v2 route behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof import (
    Story58LiveReplayProofSettings,
    run_story58_live_replay_proof,
)


def test_story58_live_replay_proof_retains_only_redacted_case_evidence(
    tmp_path: Path,
) -> None:
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / "strict-replay.json").write_text(
        json.dumps({"raw_exam_content": "must never be retained"}),
        encoding="utf-8",
    )
    (payload_dir / "artifact-download.json").write_text("{}", encoding="utf-8")
    log_capture = tmp_path / "service.log"
    log_capture.write_text(
        "jobv2_strict secret-proof-key idem-secret raw exam text "
        "/private/source/path.dxe provider prompt crset_f5ade123\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "delegated_generic_smoke_command": (
                    "pdm run hemma-verify-v2-conversions --lane host"
                ),
                "cases": [
                    {
                        "case_id": "compatible_strict_digiexam_replay",
                        "label": "compatible strict DigiExam replay",
                        "requests": [
                            {
                                "label": "strict replay",
                                "method": "POST",
                                "path": "/v2/convert/jobs",
                                "query": {"wait_seconds": "0"},
                                "headers": {"Idempotency-Key": "idem-secret"},
                                "json_file": "payloads/strict-replay.json",
                                "expect": {
                                    "http_status": 200,
                                    "idempotency_state": "strict_replay",
                                    "route_id": "digiexam_dxe_to_examnet_migration_bundle",
                                },
                            }
                        ],
                    },
                    {
                        "case_id": "stale_incompatible_digiexam_replay",
                        "label": "stale incompatible replay",
                        "requires_governed_setup_reason": (
                            "No safe existing stale production idempotency record supplied."
                        ),
                    },
                    {
                        "case_id": "missing_source_correction_apply_fail_closed",
                        "label": "missing source correction apply",
                        "safe_to_run": False,
                        "requires_governed_setup_reason": (
                            "Would require deleting or expiring a source job."
                        ),
                    },
                    {
                        "case_id": (
                            "stale_mismatched_nested_correction_artifact_download_fail_closed"
                        ),
                        "label": "mismatched nested correction artifact download",
                        "requests": [
                            {
                                "label": "download mismatched reference",
                                "method": "GET",
                                "path": (
                                    "/v2/convert/jobs/jobv2_source/"
                                    "correction-replays/aset_old/artifacts/exam_pdf"
                                ),
                                "query": {"content_sha256": "stalehash"},
                                "expect": {
                                    "http_status": [404, 409],
                                    "error_code": ("correction_replay_artifact_reference_mismatch"),
                                },
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(str(request.url))
        assert request.headers.get("X-API-Key") == "secret-proof-key"
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service_revision": "abc123",
                    "service_profile": "production",
                    "private_path": "/srv/private",
                },
            )
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            assert request.url.params["wait_seconds"] == "0"
            assert request.headers["Idempotency-Key"] == "idem-secret"
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "jobv2_strict",
                        "status": "succeeded",
                        "route_id": "digiexam_dxe_to_examnet_migration_bundle",
                        "raw_exam_content": "student answer text",
                        "source_signature": "signed-source-state",
                    },
                    "idempotency": {
                        "state": "strict_replay",
                        "idempotent_replay": True,
                        "replayed_job_id": "jobv2_strict",
                        "reason": None,
                        "idempotency_key": "idem-secret",
                    },
                    "identity": {"grant": "raw-grant-envelope"},
                    "provider_prompt": "grade this exam",
                    "answer_key_review_state_report": {
                        "schema_version": "digiexam_answer_key_review_state_v1"
                    },
                    "correction_replay_artifact_reference": {
                        "schema_version": "correction_replay_artifact_reference_v1",
                        "job_id": "jobv2_strict",
                        "artifact_set_id": "aset_123",
                        "artifact_key": "exam_pdf",
                        "content_sha256": "abcde12345",
                        "request_id": "req_123",
                        "source_binding_digest": "bind123",
                        "source_state_sha256": "state123",
                        "correction_payload_digest": "payload123",
                        "target_set_digest": "target123",
                        "created_at": "2026-06-30T10:00:00Z",
                    },
                },
            )
        if (
            request.method == "GET"
            and request.url.path
            == "/v2/convert/jobs/jobv2_source/correction-replays/aset_old/artifacts/exam_pdf"
        ):
            return httpx.Response(
                409,
                json={
                    "error": {
                        "code": "correction_replay_artifact_reference_mismatch",
                        "message": "raw path /private/source/path.dxe",
                        "details": {"signature": "raw-signature"},
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="http://proof-service.test",
        transport=httpx.MockTransport(handler),
        timeout=30.0,
    )

    summary_path = run_story58_live_replay_proof(
        Story58LiveReplayProofSettings(
            service_url="http://proof-service.test",
            api_key="secret-proof-key",
            case_manifest=manifest_path,
            output_root=tmp_path / "evidence",
            timeout_seconds=30.0,
            monitoring_pointers=("prod docker logs retained in downstream manifest",),
            log_capture_paths=(log_capture,),
        ),
        client=client,
    )

    run_dir = summary_path.parent
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases = {case["case_id"]: case for case in summary["cases"]}
    assert summary["overall_status"] == "requires_governed_setup"
    assert cases["compatible_strict_digiexam_replay"]["status"] == "passed"
    assert cases["stale_incompatible_digiexam_replay"]["status"] == "requires_governed_setup"
    assert (
        cases["missing_source_correction_apply_fail_closed"]["status"] == "requires_governed_setup"
    )
    assert (
        cases["stale_mismatched_nested_correction_artifact_download_fail_closed"]["status"]
        == "passed"
    )
    assert cases["generic_idempotency_preservation_smoke"]["status"] == "skipped"
    assert (
        "hemma-verify-v2-conversions" in cases["generic_idempotency_preservation_smoke"]["reason"]
    )
    assert any("/v2/convert/jobs?wait_seconds=0" in path for path in seen_paths)

    retained_text = "\n".join(
        path.read_text(encoding="utf-8") for path in run_dir.rglob("*") if path.is_file()
    )
    forbidden_fragments = [
        "secret-proof-key",
        "idem-secret",
        "raw_exam_content",
        "student answer text",
        "signed-source-state",
        "raw-grant-envelope",
        "grade this exam",
        "/private/source/path.dxe",
        "provider prompt",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in retained_text
    assert "jobv2_strict" in retained_text
    assert "strict_replay" in retained_text
    assert "aset_123" in retained_text
    assert "crset_f5ade123" in retained_text
    assert "abcde12345" in retained_text
    assert (run_dir / "report.md").is_file()
    assert (run_dir / "monitoring-pointers.json").is_file()
    assert (run_dir / "logs" / "service.redacted.log").is_file()


def test_story58_relationships_compare_request_level_artifact_set_identity(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "exact_duplicate_correction_retry_reuses_artifact_set",
                        "label": "duplicate retry",
                        "artifact_set_relationship": "same",
                        "requests": [
                            {
                                "label": "first duplicate apply",
                                "method": "GET",
                                "path": "/duplicate/first",
                                "expect": {"http_status": 200},
                            },
                            {
                                "label": "second duplicate apply",
                                "method": "GET",
                                "path": "/duplicate/second",
                                "expect": {"http_status": 200},
                            },
                        ],
                    },
                    {
                        "case_id": "distinct_correction_applies_distinct_artifact_sets",
                        "label": "distinct applies",
                        "artifact_set_relationship": "distinct",
                        "requests": [
                            {
                                "label": "first correction apply",
                                "method": "GET",
                                "path": "/distinct/first",
                                "expect": {"http_status": 200},
                            },
                            {
                                "label": "second correction apply",
                                "method": "GET",
                                "path": "/distinct/second",
                                "expect": {"http_status": 200},
                            },
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def response_with_refs(*, artifact_set_id: str, request_id: str) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "correction_replay_artifact_references": [
                    _artifact_reference(
                        artifact_set_id=artifact_set_id,
                        artifact_key="exam_pdf",
                        request_id=request_id,
                    ),
                    _artifact_reference(
                        artifact_set_id=artifact_set_id,
                        artifact_key="exam_qti",
                        request_id=request_id,
                    ),
                ]
            },
        )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("X-API-Key") == "secret-proof-key"
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service_revision": "abc123",
                    "service_profile": "production",
                },
            )
        if request.method == "GET" and request.url.path == "/duplicate/first":
            return response_with_refs(artifact_set_id="crset_dup", request_id="req_dup")
        if request.method == "GET" and request.url.path == "/duplicate/second":
            return response_with_refs(artifact_set_id="crset_dup", request_id="req_dup")
        if request.method == "GET" and request.url.path == "/distinct/first":
            return response_with_refs(artifact_set_id="crset_first", request_id="req_first")
        if request.method == "GET" and request.url.path == "/distinct/second":
            return response_with_refs(artifact_set_id="crset_second", request_id="req_second")
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="http://proof-service.test",
        transport=httpx.MockTransport(handler),
        timeout=30.0,
    )

    summary_path = run_story58_live_replay_proof(
        Story58LiveReplayProofSettings(
            service_url="http://proof-service.test",
            api_key="secret-proof-key",
            case_manifest=manifest_path,
            output_root=tmp_path / "evidence",
            timeout_seconds=30.0,
        ),
        client=client,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases = {case["case_id"]: case for case in summary["cases"]}
    assert cases["exact_duplicate_correction_retry_reuses_artifact_set"]["status"] == "passed"
    assert cases["distinct_correction_applies_distinct_artifact_sets"]["status"] == "passed"


def test_story58_live_replay_proof_captures_logs_after_live_requests(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "generic_idempotency_preservation_smoke",
                        "label": "generic idempotency smoke",
                        "requests": [
                            {
                                "label": "generic route",
                                "method": "GET",
                                "path": "/generic",
                                "expect": {
                                    "http_status": 200,
                                    "idempotency_state": "fresh_admission",
                                },
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    log_capture = tmp_path / "service.log"
    log_capture.write_text("before requests\n", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("X-API-Key") == "secret-proof-key"
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service_revision": "abc123",
                    "service_profile": "production",
                },
            )
        if request.method == "GET" and request.url.path == "/generic":
            with log_capture.open("a", encoding="utf-8") as log_file:
                log_file.write("jobv2_after_live_request crset_after_live_request\n")
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "jobv2_after_live_request",
                        "status": "succeeded",
                    },
                    "idempotency": {
                        "state": "fresh_admission",
                        "idempotent_replay": False,
                    },
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="http://proof-service.test",
        transport=httpx.MockTransport(handler),
        timeout=30.0,
    )

    summary_path = run_story58_live_replay_proof(
        Story58LiveReplayProofSettings(
            service_url="http://proof-service.test",
            api_key="secret-proof-key",
            case_manifest=manifest_path,
            output_root=tmp_path / "evidence",
            timeout_seconds=30.0,
            log_capture_paths=(log_capture,),
        ),
        client=client,
    )

    retained_log = (summary_path.parent / "logs" / "service.redacted.log").read_text(
        encoding="utf-8"
    )
    assert "jobv2_after_live_request" in retained_log
    assert "crset_after_live_request" in retained_log


def _artifact_reference(
    *,
    artifact_set_id: str,
    artifact_key: str,
    request_id: str,
) -> dict[str, str]:
    return {
        "schema_version": "correction_replay_artifact_reference_v1",
        "job_id": "jobv2_source",
        "artifact_set_id": artifact_set_id,
        "artifact_key": artifact_key,
        "content_sha256": f"hash_{artifact_set_id}_{artifact_key}",
        "request_id": request_id,
        "source_binding_digest": "bind123",
        "source_state_sha256": "state123",
        "correction_payload_digest": "payload123",
        "target_set_digest": "target123",
        "created_at": "2026-06-30T10:00:00Z",
    }
