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
import os
import tomllib
from pathlib import Path

import pytest

from tests.sir_convert_a_lot.speech.live_observation_test_support import (
    FakeCommandRunner,
    blocked_runtime_probe_payload,
    complete_runtime_probe_payload,
    live_observation_runner,
    mapping_at,
    profile_proof_runner,
    read_json_object,
    runtime_probe_command,
    sequence_at,
)


def test_live_observation_pdm_command_targets_purpose_named_runner() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    scripts = payload["tool"]["pdm"]["scripts"]

    assert scripts["benchmark:stt-sidecar-live-observation"] == (
        "agent-secrets run --set sir-convert-a-lot-operator -- python -m "
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_live_observation"
    )


def test_host_mode_writes_sanitized_observation_that_profile_proof_accepts(
    tmp_path: Path,
) -> None:
    live_runner = live_observation_runner()
    profile_runner = profile_proof_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=complete_runtime_probe_payload())
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
    observation = read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert observation["schema_version"] == "audio_transcription_sidecar_live_observation_v1"
    assert observation["observation_failure_reasons"] == []
    assert mapping_at(observation, "sidecar_launch")["build_contract"] == "buildkit"
    codec_boundary = mapping_at(observation, "codec_boundary")
    assert codec_boundary["valid_audio_probe_exercised"] is True
    assert codec_boundary["bad_media_fails_closed"] is True
    assert codec_boundary["no_audio_fails_closed"] is True
    assert codec_boundary["unsupported_media_fails_closed"] is True
    assert mapping_at(observation, "runtime")["gpu_execution_confirmed"] is True
    assert mapping_at(observation, "runtime")["cpu_fallback_observed"] is False
    assert mapping_at(observation, "speaker_hints") == {
        "exact_speaker_count_supported": True,
        "exact_speaker_count_exercised": True,
        "min_max_speaker_range_supported": True,
        "min_max_speaker_range_exercised": True,
    }
    assert mapping_at(observation, "duration") == {
        "proof_kind": "synthetic_duration_lifecycle",
        "duration_seconds": 7200.0,
        "chunk_count": 12,
        "max_chunk_duration_seconds": 600.0,
        "lifecycle_assumptions_exercised": True,
    }
    assert mapping_at(observation, "batch_lifecycle") == {
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

    profile_report = read_json_object(tmp_path / "profile-proof" / "profile-proof.json")
    assert profile_exit_code == 0
    assert profile_report["proof_ready"] is True


def test_host_mode_records_blocked_model_runtime_without_fabricating_readiness(
    tmp_path: Path,
) -> None:
    live_runner = live_observation_runner()
    profile_runner = profile_proof_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=blocked_runtime_probe_payload())
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
    observation = read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    assert exit_code == 2
    assert observation["observation_failure_reasons"] == [
        "faster_whisper_runtime_blocked",
        "pyannote_audio_runtime_blocked",
        "gpu_required_execution_not_proven",
    ]
    assert mapping_at(observation, "backend_dependencies")["faster_whisper_importable"] is True
    assert mapping_at(observation, "huggingface_readiness")["model_access_status"] == "blocked"
    assert mapping_at(observation, "runtime")["gpu_execution_confirmed"] is False
    assert mapping_at(observation, "runtime")["cpu_fallback_observed"] is True
    assert mapping_at(observation, "content_safety") == {
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

    profile_report = read_json_object(tmp_path / "profile-proof" / "profile-proof.json")
    rejection_reasons = sequence_at(
        mapping_at(profile_report, "profile_selection"),
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
    live_runner = live_observation_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=complete_runtime_probe_payload())
    hf_home = tmp_path / "hf"
    hf_hub_cache = hf_home / "hub"
    hf_hub_cache.mkdir(parents=True)
    english_fixture = tmp_path / "english-dialogue-two-speakers.mp3"
    swedish_fixture = tmp_path / "swedish-monologue-one-speaker.m4a"
    english_fixture.write_bytes(b"english audio placeholder")
    swedish_fixture.write_bytes(b"swedish audio placeholder")
    secret_value = "hf_private_token_value_from_repo_env"
    file_secret_value = "hf_file_token_value_must_be_ignored"
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                f"HF_TOKEN={file_secret_value}",
                f"HF_HOME={hf_home.as_posix()}",
                f"HF_HUB_CACHE={hf_hub_cache.as_posix()}",
                "",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HF_TOKEN", secret_value)

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
    observation = read_json_object(observation_path)
    persisted_text = observation_path.read_text(encoding="utf-8")
    flattened_commands = "\n".join(" ".join(command) for command in fake_runner.commands)
    runtime_probe_argv = runtime_probe_command(fake_runner.commands)
    assert exit_code == 0
    assert mapping_at(observation, "huggingface_readiness")["token_env_vars_present"] is True
    assert "-e HF_TOKEN" in flattened_commands
    assert "--preserve-env=HF_TOKEN" in runtime_probe_argv
    assert secret_value not in flattened_commands
    assert secret_value not in persisted_text
    assert file_secret_value not in flattened_commands
    assert file_secret_value not in persisted_text
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
    live_runner = live_observation_runner()
    fake_runner = FakeCommandRunner(runtime_probe_payload=complete_runtime_probe_payload())
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
