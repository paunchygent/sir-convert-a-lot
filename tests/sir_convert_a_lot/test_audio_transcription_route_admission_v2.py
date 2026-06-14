"""Audio transcription Service API v2 route-admission behavior.

Purpose:
    Prove `audio -> transcript_bundle` is admitted only through the governed
    Service API v2 request, identity, option, and idempotency boundaries.

Relationships:
    - Exercises `domain.specs_v2` and `domain.service_routes_v2` as the route
      validation authority.
    - Exercises `interfaces.http_create_job_routes_v2` and
      `interfaces.http_routes_jobs_v2` without invoking STT sidecars or
      transcript artifact persistence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import IO, TypeAlias

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
    infer_source_format_from_filename_v2,
)
from tests.sir_convert_a_lot.digiexam_migration_bundle_api_fixtures import (
    _API_KEY,
    _headers,
    _IdentitySigner,
)

_KEY_ID = "gateway-identity-rs256-v1"
AUDIO_TRANSCRIPTION_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs/converters/audio-transcription-service-api-artifact-contract.md"
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


@pytest.mark.parametrize(
    ("language", "diarization"),
    [
        (
            "auto",
            {
                "mode": "auto",
                "num_speakers": None,
                "min_speakers": None,
                "max_speakers": None,
            },
        ),
        (
            "sv",
            {
                "mode": "known_speaker_count",
                "num_speakers": 2,
                "min_speakers": None,
                "max_speakers": None,
            },
        ),
        (
            "en",
            {
                "mode": "speaker_range",
                "num_speakers": None,
                "min_speakers": 1,
                "max_speakers": 4,
            },
        ),
    ],
)
def test_job_spec_accepts_audio_transcript_bundle_public_options(
    language: str,
    diarization: Mapping[str, object],
) -> None:
    spec = JobSpecV2.model_validate(_audio_job_spec(language=language, diarization=diarization))

    assert spec.source.format.value == "audio"
    assert spec.conversion.output_format.value == "transcript_bundle"
    assert spec.audio_transcription_options is not None
    assert spec.audio_transcription_options.language == language
    assert spec.audio_transcription_options.output_artifacts == ("json",)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (("txt",), ("json", "txt")),
        (("json", "srt"), ("json", "srt")),
        (("vtt", "json", "vtt", "md"), ("json", "md", "vtt")),
        (("json", "txt", "md", "vtt", "srt"), ("json", "txt", "md", "vtt", "srt")),
    ],
)
def test_job_spec_accepts_and_normalizes_audio_formatter_output_artifacts(
    requested: tuple[str, ...],
    expected: tuple[str, ...],
) -> None:
    spec = JobSpecV2.model_validate(
        _audio_job_spec(audio_options_patch={"output_artifacts": requested})
    )

    assert spec.audio_transcription_options is not None
    assert spec.audio_transcription_options.output_artifacts == expected


@pytest.mark.parametrize(
    ("patch", "expected_code"),
    [
        ({"language": "fr"}, "audio_public_options_unsupported"),
        ({"output_artifacts": ("json", "pdf")}, "audio_public_options_unsupported"),
        ({"max_duration_seconds": 0}, "audio_duration_exceeded"),
        ({"max_duration_seconds": 7201}, "audio_duration_exceeded"),
        ({"model_id": "provider/raw-stt-model"}, "audio_public_options_unsupported"),
    ],
)
def test_job_spec_rejects_invalid_audio_public_options(
    patch: Mapping[str, object],
    expected_code: str,
) -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(audio_options_patch=patch))

    assert expected_code in str(error_info.value)


@pytest.mark.parametrize(
    "diarization",
    [
        {
            "mode": "auto",
            "num_speakers": 2,
            "min_speakers": None,
            "max_speakers": None,
        },
        {
            "mode": "known_speaker_count",
            "num_speakers": 0,
            "min_speakers": None,
            "max_speakers": None,
        },
        {
            "mode": "speaker_range",
            "num_speakers": None,
            "min_speakers": 4,
            "max_speakers": 2,
        },
    ],
)
def test_job_spec_rejects_invalid_audio_diarization_options(
    diarization: Mapping[str, object],
) -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(diarization=diarization))

    assert "audio_diarization_options_invalid" in str(error_info.value)


def test_job_spec_rejects_audio_retention_pin() -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(retention_pin=True))

    assert "audio_retention_pin_unsupported" in str(error_info.value)


def test_job_spec_requires_audio_transcription_options_for_audio_route() -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(include_audio_options=False))

    assert "audio_transcription_options is required" in str(error_info.value)


def test_job_spec_requires_audio_execution_with_route_message() -> None:
    payload = _audio_job_spec()
    payload.pop("execution")

    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(payload)

    error_text = str(error_info.value)
    assert "execution is required for audio transcription routes" in error_text
    assert "source.format is 'pdf'" not in error_text


def test_create_job_registry_registers_audio_transcript_bundle_route() -> None:
    registry = build_create_job_route_registry_v2()
    route_keys = {
        (key.source_format.value, key.output_format.value)
        for key in registry.registered_route_keys()
    }

    assert ("audio", "transcript_bundle") in route_keys


@pytest.mark.parametrize(
    "filename",
    [
        "recording.wav",
        "recording.mp3",
        "recording.m4a",
        "recording.aac",
        "recording.flac",
        "recording.ogg",
        "recording.opus",
        "recording.webm",
        "recording.aiff",
        "recording.mp4",
        "recording.mov",
        "recording.mkv",
    ],
)
def test_filename_inference_maps_audio_and_video_containers_to_audio(filename: str) -> None:
    inferred = infer_source_format_from_filename_v2(filename)

    assert inferred is not None
    assert inferred.value == "audio"


def test_create_job_admits_identity_scoped_audio_when_submit_dispatch_is_disabled(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-create",
        idempotency_key="idem-audio-admission",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job"]["status"] == JobStatus.QUEUED.value
    assert payload["job"]["source_format"] == "audio"
    assert payload["job"]["output_format"] == "transcript_bundle"


def test_audio_contract_initial_request_shape_is_admitted(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)
    spec = _audio_contract_initial_request_shape()

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-contract-audio",
        idempotency_key="idem-audio-contract-shape",
        spec=spec,
        file_bytes=b"contract audio bytes",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job"]["status"] == JobStatus.QUEUED.value
    assert payload["job"]["source_format"] == "audio"
    assert payload["job"]["output_format"] == "transcript_bundle"


def test_create_job_admits_audio_api_key_only_operator_call(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-api-key-only",
        idempotency_key="idem-audio-api-key-only",
        headers={
            "X-API-Key": _API_KEY,
            "X-Correlation-ID": "corr-audio-api-key-only",
            "Idempotency-Key": "idem-audio-api-key-only",
        },
    )

    assert response.status_code == 202
    job_id = response.json()["job"]["job_id"]

    read_response = client.get(
        f"/v2/convert/jobs/{job_id}",
        headers={"X-API-Key": _API_KEY},
    )
    assert read_response.status_code == 200
    assert read_response.json()["job"]["status"] == JobStatus.QUEUED.value


def test_create_job_audio_upload_uses_route_specific_size_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.sir_convert_a_lot.interfaces import http_create_job_routes_v2

    monkeypatch.setattr(http_create_job_routes_v2, "MAX_AUDIO_UPLOAD_BYTES", 8)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False, max_upload_bytes=4)

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-route-cap",
        idempotency_key="idem-audio-route-cap",
        file_bytes=b"12345",
    )

    assert response.status_code == 202
    assert response.json()["job"]["status"] == JobStatus.QUEUED.value


def test_create_job_audio_upload_over_route_cap_uses_audio_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.sir_convert_a_lot.interfaces import http_create_job_routes_v2

    monkeypatch.setattr(http_create_job_routes_v2, "MAX_AUDIO_UPLOAD_BYTES", 8)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False, max_upload_bytes=4)

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-route-cap-over",
        idempotency_key="idem-audio-route-cap-over",
        file_bytes=b"123456789",
    )

    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "audio_upload_size_exceeded"
    assert error["details"] == {"limit_bytes": 8}


def test_create_job_audio_idempotency_replays_and_conflicts_on_option_drift(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)
    first_spec = _audio_job_spec(language="sv")
    changed_spec = _audio_job_spec(language="en")

    first_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-idempotent-audio",
        idempotency_key="idem-audio-options",
        spec=first_spec,
    )
    replay_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-idempotent-audio",
        idempotency_key="idem-audio-options",
        spec=first_spec,
    )
    conflict_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-idempotent-audio",
        idempotency_key="idem-audio-options",
        spec=changed_spec,
    )

    assert first_response.status_code == 202
    assert replay_response.status_code == 202
    assert replay_response.headers["X-Idempotent-Replay"] == "true"
    assert replay_response.json()["job"]["job_id"] == first_response.json()["job"]["job_id"]
    assert conflict_response.status_code == 409
    assert (
        conflict_response.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"
    )


def test_audio_identity_owner_scope_is_required_for_job_reads(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)
    create_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-owner",
        idempotency_key="idem-audio-owner",
    )
    job_id = create_response.json()["job"]["job_id"]

    other_headers = _headers(
        identity,
        subject="teacher-audio-other",
        grants={"sir-convert:jobs:read-own"},
    )
    read_response = client.get(f"/v2/convert/jobs/{job_id}", headers=other_headers)

    assert create_response.status_code == 202
    assert read_response.status_code == 403
    assert read_response.json()["error"]["code"] == "job_access_denied"


def test_create_job_rejects_third_active_audio_job_at_route_capacity(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-capacity",
        idempotency_key="idem-audio-capacity-first",
    )
    second_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-capacity",
        idempotency_key="idem-audio-capacity-second",
    )
    third_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-capacity",
        idempotency_key="idem-audio-capacity-third",
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert third_response.status_code == 429
    error = third_response.json()["error"]
    assert error["code"] == "audio_route_capacity_exceeded"
    assert error["details"] == {
        "exhausted_cap": "max_active_stt_jobs_per_instance",
    }


def test_audio_route_capacity_admission_does_not_resweep_for_each_retained_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audio admission must keep retained-job scans bounded before returning 202."""
    sweep_calls = 0
    original_sweep_expired = JobStoreV2.sweep_expired

    def _counting_sweep_expired(self: JobStoreV2) -> None:
        nonlocal sweep_calls
        sweep_calls += 1
        original_sweep_expired(self)

    monkeypatch.setattr(JobStoreV2, "sweep_expired", _counting_sweep_expired)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-sweep-capacity",
        idempotency_key="idem-audio-sweep-first",
    )
    second_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-sweep-capacity",
        idempotency_key="idem-audio-sweep-second",
    )
    sweep_calls = 0
    third_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-sweep-capacity",
        idempotency_key="idem-audio-sweep-third",
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert third_response.status_code == 429
    assert sweep_calls == 0


