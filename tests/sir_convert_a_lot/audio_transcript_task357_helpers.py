"""Task 357 audio transcript test helpers.

Purpose:
    Share fake sidecar payloads and Service API v2 test-client setup for
    checkpointed audio transcript runtime tests without importing backend STT
    or diarization dependencies.

Relationships:
    - Used by Task 357 progress, checkpoint, cancellation, and alignment tests.
    - Exercises `infrastructure.audio_transcript_bundle_runtime` and the
      public Service API v2 lifecycle through the sidecar client port.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, TypeAlias

import httpx
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

API_KEY = "secret-key"
MultipartFieldValue: TypeAlias = (
    IO[bytes]
    | bytes
    | str
    | tuple[str | None, IO[bytes] | bytes | str]
    | tuple[str | None, IO[bytes] | bytes | str, str | None]
    | tuple[str | None, IO[bytes] | bytes | str, str | None, Mapping[str, str]]
)
MultipartFiles: TypeAlias = list[tuple[str, MultipartFieldValue]]


def build_test_app(tmp_path: Path, *, sidecar: AudioTranscriptionSidecarClient) -> FastAPI:
    """Build the Service API v2 app with an injected fake STT sidecar."""

    return create_app(
        ServiceConfig(
            api_key=API_KEY,
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            run_jobs_on_submit=True,
            processing_delay_seconds=0.0,
            enable_runtime_telemetry_calls=False,
            heartbeat_interval_seconds=0.05,
        ),
        audio_transcription_sidecar=sidecar,
    )


def build_test_client(
    tmp_path: Path,
    *,
    sidecar: AudioTranscriptionSidecarClient,
) -> TestClient:
    """Build a TestClient for public lifecycle assertions."""

    return TestClient(build_test_app(tmp_path, sidecar=sidecar))


def post_audio_job(
    *,
    client: TestClient,
    idempotency_key: str,
    wait_seconds: int,
) -> httpx.Response:
    """Submit a governed audio transcript job through Service API v2."""

    files: MultipartFiles = [
        ("file", ("teacher-meeting.m4a", b"audio bytes", "application/octet-stream")),
        ("job_spec", (None, json.dumps(audio_job_spec()))),
    ]
    return client.post(
        f"/v2/convert/jobs?wait_seconds={wait_seconds}",
        headers={**headers(), "Idempotency-Key": idempotency_key},
        files=files,
    )


def stored_audio_job(tmp_path: Path, *, job_id: str = "job-v2-audio-task357") -> StoredJobV2:
    """Create a stored audio job for direct runtime-port tests."""

    raw_dir = tmp_path / "raw"
    artifact_dir = tmp_path / "artifacts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    upload_path = raw_dir / "teacher-meeting.m4a"
    upload_path.write_bytes(b"audio bytes")
    now = datetime.now(UTC)
    return StoredJobV2(
        job_id=job_id,
        spec=JobSpecV2.model_validate(audio_job_spec()),
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


def headers() -> dict[str, str]:
    """Return authenticated Service API v2 test headers."""

    return {
        "X-API-Key": API_KEY,
        "X-Correlation-ID": "corr-audio-task357",
    }


def audio_job_spec() -> dict[str, object]:
    """Return the governed day-one audio transcript request shape."""

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


def healthy_sidecar() -> dict[str, object]:
    """Return sidecar health accepted by the main service policy."""

    return {
        "status": "ok",
        "ready": True,
        "backend_profile_id": "stt_sv_en_primary",
        "backend_version": "2026-06-09",
        "gpu_ready": True,
        "capability_version": "stt-sidecar-v1",
    }


def ready_capabilities() -> dict[str, object]:
    """Return sidecar capabilities accepted by the main service policy."""

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


def probe_payload(*, duration_seconds: float = 600.0) -> dict[str, object]:
    """Return normalized media metadata for deterministic chunk planning."""

    return {
        "status": "succeeded",
        "media": {
            "duration_seconds": duration_seconds,
            "normalized_audio_sha256": "sha256:normalized-audio",
            "normalized_audio_handle": "normalized://job-v2-audio-task357",
        },
        "runtime_metadata": {
            "acceleration_used": "rocm",
            "normalization_profile": "wav_16khz_mono_s16",
        },
        "warnings": [],
    }


def diarization_payload() -> dict[str, object]:
    """Return global diarization windows shared across chunks."""

    return {
        "status": "succeeded",
        "diarization": {
            "status": "succeeded",
            "mode_used": "auto",
            "windows": [
                {
                    "window_id": "speaker-window-0001",
                    "start_seconds": 0.0,
                    "end_seconds": 600.0,
                    "speaker_label": "SPEAKER_00",
                }
            ],
        },
        "warnings": [],
    }


def chunk_payload(
    *, chunk_index: int, start_seconds: float, end_seconds: float
) -> dict[str, object]:
    """Return one accepted chunk transcription payload."""

    return {
        "status": "succeeded",
        "chunk_index": chunk_index,
        "segments": [
            {
                "segment_id": f"chunk-{chunk_index}-seg-0001",
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "text": f"Chunk {chunk_index}.",
                "language": "en",
                "confidence": 0.91,
            }
        ],
        "language": {"detected": "en", "confidence": 0.91},
        "warnings": [],
    }
