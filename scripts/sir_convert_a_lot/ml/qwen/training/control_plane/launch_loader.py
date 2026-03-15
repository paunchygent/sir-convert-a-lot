"""Detached launch loading helpers for the Qwen training control plane.

Purpose:
    Load persisted detached launch metadata with the current default contract
    so host-side use cases do not duplicate launch deserialization policy.

Relationships:
    - Used by resume, eval, diagnose, schedule, status, and stop use cases.
    - Consumes metadata and model contracts from the training domain.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.metadata import load_launch
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch

from .defaults import (
    DEFAULT_DATA_PATH_PROOF_MODE,
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    DEFAULT_EVAL_INTERVAL_STEPS_CLI,
    DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    DEFAULT_NON_BLOCKING_TRANSFER,
    DEFAULT_REF_MEL_CACHE_ENABLED,
    DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    DEFAULT_ROCM_PROFILER_ENABLED,
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    DEFAULT_TORCH_PROFILER_ENABLED,
    DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    DEFAULT_TORCH_PROFILER_REPEAT,
    DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    DEFAULT_TORCH_PROFILER_WITH_STACK,
    LEGACY_SMALL_BATCH_THROUGHPUT_PROFILE_LABEL,
)


def load_training_launch(launch_root_path: Path) -> DetachedLaunch:
    """Load one previously recorded detached training launch payload."""
    return load_launch(
        launch_root_path,
        default_throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        default_legacy_small_batch_throughput_profile_label=LEGACY_SMALL_BATCH_THROUGHPUT_PROFILE_LABEL,
        default_durable_checkpoint_retention=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
        default_durable_checkpoint_min_free_bytes=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
        default_dataloader_num_workers=DEFAULT_DATALOADER_NUM_WORKERS,
        default_dataloader_pin_memory=DEFAULT_DATALOADER_PIN_MEMORY,
        default_dataloader_persistent_workers=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
        default_dataloader_prefetch_factor=DEFAULT_DATALOADER_PREFETCH_FACTOR,
        default_non_blocking_transfer=DEFAULT_NON_BLOCKING_TRANSFER,
        default_data_path_proof_mode=DEFAULT_DATA_PATH_PROOF_MODE,
        default_heartbeat_interval_optimizer_steps=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
        default_eval_interval_steps=DEFAULT_EVAL_INTERVAL_STEPS_CLI,
        default_finite_loss_max_consecutive_steps=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
        default_ref_mel_cache_enabled=DEFAULT_REF_MEL_CACHE_ENABLED,
        default_ref_mel_cache_max_items=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
        default_torch_profiler_enabled=DEFAULT_TORCH_PROFILER_ENABLED,
        default_torch_profiler_wait_steps=DEFAULT_TORCH_PROFILER_WAIT_STEPS,
        default_torch_profiler_warmup_steps=DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
        default_torch_profiler_active_steps=DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
        default_torch_profiler_repeat=DEFAULT_TORCH_PROFILER_REPEAT,
        default_torch_profiler_record_shapes=DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
        default_torch_profiler_profile_memory=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
        default_torch_profiler_with_stack=DEFAULT_TORCH_PROFILER_WITH_STACK,
        default_rocm_profiler_enabled=DEFAULT_ROCM_PROFILER_ENABLED,
    )
