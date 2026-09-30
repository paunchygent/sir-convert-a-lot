"""Transcript formatter replay artifact and lifecycle behavior."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.speech.audio_transcript_bundle_runtime_test_support import (
    _API_KEY,
    _headers,
)
from tests.sir_convert_a_lot.speech.transcript_formatter_replay_test_support import (
    _app,
    _artifact_entries,
    _post_replay_job,
    _replay_job_spec,
)


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
