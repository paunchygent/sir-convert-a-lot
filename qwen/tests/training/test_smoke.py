"""Tests for the canonical Qwen training smoke surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    SmokeSettings,
    build_smoke_probe_command,
    run_smoke_probe,
)
from scripts.sir_convert_a_lot.ml.qwen.training.smoke import (
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_HF_CACHE,
    DEFAULT_HF_CACHE_HOME_MOUNT,
    DEFAULT_IMAGE,
    DEFAULT_MODEL_ID,
    DEFAULT_OUTPUT_ROOT,
    parse_args,
)


def test_parse_args_defaults() -> None:
    """The smoke runner should expose deterministic defaults."""
    settings = parse_args([])

    assert settings.output_root == DEFAULT_OUTPUT_ROOT
    assert settings.dockerfile_path == DEFAULT_DOCKERFILE_PATH
    assert settings.image == DEFAULT_IMAGE
    assert settings.model_id == DEFAULT_MODEL_ID
    assert settings.hf_cache_dir == DEFAULT_HF_CACHE
    assert settings.hf_cache_home_mount == DEFAULT_HF_CACHE_HOME_MOUNT
    assert settings.build_image is True


def test_build_smoke_probe_command_uses_rocm_and_cache_mounts() -> None:
    """The in-container smoke command should include ROCm and cache flags."""
    settings = SmokeSettings(
        output_root=Path("build/verification/qwen-training-smoke"),
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:latest",
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        build_image=True,
    )
    mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )

    command = build_smoke_probe_command(settings, hf_mount=mount)

    assert "--device" in command
    assert "/dev/kfd" in command
    assert "/dev/dri" in command
    assert "--ipc=host" in command
    assert "HF_HOME=/cache/huggingface" in command
    assert f"{mount.effective_root.as_posix()}:/cache/huggingface" in command
    assert all("TRANSFORMERS_CACHE=" not in item for item in command)
    assert settings.model_id in command


def test_run_smoke_probe_parses_runtime_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """The smoke probe parser should keep runtime metadata typed."""
    settings = SmokeSettings(
        output_root=Path("build/verification/qwen-training-smoke"),
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:latest",
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        build_image=True,
    )
    mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )

    def fake_docker_checked(args: list[str], *, label: str) -> str:
        assert args[0] == "run"
        assert label == "docker run qwen smoke probe"
        return (
            "\n********\n"
            "Warning: flash-attn is not installed. Will only run the manual PyTorch version.\n"
            "********\n\n"
            "{"
            '"dependency_versions":{"mlflow":"3.10.1","qwen-tts":"0.1.1","torch":"2.10.0+rocm7.1"},'
            '"model_id":"Qwen/Qwen3-TTS-12Hz-1.7B-Base",'
            '"resolved_config_path":"/cache/huggingface/hub/models--Qwen/config.json",'
            '"resolved_model_path":"/cache/huggingface/hub/models--Qwen",'
            '"torchaudio_version":"2.10.0+rocm7.1",'
            '"torch_cuda_available":true,'
            '"torch_cuda_device_count":1,'
            '"torch_hip_version":"7.1.25424",'
            '"torch_version":"2.10.0+rocm7.1",'
            '"flash_attn_importable":true,'
            '"flash_attn_model_load_ok":true,'
            '"flash_attn_version":"2.8.3",'
            '"tts_model_type":"base"'
            "}"
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.docker_checked",
        fake_docker_checked,
    )

    result, command = run_smoke_probe(settings, hf_mount=mount)

    assert command[0:3] == ["sudo", "-n", "docker"]
    assert result.torch_cuda_available is True
    assert result.torch_cuda_device_count == 1
    assert result.torch_hip_version == "7.1.25424"
    assert result.torch_version == "2.10.0+rocm7.1"
    assert result.flash_attn_importable is True
    assert result.flash_attn_model_load_ok is True
    assert result.flash_attn_version == "2.8.3"
    assert result.tts_model_type == "base"
