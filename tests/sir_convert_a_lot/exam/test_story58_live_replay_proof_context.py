"""Tests for Story 58 live proof request context interpolation.

Purpose:
    Prove dependent Story 58 proof requests can use metadata extracted from
    prior redacted Service API responses without retaining raw response bodies
    or unsafe fallback values.

Relationships:
    - Exercises the public Story 58 proof runner boundary.
    - Protects Task 379 live evidence orchestration for correction replay
      artifact downloads created by earlier proof requests.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof import (
    Story58LiveReplayProofSettings,
    run_story58_live_replay_proof,
)


def test_story58_live_replay_proof_interpolates_extracted_redacted_values(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": (
                            "stale_mismatched_nested_correction_artifact_download_fail_closed"
                        ),
                        "label": "dependent correction replay download",
                        "requests": [
                            {
                                "label": "correction apply",
                                "method": "GET",
                                "path": "/correction/apply",
                                "expect": {"http_status": 200},
                                "extract": {
                                    "source_job_id": "job.job_id",
                                    "artifact_set_id": (
                                        "correction_replay_artifact_references[0].artifact_set_id"
                                    ),
                                    "content_sha256": (
                                        "correction_replay_artifact_references[0].content_sha256"
                                    ),
                                },
                            },
                            {
                                "label": "nested artifact mismatch",
                                "method": "GET",
                                "path": (
                                    "/v2/convert/jobs/{source_job_id}/correction-replays/"
                                    "{artifact_set_id}/artifacts/correction_replay_examnet_pdf"
                                ),
                                "query": {"content_sha256": "{content_sha256}"},
                                "headers": {"X-Proof-Artifact-Set": "{artifact_set_id}"},
                                "expect": {
                                    "http_status": 409,
                                    "error_code": ("correction_replay_artifact_reference_mismatch"),
                                },
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    seen_nested_request = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_nested_request
        if request.method == "GET" and request.url.path == "/readyz":
            return _readyz_response()
        if request.method == "GET" and request.url.path == "/correction/apply":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "jobv2_source",
                        "status": "succeeded",
                        "private_path": "/must/not/retain",
                    },
                    "raw_exam_content": "must not leak through context",
                    "correction_replay_artifact_references": [
                        {
                            "schema_version": "correction_replay_artifact_reference_v1",
                            "job_id": "jobv2_source",
                            "artifact_set_id": "crset_from_apply",
                            "artifact_key": "correction_replay_examnet_pdf",
                            "content_sha256": "hash_from_apply",
                            "request_id": "req_from_apply",
                        }
                    ],
                },
            )
        if request.method == "GET" and request.url.path == (
            "/v2/convert/jobs/jobv2_source/correction-replays/crset_from_apply/"
            "artifacts/correction_replay_examnet_pdf"
        ):
            seen_nested_request = True
            assert request.url.params["content_sha256"] == "hash_from_apply"
            assert request.headers["X-Proof-Artifact-Set"] == "crset_from_apply"
            return httpx.Response(
                409,
                json={
                    "error": {
                        "code": "correction_replay_artifact_reference_mismatch",
                        "retryable": False,
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    summary_path = run_story58_live_replay_proof(
        _settings(tmp_path=tmp_path, manifest_path=manifest_path),
        client=_client(handler),
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cases = {case["case_id"]: case for case in summary["cases"]}
    assert (
        cases["stale_mismatched_nested_correction_artifact_download_fail_closed"]["status"]
        == "passed"
    )
    assert seen_nested_request is True
    retained_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in summary_path.parent.rglob("*")
        if path.is_file()
    )
    assert "crset_from_apply" in retained_text
    assert "hash_from_apply" in retained_text
    assert "must not leak through context" not in retained_text
    assert "/must/not/retain" not in retained_text


def test_story58_live_replay_proof_fails_closed_on_unresolved_interpolation(
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
                        "label": "unresolved context",
                        "requests": [
                            {
                                "label": "uses missing variable",
                                "method": "GET",
                                "path": "/jobs/{missing_job_id}",
                                "expect": {"http_status": 200},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.method == "GET" and request.url.path == "/readyz":
            return _readyz_response()
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with pytest.raises(SystemExit, match="unresolved manifest interpolation"):
        run_story58_live_replay_proof(
            _settings(tmp_path=tmp_path, manifest_path=manifest_path),
            client=_client(handler),
        )
    assert seen_paths == ["/readyz"]


def _settings(
    *,
    tmp_path: Path,
    manifest_path: Path,
) -> Story58LiveReplayProofSettings:
    return Story58LiveReplayProofSettings(
        service_url="http://proof-service.test",
        api_key="secret-proof-key",
        case_manifest=manifest_path,
        output_root=tmp_path / "evidence",
        timeout_seconds=30.0,
    )


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url="http://proof-service.test",
        transport=httpx.MockTransport(handler),
        timeout=30.0,
    )


def _readyz_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "ready": True,
            "service_revision": "abc123",
            "service_profile": "production",
        },
    )
