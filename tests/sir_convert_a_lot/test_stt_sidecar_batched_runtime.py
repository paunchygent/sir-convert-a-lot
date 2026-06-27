"""STT sidecar FasterWhisper batched inference contract tests.

Purpose:
    Prove the production speech-to-text sidecar uses FasterWhisper batched
    inference with the configured batch-size contract while preserving the
    accepted chunk transcription and sanitized capability boundaries.

Relationships:
    - Exercises `stt_sidecar.runtime` and `stt_sidecar.settings` without
      importing real FasterWhisper, pyannote, or Torch dependencies.
    - Protects Epic 12 / Task 362 production remediation from drifting back to
      plain `WhisperModel.transcribe` execution.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import pytest

from scripts.sir_convert_a_lot.stt_sidecar.model_lifecycle import LoadedSttModels
from scripts.sir_convert_a_lot.stt_sidecar.normalized_audio import NormalizedAudioStore
from scripts.sir_convert_a_lot.stt_sidecar.runtime import SttSidecarRuntime
from scripts.sir_convert_a_lot.stt_sidecar.settings import SttSidecarSettings


@dataclass(frozen=True, slots=True)
class _FakeWhisperInfo:
    language: str


@dataclass(frozen=True, slots=True)
class _FakeWhisperSegment:
    start: float
    end: float
    text: str


class _RecordingBatchedWhisperModel:
    def __init__(self) -> None:
        self.transcribe_calls: list[Mapping[str, object]] = []

    def transcribe(
        self,
        audio: str,
        *,
        beam_size: int,
        batch_size: int,
        word_timestamps: bool,
        language: str | None,
    ) -> tuple[list[_FakeWhisperSegment], _FakeWhisperInfo]:
        self.transcribe_calls.append(
            {
                "audio": audio,
                "beam_size": beam_size,
                "batch_size": batch_size,
                "word_timestamps": word_timestamps,
                "language": language,
            }
        )
        return [_FakeWhisperSegment(start=0.0, end=1.5, text="Hello.")], _FakeWhisperInfo(
            language="en"
        )


class _FakeDiarizationPipeline:
    def __call__(
        self,
        file: str,
        *,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> object:
        del file, num_speakers, min_speakers, max_speakers
        return object()

    def to(self, device: object) -> object:
        del device
        return self


class _FakeWhisperModel:
    def unload_model(self) -> None:
        return None


def test_sidecar_runtime_transcribes_chunks_with_configured_batched_inference_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    stt_model = _RecordingBatchedWhisperModel()
    runtime = _ready_runtime(tmp_path, stt_model=stt_model)
    _patch_successful_media(monkeypatch)
    probe_payload = runtime.probe_media(_transcribe_request(source_path=source_path))
    media_obj = _required_mapping(probe_payload, "media")
    handle = _required_string(media_obj, "normalized_audio_handle")
    sha = _required_string(media_obj, "normalized_audio_sha256")

    chunk = runtime.transcribe_chunk(
        {
            **_normalized_request(request_handle="job-audio", handle=handle, sha=sha),
            "chunk": {
                "chunk_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "overlap_seconds": 0.0,
            },
        }
    )

    assert _required_sequence(chunk, "segments")
    assert len(stt_model.transcribe_calls) == 1
    call = stt_model.transcribe_calls[0]
    assert isinstance(call["audio"], str)
    assert call["beam_size"] == 5
    assert call["batch_size"] == 8
    assert call["word_timestamps"] is True
    assert call["language"] is None
    transcription = _required_mapping(runtime.capabilities(), "transcription")
    assert transcription["backend_family"] == "faster_whisper"
    assert transcription["batch_size"] == 8


def test_first_model_use_wraps_whisper_model_with_batched_inference_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapped_model_ids: list[str] = []
    faster_whisper_module = ModuleType("faster_whisper")

    class FakeWhisperModel:
        def __init__(
            self,
            model_size_or_path: str,
            *,
            device: str,
            compute_type: str,
        ) -> None:
            assert device == "cuda"
            assert compute_type == "float16"
            self.model_size_or_path = model_size_or_path

        def unload_model(self) -> None:
            return None

    class FakeBatchedInferencePipeline(_RecordingBatchedWhisperModel):
        def __init__(self, *, model: FakeWhisperModel) -> None:
            super().__init__()
            wrapped_model_ids.append(model.model_size_or_path)

    setattr(faster_whisper_module, "WhisperModel", FakeWhisperModel)
    setattr(faster_whisper_module, "BatchedInferencePipeline", FakeBatchedInferencePipeline)
    _install_module(monkeypatch, "faster_whisper", faster_whisper_module)
    _install_torch_module(monkeypatch)
    _install_pyannote_module(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    runtime = SttSidecarRuntime(_settings())
    runtime._normalized_audio = NormalizedAudioStore(tmp_path / "sidecar")
    _patch_successful_media(monkeypatch)
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")

    runtime.startup()
    probe_payload = runtime.probe_media(_transcribe_request(source_path=source_path))
    media = _required_mapping(probe_payload, "media")
    runtime.transcribe_chunk(
        {
            **_normalized_request(
                request_handle="job-audio",
                handle=_required_string(media, "normalized_audio_handle"),
                sha=_required_string(media, "normalized_audio_sha256"),
            ),
            "chunk": {
                "chunk_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "overlap_seconds": 0.0,
            },
        }
    )

    assert wrapped_model_ids == ["internal_stt_profile"]
    transcription = _required_mapping(runtime.capabilities(), "transcription")
    assert transcription["backend_family"] == "faster_whisper"
    assert transcription["batch_size"] == 8


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
        batch_size=8,
    )


def _ready_runtime(
    tmp_path: Path,
    *,
    stt_model: _RecordingBatchedWhisperModel,
) -> SttSidecarRuntime:
    runtime = SttSidecarRuntime(_settings())
    runtime._model_lifecycle._models = LoadedSttModels(
        whisper_model=_FakeWhisperModel(),
        stt_model=stt_model,
        diarization_pipeline=_FakeDiarizationPipeline(),
    )
    runtime._ready = True
    runtime._gpu_ready = True
    runtime._normalized_audio = NormalizedAudioStore(tmp_path / "sidecar")
    return runtime


def _patch_successful_media(monkeypatch: pytest.MonkeyPatch) -> None:
    def _duration_seconds(path: Path) -> float:
        del path
        return 2.0

    def _normalize_audio(
        *,
        source_path: Path,
        target_path: Path,
        media_duration_seconds: float,
    ) -> None:
        del source_path, media_duration_seconds
        target_path.write_bytes(b"normalized audio")

    def _trim_normalized_audio(
        *,
        source_path: Path,
        target_path: Path,
        start_seconds: float,
        end_seconds: float,
    ) -> None:
        del source_path, start_seconds, end_seconds
        target_path.write_bytes(b"chunk audio")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.stt_sidecar.runtime.duration_seconds",
        _duration_seconds,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.stt_sidecar.runtime.normalize_audio",
        _normalize_audio,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.stt_sidecar.runtime.trim_normalized_audio",
        _trim_normalized_audio,
    )


def _transcribe_request(*, source_path: Path) -> Mapping[str, object]:
    return {
        "request_handle": "job-audio",
        "source": {
            "kind": "local_upload",
            "path": source_path.as_posix(),
            "filename": "meeting.m4a",
        },
        "options": _options(),
    }


def _normalized_request(*, request_handle: str, handle: str, sha: str) -> dict[str, object]:
    return {
        "request_handle": request_handle,
        "normalized_audio": {
            "handle": handle,
            "sha256": sha,
        },
        "options": _options(),
    }


def _options() -> dict[str, object]:
    return {
        "language": "auto",
        "max_duration_seconds": 7_200,
        "output_schema_version": "transcript_json_v1",
        "diarization": {
            "mode": "auto",
            "num_speakers": None,
            "min_speakers": None,
            "max_speakers": None,
        },
    }


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    assert isinstance(value, str)
    return value


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    assert isinstance(value, Mapping)
    return value


def _required_sequence(payload: Mapping[str, object], key: str) -> Sequence[object]:
    value = payload.get(key)
    assert isinstance(value, Sequence)
    assert not isinstance(value, str)
    return value


def _install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    module.__spec__ = ModuleSpec(name, loader=None)
    monkeypatch.setitem(sys.modules, name, module)


def _install_torch_module(monkeypatch: pytest.MonkeyPatch) -> None:
    torch_module = ModuleType("torch")

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return True

    def device(value: str) -> str:
        return value

    setattr(torch_module, "cuda", FakeCuda())
    setattr(torch_module, "device", device)
    _install_module(monkeypatch, "torch", torch_module)


def _install_pyannote_module(monkeypatch: pytest.MonkeyPatch) -> None:
    pyannote_module = ModuleType("pyannote")
    pyannote_audio_module = ModuleType("pyannote.audio")

    class FakePipeline:
        @classmethod
        def from_pretrained(cls, checkpoint_path: str, *, token: str) -> "FakePipeline":
            assert checkpoint_path == "internal_diarization_profile"
            assert token == "hf_test_token"
            return cls()

        def to(self, device: object) -> object:
            assert device == "cuda"
            return self

    setattr(pyannote_audio_module, "Pipeline", FakePipeline)
    setattr(pyannote_module, "audio", pyannote_audio_module)
    setattr(pyannote_module, "__path__", [])
    _install_module(monkeypatch, "pyannote", pyannote_module)
    _install_module(monkeypatch, "pyannote.audio", pyannote_audio_module)
