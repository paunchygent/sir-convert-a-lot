"""Tests for the Task 109 containerized Qwen preprocessing surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task109_hemma_qwen_containerized_preprocessing import (
    DEFAULT_DATA_ROOT_HOME_MOUNT,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    DEFAULT_HF_CACHE,
    DEFAULT_HF_CACHE_HOME_MOUNT,
    DEFAULT_IMAGE,
    DEFAULT_OUTPUT_ROOT,
    _parse_args,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    DEFAULT_DATA_ROOT,
)
from scripts.sir_convert_a_lot.devops.task109_qwen_containerized_preprocessing_runtime import (
    Task109ContainerizedPreprocessingSettings,
    build_containerized_preprocessing_command,
    run_containerized_preprocessing,
)


def test_task109_parse_args_defaults() -> None:
    """The Task 109 runner should expose deterministic defaults."""
    settings = _parse_args([])

    assert settings.output_root == DEFAULT_OUTPUT_ROOT
    assert settings.dockerfile_path == DEFAULT_DOCKERFILE_PATH
    assert settings.image == DEFAULT_IMAGE
    assert settings.hf_cache_dir == DEFAULT_HF_CACHE
    assert settings.hf_cache_home_mount == DEFAULT_HF_CACHE_HOME_MOUNT
    assert settings.data_root == DEFAULT_DATA_ROOT
    assert settings.data_root_home_mount == DEFAULT_DATA_ROOT_HOME_MOUNT
    assert settings.fleurs_max_rows_per_split == DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT
    assert settings.rixvox_splits == ("dev", "test")
    assert settings.rixvox_max_rows_per_split is None
    assert settings.build_image is True


def test_task109_build_command_uses_repo_and_absolute_mounts() -> None:
    """The containerized preprocessing command should reuse repo and DATA mounts."""
    settings = Task109ContainerizedPreprocessingSettings(
        output_root=Path("build/verification/task-109-qwen-containerized-preprocessing"),
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        data_root=Path("/srv/scratch/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"),
        data_root_home_mount=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"
        ),
        build_image=True,
        fleurs_max_rows_per_split=8,
        rixvox_splits=("train", "dev", "test"),
        rixvox_max_rows_per_split=64,
    )
    repo_root = Path("/home/paunchygent/apps/sir-convert-a-lot")
    hf_mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )
    data_mount = MountResolution(
        canonical_root=settings.data_root,
        effective_root=settings.data_root_home_mount,
        used_home_mount=True,
    )

    command = build_containerized_preprocessing_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
    )

    assert "--device" in command
    assert "/dev/kfd" in command
    assert "/dev/dri" in command
    assert "--workdir" in command
    assert "/app" in command
    assert f"{repo_root.as_posix()}:/app" in command
    assert f"{hf_mount.effective_root.as_posix()}:{hf_mount.canonical_root.as_posix()}" in command
    assert (
        f"{data_mount.effective_root.as_posix()}:{data_mount.canonical_root.as_posix()}:ro"
        in command
    )
    assert f"HF_HOME={hf_mount.canonical_root.as_posix()}" in command
    assert "--source-mode" in command
    assert "staged-public-corpus" in command
    assert "--fleurs-max-rows-per-split" in command
    assert "8" in command
    assert "--rixvox-splits" in command
    assert "train,dev,test" in command
    assert "--rixvox-max-rows-per-split" in command
    assert "64" in command


def test_task109_run_containerized_preprocessing_parses_inner_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 109 runtime should parse the inner Task 103 report from mixed stdout."""
    settings = Task109ContainerizedPreprocessingSettings(
        output_root=Path("build/verification/task-109-qwen-containerized-preprocessing"),
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        data_root=Path("/srv/scratch/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"),
        data_root_home_mount=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"
        ),
        build_image=False,
        fleurs_max_rows_per_split=8,
        rixvox_splits=("dev", "test"),
        rixvox_max_rows_per_split=None,
    )
    repo_root = Path("/home/paunchygent/apps/sir-convert-a-lot")
    hf_mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )
    data_mount = MountResolution(
        canonical_root=settings.data_root,
        effective_root=settings.data_root_home_mount,
        used_home_mount=True,
    )

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        assert args[0] == "run"
        assert label == "docker run task109 containerized preprocessing"
        return (
            "\n********\n"
            "Warning: flash-attn is not installed. Will only run the manual PyTorch version.\n"
            "********\n\n"
            "{"
            '"output_root":"/app/build/reference/qwen3-tts-swedish-corpus",'
            '"datasets":["fleurs_sv_se","rixvox","waxholm"],'
            '"asr_model":"KBLab/kb-whisper-large",'
            '"asr_revision":"strict",'
            '"tokenizer_model":"Qwen/Qwen3-TTS-Tokenizer-12Hz",'
            '"inventory_rows":16841,'
            '"curated_rows":24,'
            '"admitted_rows":23,'
            '"prepared_rows":23,'
            '"speaker_ids":["speaker_a","speaker_b"],'
            '"manifest_counts":{"swedish_checkpoint_dev":8,"swedish_final_test":7,"swedish_waxholm_control":8}'
            "}"
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task109_qwen_containerized_preprocessing_runtime.docker_checked",
        _fake_docker_checked,
    )

    result = run_containerized_preprocessing(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
    )

    assert result.command[0:3] == ["sudo", "-n", "docker"]
    assert result.preprocessing_report.inventory_rows == 16841
    assert result.preprocessing_report.prepared_rows == 23
    assert result.preprocessing_report.datasets == ["fleurs_sv_se", "rixvox", "waxholm"]
