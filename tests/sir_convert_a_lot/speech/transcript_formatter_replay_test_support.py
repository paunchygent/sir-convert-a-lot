"""Shared Service API v2 fixtures and payload builders for transcript formatter replay tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import IO, TypeAlias

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.speech.audio_transcript_bundle_runtime_test_support import (
    _API_KEY,
    _headers,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "transcript_formatter_canonical.json"
)
_MultipartFieldValue: TypeAlias = (
    IO[bytes]
    | bytes
    | str
    | tuple[str | None, IO[bytes] | bytes | str]
    | tuple[str | None, IO[bytes] | bytes | str, str | None]
    | tuple[str | None, IO[bytes] | bytes | str, str | None, Mapping[str, str]]
)
_MultipartFiles: TypeAlias = list[tuple[str, _MultipartFieldValue]]


def _client(tmp_path: Path) -> TestClient:
    return TestClient(_app(tmp_path))


def _app(tmp_path: Path, *, run_jobs_on_submit: bool = True) -> FastAPI:
    return create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            run_jobs_on_submit=run_jobs_on_submit,
            processing_delay_seconds=0.0,
            enable_runtime_telemetry_calls=False,
        )
    )


def _post_replay_job(
    *,
    client: TestClient,
    idempotency_key: str,
    wait_seconds: int,
    file_bytes: bytes | None = None,
    spec: dict[str, object] | None = None,
    correlation_id: str | None = None,
) -> Response:
    payload = spec if spec is not None else _replay_job_spec()
    files: _MultipartFiles = [
        ("file", ("saved-transcript.json", file_bytes or _canonical_bytes(), "application/json")),
        ("job_spec", (None, json.dumps(payload))),
    ]
    headers = {**_headers(), "Idempotency-Key": idempotency_key}
    if correlation_id is not None:
        headers["X-Correlation-ID"] = correlation_id
    response: Response = client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers=headers,
        files=files,
    )
    return response


def _replay_job_spec(
    *,
    options_patch: Mapping[str, object] | None = None,
    top_level_patch: Mapping[str, object] | None = None,
) -> dict[str, object]:
    options: dict[str, object] = {
        "schema_version": "transcript_formatter_replay_v1",
        "requested_artifacts": ["txt", "md", "vtt", "srt"],
        "speaker_label_overrides": [
            {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna Andersson"},
            {"canonical_speaker_label": "SPEAKER_01", "display_name": "Karin Karlsson"},
        ],
    }
    if options_patch is not None:
        options.update(options_patch)
    payload: dict[str, object] = {
        "api_version": "v2",
        "source": {
            "kind": "upload",
            "filename": "saved-transcript.json",
            "format": "transcript_json",
        },
        "conversion": {"output_format": "transcript_bundle"},
        "transcript_formatter_options": options,
        "retention": {"pin": False},
    }
    if top_level_patch is not None:
        payload.update(top_level_patch)
    return payload


def _artifact_entries(manifest: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise AssertionError("Manifest must include an artifacts list.")
    entries: dict[str, Mapping[str, object]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise AssertionError("Artifact manifest entries must be objects.")
        key = artifact.get("artifact_key")
        if not isinstance(key, str):
            raise AssertionError("Artifact manifest entry must include artifact_key.")
        entries[key] = artifact
    return entries


def _canonical_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def _partial_canonical_bytes() -> bytes:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("Canonical fixture must decode to a JSON object.")
    diarization = payload.get("diarization")
    if not isinstance(diarization, dict):
        raise AssertionError("Canonical fixture must include diarization object.")
    diarization["status"] = "partial"
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _invalid_payload_bytes(payload_kind: str) -> bytes:
    if payload_kind == "canonical":
        return _canonical_bytes()
    if payload_kind == "malformed":
        return b"{not-json"
    if payload_kind == "partial":
        return _partial_canonical_bytes()
    raise AssertionError(f"Unsupported invalid payload kind: {payload_kind}")
