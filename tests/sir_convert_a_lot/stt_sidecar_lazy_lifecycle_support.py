"""Test support for STT sidecar lazy lifecycle behavior.

Purpose:
    Provide lightweight fake GPU, FasterWhisper, pyannote, and media helpers
    for STT sidecar lifecycle tests without importing heavyweight backends.

Relationships:
    - Used by `test_stt_sidecar_lazy_lifecycle` to prove lazy load, cache
      readiness, idle unload, and shutdown behavior.
    - Mirrors only the sidecar-facing protocol surface needed by Task 366.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import pytest

from scripts.sir_convert_a_lot.stt_sidecar.settings import SttSidecarSettings


@dataclass(slots=True)
class ModelLoadCounters:
    """Mutable counters for fake model residency operations."""

    whisper_loads: int = 0
    batched_wraps: int = 0
    diarization_loads: int = 0
    unloads: int = 0


@dataclass(slots=True)
class FakeClock:
    """Controllable monotonic clock for idle-timeout tests."""

    current: float = 0.0

    def monotonic(self) -> float:
        """Return the current fake monotonic timestamp."""
        return self.current

    def advance(self, seconds: float) -> None:
        """Move the fake clock forward."""
        self.current += seconds


@dataclass(frozen=True, slots=True)
class _FakeWhisperInfo:
    language: str


@dataclass(frozen=True, slots=True)
class _FakeWhisperSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class _FakeSpeakerTurn:
    start: float
    end: float


class _FakeDiarizationTrack:
    def itertracks(self, *, yield_label: bool) -> list[tuple[_FakeSpeakerTurn, None, str]]:
        del yield_label
        return [(_FakeSpeakerTurn(start=0.0, end=2.0), None, "SPEAKER_00")]


class _FakeDiarizationOutput:
    exclusive_speaker_diarization = _FakeDiarizationTrack()


def settings(tmp_path: Path, *, idle_unload_seconds: float = 900.0) -> SttSidecarSettings:
    """Return isolated sidecar settings for one lifecycle test."""
    cache_root = tmp_path / "hf-cache"
    cache_root.mkdir()
    return SttSidecarSettings(
        backend_profile_id="stt_sv_en_primary",
        backend_version="faster_whisper_pyannote_profile",
        stt_profile_label="stt_sv_en_primary",
        diarization_profile_label="diarization_sv_en_primary",
        stt_model_id="internal_stt_profile",
        diarization_model_id="internal_diarization_profile",
        compute_type="float16",
        hf_token_env_name="HF_TOKEN",
        hf_cache_container_root=cache_root,
        hf_cache_host_label="persistent_huggingface_cache",
        hf_cache_container_label="huggingface_cache_mount",
        acceleration_family="rocm",
        beam_size=5,
        batch_size=8,
        idle_unload_seconds=idle_unload_seconds,
    )


def write_cached_model_artifacts(sidecar_settings: SttSidecarSettings) -> None:
    """Create minimal cached snapshot files for both configured model ids."""
    for model_id in (
        sidecar_settings.stt_model_id,
        sidecar_settings.diarization_model_id,
    ):
        model_dir = (
            sidecar_settings.hf_cache_container_root
            / "hub"
            / f"models--{model_id.replace('/', '--')}"
            / "snapshots"
            / "revision"
        )
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text("{}", encoding="utf-8")


def install_torch_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a lightweight fake torch module with available CUDA."""
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


def install_stt_modules(
    monkeypatch: pytest.MonkeyPatch,
    *,
    counters: ModelLoadCounters,
    first_load_entered: threading.Event | None = None,
    load_release: threading.Event | None = None,
    transcribe_entered: threading.Event | None = None,
    transcribe_release: threading.Event | None = None,
) -> None:
    """Install fake FasterWhisper and pyannote modules for lifecycle tests."""
    faster_whisper_module = ModuleType("faster_whisper")

    class FakeWhisperModel:
        def __init__(
            self,
            model_size_or_path: str,
            *,
            device: str,
            compute_type: str,
        ) -> None:
            assert model_size_or_path == "internal_stt_profile"
            assert device == "cuda"
            assert compute_type == "float16"
            counters.whisper_loads += 1
            if first_load_entered is not None:
                first_load_entered.set()
            if load_release is not None:
                assert load_release.wait(timeout=2.0)

        def unload_model(self) -> None:
            counters.unloads += 1

    class FakeBatchedInferencePipeline:
        def __init__(self, *, model: FakeWhisperModel) -> None:
            del model
            counters.batched_wraps += 1

        def transcribe(
            self,
            audio: str,
            *,
            beam_size: int,
            batch_size: int,
            word_timestamps: bool,
            language: str | None,
        ) -> tuple[list[_FakeWhisperSegment], _FakeWhisperInfo]:
            del audio, beam_size, batch_size, word_timestamps, language
            if transcribe_entered is not None:
                transcribe_entered.set()
            if transcribe_release is not None:
                assert transcribe_release.wait(timeout=2.0)
            return [_FakeWhisperSegment(start=0.0, end=1.5, text="Hello.")], _FakeWhisperInfo(
                language="en"
            )

    setattr(faster_whisper_module, "WhisperModel", FakeWhisperModel)
    setattr(faster_whisper_module, "BatchedInferencePipeline", FakeBatchedInferencePipeline)
    _install_module(monkeypatch, "faster_whisper", faster_whisper_module)

    pyannote_module = ModuleType("pyannote")
    pyannote_audio_module = ModuleType("pyannote.audio")

    class FakePipeline:
        @classmethod
        def from_pretrained(cls, checkpoint_path: str, *, token: str) -> "FakePipeline":
            assert checkpoint_path == "internal_diarization_profile"
            assert token == "hf_test_token"
            counters.diarization_loads += 1
            return cls()

        def __call__(
            self,
            file: str,
            *,
            num_speakers: int | None = None,
            min_speakers: int | None = None,
            max_speakers: int | None = None,
        ) -> _FakeDiarizationOutput:
            del file, num_speakers, min_speakers, max_speakers
            return _FakeDiarizationOutput()

        def to(self, device: object) -> object:
            assert device == "cuda"
            return self

    setattr(pyannote_audio_module, "Pipeline", FakePipeline)
    setattr(pyannote_module, "audio", pyannote_audio_module)
    setattr(pyannote_module, "__path__", [])
    _install_module(monkeypatch, "pyannote", pyannote_module)
    _install_module(monkeypatch, "pyannote.audio", pyannote_audio_module)


def patch_successful_media(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch media probing and normalization to avoid external codecs."""

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


def transcribe_request(*, source_path: Path) -> Mapping[str, object]:
    """Return a sidecar probe/transcribe request for a local audio file."""
    return {
        "request_handle": "job-audio",
        "source": {
            "kind": "local_upload",
            "path": source_path.as_posix(),
            "filename": "meeting.m4a",
        },
        "options": _options(),
    }


def normalized_request(*, request_handle: str, handle: str, sha: str) -> dict[str, object]:
    """Return a sidecar request that references normalized audio."""
    return {
        "request_handle": request_handle,
        "normalized_audio": {
            "handle": handle,
            "sha256": sha,
        },
        "options": _options(),
    }


def required_string(payload: Mapping[str, object], key: str) -> str:
    """Return a required string value from a mapping payload."""
    value = payload.get(key)
    assert isinstance(value, str)
    return value


def required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    """Return a required nested mapping value from a mapping payload."""
    value = payload.get(key)
    assert isinstance(value, Mapping)
    return value


def _install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    module.__spec__ = ModuleSpec(name, loader=None)
    monkeypatch.setitem(sys.modules, name, module)


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
