"""Tests for Story 58 live replay proof invariants.

Purpose:
    Prove the Story 58 proof runner owns matrix-specific evidence checks
    independently from operator-authored manifest expectations.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.story58_live_replay_proof`.
    - Protects retained closeout evidence from loose manifests or unhealthy
      Service API readiness metadata.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof import (
    Story58LiveReplayProofSettings,
    run_story58_live_replay_proof,
)


def test_story58_case_invariants_fail_when_manifest_expectations_are_loose(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "compatible_strict_digiexam_replay",
                        "label": "loose strict replay",
                        "requests": [
                            {
                                "label": "wrong strict replay",
                                "method": "GET",
                                "path": "/strict/wrong",
                                "expect": {"http_status": 200},
                            }
                        ],
                    },
                    {
                        "case_id": "stale_incompatible_digiexam_replay",
                        "label": "loose stale replay",
                        "requests": [
                            {
                                "label": "wrong stale replay",
                                "method": "GET",
                                "path": "/stale/wrong",
                                "expect": {"http_status": 200},
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/readyz":
            return _readyz_response()
        if request.method == "GET" and request.url.path == "/strict/wrong":
            return _job_response(
                route_id="digiexam_dxe_to_examnet_migration_bundle",
                idempotency_state="fresh_admission",
                idempotency_reason=None,
            )
        if request.method == "GET" and request.url.path == "/stale/wrong":
            return _job_response(
                route_id="digiexam_dxe_to_examnet_migration_bundle",
                idempotency_state="service_reattempt",
                idempotency_reason="retryable_failed_terminal",
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    summary = _run_summary(tmp_path=tmp_path, manifest_path=manifest_path, handler=handler)
    cases = _case_map(summary)
    assert cases["compatible_strict_digiexam_replay"]["status"] == "failed"
    assert cases["stale_incompatible_digiexam_replay"]["status"] == "failed"
    assert summary["overall_status"] == "failed"


def test_story58_missing_source_invariant_requires_governed_fail_closed_error(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "cases.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "story58_live_replay_case_manifest_v1",
                "cases": [
                    {
                        "case_id": "missing_source_correction_apply_fail_closed",
                        "label": "loose missing source",
                        "requests": [
                            {
                                "label": "wrong fail closed error",
                                "method": "GET",
                                "path": "/missing-source/wrong",
                                "expect": {"http_status": 409},
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
            return _readyz_response()
        if request.method == "GET" and request.url.path == "/missing-source/wrong":
            return httpx.Response(
                409,
                json={
                    "error": {
                        "code": "idempotency_key_reused_with_different_payload",
                        "retryable": False,
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    summary = _run_summary(tmp_path=tmp_path, manifest_path=manifest_path, handler=handler)
    cases = _case_map(summary)
    assert cases["missing_source_correction_apply_fail_closed"]["status"] == "failed"
    assert summary["overall_status"] == "failed"


def test_story58_readiness_failure_prevents_overall_passed_proof(
    tmp_path: Path,
) -> None:
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
                        "label": "strict replay",
                        "requests": [
                            {
                                "label": "strict replay",
                                "method": "GET",
                                "path": "/strict/right",
                                "expect": {"http_status": 200},
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
            return httpx.Response(500, json={"ready": False})
        if request.method == "GET" and request.url.path == "/strict/right":
            return _job_response(
                route_id="digiexam_dxe_to_examnet_migration_bundle",
                idempotency_state="strict_replay",
                idempotency_reason=None,
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    summary = _run_summary(tmp_path=tmp_path, manifest_path=manifest_path, handler=handler)
    readiness = _object_field(summary, "readiness")
    assert summary["overall_status"] == "failed"
    assert readiness["status"] == "failed"
    assert readiness["http_status"] == 500


def _run_summary(
    *,
    tmp_path: Path,
    manifest_path: Path,
    handler: Callable[[httpx.Request], httpx.Response],
) -> dict[str, object]:
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
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("summary payload was not an object")
    return payload


def _case_map(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    cases = summary.get("cases")
    if not isinstance(cases, list):
        raise AssertionError("summary cases was not a list")

    mapped: dict[str, dict[str, object]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise AssertionError("summary case was not an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str):
            raise AssertionError("summary case was missing a string case_id")
        mapped[case_id] = dict(case)
    return mapped


def _object_field(summary: dict[str, object], field_name: str) -> dict[str, object]:
    value = summary.get(field_name)
    if not isinstance(value, dict):
        raise AssertionError(f"summary field {field_name} was not an object")
    return dict(value)


def _readyz_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "ready": True,
            "service_revision": "abc123",
            "service_profile": "production",
        },
    )


def _job_response(
    *,
    route_id: str,
    idempotency_state: str,
    idempotency_reason: str | None,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "job": {
                "job_id": "jobv2_case",
                "status": "succeeded",
                "route_id": route_id,
            },
            "idempotency": {
                "state": idempotency_state,
                "reason": idempotency_reason,
            },
        },
    )
