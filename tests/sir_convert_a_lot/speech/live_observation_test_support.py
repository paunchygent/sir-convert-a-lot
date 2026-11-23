"""Shared command-runner fake and probe payloads for STT live-observation tests.

Purpose:
    Hold the operator command-runner double and runtime-probe payloads so the
    live-observation test module stays focused on behavior cases.

Relationships:
    - Used by `test_audio_transcription_sidecar_live_observation_runtime`.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType


class FakeCommandRunner:
    """Command runner that models operator-facing subprocess outcomes."""

    def __init__(self, *, runtime_probe_payload: Mapping[str, object]) -> None:
        command_module = importlib.import_module(
            "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_commands"
        )
        self._completed_command = command_module.CompletedCommand
        self._runtime_probe_payload = dict(runtime_probe_payload)
        self.commands: list[tuple[str, ...]] = []

    def run(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
    ) -> object:
        del timeout_seconds
        normalized = tuple(command)
        self.commands.append(normalized)
        if normalized[:4] == ("sudo", "-n", "docker", "buildx"):
            return self._completed_command(returncode=0, stdout="image-built\n", stderr="")
        if _runs_runtime_probe(normalized):
            return self._completed_command(
                returncode=0,
                stdout=json.dumps(self._runtime_probe_payload),
                stderr="",
            )
        if normalized[:1] == ("ffmpeg",):
            return self._completed_command(returncode=0, stdout="ffmpeg version 7.1", stderr="")
        if _runs_tool(normalized, "ffmpeg"):
            return self._completed_command(returncode=0, stdout="ffmpeg version 7.1", stderr="")
        if _runs_tool(normalized, "ffprobe") and "-version" in normalized:
            return self._completed_command(returncode=0, stdout="ffprobe version 7.1", stderr="")
        if _runs_tool(normalized, "ffprobe") and _contains_suffix(normalized, ".mp3"):
            return self._completed_command(
                returncode=0,
                stdout=json.dumps(
                    {
                        "streams": [{"codec_name": "mp3", "sample_rate": "44100", "channels": 2}],
                        "format": {
                            "format_name": "mp3",
                            "duration": "675.250667",
                            "size": "16311853",
                        },
                    },
                ),
                stderr="",
            )
        if _runs_tool(normalized, "ffprobe") and _contains_suffix(normalized, ".m4a"):
            return self._completed_command(
                returncode=0,
                stdout=json.dumps(
                    {
                        "streams": [{"codec_name": "aac", "sample_rate": "48000", "channels": 1}],
                        "format": {
                            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                            "duration": "18.474667",
                            "size": "161184",
                        },
                    },
                ),
                stderr="",
            )
        if _runs_tool(normalized, "ffprobe"):
            return self._completed_command(returncode=1, stdout="", stderr="invalid media")
        return self._completed_command(returncode=0, stdout="", stderr="")


def live_observation_runner() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_live_observation"
    )


def profile_proof_runner() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_profile_proof"
    )


def read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def mapping_at(payload: Mapping[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"{key} must be a JSON object")
    return {str(item_key): item for item_key, item in value.items() if isinstance(item_key, str)}


def sequence_at(payload: Mapping[str, object], key: str) -> Sequence[object]:
    value = payload[key]
    if not isinstance(value, list):
        raise AssertionError(f"{key} must be a JSON array")
    return value


def _contains_suffix(command: Sequence[str], suffix: str) -> bool:
    return any(value.endswith(suffix) for value in command)


def _runs_runtime_probe(command: Sequence[str]) -> bool:
    return "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_runtime_probe" in command


def runtime_probe_command(commands: Sequence[Sequence[str]]) -> Sequence[str]:
    for command in commands:
        if _runs_runtime_probe(command):
            return command
    raise AssertionError("runtime probe command was not captured")


def _runs_tool(command: Sequence[str], tool: str) -> bool:
    return command[:1] == (tool,) or (
        command[:4] == ("sudo", "-n", "docker", "run")
        and "--entrypoint" in command
        and tool in command
    )


def complete_runtime_probe_payload() -> dict[str, object]:
    return {
        "schema_version": "audio_transcription_sidecar_runtime_probe_v1",
        "packages": {
            "faster_whisper": True,
            "pyannote_audio": True,
            "huggingface_hub": True,
            "torch": True,
            "torchaudio": True,
            "torchcodec_audio_decoder": True,
            "miopen_hiprtc_headers": True,
        },
        "torch": {
            "gpu_available": True,
            "acceleration_family": "rocm",
            "cpu_fallback_observed": False,
        },
        "model_access": {"status": "ready"},
        "stt": {
            "profile_label": "stt_sv_en_primary",
            "backend_family": "faster_whisper",
            "cache_reuse_observed": True,
            "status": "ready",
            "fixtures": [
                {
                    "fixture_label": "operator_en_fixture",
                    "language": "en",
                    "detected_language": "en",
                    "segment_count": 9,
                    "word_timestamps_available": True,
                    "duration_seconds": 675.250667,
                },
                {
                    "fixture_label": "operator_sv_fixture",
                    "language": "sv",
                    "detected_language": "sv",
                    "segment_count": 3,
                    "word_timestamps_available": True,
                    "duration_seconds": 18.474667,
                },
            ],
        },
        "diarization": {
            "profile_label": "diarization_sv_en_primary",
            "backend_family": "pyannote_audio",
            "status": "ready",
            "exclusive_diarization_available": True,
            "alignment_suitable": True,
            "exact_speaker_count_supported": True,
            "exact_speaker_count_exercised": True,
            "min_max_speaker_range_supported": True,
            "min_max_speaker_range_exercised": True,
            "fixtures": [
                {
                    "fixture_label": "operator_en_fixture",
                    "diarized_segment_count": 11,
                    "exclusive_speaker_segments": True,
                    "alignment_suitable": True,
                },
                {
                    "fixture_label": "operator_sv_fixture",
                    "diarized_segment_count": 1,
                    "exclusive_speaker_segments": True,
                    "alignment_suitable": True,
                },
            ],
        },
    }


def blocked_runtime_probe_payload() -> dict[str, object]:
    payload = complete_runtime_probe_payload()
    payload["torch"] = {
        "gpu_available": False,
        "acceleration_family": "cpu",
        "cpu_fallback_observed": True,
    }
    payload["model_access"] = {"status": "blocked"}
    stt = mapping_at(payload, "stt")
    stt["status"] = "blocked"
    stt["fixtures"] = []
    payload["stt"] = stt
    diarization = mapping_at(payload, "diarization")
    diarization["status"] = "blocked"
    diarization["fixtures"] = []
    diarization["exact_speaker_count_exercised"] = False
    diarization["min_max_speaker_range_exercised"] = False
    payload["diarization"] = diarization
    return payload
