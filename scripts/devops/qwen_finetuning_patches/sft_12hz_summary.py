"""Training-summary builders for the patched Qwen training loop.

Purpose:
    Project the final machine-readable `TrainingSummary` from accumulated loop
    state without keeping summary assembly inside the hot-path loop file.

Relationships:
    - Imported by `sft_12hz_loop.py`.
    - Consumes profiling, tracking, and prepared runtime summaries.
"""

from __future__ import annotations

import argparse

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import DurableCheckpointMetadata
from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    dataloader_tuning_payload,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun
from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import TrainingTrackerSummary


def build_training_summary(
    *,
    args: argparse.Namespace,
    prepared: PreparedTrainingRun,
    optimizer_steps_completed: int,
    train_iterations_completed: int,
    last_loss: float | None,
    smoothed_loss: float | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    eval_batches_completed: int,
    peak_memory_allocated_bytes: int | None,
    peak_memory_reserved_bytes: int | None,
    resumed_from_checkpoint_path: str | None,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    durable_checkpoint_paths: list[str],
    checkpoint_paths: list[str],
    stop_requested_during_training: bool,
    stop_signal: str | None,
    tracker_summary: TrainingTrackerSummary,
) -> TrainingSummary:
    """Build the machine-readable training summary from loop state."""
    profiling_payload: dict[str, object] = {}
    for key, value in prepared.torch_profiler_session.payload().items():
        profiling_payload[str(key)] = value
    return TrainingSummary(
        init_model_path=str(args.init_model_path),
        output_model_path=str(args.output_model_path),
        train_jsonl=str(args.train_jsonl),
        batch_size=int(args.batch_size),
        lr=float(args.lr),
        num_epochs=int(args.num_epochs),
        max_steps=None if args.max_steps is None else int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        durable_checkpoint_retention=int(args.durable_checkpoint_retention),
        durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
        dataloader_length=prepared.dataloader_length,
        eval_dataloader_length=prepared.eval_dataloader_length,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        optimizer_steps_completed=optimizer_steps_completed,
        train_iterations_completed=train_iterations_completed,
        latest_eval_loss=latest_eval_loss,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        eval_batches_completed=eval_batches_completed,
        last_loss=last_loss,
        smoothed_loss=smoothed_loss,
        eval_interval_steps=int(args.eval_interval_steps),
        peak_memory_allocated_bytes=peak_memory_allocated_bytes,
        peak_memory_reserved_bytes=peak_memory_reserved_bytes,
        resumed_from_checkpoint_path=resumed_from_checkpoint_path,
        latest_durable_checkpoint_path=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.checkpoint_path
        ),
        latest_durable_checkpoint_step=(
            None
            if latest_durable_checkpoint is None
            else latest_durable_checkpoint.optimizer_steps_completed
        ),
        latest_durable_checkpoint_epoch=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.epoch
        ),
        durable_checkpoint_paths=durable_checkpoint_paths,
        checkpoint_paths=checkpoint_paths,
        stop_requested=stop_requested_during_training,
        stop_signal=stop_signal,
        stopped_early=stop_requested_during_training,
        throughput_profile=prepared.throughput_profile_payload,
        batch_occupancy=prepared.batch_occupancy_summary.payload(),
        data_path_attribution=(
            None
            if prepared.data_path_attribution is None
            else prepared.data_path_attribution.payload()
        ),
        dataloader_tuning=dataloader_tuning_payload(prepared.effective_dataloader_tuning),
        heartbeat_policy=prepared.heartbeat_policy.payload(),
        finite_loss_guard=prepared.finite_loss_guard.payload(),
        acceptance_measurement_valid=True,
        ref_mel_cache=prepared.ref_mel_cache.payload(),
        profiling=profiling_payload,
        tracking=tracker_summary,
    )
