"""Audio transcription sidecar live-observation producer behavior.

Purpose:
    Exercise the operator command that produces sanitized live Hemma STT sidecar
    observations for profile-proof ingestion.

Relationships:
    - Exercises the live-observation producer CLI boundary.
    - Feeds generated observations into the profile-proof runner to verify the
      producer emits the contract consumed by backend profile selection.
"""

from __future__ import annotations

import importlib
import json
import os
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType

import pytest


def test_live_observation_pdm_command_targets_purpose_named_runner() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    scripts = payload["tool"]["pdm"]["scripts"]

    assert scripts["benchmark:stt-sidecar-live-observation"] == (
        "python -m "
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_live_observation"
    )


def test_host_mode_writes_sanitized_observation_that_profile_proof_accepts(
    tmp_path: Path,
) -> None:
    live_runner = _live_observation_runner()
    profile_runner = _profile_proof_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=_complete_runtime_probe_payload())
    hf_home = tmp_path / "hf"
    hf_hub_cache = hf_home / "hub"
    hf_hub_cache.mkdir(parents=True)
    english_fixture = tmp_path / "english-dialogue-two-speakers.mp3"
    swedish_fixture = tmp_path / "swedish-monologue-one-speaker.m4a"
    english_fixture.write_bytes(b"english audio placeholder")
    swedish_fixture.write_bytes(b"swedish audio placeholder")

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
        command_runner=fake_runner,
        environment={
            "HF_TOKEN": "hf_private_token_value",
            "HF_HOME": hf_home.as_posix(),
            "HF_HUB_CACHE": hf_hub_cache.as_posix(),
        },
    )

    observation_path = tmp_path / "live-observation.json"
    observation = _read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert observation["schema_version"] == "audio_transcription_sidecar_live_observation_v1"
    assert observation["observation_failure_reasons"] == []
    assert _mapping_at(observation, "sidecar_launch")["build_contract"] == "buildkit"
    codec_boundary = _mapping_at(observation, "codec_boundary")
    assert codec_boundary["valid_audio_probe_exercised"] is True
    assert codec_boundary["bad_media_fails_closed"] is True
    assert codec_boundary["no_audio_fails_closed"] is True
    assert codec_boundary["unsupported_media_fails_closed"] is True
    assert _mapping_at(observation, "runtime")["gpu_execution_confirmed"] is True
    assert _mapping_at(observation, "runtime")["cpu_fallback_observed"] is False
    assert _mapping_at(observation, "speaker_hints") == {
        "exact_speaker_count_supported": True,
        "exact_speaker_count_exercised": True,
        "min_max_speaker_range_supported": True,
        "min_max_speaker_range_exercised": True,
    }
    assert _mapping_at(observation, "duration") == {
        "proof_kind": "synthetic_duration_lifecycle",
        "duration_seconds": 7200.0,
        "chunk_count": 12,
        "max_chunk_duration_seconds": 600.0,
        "lifecycle_assumptions_exercised": True,
    }
    assert _mapping_at(observation, "batch_lifecycle") == {
        "duration_seconds": 7200.0,
        "chunk_count": 12,
        "max_chunk_duration_seconds": 600.0,
        "progress_updates_observed": True,
        "checkpoints_observed": True,
        "detached_status_capable": True,
        "cancel_semantics_observed": True,
        "retry_semantics_observed": True,
    }
    assert "english-dialogue-two-speakers.mp3" not in persisted_text
    assert "swedish-monologue-one-speaker.m4a" not in persisted_text
    assert "hf_private_token_value" not in persisted_text
    assert hf_home.as_posix() not in persisted_text
    assert "provider/private-stt-model" not in persisted_text

    profile_exit_code = profile_runner.main(
        [
            "--mode",
            "live",
            "--live-observation-json",
            observation_path.as_posix(),
            "--output-root",
            (tmp_path / "profile-proof").as_posix(),
        ],
    )

    profile_report = _read_json_object(tmp_path / "profile-proof" / "profile-proof.json")
    assert profile_exit_code == 0
    assert profile_report["proof_ready"] is True


