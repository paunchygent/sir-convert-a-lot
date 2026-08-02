"""Story 58 live proof route-key evidence tests.

Purpose:
    Prove the Story 58 proof runner accepts the real Service API v2 route
    metadata shape, where create-job responses carry idempotency state and
    result responses carry DigiExam route metadata as `route_key`.

Relationships:
    - Exercises the public Story 58 proof runner boundary with redacted
      evidence only.
    - Complements `test_story58_live_replay_proof.py` without expanding that
      near-limit module.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof import (
    Story58LiveReplayProofSettings,
    run_story58_live_replay_proof,
)

DIGIEXAM_ROUTE_KEY = "digiexam_dxe_to_examnet_migration_bundle"


def test_story58_strict_replay_accepts_matching_v2_result_route_key(
    tmp_path: Path,
) -> None:
    """Strict replay and matching v2 route-key evidence may arrive in separate responses."""
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "compatible_strict_digiexam_replay",
                        "label": "compatible strict replay with v2 result route key",
                        "requests": [
                            {
                                "label": "strict replay",
                                "method": "POST",
                                "path": "/v2/convert/jobs",
                                "headers": {"Idempotency-Key": "idem-proof"},
                                "expect": {
                                    "http_status": 200,
                                    "idempotency_state": "strict_replay",
                                },
                                "extract": {"job_id": "idempotency.active_job_id"},
                            },
                            {
                                "label": "matching result metadata",
                                "method": "GET",
                                "path": "/v2/convert/jobs/{job_id}/result",
                                "expect": {
                                    "http_status": 200,
                                    "route_key": DIGIEXAM_ROUTE_KEY,
                                },
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service_revision": "abc123",
                    "service_profile": "dev",
                },
            )
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "jobv2_route_key",
                        "status": "succeeded",
                        "created_at": "2026-06-30T12:00:00Z",
                        "updated_at": "2026-06-30T12:00:01Z",
                    },
                    "idempotency": {
                        "state": "strict_replay",
                        "idempotent_replay": True,
                        "active_job_id": "jobv2_route_key",
                        "replayed_job_id": "jobv2_route_key",
                        "attempt_count": 1,
                        "previous_attempts": [],
                    },
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v2/convert/jobs/jobv2_route_key/result"
        ):
            return httpx.Response(
                200,
                json={
                    "api_version": "v2",
                    "job_id": "jobv2_route_key",
                    "status": "succeeded",
                    "result": {
                        "artifact": {
                            "filename": "ak7_lag_och_ratt.zip",
                            "format": "examnet_migration_bundle",
                            "size_bytes": 1234,
                            "sha256": "abc123",
                            "content_type": "application/zip",
                        },
                        "conversion_metadata": {
                            "route_key": DIGIEXAM_ROUTE_KEY,
                            "bundle_schema_version": "digiexam_migration_bundle_v1",
                            "bundle_status": "complete",
                            "source_sha256": "source123",
                            "target_readiness_report_artifact_key": ("target_readiness_report"),
                            "manual_follow_up_required": False,
                            "warning_count": 0,
                            "artifact_count": 2,
                        },
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
        ),
        client=client,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases = {case["case_id"]: case for case in summary["cases"]}
    assert cases["compatible_strict_digiexam_replay"]["status"] == "passed"

    retained_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in summary_path.parent.rglob("*")
        if path.is_file()
    )
    assert "jobv2_route_key" in retained_text
    assert DIGIEXAM_ROUTE_KEY in retained_text
    assert "secret-proof-key" not in retained_text
    assert "idem-proof" not in retained_text


def test_story58_stale_reattempt_rejects_route_key_from_superseded_job(
    tmp_path: Path,
) -> None:
    """Stale replay route proof must ignore replayed_job_id route matches."""
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "stale_incompatible_digiexam_replay",
                        "label": "stale replay with old-job route metadata",
                        "requests": [
                            {
                                "label": "service-owned reattempt",
                                "method": "POST",
                                "path": "/v2/convert/jobs",
                                "expect": {
                                    "http_status": 200,
                                    "idempotency_state": "service_reattempt",
                                    "idempotency_reason": (
                                        "terminal_artifact_contract_incompatible"
                                    ),
                                },
                            },
                            {
                                "label": "superseded result metadata",
                                "method": "GET",
                                "path": "/v2/convert/jobs/jobv2_old/result",
                                "expect": {
                                    "http_status": 200,
                                    "route_key": DIGIEXAM_ROUTE_KEY,
                                },
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service_revision": "abc123",
                    "service_profile": "dev",
                },
            )
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            return httpx.Response(
                200,
                json={
                    "job": {"job_id": "jobv2_new", "status": "succeeded"},
                    "idempotency": {
                        "state": "service_reattempt",
                        "reason": "terminal_artifact_contract_incompatible",
                        "idempotent_replay": False,
                        "active_job_id": "jobv2_new",
                        "replayed_job_id": "jobv2_old",
                        "reattempt_of_job_id": "jobv2_old",
                        "attempt_count": 2,
                        "previous_attempts": [{"job_id": "jobv2_old", "status": "succeeded"}],
                    },
                },
            )
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/jobv2_old/result":
            return httpx.Response(
                200,
                json={
                    "api_version": "v2",
                    "job_id": "jobv2_old",
                    "status": "succeeded",
                    "result": {"conversion_metadata": {"route_key": DIGIEXAM_ROUTE_KEY}},
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
        ),
        client=client,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases = {case["case_id"]: case for case in summary["cases"]}
    assert cases["stale_incompatible_digiexam_replay"]["status"] == "failed"
