"""Contracts for the patched Qwen fine-tuning trainer.

Purpose:
    Keep the machine-readable summary contract separate from the training
    facade so `sft_12hz.py` can stay small while status/reporting code keeps a
    stable typed payload.

Relationships:
    - Imported by `sft_12hz.py` and the extracted training modules.
    - Consumed by the detached training reporter in the domain-centric Qwen
      training surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import TrainingTrackerSummary


@dataclass(frozen=True)
class TrainingSummary:
    """Machine-readable summary for one bounded Qwen fine-tuning run."""

    init_model_path: str
    output_model_path: str
    train_jsonl: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int | None
    checkpoint_interval_steps: int
    eval_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    gradient_accumulation_steps: int
    optimizer_steps_completed: int
    train_iterations_completed: int
    eval_runs_completed: int
    eval_batches_completed: int
    last_loss: float | None
    smoothed_loss: float | None
    latest_eval_loss: float | None
    best_eval_loss: float | None
    best_eval_step: int | None
    peak_memory_allocated_bytes: int | None
    peak_memory_reserved_bytes: int | None
    resumed_from_checkpoint_path: str | None
    latest_durable_checkpoint_path: str | None
    latest_durable_checkpoint_step: int | None
    latest_durable_checkpoint_epoch: int | None
    durable_checkpoint_paths: list[str]
    checkpoint_paths: list[str]
    stop_requested: bool
    stop_signal: str | None
    stopped_early: bool
    throughput_profile: dict[str, object]
    batch_occupancy: dict[str, object]
    data_path_attribution: dict[str, bool | float | int] | None
    dataloader_tuning: dict[str, object]
    heartbeat_policy: dict[str, int]
    finite_loss_guard: dict[str, bool | float | int | None]
    acceptance_measurement_valid: bool
    ref_mel_cache: dict[str, bool | float | int | None]
    profiling: dict[str, object] | None
    tracking: TrainingTrackerSummary | None = None
