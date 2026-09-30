"""Shared Service API v2 audio transcript-bundle runtime fixtures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, TypeAlias

import httpx2
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    AudioTranscriptionSidecarClient,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_KEY = "secret-key"
_MultipartFieldValue: TypeAlias = (
    IO[bytes]
    | bytes
    | str
    | tuple[str | None, IO[bytes] | bytes | str]
    | tuple[str | None, IO[bytes] | bytes | str, str | None]
    | tuple[str | None, IO[bytes] | bytes | str, str | None, Mapping[str, str]]
)
_MultipartFiles: TypeAlias = list[tuple[str, _MultipartFieldValue]]


def _client(tmp_path: Path, *, sidecar: AudioTranscriptionSidecarClient) -> TestClient:
    return TestClient(_app(tmp_path, sidecar=sidecar))


def _app(tmp_path: Path, *, sidecar: AudioTranscriptionSidecarClient) -> FastAPI:
    return create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            run_jobs_on_submit=True,
            processing_delay_seconds=0.0,
            enable_runtime_telemetry_calls=False,
        ),
        audio_transcription_sidecar=sidecar,
    )


def _post_audio_job(
    *,
    client: TestClient,
    idempotency_key: str,
    wait_seconds: int,
) -> httpx2.Response:
    payload = _audio_job_spec()
    files: _MultipartFiles = [
        ("file", ("teacher-meeting.m4a", b"audio bytes", "application/octet-stream")),
        ("job_spec", (None, json.dumps(payload))),
    ]
    response: httpx2.Response = client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers={**_headers(), "Idempotency-Key": idempotency_key},
        files=files,
    )
    return response


def _stored_audio_job(tmp_path: Path) -> StoredJobV2:
    raw_dir = tmp_path / "raw"
    artifact_dir = tmp_path / "artifacts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    upload_path = raw_dir / "teacher-meeting.m4a"
    upload_path.write_bytes(b"audio bytes")
    now = datetime.now(UTC)
    return StoredJobV2(
        job_id="job-v2-audio-runtime-test",
        spec=JobSpecV2.model_validate(_audio_job_spec()),
        source_filename="teacher-meeting.m4a",
        source_format=SourceFormatV2.AUDIO,
        output_format=OutputFormatV2.TRANSCRIPT_BUNDLE,
        upload_path=upload_path,
        resources_zip_path=None,
        reference_docx_path=None,
        artifact_path=artifact_dir / "transcript_json.json",
        status=JobStatus.RUNNING,
        created_at=now,
        updated_at=now,
        expires_at=None,
        progress_stage="running",
    )


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": _API_KEY,
        "X-Correlation-ID": "corr-audio-runtime",
    }


def _audio_job_spec() -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "teacher-meeting.m4a", "format": "audio"},
        "conversion": {"output_format": "transcript_bundle"},
        "execution": {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 7200,
        },
        "audio_transcription_options": {
            "language": "auto",
            "diarization": {
                "mode": "auto",
                "num_speakers": None,
                "min_speakers": None,
                "max_speakers": None,
            },
            "max_duration_seconds": 7200,
            "output_artifacts": ["json"],
        },
        "retention": {"pin": False},
    }
