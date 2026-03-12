"""Tests for the Task 101 containerized pilot-bundle batch runtime."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    Task101PilotBundleContainerSettings,
    Task101PilotBundleRuntimeFingerprint,
    build_containerized_task101_pilot_bundle_batch_command,
    prepare_task101_pilot_bundle_batch_runtime,
    resolve_effective_output_root,
    run_containerized_task101_pilot_bundle_batch,
    task101_pilot_bundle_output_root_home_mount,
)


def _settings() -> Task101PilotBundleContainerSettings:
    """Return deterministic runtime settings for Task 101 batch helper tests."""
    return Task101PilotBundleContainerSettings(
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        triton_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/triton/task101-audio-codes"),
        triton_cache_home_mount=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/cache/triton/task101-audio-codes"
        ),
        output_root_home_mount_base=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/task101-pilot-bundle-output-roots"
        ),
        build_image=True,
    )


def test_build_containerized_task101_batch_command_uses_fixed_hf_cache_root() -> None:
    """The Task 101 batch runtime should reuse the fixed in-container HF cache root."""
    repo_root = Path("/home/paunchygent/apps/sir-convert-a-lot")
    output_root = Path("/srv/storage/sir-convert-a-lot/tmp/task101-bundle")
    hf_mount = MountResolution(
        canonical_root=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        effective_root=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        used_home_mount=True,
    )
    output_root_mount = MountResolution(
        canonical_root=output_root,
        effective_root=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/task101-pilot-bundle-output-roots"
            "/srv/storage/sir-convert-a-lot/tmp/task101-bundle"
        ),
        used_home_mount=True,
    )
    triton_mount = MountResolution(
        canonical_root=Path("/srv/scratch/sir-convert-a-lot/cache/triton/task101-audio-codes"),
        effective_root=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/cache/triton/task101-audio-codes"
        ),
        used_home_mount=True,
    )

    command = build_containerized_task101_pilot_bundle_batch_command(
        repo_root=repo_root,
        output_root=output_root,
        manifest_family="swedish_pilot_train",
        batch_index=3,
        batch_count=4,
        audio_codes_chunk_size=5,
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_mount=hf_mount,
        triton_mount=triton_mount,
        output_root_mount=output_root_mount,
        host_uid=1000,
        host_gid=1001,
        gpu_group_ids=["44", "109"],
    )

    assert "--user" in command
    assert "1000:1001" in command
    assert command.count("--group-add") == 2
    assert "44" in command
    assert "109" in command
    assert "HF_HOME=/cache/huggingface" in command
    assert "HUGGINGFACE_HUB_CACHE=/cache/huggingface/hub" in command
    assert "TORCH_HOME=/cache/huggingface/torch" in command
    assert "TRITON_CACHE_DIR=/cache/triton" in command
    assert f"{hf_mount.effective_root.as_posix()}:/cache/huggingface" in command
    assert f"{triton_mount.effective_root.as_posix()}:/cache/triton" in command
    assert f"{output_root_mount.effective_root.as_posix()}:{output_root.as_posix()}" in command
    assert "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_in_container" in command
    assert "--manifest-family" in command
    assert "--batch-count" in command
    assert "4" in command
    assert "swedish_pilot_train" in command


def test_prepare_task101_batch_runtime_reuses_qwen_image_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preparing the Task 101 batch runtime should reuse the shared Qwen helpers."""
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime.prepare_qwen_image",
        lambda settings, *, emit=print: (
            observed.setdefault("image", settings.image),
            "sha256:test-image",
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime.resolve_effective_hf_cache_dir",
        lambda settings: MountResolution(
            canonical_root=settings.hf_cache_dir,
            effective_root=settings.hf_cache_home_mount,
            used_home_mount=True,
        ),
    )

    hf_mount, fingerprint = prepare_task101_pilot_bundle_batch_runtime(settings=_settings())

    assert observed["image"] == "sir-convert-a-lot-qwen-finetune-hemma:task100"
    assert hf_mount.effective_root == Path(
        "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"
    )
    assert fingerprint.image_id == "sha256:test-image"
    assert fingerprint.container_hf_home == "/cache/huggingface"
    assert fingerprint.container_hf_hub_cache == "/cache/huggingface/hub"
    assert fingerprint.container_torch_home == "/cache/huggingface/torch"
    assert fingerprint.audio_codes_runtime_kind == "task101_task103_qwen_audio_codes_gpu_v1"
    assert fingerprint.audio_codes_device == "cuda:0"
    assert fingerprint.audio_codes_dtype == "bfloat16"
    assert fingerprint.audio_codes_attn_implementation == "flash_attention_2"
    assert fingerprint.audio_codes_require_gpu is True
    assert fingerprint.audio_codes_require_flash_attn is True


