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
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import IO, TypeAlias

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_runtime import (
    AudioProgressUpdateV2,
    execute_audio_transcript_bundle_job,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    AudioTranscriptionSidecarClient,
    HttpAudioTranscriptionSidecarClient,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfConversionCanceledV2,
)
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


class _FakeAudioTranscriptionSidecar:
    def __init__(
        self,
        *,
        health_payload: Mapping[str, object] | None = None,
        capability_payload: Mapping[str, object] | None = None,
        transcribe_payload: Mapping[str, object] | None = None,
    ) -> None:
        self.health_payload = dict(health_payload or _healthy_sidecar())
        self.capability_payload = dict(capability_payload or _ready_capabilities())
        self.transcribe_payload = dict(transcribe_payload or _successful_transcription())
        self.transcribe_requests: list[Mapping[str, object]] = []
        self.canceled_handles: list[str] = []

    def health(self) -> Mapping[str, object]:
        return self.health_payload

    def capabilities(self) -> Mapping[str, object]:
        return self.capability_payload

    def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.transcribe_requests.append(dict(request))
        return self.transcribe_payload

    def cancel(self, request_handle: str) -> None:
        self.canceled_handles.append(request_handle)


class _BlockingAudioTranscriptionSidecar(_FakeAudioTranscriptionSidecar):
    def __init__(self) -> None:
        super().__init__()
        self.transcribe_started = threading.Event()
        self.cancel_received = threading.Event()
        self.release_transcribe = threading.Event()

    def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.transcribe_requests.append(dict(request))
        self.transcribe_started.set()
        self.release_transcribe.wait(timeout=5.0)
        return self.transcribe_payload

    def cancel(self, request_handle: str) -> None:
        self.canceled_handles.append(request_handle)
        self.cancel_received.set()


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
    assert len(sidecar.transcribe_requests) == 1

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
    assert artifact_entries["transcript_md"]["availability"] == "not_implemented"


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
    assert len(sidecar.transcribe_requests) == 0

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


def test_canceling_running_audio_job_propagates_to_sidecar_and_keeps_no_artifact(
    tmp_path: Path,
) -> None:
    sidecar = _BlockingAudioTranscriptionSidecar()
    app = _app(tmp_path, sidecar=sidecar)
    client = TestClient(app)
    create_response = _post_audio_job(
        client=client,
        idempotency_key="idem-audio-runtime-in-flight-cancel",
        wait_seconds=0,
    )
    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]
    assert sidecar.transcribe_started.wait(timeout=5.0)

    cancel_response = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers=_headers(),
    )

    assert cancel_response.status_code == 202
    assert sidecar.cancel_received.is_set()
    assert sidecar.canceled_handles == [job_id]
    sidecar.release_transcribe.set()
    runtime = app.state.runtime_v2
    stored_job = runtime.get_job(job_id)
    assert stored_job is not None
    assert stored_job.status == JobStatus.CANCELED
    assert _eventually_canceled(runtime=runtime, job_id=job_id)
    stored_job = runtime.get_job(job_id)
    assert stored_job is not None
    assert stored_job.status == JobStatus.CANCELED
    assert not stored_job.artifact_path.exists()

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


def test_audio_cancellation_cancels_sidecar_without_publishing_artifact(
    tmp_path: Path,
) -> None:
    sidecar = _FakeAudioTranscriptionSidecar()
    job = _stored_audio_job(tmp_path)
    progress_updates: list[AudioProgressUpdateV2] = []

    with pytest.raises(PdfConversionCanceledV2):
        execute_audio_transcript_bundle_job(
            job=job,
            config=ServiceConfig(
                api_key=_API_KEY,
                data_root=tmp_path / "service_data",
                enable_supervisor=False,
            ),
            sidecar=sidecar,
            progress_callback=progress_updates.append,
            is_cancel_requested=lambda: True,
        )

    assert sidecar.canceled_handles == [job.job_id]
    assert sidecar.transcribe_requests == []
    assert not job.artifact_path.exists()
    assert [update.stage for update in progress_updates] == ["probing_media"]


