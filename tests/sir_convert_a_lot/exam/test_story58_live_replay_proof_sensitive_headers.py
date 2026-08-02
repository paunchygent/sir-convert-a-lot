"""Tests for Story 58 live proof sensitive request headers.

Purpose:
    Prove the Story 58 proof runner can consume operator-private transport
    headers without retaining their values or file locations in evidence.

Relationships:
    - Exercises the public Story 58 proof runner boundary.
    - Protects the live proof operator input contract for sensitive HuleEdu
      identity and grant headers.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof import (
    Story58LiveReplayProofSettings,
    run_story58_live_replay_proof,
)


def test_story58_live_replay_proof_loads_sensitive_headers_without_retention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sensitive header sources should affect the live request, not retained proof."""
    private_dir = tmp_path / "private-header-inputs"
    private_dir.mkdir()
    header_file = private_dir / "story58-private-headers.json"
    header_file.write_text(
        json.dumps({"X-HuleEdu-Internal-Grant": "grant-envelope-secret"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HULEEDU_IDENTITY_CONTEXT", "identity-context-secret")
    monkeypatch.setenv("STORY58_PRIVATE_HEADERS_FILE", header_file.as_posix())
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "generic_idempotency_preservation_smoke",
                        "label": "generic smoke with private headers",
                        "requests": [
                            {
                                "label": "generic route",
                                "method": "GET",
                                "path": "/generic",
                                "headers": {"Idempotency-Key": "non-secret-proof-key"},
                                "header_env": {
                                    "X-HuleEdu-Identity-Context": ("HULEEDU_IDENTITY_CONTEXT")
                                },
                                "headers_file_env": "STORY58_PRIVATE_HEADERS_FILE",
                                "expect": {
                                    "http_status": 200,
                                    "idempotency_state": "fresh_admission",
                                },
                            }
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
        if request.method == "GET" and request.url.path == "/generic":
            assert request.headers["Idempotency-Key"] == "non-secret-proof-key"
            assert request.headers["X-HuleEdu-Identity-Context"] == "identity-context-secret"
            assert request.headers["X-HuleEdu-Internal-Grant"] == "grant-envelope-secret"
            return httpx.Response(
                200,
                json={
                    "job": {"job_id": "jobv2_private_header_smoke", "status": "succeeded"},
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
            api_key="api-key-secret",
            case_manifest=manifest_path,
            output_root=tmp_path / "evidence",
            timeout_seconds=30.0,
        ),
        client=client,
    )

    retained_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in summary_path.parent.rglob("*")
        if path.is_file()
    )
    assert "jobv2_private_header_smoke" in retained_text
    assert "identity-context-secret" not in retained_text
    assert "grant-envelope-secret" not in retained_text
    assert header_file.as_posix() not in retained_text
    assert "story58-private-headers.json" not in retained_text