def test_task101_output_root_home_mount_is_deterministic() -> None:
    """Task 101 output roots should map to a stable home-backed bind path."""
    output_root = Path("/srv/scratch/sir-convert-a-lot/build/reference/task101-bundle")

    resolved_home_mount = task101_pilot_bundle_output_root_home_mount(
        output_root,
        home_mount_base=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/task101-pilot-bundle-output-roots"
        ),
    )

    assert resolved_home_mount == Path(
        "/home/paunchygent/.data/sir-convert-a-lot/task101-pilot-bundle-output-roots"
        "/srv/scratch/sir-convert-a-lot/build/reference/task101-bundle"
    )


def test_resolve_effective_output_root_reuses_shared_bind_root_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 101 output roots should reuse the shared home-bind fallback helper."""
    observed: dict[str, object] = {}
    output_root = Path("/srv/scratch/sir-convert-a-lot/build/reference/task101-bundle")
    expected_mount = MountResolution(
        canonical_root=output_root,
        effective_root=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/task101-pilot-bundle-output-roots"
            "/srv/scratch/sir-convert-a-lot/build/reference/task101-bundle"
        ),
        used_home_mount=True,
    )

    def _fake_resolve_effective_bind_root(
        canonical_root: Path,
        home_mount: Path,
        *,
        image: str,
        sync_home_into_canonical: bool,
    ) -> MountResolution:
        observed["canonical_root"] = canonical_root
        observed["home_mount"] = home_mount
        observed["image"] = image
        observed["sync_home_into_canonical"] = sync_home_into_canonical
        return expected_mount

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime.resolve_effective_bind_root",
        _fake_resolve_effective_bind_root,
    )

    resolved_mount = resolve_effective_output_root(output_root, settings=_settings())

    assert resolved_mount == expected_mount
    assert observed["canonical_root"] == output_root
    assert observed["home_mount"] == expected_mount.effective_root
    assert observed["image"] == "sir-convert-a-lot-qwen-finetune-hemma:task100"
    assert observed["sync_home_into_canonical"] is False


def test_run_containerized_task101_batch_writes_runtime_and_launches_docker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The batch runtime should record runtime provenance before Docker launch."""
    output_root = tmp_path / "bundle"
    output_root.mkdir(parents=True, exist_ok=True)
    emitted: list[str] = []
    observed_command: list[str] = []
    hf_mount = MountResolution(
        canonical_root=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        effective_root=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        used_home_mount=True,
    )

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        del label
        observed_command.extend(args)
        return "ok"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime.docker_checked",
        _fake_docker_checked,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime.resolve_effective_output_root",
        lambda output_root, *, settings: MountResolution(
            canonical_root=output_root,
            effective_root=Path("/home/paunchygent/.data/sir-convert-a-lot/task101-bundle"),
            used_home_mount=True,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime.resolve_effective_triton_cache_dir",
        lambda settings: MountResolution(
            canonical_root=settings.triton_cache_dir,
            effective_root=settings.triton_cache_home_mount,
            used_home_mount=True,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime._gpu_device_group_ids",
        lambda: ["44", "109"],
    )
    fingerprint = Task101PilotBundleRuntimeFingerprint(
        runtime_kind="task101_qwen_pilot_bundle_containerized_batch_v1",
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        image_id="sha256:test-image",
        dockerfile_path="containers/qwen-finetune-hemma/Dockerfile",
        container_entry_module=(
            "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_in_container"
        ),
        container_hf_home="/cache/huggingface",
        container_hf_hub_cache="/cache/huggingface/hub",
        container_torch_home="/cache/huggingface/torch",
        audio_codes_runtime_kind="task101_task103_qwen_audio_codes_gpu_v1",
        audio_codes_device="cuda:0",
        audio_codes_dtype="bfloat16",
        audio_codes_attn_implementation="flash_attention_2",
        audio_codes_require_gpu=True,
        audio_codes_require_flash_attn=True,
    )

    result = run_containerized_task101_pilot_bundle_batch(
        repo_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        output_root=output_root,
        manifest_family="swedish_checkpoint_dev",
        batch_index=1,
        batch_count=3,
        audio_codes_chunk_size=4,
        settings=_settings(),
        hf_mount=hf_mount,
        fingerprint=fingerprint,
        emit=emitted.append,
    )

    runtime_path = output_root / "reports" / "task101_pilot_bundle_runtime.json"
    assert runtime_path.is_file()
    assert result == fingerprint
    assert observed_command[0] == "run"
    assert "--user" in observed_command
    assert f"{os.getuid()}:{os.getgid()}" in observed_command
    assert observed_command.count("--group-add") == 2
    assert "44" in observed_command
    assert "109" in observed_command
    assert "--device" in observed_command
    assert "swedish_checkpoint_dev" in observed_command
    assert any("batch_container_launch" in line for line in emitted)
    assert any(
        item.startswith("/home/paunchygent/.data/sir-convert-a-lot/task101-bundle:")
        for item in observed_command
    )
    assert any(
        item.startswith(
            "/home/paunchygent/.data/sir-convert-a-lot/cache/triton/task101-audio-codes:"
        )
        for item in observed_command
    )
    assert "--batch-count" in observed_command
    assert "3" in observed_command
    assert any('"used_output_root_home_mount": true' in line for line in emitted)
    assert any('"used_triton_cache_home_mount": true' in line for line in emitted)
