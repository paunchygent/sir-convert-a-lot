"""Shared fake sidecars and transcription payload fixtures for speech tests."""

from __future__ import annotations

import shutil
import threading
from collections.abc import Mapping
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError


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
        self.probe_requests: list[Mapping[str, object]] = []
        self.probe_source_bytes: list[bytes] = []
        self.chunk_requests: list[Mapping[str, object]] = []
        self.canceled_handles: list[str] = []
        self.finalized_handles: list[str] = []

    def health(self) -> Mapping[str, object]:
        return self.health_payload

    def capabilities(self) -> Mapping[str, object]:
        return self.capability_payload

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.probe_requests.append(dict(request))
        source_obj = request.get("source")
        if isinstance(source_obj, Mapping):
            path_obj = source_obj.get("path")
            if isinstance(path_obj, str) and path_obj.strip() != "":
                source_path = Path(path_obj)
                if source_path.is_file():
                    self.probe_source_bytes.append(source_path.read_bytes())
        media = self.transcribe_payload.get("media")
        runtime_metadata = self.transcribe_payload.get("runtime_metadata")
        return {
            "status": "succeeded",
            "media": media if isinstance(media, Mapping) else {},
            "runtime_metadata": runtime_metadata if isinstance(runtime_metadata, Mapping) else {},
            "warnings": self.transcribe_payload.get("warnings", []),
        }

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        diarization = self.transcribe_payload.get("diarization")
        return {
            "status": "succeeded",
            "diarization": {
                "status": "succeeded",
                "mode_used": (
                    diarization.get("mode_used") if isinstance(diarization, Mapping) else "auto"
                ),
                "windows": _diarization_windows_from_transcription(self.transcribe_payload),
            },
            "warnings": self.transcribe_payload.get("warnings", []),
        }

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.chunk_requests.append(dict(request))
        chunk_obj = request.get("chunk")
        chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
        return _chunk_response_from_transcription(
            transcription=self.transcribe_payload,
            chunk_index=_int_field(chunk, "chunk_index", fallback=0),
            start_seconds=_float_field(chunk, "start_seconds", fallback=0.0),
            end_seconds=_float_field(chunk, "end_seconds", fallback=0.0),
        )

    def cancel(self, request_handle: str) -> None:
        self.canceled_handles.append(request_handle)

    def finalize(self, request_handle: str) -> None:
        self.finalized_handles.append(request_handle)


class _BlockingAudioTranscriptionSidecar(_FakeAudioTranscriptionSidecar):
    def __init__(self, *, scratch_root: Path) -> None:
        super().__init__()
        self._scratch_root = scratch_root
        self.chunk_started = threading.Event()
        self.cancel_received = threading.Event()
        self.release_chunk = threading.Event()

    @property
    def scratch_path(self) -> Path:
        return self._scratch_root / "normalized-job-media"

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        payload = super().probe_media(request)
        self.scratch_path.mkdir(parents=True, exist_ok=True)
        (self.scratch_path / "normalized.wav").write_bytes(b"normalized audio")
        return payload

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.chunk_requests.append(dict(request))
        self.chunk_started.set()
        self.release_chunk.wait(timeout=5.0)
        chunk_obj = request.get("chunk")
        chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
        return _chunk_response_from_transcription(
            transcription=self.transcribe_payload,
            chunk_index=_int_field(chunk, "chunk_index", fallback=0),
            start_seconds=_float_field(chunk, "start_seconds", fallback=0.0),
            end_seconds=_float_field(chunk, "end_seconds", fallback=0.0),
        )

    def cancel(self, request_handle: str) -> None:
        self.canceled_handles.append(request_handle)
        _remove_tree(self.scratch_path)
        self.cancel_received.set()


class _CleanupTrackingAudioTranscriptionSidecar(_FakeAudioTranscriptionSidecar):
    def __init__(
        self,
        *,
        scratch_root: Path,
        failure: tuple[str, bool] | None = None,
    ) -> None:
        super().__init__()
        self._scratch_root = scratch_root
        self._failure = failure

    @property
    def scratch_path(self) -> Path:
        return self._scratch_root / "normalized-job-media"

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        payload = super().probe_media(request)
        self.scratch_path.mkdir(parents=True, exist_ok=True)
        (self.scratch_path / "normalized.wav").write_bytes(b"normalized audio")
        return payload

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        if self._failure is not None:
            code, retryable = self._failure
            raise ServiceError(
                status_code=503 if retryable else 502,
                code=code,
                message="Injected sidecar failure.",
                retryable=retryable,
            )
        return super().transcribe_chunk(request)

    def cancel(self, request_handle: str) -> None:
        super().cancel(request_handle)
        _remove_tree(self.scratch_path)

    def finalize(self, request_handle: str) -> None:
        super().finalize(request_handle)
        _remove_tree(self.scratch_path)


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


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


def _diarization_windows_from_transcription(
    transcription: Mapping[str, object],
) -> list[dict[str, object]]:
    segments_obj = transcription.get("segments")
    if not isinstance(segments_obj, list):
        return []
    windows: list[dict[str, object]] = []
    for index, segment_obj in enumerate(segments_obj, start=1):
        if not isinstance(segment_obj, Mapping):
            continue
        windows.append(
            {
                "window_id": f"speaker-window-{index:04d}",
                "start_seconds": _float_field(segment_obj, "start_seconds", fallback=0.0),
                "end_seconds": _float_field(segment_obj, "end_seconds", fallback=0.0),
                "speaker_label": _string_field(
                    segment_obj,
                    "speaker_label",
                    fallback="SPEAKER_00",
                ),
            }
        )
    return windows


def _chunk_response_from_transcription(
    *,
    transcription: Mapping[str, object],
    chunk_index: int,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, object]:
    segments_obj = transcription.get("segments")
    segments = segments_obj if isinstance(segments_obj, list) else []
    chunk_segments: list[dict[str, object]] = []
    for segment_obj in segments:
        if not isinstance(segment_obj, Mapping):
            continue
        segment_start = _float_field(segment_obj, "start_seconds", fallback=0.0)
        segment_end = _float_field(segment_obj, "end_seconds", fallback=0.0)
        midpoint = segment_start + ((segment_end - segment_start) / 2.0)
        if start_seconds <= midpoint <= end_seconds:
            chunk_segments.append(
                {
                    "segment_id": _string_field(segment_obj, "segment_id", fallback="seg"),
                    "start_seconds": segment_start,
                    "end_seconds": segment_end,
                    "text": _string_field(segment_obj, "text", fallback=""),
                    "language": _string_field(segment_obj, "language", fallback="en"),
                    "confidence": _float_field(segment_obj, "confidence", fallback=0.0),
                }
            )
    return {
        "status": "succeeded",
        "chunk_index": chunk_index,
        "segments": chunk_segments,
        "language": transcription.get("language", {"detected": "en", "confidence": None}),
        "warnings": transcription.get("warnings", []),
    }


def _int_field(payload: Mapping[str, object], key: str, *, fallback: int) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else fallback


def _float_field(payload: Mapping[str, object], key: str, *, fallback: float) -> float:
    value = payload.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return fallback


def _string_field(payload: Mapping[str, object], key: str, *, fallback: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) and value.strip() != "" else fallback


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
