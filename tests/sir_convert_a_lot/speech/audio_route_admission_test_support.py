"""Shared builders for audio transcription Service API v2 route-admission tests.

Purpose:
    Provide the typed test client, audio job-spec builder, and multipart audio
    job submission helper shared by the audio JobSpec, route-admission, and
    route-capacity test modules.

Relationships:
    - Builds the app through `interfaces.http_api.create_app` with a gateway
      identity public key from `tests.sir_convert_a_lot.identity_test_support`.
    - Posts to the `/v2/convert/jobs` route owned by
      `interfaces.http_create_job_routes_v2`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import IO, TypeAlias

from fastapi.testclient import TestClient
from httpx2 import Response

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.identity_test_support import API_KEY, IdentitySigner
from tests.sir_convert_a_lot.identity_test_support import headers as identity_headers

KEY_ID = "gateway-identity-rs256-v1"
MultipartFieldValue: TypeAlias = (
    IO[bytes]
    | bytes
    | str
    | tuple[str | None, IO[bytes] | bytes | str]
    | tuple[str | None, IO[bytes] | bytes | str, str | None]
    | tuple[str | None, IO[bytes] | bytes | str, str | None, Mapping[str, str]]
)
MultipartFiles: TypeAlias = list[tuple[str, MultipartFieldValue]]


def client(
    tmp_path: Path,
    identity: IdentitySigner,
    *,
    run_jobs_on_submit: bool,
    max_upload_bytes: int = 50 * 1024 * 1024,
) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key=API_KEY,
            data_root=tmp_path / "service_data",
            max_upload_bytes=max_upload_bytes,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            run_jobs_on_submit=run_jobs_on_submit,
            internal_identity_public_keys={KEY_ID: identity.public_key_pem},
        )
    )
    return TestClient(app)


def post_audio_job(
    *,
    client: TestClient,
    identity: IdentitySigner,
    subject: str,
    idempotency_key: str,
    spec: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    file_bytes: bytes = b"audio bytes",
) -> Response:
    request_headers = headers or identity_headers(
        identity,
        subject=subject,
        grants={"sir-convert:jobs:create"},
    )
    request_headers["Idempotency-Key"] = idempotency_key
    payload = spec if spec is not None else audio_job_spec(filename="teacher-meeting.m4a")
    file_name = source_filename_from_payload(payload)
    files: MultipartFiles = [
        ("file", (file_name, file_bytes, "application/octet-stream")),
        ("job_spec", (None, json.dumps(payload))),
    ]
    response: Response = client.post("/v2/convert/jobs", headers=request_headers, files=files)
    return response


def audio_job_spec(
    *,
    filename: str = "teacher-meeting.m4a",
    language: str = "auto",
    diarization: Mapping[str, object] | None = None,
    audio_options_patch: Mapping[str, object] | None = None,
    retention_pin: bool = False,
    include_audio_options: bool = True,
) -> dict[str, object]:
    if diarization is None:
        diarization = {
            "mode": "auto",
            "num_speakers": None,
            "min_speakers": None,
            "max_speakers": None,
        }
    audio_options: dict[str, object] = {
        "language": language,
        "diarization": dict(diarization),
        "max_duration_seconds": 7200,
        "output_artifacts": ["json"],
    }
    if audio_options_patch is not None:
        audio_options.update(audio_options_patch)
    payload: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": "audio"},
        "conversion": {"output_format": "transcript_bundle"},
        "execution": {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 7200,
        },
        "retention": {"pin": retention_pin},
    }
    if include_audio_options:
        payload["audio_transcription_options"] = audio_options
    return payload


def source_filename_from_payload(payload: Mapping[str, object]) -> str:
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise AssertionError("Audio job payload must include a source object.")
    filename = source.get("filename")
    if not isinstance(filename, str):
        raise AssertionError("Audio job payload source filename must be a string.")
    return filename
