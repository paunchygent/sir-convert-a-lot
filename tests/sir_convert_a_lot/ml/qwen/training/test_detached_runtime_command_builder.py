"""Focused tests for detached Qwen Docker command construction.

Purpose:
    Verify the bounded detached-runtime command builder without routing through
    broader orchestration tests.

Relationships:
    - Exercises `detached_runtime.command_builder`.
    - Keeps Docker argv assertions close to the module that owns them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    build_detached_training_command,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings


def _training_settings() -> TrainingSettings:
    """Return deterministic settings for detached-runtime command tests."""
    return TrainingSettings(
        output_root=Path("/srv/scratch/sir-convert-a-lot/build/verification/qwen-training"),
        image="sir-convert-a-lot-qwen-finetune-hemma:latest",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        scratch_build_root=Path("/srv/scratch/sir-convert-a-lot/build"),
        scratch_build_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/build"),
        pilot_bundle_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-pilot-bundle"
        ),
        runs_root=Path("/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune"),
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        batch_size=8,
        throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        text_embedding_assembly_mode="semantic_only",
        text_embedding_mask_policy="text_span_only",
    )


def _mounts(settings: TrainingSettings) -> tuple[MountResolution, MountResolution]:
    """Return deterministic HF and scratch mounts for command-builder tests."""
    hf_mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )
    scratch_mount = MountResolution(
        canonical_root=settings.scratch_build_root,
        effective_root=settings.scratch_build_home_mount,
        used_home_mount=True,
    )
    return hf_mount, scratch_mount


def test_build_detached_training_command_uses_rocm_mounts_and_prepared_manifest() -> None:
    """Detached training should target prepared manifests and governed mounts."""
    settings = _training_settings()
    hf_mount, scratch_mount = _mounts(settings)

    command, run_root = build_detached_training_command(
        settings,
        repo_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id="qwen-20260309t120000z",
        container_name="qwen-20260309t120000z-container",
        launch_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/verification/qwen-training/qwen-20260309t120000z"
        ),
    )

    assert run_root.as_posix().endswith("/qwen-20260309t120000z")
    assert "--device" in command
    assert "/dev/kfd" in command
    assert "--ipc=host" in command
    assert "HF_HOME=/cache/huggingface" in command
    assert (
        "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface:/cache/huggingface" in command
    )
    assert "/home/paunchygent/.data/sir-convert-a-lot/build:/app/build" in command
    assert (
        "/app/build/reference/qwen3-tts-swedish-pilot-bundle/manifests/"
        "swedish_pilot_train.prepared.jsonl" in command
    )
    assert (
        "/app/build/reference/qwen3-tts-swedish-pilot-bundle/manifests/"
        "swedish_checkpoint_dev.prepared.jsonl" in command
    )
    assert "--text-embedding-assembly-mode" in command
    assert "semantic_only" in command
    assert "--text-embedding-mask-policy" in command
    assert "text_span_only" in command
    assert "--gradient-accumulation-steps" in command
    assert "4" in command


@pytest.mark.parametrize(
    ("path_kwargs", "offending_path", "expected_label"),
    [
        (
            {"launch_root": Path("/tmp/qwen-launch")},
            "/tmp/qwen-launch/launch.json",
            "launch_metadata_path",
        ),
        (
            {"run_root": Path("/tmp/qwen-run")},
            "/tmp/qwen-run",
            "run_root",
        ),
        (
            {"resume_from_checkpoint": Path("/tmp/qwen-checkpoint/state-step-00000008")},
            "/tmp/qwen-checkpoint/state-step-00000008",
            "resume_from_checkpoint",
        ),
    ],
)
def test_build_detached_training_command_rejects_paths_outside_scratch_root(
    path_kwargs: dict[str, Path],
    offending_path: str,
    expected_label: str,
) -> None:
    """Detached launches should fail closed before Docker for escaped write paths."""
    settings = _training_settings()
    hf_mount, scratch_mount = _mounts(settings)
    launch_root = path_kwargs.get(
        "launch_root",
        Path("/srv/scratch/sir-convert-a-lot/build/verification/qwen-training/qwen-launch"),
    )

    with pytest.raises(ValueError) as exc_info:
        build_detached_training_command(
            settings,
            repo_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            launch_id="qwen-launch",
            container_name="qwen-launch-container",
            launch_root=launch_root,
            run_root=path_kwargs.get("run_root"),
            resume_from_checkpoint=path_kwargs.get("resume_from_checkpoint"),
        )

    message = str(exc_info.value)
    assert expected_label in message
    assert Path(offending_path).resolve().as_posix() in message
    assert settings.scratch_build_root.as_posix() in message
