"""STT sidecar media probing and runtime limit behavior.

Purpose:
    Prove the internal speech-to-text sidecar enforces audio ingestion safety
    limits before model execution and maps codec subprocess failures to stable
    public audio error codes.

Relationships:
    - Exercises `stt_sidecar.media` timeout mapping without invoking FFmpeg.
    - Exercises `stt_sidecar.runtime` before backend-native STT or diarization
      dependencies are loaded in the main service test lane.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.stt_sidecar import media
from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError
from scripts.sir_convert_a_lot.stt_sidecar.runtime import SttSidecarRuntime
from scripts.sir_convert_a_lot.stt_sidecar.settings import SttSidecarSettings


class _ForbiddenWhisperModel:
    def __init__(self) -> None:
        self.transcribe_called = False

    def transcribe(
        self,
        audio: str,
        *,
        beam_size: int,
        word_timestamps: bool,
        language: str | None,
    ) -> tuple[list[object], object]:
        del audio, beam_size, word_timestamps, language
        self.transcribe_called = True
        raise AssertionError("Transcription must not run for over-limit media.")


class _ForbiddenDiarizationPipeline:
    def __init__(self) -> None:
        self.diarization_called = False

    def __call__(
        self,
        file: str,
        *,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> object:
        del file, num_speakers, min_speakers, max_speakers
        self.diarization_called = True
        raise AssertionError("Diarization must not run for over-limit media.")

    def to(self, device: object) -> object:
        del device
        return self


def test_sidecar_runtime_rejects_over_limit_duration_before_model_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    normalization_calls: list[Path] = []

    def _duration_seconds(path: Path) -> float:
        assert path == source_path
        return 7_201.0

    def _normalize_audio(
        *,
        source_path: Path,
        target_path: Path,
        media_duration_seconds: float,
    ) -> None:
        del target_path, media_duration_seconds
        normalization_calls.append(source_path)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.stt_sidecar.runtime.duration_seconds",
        _duration_seconds,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.stt_sidecar.runtime.normalize_audio",
        _normalize_audio,
    )
    runtime = SttSidecarRuntime(_settings())
    whisper_model = _ForbiddenWhisperModel()
    diarization_pipeline = _ForbiddenDiarizationPipeline()
    runtime._stt_model = whisper_model
    runtime._diarization_pipeline = diarization_pipeline
    runtime._ready = True

    with pytest.raises(SttSidecarRequestError) as exc_info:
        runtime.transcribe(_transcribe_request(source_path=source_path))

    assert exc_info.value.code == "audio_duration_exceeded"
    assert normalization_calls == []
    assert whisper_model.transcribe_called is False
    assert diarization_pipeline.diarization_called is False


def test_duration_probe_timeout_maps_to_probe_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_timeouts: list[float] = []

    def _run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        captured_timeouts.append(timeout)
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(SttSidecarRequestError) as exc_info:
        media.duration_seconds(Path("meeting.m4a"))

    assert exc_info.value.code == "audio_probe_timeout"
    assert captured_timeouts == [30.0]


def test_normalization_timeout_uses_duration_based_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_timeouts: list[float] = []

    def _run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        captured_timeouts.append(timeout)
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(SttSidecarRequestError) as exc_info:
        media.normalize_audio(
            source_path=Path("meeting.m4a"),
            target_path=Path("normalized.wav"),
            media_duration_seconds=900.0,
        )

    assert exc_info.value.code == "audio_normalization_timeout"
    assert captured_timeouts == [1_800.0]


def _settings() -> SttSidecarSettings:
    return SttSidecarSettings(
        backend_profile_id="stt_sv_en_primary",
        backend_version="faster_whisper_pyannote_profile",
        stt_profile_label="stt_sv_en_primary",
        diarization_profile_label="diarization_sv_en_primary",
        stt_model_id="internal_stt_profile",
        diarization_model_id="internal_diarization_profile",
        compute_type="float16",
        hf_token_env_name="HF_TOKEN",
        hf_cache_container_root=Path("/tmp/sir-convert-test-cache"),
        hf_cache_host_label="persistent_huggingface_cache",
        hf_cache_container_label="huggingface_cache_mount",
        acceleration_family="rocm",
        beam_size=5,
    )


def _transcribe_request(*, source_path: Path) -> Mapping[str, object]:
    return {
        "request_handle": "job-audio-over-limit",
        "source": {
            "kind": "local_upload",
            "path": source_path.as_posix(),
            "filename": "meeting.m4a",
        },
        "options": {
            "language": "auto",
            "max_duration_seconds": 7_200,
            "output_schema_version": "transcript_json_v1",
            "diarization": {
                "mode": "auto",
                "num_speakers": None,
                "min_speakers": None,
                "max_speakers": None,
            },
        },
    }