def _eventually_canceled(*, runtime: ServiceRuntimeV2, job_id: str) -> bool:
    deadline = threading.Event()
    for _ in range(50):
        stored_job = runtime.get_job(job_id)
        if stored_job is not None and stored_job.status == JobStatus.CANCELED:
            return True
        deadline.wait(timeout=0.02)
    return False


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
            if self.path == "/transcribe":
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
) -> httpx.Response:
    payload = _audio_job_spec()
    files: _MultipartFiles = [
        ("file", ("teacher-meeting.m4a", b"audio bytes", "application/octet-stream")),
        ("job_spec", (None, json.dumps(payload))),
    ]
    return client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers={**_headers(), "Idempotency-Key": idempotency_key},
        files=files,
    )


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


def _healthy_sidecar() -> dict[str, object]:
    return {
        "status": "ok",
        "ready": True,
        "backend_profile_id": "stt_sv_en_primary",
        "backend_version": "2026-06-09",
        "gpu_ready": True,
        "capability_version": "stt-sidecar-v1",
    }


def _ready_capabilities() -> dict[str, object]:
    return {
        "adapter_contract_version": "stt-sidecar-v1",
        "runtime": {
            "network_scope": "internal_only",
            "published_port_allowed": False,
            "gpu_required": True,
            "acceleration_family": "rocm",
            "acceleration_ready": True,
        },
        "media": {
            "max_upload_bytes": 524288000,
            "max_duration_seconds": 7200,
            "accepted_containers": [
                "wav",
                "mp3",
                "m4a",
                "aac",
                "flac",
                "ogg",
                "opus",
                "webm",
                "aiff",
                "mp4",
                "mov",
                "mkv",
            ],
            "input_protocols": ["local_upload"],
            "normalized_audio": {
                "container": "wav",
                "sample_rate_hz": 16000,
                "channels": 1,
                "sample_format": "s16",
            },
        },
        "transcription": {
            "profile_label": "stt_sv_en_primary",
            "languages": ["auto", "sv", "en"],
            "word_timestamps_supported": True,
        },
        "diarization": {
            "profile_label": "diarization_sv_en_primary",
            "required_for_success": True,
            "modes": ["auto", "known_speaker_count", "speaker_range"],
            "exclusive_speaker_segments_supported": True,
        },
        "cache": {
            "cache_family": "huggingface",
            "host_root": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            "container_root": "/cache/huggingface",
            "cache_roots_ready": True,
            "model_artifacts_present": True,
        },
        "secrets": {
            "required_secret_names": ["HF_TOKEN"],
            "required_secrets_present": True,
            "values_exposed": False,
        },
    }


def _successful_transcription() -> dict[str, object]:
    return {
        "status": "succeeded",
        "transcript_text": "Hello there. Hi back.",
        "segments": [
            {
                "segment_id": "seg-0001",
                "start_seconds": 0.0,
                "end_seconds": 4.2,
                "speaker_label": "SPEAKER_00",
                "text": "Hello there.",
                "language": "en",
                "confidence": 0.94,
            },
            {
                "segment_id": "seg-0002",
                "start_seconds": 4.4,
                "end_seconds": 9.5,
                "speaker_label": "SPEAKER_01",
                "text": "Hi back.",
                "language": "en",
                "confidence": 0.92,
            },
        ],
        "language": {"detected": "en", "confidence": 0.98},
        "diarization": {"status": "succeeded", "mode_used": "auto"},
        "media": {
            "duration_seconds": 9.5,
            "normalized_audio_sha256": "sha256:normalized-audio",
            "chunks": [
                {
                    "chunk_index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 9.5,
                    "overlap_seconds": 0.0,
                }
            ],
        },
        "runtime_metadata": {
            "acceleration_used": "rocm",
            "normalization_profile": "wav_16khz_mono_s16",
            "raw_model_id": "Systran/faster-whisper-large-v3",
            "hf_token": "hf_deadbeef",
            "cache_path": "/srv/scratch/private/cache",
        },
        "warnings": [],
    }
