"""Shared data models for the Qwen training domain.

Purpose:
    Provide stable, SRP-aligned data contracts for training settings,
    detached-launch metadata, in-container status reporting, and terminal
    reports.

Relationships:
    - Consumes base infrastructure models from `ml.qwen.common.models`.
    - Consumed by training orchestrators, in-container trainers, and status
      reporters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrainingSettings:
    """Normalized settings for the detached Qwen training pilot."""

    output_root: Path
    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    scratch_build_root: Path
    scratch_build_home_mount: Path
    pilot_bundle_root: Path
    runs_root: Path
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int
    checkpoint_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    dataloader_num_workers: int = 4
    dataloader_pin_memory: bool = True
    dataloader_persistent_workers: bool = True
    dataloader_prefetch_factor: int = 4
    non_blocking_transfer: bool = True
    heartbeat_interval_optimizer_steps: int = 20
    finite_loss_max_consecutive_steps: int = 3
    ref_mel_cache_enabled: bool = True
    ref_mel_cache_max_items: int = 2048
    torch_profiler_enabled: bool = False
    torch_profiler_wait_steps: int = 1
    torch_profiler_warmup_steps: int = 1
    torch_profiler_active_steps: int = 4
    torch_profiler_repeat: int = 1
    torch_profiler_record_shapes: bool = True
    torch_profiler_profile_memory: bool = True
    torch_profiler_with_stack: bool = False
    rocm_profiler_enabled: bool = False


@dataclass(frozen=True)
class TrainingSettingsSnapshot:
    """JSON-serializable snapshot of one Qwen training configuration."""

    output_root: str
    image: str
    hf_cache_dir: str
    hf_cache_home_mount: str
    scratch_build_root: str
    scratch_build_home_mount: str
    pilot_bundle_root: str
    runs_root: str
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int
    checkpoint_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    dataloader_num_workers: int = 4
    dataloader_pin_memory: bool = True
    dataloader_persistent_workers: bool = True
    dataloader_prefetch_factor: int = 4
    non_blocking_transfer: bool = True
    heartbeat_interval_optimizer_steps: int = 20
    finite_loss_max_consecutive_steps: int = 3
    ref_mel_cache_enabled: bool = True
    ref_mel_cache_max_items: int = 2048
    torch_profiler_enabled: bool = False
    torch_profiler_wait_steps: int = 1
    torch_profiler_warmup_steps: int = 1
    torch_profiler_active_steps: int = 4
    torch_profiler_repeat: int = 1
    torch_profiler_record_shapes: bool = True
    torch_profiler_profile_memory: bool = True
    torch_profiler_with_stack: bool = False
    rocm_profiler_enabled: bool = False


@dataclass(frozen=True)
class DetachedLaunch:
    """Deterministic launch metadata for one detached training run."""

    generated_at: str
    launch_id: str
    container_name: str
    container_id: str
    repo_root: str
    run_root: str
    pilot_bundle_root: str
    train_jsonl: str
    eval_jsonl: str
    train_manifest_family: str
    eval_manifest_family: str
    dockerfile_path: str | None
    resumed_from_checkpoint_path: str | None
    settings: TrainingSettingsSnapshot
    command: list[str]
    bundle_precomputed_reference_input: dict[str, object] | None = None
    tracking: dict[str, object] | None = None
    resource_monitor: dict[str, object] | None = None


@dataclass(frozen=True)
class DetachedStatus:
    """Deterministic status view for one detached training run."""

    checked_at: str
    launch_id: str
    container_name: str
    container_id: str
    status: str
    running: bool
    exit_code: int
    oom_killed: bool
    started_at: str
    finished_at: str
    pilot_status_found: bool
    pilot_status: dict[str, object] | None
    pilot_report_found: bool
    pilot_report: dict[str, object] | None
    latest_checkpoint_found: bool
    latest_checkpoint: dict[str, object] | None
    logs_tail: str
    resource_monitor: dict[str, object] | None = None


@dataclass(frozen=True)
class DetachedStop:
    """Deterministic stop result for one detached training container."""

    stopped_at: str
    launch_id: str
    container_name: str
    container_id: str
    stop_output: str


@dataclass(frozen=True)
class TrainingReport:
    """Machine-readable report emitted by the detached training probe."""

    generated_at: str
    model_id: str
    train_jsonl: str
    eval_jsonl: str
    output_dir: str
    train_row_count: int
    eval_row_count: int
    upstream_trainer_uses_eval_manifest: bool
    torch_version: str
    torchaudio_version: str | None
    torch_cuda_available: bool
    torch_cuda_device_count: int
    torch_hip_version: str | None
    flash_attn_importable: bool
    flash_attn_version: str | None
    bundle_precomputed_reference_input: dict[str, object] | None
    tracking: dict[str, object] | None
    training_summary: dict[str, object]


def settings_from_snapshot(snapshot: TrainingSettingsSnapshot) -> TrainingSettings:
    """Rehydrate runtime settings from one detached-launch snapshot."""
    return TrainingSettings(
        output_root=Path(snapshot.output_root),
        image=snapshot.image,
        hf_cache_dir=Path(snapshot.hf_cache_dir),
        hf_cache_home_mount=Path(snapshot.hf_cache_home_mount),
        scratch_build_root=Path(snapshot.scratch_build_root),
        scratch_build_home_mount=Path(snapshot.scratch_build_home_mount),
        pilot_bundle_root=Path(snapshot.pilot_bundle_root),
        runs_root=Path(snapshot.runs_root),
        model_id=snapshot.model_id,
        train_manifest_family=snapshot.train_manifest_family,
        eval_manifest_family=snapshot.eval_manifest_family,
        batch_size=snapshot.batch_size,
        lr=snapshot.lr,
        num_epochs=snapshot.num_epochs,
        max_steps=snapshot.max_steps,
        checkpoint_interval_steps=snapshot.checkpoint_interval_steps,
        durable_checkpoint_retention=snapshot.durable_checkpoint_retention,
        durable_checkpoint_min_free_bytes=snapshot.durable_checkpoint_min_free_bytes,
        dataloader_num_workers=snapshot.dataloader_num_workers,
        dataloader_pin_memory=snapshot.dataloader_pin_memory,
        dataloader_persistent_workers=snapshot.dataloader_persistent_workers,
        dataloader_prefetch_factor=snapshot.dataloader_prefetch_factor,
        non_blocking_transfer=snapshot.non_blocking_transfer,
        heartbeat_interval_optimizer_steps=snapshot.heartbeat_interval_optimizer_steps,
        finite_loss_max_consecutive_steps=snapshot.finite_loss_max_consecutive_steps,
        ref_mel_cache_enabled=snapshot.ref_mel_cache_enabled,
        ref_mel_cache_max_items=snapshot.ref_mel_cache_max_items,
        torch_profiler_enabled=snapshot.torch_profiler_enabled,
        torch_profiler_wait_steps=snapshot.torch_profiler_wait_steps,
        torch_profiler_warmup_steps=snapshot.torch_profiler_warmup_steps,
        torch_profiler_active_steps=snapshot.torch_profiler_active_steps,
        torch_profiler_repeat=snapshot.torch_profiler_repeat,
        torch_profiler_record_shapes=snapshot.torch_profiler_record_shapes,
        torch_profiler_profile_memory=snapshot.torch_profiler_profile_memory,
        torch_profiler_with_stack=snapshot.torch_profiler_with_stack,
        rocm_profiler_enabled=snapshot.rocm_profiler_enabled,
    )
