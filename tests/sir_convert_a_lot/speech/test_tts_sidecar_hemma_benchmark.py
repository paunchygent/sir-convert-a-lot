"""Tests for the Hemma TTS sidecar benchmark Docker launch and readiness helpers.

Purpose:
    Protect the container launch, readiness, and settings-parsing helpers
    behind the live Hemma sidecar benchmark so local regressions are caught
    before remote runs.

Relationships:
    - Exercises `tts_sidecar_benchmark_runtime` and the
      `run_tts_sidecar_hemma_benchmark` entrypoint.
    - Cache, measurement, and report-probe cases live in
      `test_tts_sidecar_benchmark_probes`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_tts_sidecar_hemma_benchmark
from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    _build_runtime_metadata_probe_python,
    prefetch_qwen3_tts_assets,
    start_sidecar,
)
from tests.sir_convert_a_lot.speech.tts_sidecar_benchmark_test_support import (
    build_settings,
)


def test_runtime_metadata_probe_script_is_valid_python() -> None:
    script = _build_runtime_metadata_probe_python()

    ast.parse(script)
    assert "HF_HOME" in script
    assert "vllm-omni" in script
    assert "VLLM_USE_TRITON_FLASH_ATTN" in script


def test_parse_args_prefers_canonical_hemma_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH",
        "/srv/scratch/custom/cache/huggingface",
    )
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT",
        "/home/paunchygent/.data/custom/cache/huggingface",
    )

    settings = run_tts_sidecar_hemma_benchmark._parse_args([])

    assert settings.hf_cache_dir == Path("/srv/scratch/custom/cache/huggingface")
    assert settings.hf_cache_home_mount == Path("/home/paunchygent/.data/custom/cache/huggingface")
    assert settings.voice == "ryan"
    assert settings.task_type == "CustomVoice"
    assert settings.model == "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"


def test_parse_args_uses_base_model_defaults_for_clone_lane(tmp_path: Path) -> None:
    probe_text_path = tmp_path / "probe.txt"
    probe_text_path.write_text("hello from file\n", encoding="utf-8")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("reference transcript\n", encoding="utf-8")

    settings = run_tts_sidecar_hemma_benchmark._parse_args(
        [
            "--profile-type",
            "Base",
            "--language",
            "English",
            "--probe-text-file",
            probe_text_path.as_posix(),
            "--reference-audio",
            (tmp_path / "reference.wav").as_posix(),
            "--reference-transcript-file",
            transcript_path.as_posix(),
        ]
    )

    assert settings.task_type == "Base"
    assert settings.language == "English"
    assert settings.model == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
    assert settings.probe_text == "hello from file"
    assert settings.reference_transcript == "reference transcript"
    assert settings.use_triton_flash_attn is True


def test_parse_args_allows_disabling_triton_flash_attention() -> None:
    settings = run_tts_sidecar_hemma_benchmark._parse_args(
        [
            "--disable-triton-flash-attn",
        ]
    )

    assert settings.use_triton_flash_attn is False


def test_prefetch_qwen3_tts_assets_downloads_tokenizer_and_enables_triton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage_config_path = tmp_path / "tts-sidecar-stage-config.yaml"
    stage_config_path.write_text("stage_args: []\n", encoding="utf-8")
    hf_cache_dir = tmp_path / "hf-cache"
    recorded_commands: list[list[str]] = []

    def _fake_docker_checked(
        args: list[str], *, label: str, preserve_env: tuple[str, ...] = ()
    ) -> str:
        assert label == "docker run tts-sidecar tokenizer prefetch"
        assert preserve_env == ()
        recorded_commands.append(args)
        return (
            '{"copied_targets":["/cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-0.6B-'
            'CustomVoice/snapshots/test/speech_tokenizer"]}'
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime.docker_checked",
        _fake_docker_checked,
    )
    settings = build_settings(
        tmp_path,
        hf_cache_dir=hf_cache_dir,
        voice="Chelsie",
        stage_config_path=stage_config_path,
    )

    prefetch_qwen3_tts_assets(settings)

    assert len(recorded_commands) == 1
    command = recorded_commands[0]
    assert f"{hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}" in command
    assert "VLLM_USE_TRITON_FLASH_ATTN=1" in command
    assert "Qwen/Qwen3-TTS-Tokenizer-12Hz" in command[-1]


def test_prepare_output_root_removes_stale_failure_and_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "tts-sidecar-output"
    artifacts_dir = output_root / "artifacts"
    inputs_dir = output_root / "inputs"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "sample.wav").write_bytes(b"stale")
    (artifacts_dir / "sample.wav.error.txt").write_text("stale error\n", encoding="utf-8")
    (inputs_dir / "reference_audio.wav").write_bytes(b"keep-me")
    (output_root / "failure.txt").write_text("old failure\n", encoding="utf-8")
    (output_root / "report.json").write_text("{}", encoding="utf-8")

    prepared = run_tts_sidecar_hemma_benchmark._prepare_output_root(output_root)

    (
        prepared_artifacts_dir,
        prepared_inputs_dir,
        logs_path,
        report_json_path,
        report_md_path,
        failure_path,
    ) = prepared
    assert prepared_artifacts_dir == artifacts_dir
    assert prepared_inputs_dir == inputs_dir
    assert list(prepared_artifacts_dir.iterdir()) == []
    assert (prepared_inputs_dir / "reference_audio.wav").read_bytes() == b"keep-me"
    assert logs_path.exists() is False
    assert report_json_path.exists() is False
    assert report_md_path.exists() is False
    assert failure_path.exists() is False


def test_start_sidecar_uses_persistent_hf_cache_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage_config_path = tmp_path / "tts-sidecar-stage-config.yaml"
    stage_config_path.write_text("model: test\n", encoding="utf-8")
    hf_cache_dir = tmp_path / "hf-cache"
    recorded_commands: list[list[str]] = []

    def _fake_docker_checked(
        args: list[str], *, label: str, preserve_env: tuple[str, ...] = ()
    ) -> str:
        assert label == "docker run tts-sidecar sidecar"
        assert preserve_env == ()
        recorded_commands.append(args)
        return "container-id"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime.docker_checked",
        _fake_docker_checked,
    )
    settings = build_settings(
        tmp_path,
        hf_cache_dir=hf_cache_dir,
        voice="Chelsie",
        stage_config_path=stage_config_path,
    )

    start_sidecar(settings)

    assert len(recorded_commands) == 1
    command = recorded_commands[0]
    assert f"{hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}" in command
    assert f"HF_HOME={CONTAINER_HF_HOME}" in command
    assert f"HF_HUB_CACHE={CONTAINER_HF_HUB_CACHE}" in command
    assert f"TRANSFORMERS_CACHE={CONTAINER_HF_HOME}" in command
    assert "VLLM_USE_TRITON_FLASH_ATTN=1" in command
    assert "--enforce-eager" in command


def test_start_sidecar_preserves_hf_token_name_across_sudo_without_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage_config_path = tmp_path / "tts-sidecar-stage-config.yaml"
    stage_config_path.write_text("model: test\n", encoding="utf-8")
    token_sentinel = "hf_synthetic_marker_value"
    monkeypatch.setenv("HF_TOKEN", token_sentinel)
    recorded_commands: list[list[str]] = []

    def _fake_run_checked(command: list[str], *, label: str) -> str:
        assert label == "docker run tts-sidecar sidecar"
        recorded_commands.append(command)
        return "container-id"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime.run_checked",
        _fake_run_checked,
    )
    settings = build_settings(
        tmp_path,
        stage_config_path=stage_config_path,
        hf_token_present=True,
    )

    start_sidecar(settings)

    command = recorded_commands[0]
    assert command[:3] == ["sudo", "-n", "--preserve-env=HF_TOKEN"]
    assert "docker" in command
    token_index = command.index("HF_TOKEN")
    assert command[token_index - 1] == "-e"
    assert not any(
        argument.startswith("HF_TOKEN=") or token_sentinel in argument for argument in command
    )


def test_parse_args_records_hf_token_presence_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HF_TOKEN", "  hf_synthetic_marker_value  ")

    settings = run_tts_sidecar_hemma_benchmark._parse_args([])

    assert settings.hf_token_present is True


def test_parse_args_rejects_hf_token_command_line_flag() -> None:
    with pytest.raises(SystemExit):
        run_tts_sidecar_hemma_benchmark._parse_args(["--hf-token", "hf_synthetic_marker_value"])
