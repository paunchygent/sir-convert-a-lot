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
    tracking: dict[str, object] | None
    training_summary: dict[str, object]
