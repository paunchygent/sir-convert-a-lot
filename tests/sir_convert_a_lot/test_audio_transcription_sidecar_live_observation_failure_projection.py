"""Audio transcription sidecar live-observation failure projection behavior.

Purpose:
    Describe how retained live-observation JSON carries bounded backend failure
    classifications from runtime-probe payloads while excluding backend-native
    messages, paths, model identifiers, tokens, or transcript text.

Relationships:
    - Exercises the live-observation producer CLI boundary with a fake runtime
      probe command result.
    - Covers the retained observation schema that profile-proof ingestion reads.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_commands import (
    CompletedCommand,
)


def test_live_observation_projects_bounded_backend_failures_without_raw_values(
    tmp_path: Path,
) -> None:
    live_runner = _live_observation_runner()
    hf_home = tmp_path / "hf"
    hf_hub_cache = hf_home / "hub"
    hf_hub_cache.mkdir(parents=True)
    fixture_root = tmp_path / "operator-fixtures"
    fixture_root.mkdir()
    english_fixture = fixture_root / "english-dialogue-two-speakers.mp3"
    swedish_fixture = fixture_root / "swedish-monologue-one-speaker.m4a"
    english_fixture.write_bytes(b"english audio placeholder")
    swedish_fixture.write_bytes(b"swedish audio placeholder")
    raw_model_id = "pyannote/speaker-diarization-community-1"
    raw_token_value = "hf_private_token_value"
    raw_transcript_text = "raw transcript text must not persist"
    private_cache_path = "/private/operator/cache/huggingface"
    runtime_probe_payload = _noisy_blocked_runtime_probe_payload(
        english_fixture=english_fixture,
        hf_home=hf_home,
        private_cache_path=private_cache_path,
        raw_model_id=raw_model_id,
        raw_token_value=raw_token_value,
        raw_transcript_text=raw_transcript_text,
    )
    command_runner = FailureProjectionCommandRunner(runtime_probe_payload=runtime_probe_payload)

    exit_code = live_runner.main(
        [
            "--runtime-mode",
            "host",
            "--sidecar-launch-observed",
            "--english-fixture",
            english_fixture.as_posix(),
            "--swedish-fixture",
            swedish_fixture.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
        ],
        command_runner=command_runner,
        environment={
            "HF_TOKEN": raw_token_value,
            "HF_HOME": hf_home.as_posix(),
            "HF_HUB_CACHE": hf_hub_cache.as_posix(),
        },
    )

    observation_path = tmp_path / "live-observation.json"
    observation = _read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    assert exit_code == 2
    assert _mapping_at(observation, "backend_failures") == {
        "stt": {
            "backend_family": "faster_whisper",
            "exception_class": "RuntimeError",
            "failure_code": "gpu_backend_runtime_unavailable",
            "status": "blocked",
        },
        "diarization": {
            "backend_family": "pyannote_audio",
            "exception_class": "GatedRepoError",
            "failure_code": "gated_model_access_denied",
            "status": "blocked",
        },
    }
    assert "CUDA failed with error" not in persisted_text
    assert "Gated model access denied" not in persisted_text
    assert raw_model_id not in persisted_text
    assert raw_token_value not in persisted_text
    assert hf_home.as_posix() not in persisted_text
    assert hf_hub_cache.as_posix() not in persisted_text
    assert private_cache_path not in persisted_text
    assert english_fixture.as_posix() not in persisted_text
    assert raw_transcript_text not in persisted_text


class FailureProjectionCommandRunner:
    """Command runner that returns codec proof and a noisy runtime payload."""

    def __init__(self, *, runtime_probe_payload: Mapping[str, object]) -> None:
        self._runtime_probe_payload = dict(runtime_probe_payload)

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
    ) -> CompletedCommand:
        del timeout_seconds
        if _runs_runtime_probe(command):
            return CompletedCommand(
                returncode=0,
                stdout=json.dumps(self._runtime_probe_payload),
                stderr="",
            )
        if command[:1] == ("ffmpeg",):
            return CompletedCommand(returncode=0, stdout="ffmpeg version 7.1", stderr="")
        if command[:1] == ("ffprobe",) and "-version" in command:
            return CompletedCommand(returncode=0, stdout="ffprobe version 7.1", stderr="")
        if command[:1] == ("ffprobe",) and _contains_suffix(command, ".mp3"):
            return CompletedCommand(returncode=0, stdout=json.dumps(_audio_probe()), stderr="")
        if command[:1] == ("ffprobe",) and _contains_suffix(command, ".m4a"):
            return CompletedCommand(returncode=0, stdout=json.dumps(_audio_probe()), stderr="")
        if command[:1] == ("ffprobe",):
            return CompletedCommand(returncode=1, stdout="", stderr="invalid media")
        return CompletedCommand(returncode=0, stdout="", stderr="")


def _live_observation_runner() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_live_observation"
    )


def _noisy_blocked_runtime_probe_payload(
    *,
    english_fixture: Path,
    hf_home: Path,
    private_cache_path: str,
    raw_model_id: str,
    raw_token_value: str,
    raw_transcript_text: str,
) -> dict[str, object]:
    return {
        "schema_version": "audio_transcription_sidecar_runtime_probe_v1",
        "packages": {
            "faster_whisper": True,
            "pyannote_audio": True,
            "huggingface_hub": True,
            "torch": True,
        },
        "torch": {
            "gpu_available": False,
            "acceleration_family": "cpu",
            "cpu_fallback_observed": True,
        },
        "model_access": {"status": "blocked"},
        "stt": {
            "profile_label": "stt_sv_en_primary",
            "backend_family": "faster_whisper",
            "cache_reuse_observed": False,
            "status": "blocked",
            "failure": {
                "exception_class": "RuntimeError",
                "failure_code": "gpu_backend_runtime_unavailable",
                "fixture_path": english_fixture.as_posix(),
                "message": "CUDA failed with error CUDA driver version is insufficient",
                "model_id": raw_model_id,
                "private_cache_path": private_cache_path,
                "token_value": raw_token_value,
                "transcript_text": raw_transcript_text,
            },
            "fixtures": [],
        },
        "diarization": {
            "profile_label": "diarization_sv_en_primary",
            "backend_family": "pyannote_audio",
            "status": "blocked",
            "failure": {
                "cache_root": hf_home.as_posix(),
                "exception_class": "GatedRepoError",
                "failure_code": "gated_model_access_denied",
                "message": "Gated model access denied for selected pyannote model",
                "model_id": raw_model_id,
                "token_value": raw_token_value,
            },
            "exclusive_diarization_available": False,
            "alignment_suitable": False,
            "exact_speaker_count_supported": True,
            "exact_speaker_count_exercised": False,
            "min_max_speaker_range_supported": True,
            "min_max_speaker_range_exercised": False,
            "fixtures": [],
        },
    }


def _audio_probe() -> dict[str, object]:
    return {
        "streams": [{"codec_name": "mp3", "sample_rate": "44100", "channels": 2}],
        "format": {"format_name": "mp3", "duration": "12.0", "size": "1000"},
    }


def _contains_suffix(command: Sequence[str], suffix: str) -> bool:
    return any(value.endswith(suffix) for value in command)


def _runs_runtime_probe(command: Sequence[str]) -> bool:
    return "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_runtime_probe" in command


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def _mapping_at(payload: Mapping[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"{key} must be a JSON object")
    return {str(item_key): item for item_key, item in value.items() if isinstance(item_key, str)}
