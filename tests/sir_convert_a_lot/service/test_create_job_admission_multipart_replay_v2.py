"""Create-job admission multipart replay regression tests.

Purpose:
    Prove Service API v2 job admission relies on FastAPI-bound multipart
    parameters and does not parse the request form a second time after upload
    binding, protecting downstream STT proof from fixed admission stalls.

Relationships:
    - Exercises `interfaces.http_routes_jobs_v2` through the public
      `POST /v2/convert/jobs` boundary.
    - Guards the Task 365 admission remediation before Hemma proof work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette._utils import AwaitableOrContextManager
from starlette.datastructures import FormData
from starlette.requests import Request as StarletteRequest

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_KEY = "secret-key"
_MultipartFieldValue: TypeAlias = (
    bytes | str | tuple[str | None, bytes | str] | tuple[str | None, bytes | str, str | None]
)
_MultipartFiles: TypeAlias = list[tuple[str, _MultipartFieldValue]]


def test_create_job_admission_uses_bound_multipart_parameters_without_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_form = StarletteRequest.form
    form_call_count = 0

    def guarded_form(
        self: StarletteRequest,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
        max_part_size: int = 1024 * 1024,
    ) -> AwaitableOrContextManager[FormData]:
        nonlocal form_call_count
        form_call_count += 1
        if form_call_count > 1:
            raise AssertionError("create-job admission must not replay multipart form parsing")
        return original_form(
            self,
            max_files=max_files,
            max_fields=max_fields,
            max_part_size=max_part_size,
        )

    monkeypatch.setattr(StarletteRequest, "form", guarded_form)
    client = TestClient(
        create_app(
            ServiceConfig(
                api_key=_API_KEY,
                data_root=tmp_path / "service-data",
                enable_supervisor=False,
                run_jobs_on_submit=False,
                processing_delay_seconds=0.0,
                enable_runtime_telemetry_calls=False,
            )
        )
    )

    response = _post_audio_job(client=client)

    assert response.status_code == 202
    assert form_call_count == 1


def _post_audio_job(*, client: TestClient) -> httpx.Response:
    files: _MultipartFiles = [
        ("file", ("teacher-meeting.m4a", b"audio bytes", "application/octet-stream")),
        ("job_spec", (None, json.dumps(_audio_job_spec()))),
    ]
    response: httpx.Response = client.post(
        "/v2/convert/jobs?wait_seconds=0",
        headers={
            "X-API-Key": _API_KEY,
            "Idempotency-Key": "task-365-no-multipart-replay",
            "X-Correlation-ID": "task-365-no-multipart-replay",
        },
        files=files,
    )
    return response


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
