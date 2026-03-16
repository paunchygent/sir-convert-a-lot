"""Training-settings snapshot helpers for detached Qwen runtime launches.

Purpose:
    Convert live `TrainingSettings` into stable JSON-serializable snapshots for
    detached launch artifacts.

Relationships:
    - Used by detached launch services when materializing `DetachedLaunch`.
    - Consumes training contracts from `ml.qwen.training.models`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    TrainingSettings,
    TrainingSettingsSnapshot,
)


def snapshot_settings(settings: TrainingSettings) -> TrainingSettingsSnapshot:
    """Create one JSON-serializable snapshot of the current training settings."""
    return TrainingSettingsSnapshot(
        output_root=settings.output_root.as_posix(),
        image=settings.image,
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        hf_cache_home_mount=settings.hf_cache_home_mount.as_posix(),
        scratch_build_root=settings.scratch_build_root.as_posix(),
        scratch_build_home_mount=settings.scratch_build_home_mount.as_posix(),
        pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
        runs_root=settings.runs_root.as_posix(),
        model_id=settings.model_id,
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        text_embedding_mask_policy=settings.text_embedding_mask_policy,
        batch_size=settings.batch_size,
        throughput_profile_label=settings.throughput_profile_label,
        lr=settings.lr,
        num_epochs=settings.num_epochs,
        max_steps=settings.max_steps,
        checkpoint_interval_steps=settings.checkpoint_interval_steps,
        eval_interval_steps=settings.eval_interval_steps,
        durable_checkpoint_retention=settings.durable_checkpoint_retention,
        durable_checkpoint_min_free_bytes=settings.durable_checkpoint_min_free_bytes,
        gradient_accumulation_steps=settings.gradient_accumulation_steps,
        dataloader_num_workers=settings.dataloader_num_workers,
        dataloader_pin_memory=settings.dataloader_pin_memory,
        dataloader_persistent_workers=settings.dataloader_persistent_workers,
        dataloader_prefetch_factor=settings.dataloader_prefetch_factor,
        non_blocking_transfer=settings.non_blocking_transfer,
        data_path_proof_mode=settings.data_path_proof_mode,
        heartbeat_interval_optimizer_steps=settings.heartbeat_interval_optimizer_steps,
        finite_loss_max_consecutive_steps=settings.finite_loss_max_consecutive_steps,
        ref_mel_cache_enabled=settings.ref_mel_cache_enabled,
        ref_mel_cache_max_items=settings.ref_mel_cache_max_items,
        torch_profiler_enabled=settings.torch_profiler_enabled,
        torch_profiler_wait_steps=settings.torch_profiler_wait_steps,
        torch_profiler_warmup_steps=settings.torch_profiler_warmup_steps,
        torch_profiler_active_steps=settings.torch_profiler_active_steps,
        torch_profiler_repeat=settings.torch_profiler_repeat,
        torch_profiler_record_shapes=settings.torch_profiler_record_shapes,
        torch_profiler_profile_memory=settings.torch_profiler_profile_memory,
        torch_profiler_with_stack=settings.torch_profiler_with_stack,
        rocm_profiler_enabled=settings.rocm_profiler_enabled,
    )