def test_host_mode_records_blocked_model_runtime_without_fabricating_readiness(
    tmp_path: Path,
) -> None:
    live_runner = _live_observation_runner()
    profile_runner = _profile_proof_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=_blocked_runtime_probe_payload())
    hf_home = tmp_path / "hf"
    hf_hub_cache = hf_home / "hub"
    hf_hub_cache.mkdir(parents=True)
    english_fixture = tmp_path / "english-dialogue-two-speakers.mp3"
    swedish_fixture = tmp_path / "swedish-monologue-one-speaker.m4a"
    english_fixture.write_bytes(b"english audio placeholder")
    swedish_fixture.write_bytes(b"swedish audio placeholder")

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
        command_runner=fake_runner,
        environment={
            "HF_TOKEN": "hf_private_token_value",
            "HF_HOME": hf_home.as_posix(),
            "HF_HUB_CACHE": hf_hub_cache.as_posix(),
        },
    )

    observation_path = tmp_path / "live-observation.json"
    observation = _read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    assert exit_code == 2
    assert observation["observation_failure_reasons"] == [
        "faster_whisper_runtime_blocked",
        "pyannote_audio_runtime_blocked",
        "gpu_required_execution_not_proven",
    ]
    assert _mapping_at(observation, "backend_dependencies")["faster_whisper_importable"] is True
    assert _mapping_at(observation, "huggingface_readiness")["model_access_status"] == "blocked"
    assert _mapping_at(observation, "runtime")["gpu_execution_confirmed"] is False
    assert _mapping_at(observation, "runtime")["cpu_fallback_observed"] is True
    assert _mapping_at(observation, "content_safety") == {
        "transcript_text_in_report": False,
        "raw_model_ids_in_report": False,
        "secret_values_in_report": False,
        "private_paths_in_report": False,
        "generated_artifacts_in_repo": False,
    }
    assert "hf_private_token_value" not in persisted_text
    assert hf_home.as_posix() not in persisted_text

    profile_exit_code = profile_runner.main(
        [
            "--mode",
            "live",
            "--live-observation-json",
            observation_path.as_posix(),
            "--output-root",
            (tmp_path / "profile-proof").as_posix(),
        ],
    )

    profile_report = _read_json_object(tmp_path / "profile-proof" / "profile-proof.json")
    rejection_reasons = _sequence_at(
        _mapping_at(profile_report, "profile_selection"),
        "rejection_reasons",
    )
    assert profile_exit_code == 2
    assert "faster_whisper_runtime_blocked" in rejection_reasons
    assert "pyannote_audio_runtime_blocked" in rejection_reasons
    assert "gpu_required_execution_not_proven" in rejection_reasons
    assert "cpu_fallback_observed" in rejection_reasons


def test_operator_command_loads_repo_env_without_exposing_secret_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_runner = _live_observation_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=_complete_runtime_probe_payload())
    hf_home = tmp_path / "hf"
    hf_hub_cache = hf_home / "hub"
    hf_hub_cache.mkdir(parents=True)
    english_fixture = tmp_path / "english-dialogue-two-speakers.mp3"
    swedish_fixture = tmp_path / "swedish-monologue-one-speaker.m4a"
    english_fixture.write_bytes(b"english audio placeholder")
    swedish_fixture.write_bytes(b"swedish audio placeholder")
    secret_value = "hf_private_token_value_from_repo_env"
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                f"HF_TOKEN={secret_value}",
                f"HF_HOME={hf_home.as_posix()}",
                f"HF_HUB_CACHE={hf_hub_cache.as_posix()}",
                "",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    exit_code = live_runner.main(
        [
            "--runtime-mode",
            "docker",
            "--sidecar-launch-observed",
            "--english-fixture",
            english_fixture.as_posix(),
            "--swedish-fixture",
            swedish_fixture.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
        ],
        command_runner=fake_runner,
    )

    observation_path = tmp_path / "live-observation.json"
    observation = _read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    flattened_commands = "\n".join(" ".join(command) for command in fake_runner.commands)
    runtime_probe_command = _runtime_probe_command(fake_runner.commands)
    assert exit_code == 0
    assert _mapping_at(observation, "huggingface_readiness")["token_env_vars_present"] is True
    assert "-e HF_TOKEN" in flattened_commands
    assert "--preserve-env=HF_TOKEN" in runtime_probe_command
    assert secret_value not in flattened_commands
    assert secret_value not in persisted_text
    assert hf_home.as_posix() not in persisted_text