def test_existing_markdown_pdf_route_remains_registered() -> None:
    registry = build_create_job_route_registry_v2()
    route_keys = {
        (key.source_format.value, key.output_format.value)
        for key in registry.registered_route_keys()
    }

    assert ("md", "pdf") in route_keys


def _client(
    tmp_path: Path,
    identity: _IdentitySigner,
    *,
    run_jobs_on_submit: bool,
    max_upload_bytes: int = 50 * 1024 * 1024,
) -> TestClient:
    app = create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            max_upload_bytes=max_upload_bytes,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            run_jobs_on_submit=run_jobs_on_submit,
            internal_identity_public_keys={_KEY_ID: identity.public_key_pem},
        )
    )
    return TestClient(app)


def _post_audio_job(
    *,
    client: TestClient,
    identity: _IdentitySigner,
    subject: str,
    idempotency_key: str,
    spec: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    file_bytes: bytes = b"audio bytes",
) -> Response:
    request_headers = headers or _headers(
        identity,
        subject=subject,
        grants={"sir-convert:jobs:create"},
    )
    request_headers["Idempotency-Key"] = idempotency_key
    payload = spec if spec is not None else _audio_job_spec(filename="teacher-meeting.m4a")
    file_name = _source_filename_from_payload(payload)
    files: _MultipartFiles = [
        ("file", (file_name, file_bytes, "application/octet-stream")),
        ("job_spec", (None, json.dumps(payload))),
    ]
    return client.post("/v2/convert/jobs", headers=request_headers, files=files)


def _audio_job_spec(
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


def _source_filename_from_payload(payload: Mapping[str, object]) -> str:
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise AssertionError("Audio job payload must include a source object.")
    filename = source.get("filename")
    if not isinstance(filename, str):
        raise AssertionError("Audio job payload source filename must be a string.")
    return filename


def _audio_contract_initial_request_shape() -> dict[str, object]:
    source = AUDIO_TRANSCRIPTION_CONTRACT_PATH.read_text(encoding="utf-8")
    section_start = source.index("## Initial Request Shape")
    fence_start = source.index("```json", section_start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("```", payload_start)
    payload = json.loads(source[payload_start:payload_end])
    if not isinstance(payload, dict):
        raise AssertionError("Audio contract request shape must decode to a JSON object.")
    return payload
