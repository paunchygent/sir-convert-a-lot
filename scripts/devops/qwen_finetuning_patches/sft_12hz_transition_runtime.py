"""Checkpoint/eval transition helpers for the patched Qwen training loop.

Purpose:
    Own the interval-boundary and terminal transition work for the patched
    Qwen loop so the top-level loop only coordinates epoch traversal and stop
    decisions.

Relationships:
    - Imported by `sft_12hz_loop.py`.
    - Reuses checkpointing, eval, export, and phase-runtime helpers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import torch
from accelerate import Accelerator

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
    _checkpoint_advanced_since_latest_save,
    _current_durable_checkpoint_paths,
    _save_durable_checkpoint,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_eval import run_eval_pass
from scripts.devops.qwen_finetuning_patches.sft_12hz_export import save_checkpoint
from scripts.devops.qwen_finetuning_patches.sft_12hz_loss_runtime import (
    consume_loss_observations,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_phase_runtime import (
    emit_progress_phase,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun


@dataclass(frozen=True)
class IntervalBoundaryResult:
    """Updated loop state after one optimizer-step interval boundary check."""

    latest_eval_loss: float | None
    latest_eval_step: int | None
    best_eval_loss: float | None
    best_eval_step: int | None
    eval_runs_completed: int
    eval_batches_completed: int
    latest_durable_checkpoint: DurableCheckpointMetadata | None
    durable_checkpoint_paths: list[str]
    interval_transition_occurred: bool


@dataclass(frozen=True)
class TerminalTransitionResult:
    """Updated loop state after terminal drain, save, eval, and export work."""

    last_loss: float | None
    smoothed_loss: float | None
    emitted_train_progress: bool
    latest_eval_loss: float | None
    latest_eval_step: int | None
    best_eval_loss: float | None
    best_eval_step: int | None
    eval_runs_completed: int
    eval_batches_completed: int
    latest_durable_checkpoint: DurableCheckpointMetadata | None
    durable_checkpoint_paths: list[str]
    checkpoint_paths: list[str]
    peak_memory_allocated_bytes: int | None
    peak_memory_reserved_bytes: int | None


def handle_interval_boundaries(
    *,
    accelerator: Accelerator,
    prepared: PreparedTrainingRun,
    output_model_path,
    checkpoint_interval_steps: int,
    eval_interval_steps: int,
    durable_checkpoint_retention: int,
    durable_checkpoint_min_free_bytes: int,
    current_epoch: int,
    step_in_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    last_loss: float | None,
    smoothed_loss: float | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    eval_batches_completed: int,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    durable_checkpoint_paths: list[str],
    completed_optimizer_step: bool,
    progress_callback,
) -> IntervalBoundaryResult:
    """Handle durable checkpoint and interval eval work for one optimizer step."""
    checkpoint_saved = False
    if (
        completed_optimizer_step
        and current_optimizer_step > 0
        and current_optimizer_step % checkpoint_interval_steps == 0
    ):
        checkpoint_saved = True
        emit_progress_phase(
            progress_callback=progress_callback,
            phase="durable-checkpoint-save",
            current_epoch=current_epoch,
            current_optimizer_step=current_optimizer_step,
            current_train_iteration=current_train_iteration,
            dataloader_length=prepared.dataloader_length,
            eval_dataloader_length=prepared.eval_dataloader_length,
            latest_loss=last_loss,
            smoothed_loss=smoothed_loss,
            latest_eval_loss=latest_eval_loss,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
            latest_durable_checkpoint=latest_durable_checkpoint,
        )
        with prepared.torch_profiler_session.phase("task101.durable-checkpoint-save"):
            latest_durable_checkpoint = _save_durable_checkpoint(
                accelerator=accelerator,
                output_model_path=output_model_path,
                optimizer_steps_completed=current_optimizer_step,
                epoch=current_epoch,
                step_in_epoch=step_in_epoch,
                dataloader_length=prepared.dataloader_length,
                reason="interval",
                durable_checkpoint_retention=durable_checkpoint_retention,
                durable_checkpoint_min_free_bytes=durable_checkpoint_min_free_bytes,
            )
        durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
    should_run_interval_eval = (
        completed_optimizer_step
        and current_optimizer_step > 0
        and current_optimizer_step % eval_interval_steps == 0
    )
    if should_run_interval_eval:
        eval_result = run_eval_pass(
            prepared=prepared,
            current_epoch=current_epoch,
            current_optimizer_step=current_optimizer_step,
            current_train_iteration=current_train_iteration,
            latest_loss=last_loss,
            smoothed_loss=smoothed_loss,
            latest_durable_checkpoint=latest_durable_checkpoint,
            latest_eval_loss=latest_eval_loss,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
            eval_batches_completed=eval_batches_completed,
            progress_callback=progress_callback,
        )
        latest_eval_loss = eval_result.latest_eval_loss
        latest_eval_step = eval_result.latest_eval_step
        best_eval_loss = eval_result.best_eval_loss
        best_eval_step = eval_result.best_eval_step
        eval_runs_completed = eval_result.eval_runs_completed
        eval_batches_completed = eval_result.eval_batches_completed
    else:
        latest_eval_step = None
    return IntervalBoundaryResult(
        latest_eval_loss=latest_eval_loss,
        latest_eval_step=latest_eval_step,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        eval_batches_completed=eval_batches_completed,
        latest_durable_checkpoint=latest_durable_checkpoint,
        durable_checkpoint_paths=durable_checkpoint_paths,
        interval_transition_occurred=checkpoint_saved or should_run_interval_eval,
    )


def save_epoch_export_checkpoint(
    *,
    accelerator: Accelerator,
    prepared: PreparedTrainingRun,
    checkpoint_paths: list[str],
    output_model_path,
    current_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    last_loss: float | None,
    smoothed_loss: float | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    progress_callback,
) -> list[str]:
    """Save one epoch export checkpoint on the main process."""
    if not accelerator.is_main_process:
        return checkpoint_paths
    output_dir = output_model_path / f"checkpoint-epoch-{current_epoch}"
    emit_progress_phase(
        progress_callback=progress_callback,
        phase="export-checkpoint-save",
        current_epoch=current_epoch,
        current_optimizer_step=current_optimizer_step,
        current_train_iteration=current_train_iteration,
        dataloader_length=prepared.dataloader_length,
        eval_dataloader_length=prepared.eval_dataloader_length,
        latest_loss=last_loss,
        smoothed_loss=smoothed_loss,
        latest_eval_loss=latest_eval_loss,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        latest_durable_checkpoint=latest_durable_checkpoint,
    )
    with prepared.torch_profiler_session.phase("task101.export-checkpoint-save"):
        return [
            *checkpoint_paths,
            save_checkpoint(
                accelerator=accelerator,
                model=prepared.checkpointable_model,
                model_path=prepared.model_path,
                output_dir=output_dir,
            ),
        ]


def finalize_training_runtime(
    *,
    accelerator: Accelerator,
    prepared: PreparedTrainingRun,
    output_model_path,
    checkpoint_interval_steps: int,
    durable_checkpoint_retention: int,
    durable_checkpoint_min_free_bytes: int,
    current_epoch: int,
    step_in_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    last_loss: float | None,
    smoothed_loss: float | None,
    emitted_train_progress: bool,
    latest_eval_loss: float | None,
    latest_eval_step: int | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    eval_batches_completed: int,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    durable_checkpoint_paths: list[str],
    checkpoint_paths: list[str],
    stop_requested_during_training: bool,
    capture_mode_enabled: bool,
    progress_callback: Callable | None,
) -> TerminalTransitionResult:
    """Run terminal loss drain, final saves, trailing eval, and final export."""
    last_loss, smoothed_loss, emitted_train_progress = consume_loss_observations(
        accelerator=accelerator,
        prepared=prepared,
        observations=prepared.loss_observer.drain_ready(force=True),
        checkpoint_interval_steps=checkpoint_interval_steps,
        progress_callback=progress_callback,
        emitted_train_progress=emitted_train_progress,
        smoothed_loss=smoothed_loss,
        last_loss=last_loss,
        latest_eval_loss=latest_eval_loss,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        latest_durable_checkpoint=latest_durable_checkpoint,
    )
    if _checkpoint_advanced_since_latest_save(
        latest_durable_checkpoint,
        optimizer_steps_completed=current_optimizer_step,
    ):
        emit_progress_phase(
            progress_callback=progress_callback,
            phase="durable-checkpoint-save",
            current_epoch=current_epoch,
            current_optimizer_step=current_optimizer_step,
            current_train_iteration=current_train_iteration,
            dataloader_length=prepared.dataloader_length,
            eval_dataloader_length=prepared.eval_dataloader_length,
            latest_loss=last_loss,
            smoothed_loss=smoothed_loss,
            latest_eval_loss=latest_eval_loss,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
            latest_durable_checkpoint=latest_durable_checkpoint,
        )
        with prepared.torch_profiler_session.phase("task101.durable-checkpoint-save"):
            latest_durable_checkpoint = _save_durable_checkpoint(
                accelerator=accelerator,
                output_model_path=output_model_path,
                optimizer_steps_completed=current_optimizer_step,
                epoch=current_epoch,
                step_in_epoch=step_in_epoch,
                dataloader_length=prepared.dataloader_length,
                reason="signal-stop" if stop_requested_during_training else "final-step",
                durable_checkpoint_retention=durable_checkpoint_retention,
                durable_checkpoint_min_free_bytes=durable_checkpoint_min_free_bytes,
            )
        durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
    if capture_mode_enabled:
        peak_memory_allocated_bytes = (
            int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
        )
        peak_memory_reserved_bytes = (
            int(torch.cuda.max_memory_reserved()) if torch.cuda.is_available() else None
        )
        return TerminalTransitionResult(
            last_loss=last_loss,
            smoothed_loss=smoothed_loss,
            emitted_train_progress=emitted_train_progress,
            latest_eval_loss=latest_eval_loss,
            latest_eval_step=latest_eval_step,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
            eval_batches_completed=eval_batches_completed,
            latest_durable_checkpoint=latest_durable_checkpoint,
            durable_checkpoint_paths=durable_checkpoint_paths,
            checkpoint_paths=checkpoint_paths,
            peak_memory_allocated_bytes=peak_memory_allocated_bytes,
            peak_memory_reserved_bytes=peak_memory_reserved_bytes,
        )
    if current_optimizer_step > 0 and latest_eval_step != current_optimizer_step:
        eval_result = run_eval_pass(
            prepared=prepared,
            current_epoch=current_epoch,
            current_optimizer_step=current_optimizer_step,
            current_train_iteration=current_train_iteration,
            latest_loss=last_loss,
            smoothed_loss=smoothed_loss,
            latest_durable_checkpoint=latest_durable_checkpoint,
            latest_eval_loss=latest_eval_loss,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
            eval_batches_completed=eval_batches_completed,
            progress_callback=progress_callback,
        )
        latest_eval_loss = eval_result.latest_eval_loss
        latest_eval_step = eval_result.latest_eval_step
        best_eval_loss = eval_result.best_eval_loss
        best_eval_step = eval_result.best_eval_step
        eval_runs_completed = eval_result.eval_runs_completed
        eval_batches_completed = eval_result.eval_batches_completed
    if accelerator.is_main_process:
        final_output_dir = output_model_path / "checkpoint-final"
        emit_progress_phase(
            progress_callback=progress_callback,
            phase="export-checkpoint-save",
            current_epoch=current_epoch,
            current_optimizer_step=current_optimizer_step,
            current_train_iteration=current_train_iteration,
            dataloader_length=prepared.dataloader_length,
            eval_dataloader_length=prepared.eval_dataloader_length,
            latest_loss=last_loss,
            smoothed_loss=smoothed_loss,
            latest_eval_loss=latest_eval_loss,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
            latest_durable_checkpoint=latest_durable_checkpoint,
        )
        with prepared.torch_profiler_session.phase("task101.export-checkpoint-save"):
            checkpoint_paths = [
                *checkpoint_paths,
                save_checkpoint(
                    accelerator=accelerator,
                    model=prepared.checkpointable_model,
                    model_path=prepared.model_path,
                    output_dir=final_output_dir,
                ),
            ]
    peak_memory_allocated_bytes = (
        int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
    )
    peak_memory_reserved_bytes = (
        int(torch.cuda.max_memory_reserved()) if torch.cuda.is_available() else None
    )
    return TerminalTransitionResult(
        last_loss=last_loss,
        smoothed_loss=smoothed_loss,
        emitted_train_progress=emitted_train_progress,
        latest_eval_loss=latest_eval_loss,
        latest_eval_step=latest_eval_step,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        eval_batches_completed=eval_batches_completed,
        latest_durable_checkpoint=latest_durable_checkpoint,
        durable_checkpoint_paths=durable_checkpoint_paths,
        checkpoint_paths=checkpoint_paths,
        peak_memory_allocated_bytes=peak_memory_allocated_bytes,
        peak_memory_reserved_bytes=peak_memory_reserved_bytes,
    )
