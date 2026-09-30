"""Audio transcript-bundle runtime and artifact behavior.

Purpose:
    Prove admitted audio transcript-bundle jobs execute through the internal
    STT sidecar boundary and publish only the canonical transcript JSON
    artifact through the Service API v2 lifecycle.

Relationships:
    - Exercises `interfaces.http_routes_jobs_v2` as the public lifecycle
      boundary.
    - Uses a fake sidecar at the production adapter boundary instead of
      backend-native STT or diarization APIs.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_runtime import (
    execute_audio_transcript_bundle_job,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    HttpAudioTranscriptionSidecarClient,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from tests.sir_convert_a_lot.speech.audio_transcript_bundle_runtime_test_support import (
    _API_KEY,
    _app,
    _client,
    _headers,
    _post_audio_job,
    _stored_audio_job,
)
from tests.sir_convert_a_lot.speech.audio_transcript_sidecar_test_doubles import (
    _FakeAudioTranscriptionSidecar,
    _healthy_sidecar,
    _ready_capabilities,
)


def test_audio_job_persists_transcript_json_and_named_artifact(tmp_path: Path) -> None:
    sidecar = _FakeAudioTranscriptionSidecar()
    client = _client(tmp_path, sidecar=sidecar)

    create_response = _post_audio_job(
        client=client,
        idempotency_key="idem-audio-runtime-success",
        wait_seconds=20,
    )

    assert create_response.status_code == 200
    job = create_response.json()["job"]
    assert job["status"] == "succeeded"
    assert job["progress"]["stage"] == "succeeded"
    assert job["progress"]["total_pages"] is None
    assert job["progress"]["processed_pages"] is None
    assert job["progress"]["percent_complete"] is None
    assert job["progress"]["audio_total_media_seconds"] == 9.5
    assert job["progress"]["audio_processed_media_seconds"] == 9.5
    assert job["progress"]["audio_percent_complete"] == 100.0
    assert job["progress"]["audio_current_chunk_index"] == 0
    assert job["progress"]["audio_total_chunks"] == 1
    assert len(sidecar.chunk_requests) == 1

    job_id = job["job_id"]
    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers=_headers(),
    )
    assert result_response.status_code == 200
    result = result_response.json()["result"]
    assert result["artifact"]["filename"] == "transcript_json.json"
    assert result["artifact"]["content_type"] == "application/json"
    assert result["conversion_metadata"]["pipeline_used"] == "audio_to_transcript_bundle_v2"
    assert result["conversion_metadata"]["backend_used"] == "stt_sidecar"
    assert result["conversion_metadata"]["acceleration_used"] == "rocm"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_json",
        headers=_headers(),
    )
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("application/json")
    transcript = artifact_response.json()
    assert transcript["schema_version"] == "transcript_json_v1"
    assert transcript["transcript"]["text"] == "Hello there. Hi back."
    assert [segment["speaker_label"] for segment in transcript["segments"]] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]
    assert transcript["language"]["detected"] == "en"
    assert transcript["diarization"]["status"] == "succeeded"
    runtime_metadata = transcript["metadata"]["runtime"]
    assert runtime_metadata == {
        "acceleration_used": "rocm",
        "diarization_profile": "diarization_sv_en_primary",
        "normalization_profile": "wav_16khz_mono_s16",
        "sidecar_contract_version": "stt-sidecar-v1",
        "stt_profile": "stt_sv_en_primary",
    }
    serialized_transcript = json.dumps(transcript, sort_keys=True)
    assert "hf_deadbeef" not in serialized_transcript
    assert "/srv/scratch" not in serialized_transcript
    assert "large-v3" not in serialized_transcript

    singular_artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers=_headers(),
    )
    assert singular_artifact_response.status_code == 200
    assert singular_artifact_response.json() == transcript

    manifest_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=_headers(),
    )
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    artifact_entries = {entry["artifact_key"]: entry for entry in manifest["artifacts"]}
    assert artifact_entries["transcript_json"]["availability"] == "available"
    assert artifact_entries["transcript_md"]["availability"] == "unrequested"


def test_audio_runtime_stages_source_for_shared_hosted_sidecar(tmp_path: Path) -> None:
    sidecar = _FakeAudioTranscriptionSidecar()
    job = _stored_audio_job(tmp_path)
    input_dir = tmp_path / "stt-sidecar-inputs"

    execute_audio_transcript_bundle_job(
        job=job,
        config=ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            audio_transcription_sidecar_input_dir=input_dir,
        ),
        sidecar=sidecar,
        progress_callback=None,
        is_cancel_requested=lambda: False,
    )

    assert len(sidecar.probe_requests) == 1
    assert sidecar.probe_source_bytes == [b"audio bytes"]
    source_obj = sidecar.probe_requests[0].get("source")
    assert isinstance(source_obj, Mapping)
    assert source_obj["kind"] == "local_upload"
    assert source_obj["filename"] == "teacher-meeting.m4a"
    assert source_obj["path"] == (input_dir / job.job_id / "input.audio").as_posix()
    assert not (input_dir / job.job_id).exists()


def test_audio_sidecar_readiness_failure_is_terminal_without_artifact(tmp_path: Path) -> None:
    sidecar = _FakeAudioTranscriptionSidecar(
        health_payload={
            "status": "ok",
            "ready": True,
            "backend_profile_id": "stt_sv_en_primary",
            "backend_version": "2026-06-09",
            "gpu_ready": False,
            "capability_version": "stt-sidecar-v1",
        }
    )
    app = _app(tmp_path, sidecar=sidecar)
    client = TestClient(app)

    create_response = _post_audio_job(
        client=client,
        idempotency_key="idem-audio-runtime-gpu-unavailable",
        wait_seconds=20,
    )

    assert create_response.status_code == 200
    job = create_response.json()["job"]
    assert job["status"] == "failed"
    assert job["progress"]["total_pages"] is None
    assert job["progress"]["processed_pages"] is None
    assert job["progress"]["percent_complete"] is None
    assert len(sidecar.chunk_requests) == 0

    job_id = job["job_id"]
    stored_job = app.state.runtime_v2.get_job(job_id)
    assert stored_job is not None
    assert stored_job.failure_retryable is True

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers=_headers(),
    )
    assert result_response.status_code == 409
    assert result_response.json()["error"]["code"] == "job_not_succeeded"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_json",
        headers=_headers(),
    )
    assert artifact_response.status_code == 409
    assert artifact_response.json()["error"]["code"] == "job_not_succeeded"

    checkpoint_response = client.get(
        f"/v2/convert/jobs/{job_id}/checkpoint",
        headers=_headers(),
    )
    assert checkpoint_response.status_code == 409
    assert checkpoint_response.json()["error"]["code"] == "checkpoint_not_supported"


@pytest.mark.parametrize(
    ("sidecar_code", "sidecar_status", "expected_retryable"),
    [
        ("unsupported_audio_codec", 415, False),
        ("audio_diarization_failed", 502, False),
        ("audio_model_access_denied", 503, False),
        ("audio_sidecar_canceled", 409, False),
    ],
)
def test_real_http_sidecar_error_codes_are_preserved_in_stored_job_failure(
    tmp_path: Path,
    sidecar_code: str,
    sidecar_status: int,
    expected_retryable: bool,
) -> None:
    with _failing_sidecar_http_app(
        sidecar_code=sidecar_code,
        sidecar_status=sidecar_status,
    ) as sidecar_url:
        sidecar = HttpAudioTranscriptionSidecarClient(
            base_url=sidecar_url,
            timeout_seconds=2.0,
        )
        app = _app(tmp_path, sidecar=sidecar)
        client = TestClient(app)

        create_response = _post_audio_job(
            client=client,
            idempotency_key=f"idem-http-sidecar-{sidecar_code}",
            wait_seconds=20,
        )

    assert create_response.status_code == 200
    job = create_response.json()["job"]
    assert job["status"] == "failed"
    stored_job = app.state.runtime_v2.get_job(job["job_id"])
    assert stored_job is not None
    assert stored_job.failure_code == sidecar_code
    assert stored_job.failure_retryable is expected_retryable
    serialized_failure = json.dumps(
        {
            "message": stored_job.failure_message,
            "details": stored_job.failure_details,
        },
        sort_keys=True,
    )
    assert "/srv/scratch" not in serialized_failure
    assert "large-v3" not in serialized_failure
    assert "hf_deadbeef" not in serialized_failure
    assert "private transcript text" not in serialized_failure


@contextmanager
def _failing_sidecar_http_app(*, sidecar_code: str, sidecar_status: int) -> Iterator[str]:
    handler = _failing_sidecar_handler(
        sidecar_code=sidecar_code,
        sidecar_status=sidecar_status,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def _failing_sidecar_handler(
    *,
    sidecar_code: str,
    sidecar_status: int,
) -> type[BaseHTTPRequestHandler]:
    class _FailingSidecarHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                self._write_json(status_code=200, payload=_healthy_sidecar())
                return
            if self.path == "/capabilities":
                self._write_json(status_code=200, payload=_ready_capabilities())
                return
            self._write_json(
                status_code=404,
                payload={"code": "not_found", "error": "Not found."},
            )

        def do_POST(self) -> None:
            length_header = self.headers.get("content-length", "0")
            content_length = int(length_header) if length_header.isdigit() else 0
            if content_length > 0:
                self.rfile.read(content_length)
            if self.path in {"/probe-media", "/diarize", "/transcribe-chunk"}:
                self._write_json(
                    status_code=sidecar_status,
                    payload={
                        "code": sidecar_code,
                        "error": (
                            "private transcript text /srv/scratch "
                            "Systran/faster-whisper-large-v3 hf_deadbeef"
                        ),
                    },
                )
                return
            if self.path == "/cancel":
                self._write_json(
                    status_code=200,
                    payload={"status": "cancel_requested"},
                )
                return
            if self.path == "/finalize":
                self._write_json(
                    status_code=200,
                    payload={"status": "finalized"},
                )
                return
            self._write_json(
                status_code=404,
                payload={"code": "not_found", "error": "Not found."},
            )

        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _write_json(self, *, status_code: int, payload: Mapping[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _FailingSidecarHandler