def test_subprocess_runner_forwards_loaded_operator_environment() -> None:
    command_module = importlib.import_module(
        "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_commands"
    )
    secret_value = "hf_private_token_value_for_child_process"
    runner = command_module.SubprocessCommandRunner(
        environment={**os.environ, "HF_TOKEN": secret_value}
    )

    result = runner.run(("/usr/bin/env",), timeout_seconds=5.0)

    assert result.returncode == 0
    assert f"HF_TOKEN={secret_value}" in result.stdout


def test_docker_mode_uses_buildkit_buildx_for_benchmark_sidecar(
    tmp_path: Path,
) -> None:
    live_runner = _live_observation_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=_complete_runtime_probe_payload())
    hf_home = tmp_path / "hf"
    hf_hub_cache = hf_home / "hub"
    hf_hub_cache.mkdir(parents=True)
    english_fixture = tmp_path / "english-dialogue-two-speakers.mp3"
    swedish_fixture = tmp_path / "swedish-monologue-one-speaker.m4a"
    english_fixture.write_bytes(b"english audio placeholder")
    swedish_fixture.write_bytes(b"swedish audio placeholder")

    exit_code = live_runner.main(
        [
            "--runtime-mode",
            "docker",
            "--sidecar-launch-observed",
            "--english-fixture",
            english_fixture.as_posix(),
            "--swedish-fixture",
            swedish_fixture.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
        ],
        command_runner=fake_runner,
        environment={
            "HF_TOKEN": "hf_private_token_value",
            "HF_HOME": hf_home.as_posix(),
            "HF_HUB_CACHE": hf_hub_cache.as_posix(),
        },
    )

    assert exit_code == 0
    assert any(
        command[:5]
        == (
            "sudo",
            "-n",
            "docker",
            "buildx",
            "build",
        )
        and "--load" in command
        for command in fake_runner.commands
    )
    assert not any(
        command[:4] == ("sudo", "-n", "docker", "build") for command in fake_runner.commands
    )
    assert any(command[:4] == ("sudo", "-n", "docker", "run") for command in fake_runner.commands)
    dockerfile = Path("containers/stt-sidecar-benchmark/Dockerfile").read_text(encoding="utf-8")
    assert "faster-whisper" in dockerfile
    assert "pyannote.audio" in dockerfile
    assert '"huggingface-hub==0.34.4"' in dockerfile


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


def _live_observation_runner() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_live_observation"
    )


def _profile_proof_runner() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_profile_proof"
    )


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


def _sequence_at(payload: Mapping[str, object], key: str) -> Sequence[object]:
    value = payload[key]
    if not isinstance(value, list):
        raise AssertionError(f"{key} must be a JSON array")
    return value


def _contains_suffix(command: Sequence[str], suffix: str) -> bool:
    return any(value.endswith(suffix) for value in command)


def _runs_runtime_probe(command: Sequence[str]) -> bool:
    return "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_runtime_probe" in command


def _runtime_probe_command(commands: Sequence[Sequence[str]]) -> Sequence[str]:
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


def _complete_runtime_probe_payload() -> dict[str, object]:
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


def _blocked_runtime_probe_payload() -> dict[str, object]:
    payload = _complete_runtime_probe_payload()
    payload["torch"] = {
        "gpu_available": False,
        "acceleration_family": "cpu",
        "cpu_fallback_observed": True,
    }
    payload["model_access"] = {"status": "blocked"}
    stt = _mapping_at(payload, "stt")
    stt["status"] = "blocked"
    stt["fixtures"] = []
    payload["stt"] = stt
    diarization = _mapping_at(payload, "diarization")
    diarization["status"] = "blocked"
    diarization["fixtures"] = []
    diarization["exact_speaker_count_exercised"] = False
    diarization["min_max_speaker_range_exercised"] = False
    payload["diarization"] = diarization
    return payload
