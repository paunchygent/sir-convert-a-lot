"""Phase-runtime helpers for the patched Qwen training loop.

Purpose:
    Own explicit phase-transition heartbeat emission and deterministic
    dataloader epoch synchronization for the patched Qwen training loop.

Relationships:
    - Imported by the training loop and loss runtime helpers.
    - Consumes the shared progress heartbeat builder.
"""

from __future__ import annotations

from collections.abc import Callable

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import DurableCheckpointMetadata
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import (
    TrainingPhase,
    TrainingProgressHeartbeat,
    build_training_progress_heartbeat,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)


def emit_progress_phase(
    *,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None,
    phase: TrainingPhase,
    current_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    dataloader_length: int,
    eval_dataloader_length: int,
    latest_loss: float | None,
    smoothed_loss: float | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
) -> None:
    """Emit one explicit phase-transition heartbeat when reporting is enabled."""
    if progress_callback is None:
        return
    progress_callback(
        build_training_progress_heartbeat(
            phase=phase,
            current_epoch=current_epoch,
            current_optimizer_step=current_optimizer_step,
            current_train_iteration=current_train_iteration,
            gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
            dataloader_length=dataloader_length,
            eval_dataloader_length=eval_dataloader_length,
            latest_loss=latest_loss,
            smoothed_loss=smoothed_loss,
            latest_durable_checkpoint=latest_durable_checkpoint,
            latest_eval_loss=latest_eval_loss,
            best_eval_loss=best_eval_loss,
            best_eval_step=best_eval_step,
            eval_runs_completed=eval_runs_completed,
        )
    )


def set_dataloader_epoch_if_supported(dataloader: object, *, epoch: int) -> None:
    """Set one epoch cursor on batch samplers that support deterministic replay."""
    batch_sampler = getattr(dataloader, "batch_sampler", None)
    set_epoch = getattr(batch_sampler, "set_epoch", None)
    if callable(set_epoch):
        set_epoch(epoch)
