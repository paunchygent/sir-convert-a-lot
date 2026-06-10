"""STT sidecar HTTP contract tests.

Purpose:
    Prove the internal speech-to-text sidecar exposes the normalized HTTP
    boundary consumed by Service API v2 audio transcript-bundle execution.

Relationships:
    - Exercises the STT sidecar FastAPI factory without loading model
      dependencies in the main service test lane.
    - Reuses the audio transcription readiness policy that the main service
      applies before dispatching transcript jobs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    evaluate_stt_sidecar_readiness,
)
from scripts.sir_convert_a_lot.stt_sidecar.app_factory import create_stt_sidecar_app
from scripts.sir_convert_a_lot.stt_sidecar.contracts import (
    SttSidecarBackend,
    SttSidecarRequestError,
)


class _FakeSttBackend:
    def __init__(self) -> None:
        self.started = False
        self.transcribe_requests: list[Mapping[str, object]] = []
        self.canceled_handles: list[str] = []

    def startup(self) -> None:
        self.started = True

    def health(self) -> Mapping[str, object]:
        return {
            "status": "ok",
            "ready": self.started,
            "backend_profile_id": "stt_sv_en_primary",
            "backend_version": "faster_whisper_pyannote_profile",
            "gpu_ready": True,
            "capability_version": "stt-sidecar-v1",
        }

    def capabilities(self) -> Mapping[str, object]:
        return _capabilities()

    def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.transcribe_requests.append(dict(request))
        return _transcription_payload()

    def cancel(self, request_handle: str) -> Mapping[str, object]:
        self.canceled_handles.append(request_handle)
        return {"status": "cancel_requested", "request_handle": request_handle}


def test_stt_sidecar_http_contract_matches_main_service_readiness() -> None:
    backend = _FakeSttBackend()
    app = create_stt_sidecar_app(_backend(backend), title="test-stt-sidecar")

    with TestClient(app) as client:
        health_response = client.get("/health")
        capabilities_response = client.get("/capabilities")

    assert health_response.status_code == 200
    assert capabilities_response.status_code == 200
    readiness = evaluate_stt_sidecar_readiness(
        health_payload=health_response.json(),
        capability_payload=capabilities_response.json(),
    )
    assert readiness.ready is True
    serialized_capabilities = json.dumps(capabilities_response.json(), sort_keys=True)
    for forbidden_value in (
        "/srv/",
        "/cache/",
        "hf_",
        "large-v3",
        "pyannote/speaker",
        "model_id",
        "token",
    ):
        assert forbidden_value not in serialized_capabilities


def test_stt_sidecar_transcribe_and_cancel_endpoints_use_bounded_payloads(
    tmp_path: Path,
) -> None:
    backend = _FakeSttBackend()
    app = create_stt_sidecar_app(_backend(backend), title="test-stt-sidecar")
    source_path = tmp_path / "meeting.wav"
    source_path.write_bytes(b"audio")

    with TestClient(app) as client:
        transcribe_response = client.post(
            "/transcribe",
            json={
                "request_handle": "job-audio-1",
                "source": {
                    "kind": "local_upload",
                    "path": source_path.as_posix(),
                    "filename": "meeting.wav",
                },
                "options": {
                    "language": "auto",
                    "max_duration_seconds": 7200,
                    "output_schema_version": "transcript_json_v1",
                    "diarization": {
                        "mode": "auto",
                        "num_speakers": None,
                        "min_speakers": None,
                        "max_speakers": None,
                    },
                },
            },
        )
        cancel_response = client.post(
            "/cancel",
            json={"request_handle": "job-audio-1"},
        )

    assert transcribe_response.status_code == 200
    payload = transcribe_response.json()
    assert payload["status"] == "succeeded"
    assert payload["runtime_metadata"] == {
        "acceleration_used": "rocm",
        "normalization_profile": "wav_16khz_mono_s16",
    }
    assert payload["segments"][0]["speaker_label"] == "SPEAKER_00"
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancel_requested"
    assert backend.canceled_handles == ["job-audio-1"]
    serialized_payload = json.dumps(payload, sort_keys=True)
    for forbidden_value in (
        "/srv/",
        "/cache/",
        "hf_",
        "large-v3",
        "pyannote/speaker",
    ):
        assert forbidden_value not in serialized_payload


def test_stt_sidecar_request_errors_return_client_safe_error_payload() -> None:
    class _RejectingBackend(_FakeSttBackend):
        def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
            del request
            raise SttSidecarRequestError(
                code="unsupported_audio_codec",
                message="Audio payload could not be decoded.",
                status_code=415,
            )

    app = create_stt_sidecar_app(_backend(_RejectingBackend()), title="test-stt-sidecar")

    with TestClient(app) as client:
        response = client.post(
            "/transcribe",
            json={"request_handle": "job-audio-1", "source": {}, "options": {}},
        )

    assert response.status_code == 415
    assert response.json() == {
        "error": "Audio payload could not be decoded.",
        "code": "unsupported_audio_codec",
    }


def _backend(backend: _FakeSttBackend) -> SttSidecarBackend:
    return backend


def _capabilities() -> dict[str, object]:
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
            "backend_family": "faster_whisper",
            "languages": ["auto", "sv", "en"],
            "word_timestamps_supported": True,
        },
        "diarization": {
            "profile_label": "diarization_sv_en_primary",
            "backend_family": "pyannote_audio",
            "required_for_success": True,
            "modes": ["auto", "known_speaker_count", "speaker_range"],
            "exclusive_speaker_segments_supported": True,
        },
        "cache": {
            "cache_family": "huggingface",
            "host_root": "persistent_huggingface_cache",
            "container_root": "huggingface_cache_mount",
            "cache_roots_ready": True,
            "model_artifacts_present": True,
        },
        "secrets": {
            "required_secret_names": ["HF_TOKEN"],
            "required_secrets_present": True,
            "values_exposed": False,
        },
    }


def _transcription_payload() -> dict[str, object]:
    return {
        "status": "succeeded",
        "transcript_text": "Hello there.",
        "segments": [
            {
                "segment_id": "seg-0001",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "speaker_label": "SPEAKER_00",
                "text": "Hello there.",
                "language": "en",
                "confidence": 0.91,
            }
        ],
        "language": {"detected": "en", "confidence": 0.91},
        "diarization": {"status": "succeeded", "mode_used": "auto"},
        "media": {
            "duration_seconds": 2.0,
            "normalized_audio_sha256": "sha256:abc123",
            "chunks": [
                {
                    "chunk_index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 2.0,
                    "overlap_seconds": 0.0,
                }
            ],
        },
        "runtime_metadata": {
            "acceleration_used": "rocm",
            "normalization_profile": "wav_16khz_mono_s16",
        },
        "warnings": [],
    }
