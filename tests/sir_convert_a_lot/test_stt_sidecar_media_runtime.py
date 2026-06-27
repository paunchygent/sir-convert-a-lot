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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.stt_sidecar import media
from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError
from scripts.sir_convert_a_lot.stt_sidecar.model_lifecycle import LoadedSttModels
from scripts.sir_convert_a_lot.stt_sidecar.normalized_audio import NormalizedAudioStore
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
        batch_size: int,
        word_timestamps: bool,
        language: str | None,
    ) -> tuple[list[object], object]:
        del audio, beam_size, batch_size, word_timestamps, language
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


class _SuccessfulWhisperModel:
    def unload_model(self) -> None:
        return None

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
        return [_FakeWhisperSegment(start=0.0, end=1.5, text="Hello.")], _FakeWhisperInfo(
            language="en"
        )


class _SuccessfulDiarizationPipeline:
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
    runtime._ready = True
    runtime._gpu_ready = True

    with pytest.raises(SttSidecarRequestError) as exc_info:
        runtime.probe_media(_transcribe_request(source_path=source_path))

    assert exc_info.value.code == "audio_duration_exceeded"
    assert normalization_calls == []
    assert whisper_model.transcribe_called is False
    assert diarization_pipeline.diarization_called is False


def test_sidecar_runtime_accepts_only_probe_issued_normalized_handles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    runtime = _ready_runtime(tmp_path)
    _patch_successful_media(monkeypatch)

    probe_payload = runtime.probe_media(_transcribe_request(source_path=source_path))
    media_obj = probe_payload["media"]
    assert isinstance(media_obj, Mapping)
    handle = _required_string(media_obj, "normalized_audio_handle")
    sha = _required_string(media_obj, "normalized_audio_sha256")

    diarization = runtime.diarize(
        _normalized_request(
            request_handle="job-audio-over-limit",
            handle=handle,
            sha=sha,
        )
    )
    chunk = runtime.transcribe_chunk(
        {
            **_normalized_request(request_handle="job-audio-over-limit", handle=handle, sha=sha),
            "chunk": {
                "chunk_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "overlap_seconds": 0.0,
            },
        }
    )

    diarization_obj = _required_mapping(diarization, "diarization")
    windows = _required_sequence(diarization_obj, "windows")
    first_window = windows[0]
    assert isinstance(first_window, Mapping)
    assert first_window["speaker_label"] == "SPEAKER_00"
    segments = _required_sequence(chunk, "segments")
    first_segment = segments[0]
    assert isinstance(first_segment, Mapping)
    assert first_segment["segment_id"] == "chunk-0-seg-0001"
    assert list((tmp_path / "sidecar").glob("*/normalized.wav"))


@pytest.mark.parametrize(
    ("request_handle", "handle", "sha", "expected_code"),
    [
        ("job-audio-over-limit", "normalized:unknown", "sha256:missing", "audio_stream_missing"),
        ("wrong-job", "issued", "issued", "audio_stream_missing"),
        ("job-audio-over-limit", "issued", "sha256:wrong", "audio_normalization_failed"),
    ],
)
def test_sidecar_runtime_rejects_unknown_mismatched_or_wrong_sha_handles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request_handle: str,
    handle: str,
    sha: str,
    expected_code: str,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    runtime = _ready_runtime(tmp_path)
    _patch_successful_media(monkeypatch)
    probe_payload = runtime.probe_media(_transcribe_request(source_path=source_path))
    media_obj = probe_payload["media"]
    assert isinstance(media_obj, Mapping)
    issued_handle = _required_string(media_obj, "normalized_audio_handle")
    issued_sha = _required_string(media_obj, "normalized_audio_sha256")
    resolved_handle = issued_handle if handle == "issued" else handle
    resolved_sha = issued_sha if sha == "issued" else sha

    with pytest.raises(SttSidecarRequestError) as exc_info:
        runtime.diarize(
            _normalized_request(
                request_handle=request_handle,
                handle=resolved_handle,
                sha=resolved_sha,
            )
        )

    assert exc_info.value.code == expected_code


def test_sidecar_runtime_rejects_stale_finalized_handles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    runtime = _ready_runtime(tmp_path)
    _patch_successful_media(monkeypatch)
    probe_payload = runtime.probe_media(_transcribe_request(source_path=source_path))
    media_obj = probe_payload["media"]
    assert isinstance(media_obj, Mapping)
    handle = _required_string(media_obj, "normalized_audio_handle")
    sha = _required_string(media_obj, "normalized_audio_sha256")

    runtime.finalize("job-audio-over-limit")

    assert not list((tmp_path / "sidecar").glob("*/normalized.wav"))
    with pytest.raises(SttSidecarRequestError) as exc_info:
        runtime.transcribe_chunk(
            {
                **_normalized_request(
                    request_handle="job-audio-over-limit",
                    handle=handle,
                    sha=sha,
                ),
                "chunk": {
                    "chunk_index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 2.0,
                    "overlap_seconds": 0.0,
                },
            }
        )

    assert exc_info.value.code == "audio_stream_missing"


def test_sidecar_runtime_cancel_removes_job_scoped_normalized_media(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    runtime = _ready_runtime(tmp_path)
    _patch_successful_media(monkeypatch)

    runtime.probe_media(_transcribe_request(source_path=source_path))
    assert list((tmp_path / "sidecar").glob("*/normalized.wav"))

    runtime.cancel("job-audio-over-limit")

    assert not list((tmp_path / "sidecar").glob("*/normalized.wav"))


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
        batch_size=8,
    )


def _ready_runtime(tmp_path: Path) -> SttSidecarRuntime:
    runtime = SttSidecarRuntime(_settings())
    runtime._model_lifecycle._models = LoadedSttModels(
        whisper_model=_SuccessfulWhisperModel(),
        stt_model=_SuccessfulWhisperModel(),
        diarization_pipeline=_SuccessfulDiarizationPipeline(),
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


def _normalized_request(*, request_handle: str, handle: str, sha: str) -> dict[str, object]:
    return {
        "request_handle": request_handle,
        "normalized_audio": {
            "handle": handle,
            "sha256": sha,
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
