"""Tests for governed training-bundle container runtime helpers.

Purpose:
    Verify that the restored training-bundle batch runtime launches the shared
    Qwen image with the expected bind mounts, GPU posture, and in-container
    entrypoint instead of finalizing batches in host Python.

Relationships:
    - Exercises `ml.qwen.training.bundle_runtime`.
    - Protects the Task 149/150 governed runtime contract after the migration.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime import (
    TrainingBundleRuntimeFingerprint,
    build_containerized_training_bundle_batch_command,
    run_containerized_training_bundle_batch,
)


def test_build_containerized_training_bundle_batch_command_uses_repo_and_mounts() -> None:
    """The batch command should target the in-container bundle entrypoint with binds."""
    command = build_containerized_training_bundle_batch_command(
        repo_root=Path("/repo"),
        output_root=Path("/srv/scratch/bundle-root"),
        manifest_family="swedish_pilot_train",
        batch_index=3,
        batch_count=2,
        audio_codes_chunk_size=64,
        image="qwen-image:latest",
        hf_mount=MountResolution(
            canonical_root=Path("/srv/scratch/cache/hf"),
            effective_root=Path("/srv/scratch/cache/hf"),
            used_home_mount=False,
        ),
        triton_mount=MountResolution(
            canonical_root=Path("/srv/scratch/cache/triton"),
            effective_root=Path("/srv/scratch/cache/triton"),
            used_home_mount=False,
        ),
        output_root_mount=MountResolution(
            canonical_root=Path("/srv/scratch/bundle-root"),
            effective_root=Path("/srv/scratch/bundle-root"),
            used_home_mount=False,
        ),
    )

    assert command[:6] == [
        "run",
        "--rm",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
    ]
    assert "/repo:/app" in command
    assert "/srv/scratch/cache/hf:/cache/huggingface" in command
    assert "/srv/scratch/cache/triton:/cache/triton" in command
    assert "/srv/scratch/bundle-root:/srv/scratch/bundle-root" in command
    assert command[-12:] == [
        "-m",
        "scripts.sir_convert_a_lot.ml.qwen.training.bundle_in_container",
        "--output-root",
        "/srv/scratch/bundle-root",
        "--manifest-family",
        "swedish_pilot_train",
        "--batch-index",
        "3",
        "--batch-count",
        "2",
        "--audio-codes-chunk-size",
        "64",
    ]


def test_run_containerized_training_bundle_batch_writes_fingerprint_and_launches_docker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The runtime helper should persist provenance before launching Docker."""
    output_root = tmp_path / "bundle-root"
    output_root.mkdir(parents=True, exist_ok=True)
    fingerprint = TrainingBundleRuntimeFingerprint(
        runtime_kind="runtime-kind",
        image="image",
        image_id="image-id",
        dockerfile_path="Dockerfile",
        container_entry_module="entry-module",
        container_hf_home="/cache/hf",
        container_hf_hub_cache="/cache/hf/hub",
        container_torch_home="/cache/hf/torch",
        audio_codes_runtime_kind="audio-runtime",
        audio_codes_device="cuda:0",
        audio_codes_dtype="bfloat16",
        audio_codes_attn_implementation="flash_attention_2",
        audio_codes_require_gpu=True,
        audio_codes_require_flash_attn=True,
    )
    docker_calls: list[list[str]] = []

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime.resolve_effective_triton_cache_dir",
        lambda settings: MountResolution(
            canonical_root=Path("/srv/scratch/cache/triton"),
            effective_root=Path("/srv/scratch/cache/triton"),
            used_home_mount=False,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime.resolve_effective_output_root",
        lambda output_root_arg, settings: MountResolution(
            canonical_root=output_root_arg,
            effective_root=output_root_arg,
            used_home_mount=False,
        ),
    )

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        del label
        docker_calls.append(args)
        return ""

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime.docker_checked",
        _fake_docker_checked,
    )

    returned_fingerprint = run_containerized_training_bundle_batch(
        repo_root=Path("/repo"),
        output_root=output_root,
        manifest_family="swedish_pilot_train",
        batch_index=0,
        batch_count=1,
        audio_codes_chunk_size=64,
        hf_mount=MountResolution(
            canonical_root=Path("/srv/scratch/cache/hf"),
            effective_root=Path("/srv/scratch/cache/hf"),
            used_home_mount=False,
        ),
        fingerprint=fingerprint,
    )

    assert returned_fingerprint == fingerprint
    assert docker_calls
    persisted_fingerprint = (output_root / "reports" / "training_bundle_runtime.json").read_text(
        encoding="utf-8"
    )
    assert '"image_id": "image-id"' in persisted_fingerprint
