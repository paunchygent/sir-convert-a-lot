"""Transcript formatter replay Service API v2 behavior.

Purpose:
    Prove saved canonical transcript JSON can be replayed through the normal
    v2 job lifecycle with typed speaker display-name overlays and product-
    neutral formatter artifacts.

Relationships:
    - Exercises the public `transcript_json -> transcript_bundle` route.
    - Exercises the pure replay formatter projection without invoking STT,
      diarization, alignment, sidecar, codec, or source-media modules.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import IO, TypeAlias

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
    infer_source_format_from_filename_v2,
)
from tests.sir_convert_a_lot.test_audio_transcript_bundle_runtime_v2 import (
    _API_KEY,
    _headers,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "transcript_formatter_canonical.json"
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


def test_replay_options_are_strict_and_route_is_registered() -> None:
    registry = build_create_job_route_registry_v2()
    route_keys = {
        (key.source_format.value, key.output_format.value)
        for key in registry.registered_route_keys()
    }
    spec = JobSpecV2.model_validate(_replay_job_spec())

    assert ("transcript_json", "transcript_bundle") in route_keys
    assert infer_source_format_from_filename_v2("saved-transcript.json") is not None
    assert spec.source.format.value == "transcript_json"
    assert spec.conversion.output_format.value == "transcript_bundle"
    assert spec.transcript_formatter_options is not None
    assert spec.transcript_formatter_options.requested_artifacts == ("txt", "md", "vtt", "srt")


@pytest.mark.parametrize(
    ("patch", "expected_text"),
    [
        ({"schema_version": "other"}, "transcript_formatter_replay_v1"),
        ({"requested_artifacts": ["json"]}, "unsupported transcript formatter artifact"),
        ({"requested_artifacts": []}, "at least one requested artifact"),
        ({"speaker_label_overrides": []}, "at least one speaker label override"),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Karin"},
                ]
            },
            "duplicate canonical speaker label",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
                    {"canonical_speaker_label": "SPEAKER_01", "display_name": "Anna"},
                ]
            },
            "duplicate display name",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "   "}
                ]
            },
            "display name must not be empty",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna\nA"}
                ]
            },
            "control characters",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "A" * 121}
                ]
            },
            "at most 120 characters",
        ),
        ({"unexpected": True}, "Extra inputs are not permitted"),
    ],
)
def test_replay_options_reject_invalid_shapes(
    patch: Mapping[str, object],
    expected_text: str,
) -> None:
    payload = _replay_job_spec(options_patch=patch)

    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(payload)

    assert expected_text in str(error_info.value)


def test_replay_api_produces_overlay_formatter_artifacts_without_json_named_artifact(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    client = TestClient(app)

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-transcript-replay-success",
        wait_seconds=20,
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.SUCCEEDED.value
    assert job["source_format"] == "transcript_json"
    assert job["output_format"] == "transcript_bundle"
    job_id = job["job_id"]

    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=_headers())
    assert result_response.status_code == 200
    result = result_response.json()["result"]
    assert result["artifact"]["filename"] == "transcript_replay_bundle_manifest.json"
    assert result["conversion_metadata"]["pipeline_used"] == (
        "transcript_json_to_transcript_bundle_replay_v2"
    )
    assert result["conversion_metadata"]["backend_used"] is None
    assert result["conversion_metadata"]["acceleration_used"] is None

    singular_response = client.get(f"/v2/convert/jobs/{job_id}/artifact", headers=_headers())
    assert singular_response.status_code == 200
    singular_payload = singular_response.json()
    assert singular_payload["schema_version"] == "transcript_formatter_replay_result_v1"
    serialized_primary = json.dumps(singular_payload, sort_keys=True)
    assert "Hello <there>" not in serialized_primary
    assert "Anna Andersson" not in serialized_primary
    assert "transcript_json" not in {
        entry["artifact_key"] for entry in singular_payload["artifacts"]
    }

    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=_headers())
    assert manifest_response.status_code == 200
    entries = _artifact_entries(manifest_response.json())
    assert "transcript_json" not in entries
    assert entries["transcript_txt"]["availability"] == "available"
    assert entries["transcript_md"]["availability"] == "available"
    assert entries["transcript_vtt"]["availability"] == "available"
    assert entries["transcript_srt"]["availability"] == "available"

    txt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_txt",
        headers=_headers(),
    )
    md_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_md",
        headers=_headers(),
    )
    vtt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_vtt",
        headers=_headers(),
    )
    srt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_srt",
        headers=_headers(),
    )
    json_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_json",
        headers=_headers(),
    )

    assert txt_response.status_code == 200
    assert "Anna Andersson" in txt_response.text
    assert "Karin Karlsson" in txt_response.text
    assert "SPEAKER_00" not in txt_response.text
    assert md_response.status_code == 200
    assert "| Anna Andersson |" in md_response.text
    assert vtt_response.status_code == 200
    assert "Anna Andersson: Hello" in vtt_response.text
    assert srt_response.status_code == 200
    assert "Karin Karlsson: Adjacent cue" in srt_response.text
    assert json_response.status_code == 404
    assert json_response.json()["error"]["code"] == "transcript_replay_artifact_unavailable"


@pytest.mark.parametrize(
    ("payload_kind", "spec_patch", "expected_code"),
    [
        ("canonical", {"retention": {"pin": True}}, "validation_error"),
        (
            "canonical",
            {
                "transcript_formatter_options": {
                    "schema_version": "transcript_formatter_replay_v1",
                    "requested_artifacts": ["txt"],
                    "speaker_label_overrides": [
                        {"canonical_speaker_label": "UNKNOWN", "display_name": "Anna"}
                    ],
                }
            },
            "transcript_formatter_replay_invalid",
        ),
        ("malformed", {}, "transcript_formatter_replay_invalid"),
        ("partial", {}, "transcript_formatter_replay_invalid"),
    ],
)
def test_replay_invalid_requests_fail_before_artifact_generation(
    tmp_path: Path,
    payload_kind: str,
    spec_patch: Mapping[str, object],
    expected_code: str,
) -> None:
    app = _app(tmp_path)
    client = TestClient(app)

    response = _post_replay_job(
        client=client,
        idempotency_key=f"idem-transcript-replay-invalid-{expected_code}-{payload_kind}",
        wait_seconds=20,
        file_bytes=_invalid_payload_bytes(payload_kind),
        spec=_replay_job_spec(top_level_patch=spec_patch),
    )

    if expected_code == "validation_error":
        assert response.status_code == 422
        assert response.json()["error"]["code"] == expected_code
        return

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.FAILED.value
    job_id = job["job_id"]
    stored_job = app.state.runtime_v2.get_job(job_id)
    assert stored_job is not None
    assert stored_job.failure_code == expected_code
    assert not (stored_job.artifact_path.parent / "transcript_txt.txt").exists()
    assert not (stored_job.artifact_path.parent / "transcript_md.md").exists()


def test_replay_unrequested_artifacts_fail_with_route_specific_code(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path))
    spec = _replay_job_spec(options_patch={"requested_artifacts": ["txt"]})

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-transcript-replay-unrequested-artifact",
        wait_seconds=20,
        spec=spec,
    )

    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=_headers())
    assert manifest_response.status_code == 200
    entries = _artifact_entries(manifest_response.json())
    assert entries["transcript_txt"]["availability"] == "available"
    assert entries["transcript_md"]["availability"] == "unrequested"
    assert entries["transcript_md"]["unavailable_code"] == (
        "transcript_replay_artifact_unavailable"
    )

    md_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_md",
        headers=_headers(),
    )

    assert md_response.status_code == 409
    error = md_response.json()["error"]
    assert error["code"] == "transcript_replay_artifact_unavailable"
    assert error["details"]["availability"] == "unrequested"


def test_replay_fast_lane_terminal_job_rejects_cancel_through_v2_lifecycle(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path, run_jobs_on_submit=False))

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-transcript-replay-cancel",
        wait_seconds=0,
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.SUCCEEDED.value
    job_id = job["job_id"]

    cancel_response = client.post(f"/v2/convert/jobs/{job_id}/cancel", headers=_headers())
    assert cancel_response.status_code == 409
    assert cancel_response.json()["error"]["code"] == "job_not_cancelable"

    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=_headers())
    assert result_response.status_code == 200
    assert result_response.json()["status"] == JobStatus.SUCCEEDED.value


def test_replay_runtime_does_not_touch_audio_sidecar(tmp_path: Path) -> None:
    sidecar = _ExplodingAudioSidecar()
    client = TestClient(
        create_app(
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
    )

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-transcript-replay-no-sidecar",
        wait_seconds=20,
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    assert sidecar.calls == []


class _ExplodingAudioSidecar:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def health(self) -> Mapping[str, object]:
        self.calls.append("health")
        raise AssertionError("replay must not call audio sidecar health")

    def capabilities(self) -> Mapping[str, object]:
        self.calls.append("capabilities")
        raise AssertionError("replay must not call audio sidecar capabilities")

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        self.calls.append("probe_media")
        raise AssertionError("replay must not probe media")

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        self.calls.append("diarize")
        raise AssertionError("replay must not diarize")

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        self.calls.append("transcribe_chunk")
        raise AssertionError("replay must not transcribe")

    def cancel(self, request_handle: str) -> None:
        del request_handle
        self.calls.append("cancel")

    def finalize(self, request_handle: str) -> None:
        del request_handle
        self.calls.append("finalize")


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
