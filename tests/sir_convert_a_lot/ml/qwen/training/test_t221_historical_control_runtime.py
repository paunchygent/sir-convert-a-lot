"""Focused tests for the T221 historical-control runtime surface.

Purpose:
    Verify the dedicated T221 Docker argv so the repo can recreate the
    historical Task 101 contract without silently falling back to the newer
    scratch-only control plane.

Relationships:
    - Exercises `t221_historical_control_runtime.py`.
    - Keeps T221 command assertions close to the module that owns them.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings
from scripts.sir_convert_a_lot.ml.qwen.training.t221_historical_control_runtime import (
    build_detached_historical_control_command,
)


def test_build_detached_historical_control_command_mounts_historical_bundle() -> None:
    """T221 should mount the surviving historical bundle separately from scratch."""
    settings = TrainingSettings(
        output_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/verification/qwen-t221-historical-control"
        ),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        scratch_build_root=Path("/srv/scratch/sir-convert-a-lot/build"),
        scratch_build_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/build"),
        pilot_bundle_root=Path(
            "/srv/storage/sir-convert-a-lot/backups/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle-20260312h"
        ),
        runs_root=Path("/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune"),
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        batch_size=1,
        throughput_profile_label="hemma-throughput-balanced-v1",
        lr=2e-5,
        num_epochs=1000,
        max_steps=64,
        checkpoint_interval_steps=2,
        eval_interval_steps=1_000_000,
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        gradient_accumulation_steps=4,
        text_embedding_assembly_mode="full_channel_masked",
        text_embedding_mask_policy="text_span_only",
    )
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
    bundle_mount = MountResolution(
        canonical_root=settings.pilot_bundle_root,
        effective_root=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle-20260312h"
        ),
        used_home_mount=True,
    )

    command, run_root = build_detached_historical_control_command(
        settings,
        repo_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        bundle_mount=bundle_mount,
        launch_id="task221-20260317t190000z-a1",
        container_name="task221-20260317t190000z-a1-container",
        launch_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/verification/"
            "qwen-t221-historical-control/task221-20260317t190000z-a1"
        ),
    )

    assert run_root.as_posix().endswith("/task221-20260317t190000z-a1")
    assert (
        "/home/paunchygent/.data/sir-convert-a-lot/reference/"
        "qwen3-tts-swedish-task101-pilot-bundle-20260312h:"
        "/app/historical-task101-pilot-bundle:ro" in command
    )
    assert (
        "/app/historical-task101-pilot-bundle/manifests/swedish_pilot_train.prepared.jsonl"
        in command
    )
    assert (
        "/app/historical-task101-pilot-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl"
        in command
    )
    assert "--text-embedding-assembly-mode" in command
    assert "full_channel_masked" in command
    assert "--text-embedding-mask-policy" in command
    assert "text_span_only" in command
    assert "--batch-size" in command
    assert "1" in command
    assert "--checkpoint-interval-steps" in command
    assert "2" in command
    assert "--eval-interval-steps" in command
    assert "1000000" in command
    assert "--gradient-accumulation-steps" in command
    assert "4" in command
    assert "sir-convert-a-lot-qwen-finetune-hemma:task100" in command
    assert "task101-qwen-pilot" in command
