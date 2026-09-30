"""Audio transcription Service API v2 route-admission behavior.

Purpose:
    Prove `audio -> transcript_bundle` is registered, inferred from media
    filenames, and admitted over HTTP only through the governed identity,
    API-key, owner-scope, and idempotency boundaries.

Relationships:
    - Exercises `interfaces.http_create_job_routes_v2` and
      `interfaces.http_routes_jobs_v2` without invoking STT sidecars or
      transcript artifact persistence.
    - JobSpec validation lives in `test_audio_transcription_job_spec_v2`;
      upload-size and capacity admission live in
      `test_audio_transcription_route_capacity_v2`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
    infer_source_format_from_filename_v2,
)
from tests.sir_convert_a_lot.identity_test_support import (
    API_KEY as _API_KEY,
)
from tests.sir_convert_a_lot.identity_test_support import (
    IdentitySigner as _IdentitySigner,
)
from tests.sir_convert_a_lot.identity_test_support import (
    headers as _headers,
)
from tests.sir_convert_a_lot.speech.audio_route_admission_test_support import (
    audio_job_spec as _audio_job_spec,
)
from tests.sir_convert_a_lot.speech.audio_route_admission_test_support import (
    client as _client,
)
from tests.sir_convert_a_lot.speech.audio_route_admission_test_support import (
    post_audio_job as _post_audio_job,
)

AUDIO_TRANSCRIPTION_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "reference"
    / (
        "ref-sircon-general-audio-transcription-service-api-artifact-contract-"
        "audio-transcription-service-api-artifact-contract.md"
    )
)


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


def test_existing_markdown_pdf_route_remains_registered() -> None:
    registry = build_create_job_route_registry_v2()
    route_keys = {
        (key.source_format.value, key.output_format.value)
        for key in registry.registered_route_keys()
    }

    assert ("md", "pdf") in route_keys


def _audio_contract_initial_request_shape() -> dict[str, object]:
    source = AUDIO_TRANSCRIPTION_CONTRACT_PATH.read_text(encoding="utf-8")
    section_start = source.index("## Initial Request Shape")
    request_line = source[section_start:].splitlines()[1]
    payload = json.loads(request_line.strip("`"))
    if not isinstance(payload, dict):
        raise AssertionError("Audio contract request shape must decode to a JSON object.")
    return payload
