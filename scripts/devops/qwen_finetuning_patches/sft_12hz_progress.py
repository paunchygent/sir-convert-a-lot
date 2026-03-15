"""Progress heartbeat helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Keep live phase/heartbeat dataclasses and heartbeat-construction helpers
    out of `sft_12hz.py` so the trainer can emit truthful progress updates
    without owning the detached Task 101 status payload contract directly.

Relationships:
    - Imported by `sft_12hz.py` to emit bounded live training heartbeats.
    - Consumed by the detached Task 101 probe status reporter to persist
      current phase, loss, and checkpoint progress into `status.json`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

try:
    from sft_12hz_checkpointing import DurableCheckpointMetadata
except ModuleNotFoundError:
    from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
        DurableCheckpointMetadata,
    )

TrainingPhase = Literal["startup", "train", "eval", "checkpoint-save", "signal-stop"]


@dataclass(frozen=True)
class TrainingProgressHeartbeat:
    """One bounded live heartbeat emitted by the patched Qwen trainer."""

    phase: TrainingPhase
    updated_at: str
    current_epoch: int
    current_step: int
    latest_loss: float | None
    smoothed_loss: float | None
    latest_durable_checkpoint_path: str | None
    latest_durable_checkpoint_step: int | None
    latest_durable_checkpoint_saved_at: str | None
    dataloader_length: int | None = None
    eval_dataloader_length: int | None = None
    current_optimizer_step: int | None = None
    current_train_iteration: int | None = None
    gradient_accumulation_steps: int | None = None
    latest_eval_loss: float | None = None
    best_eval_loss: float | None = None
    best_eval_step: int | None = None
    eval_runs_completed: int | None = None


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_training_progress_heartbeat(
    *,
    phase: TrainingPhase,
    current_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    gradient_accumulation_steps: int,
    dataloader_length: int | None,
    eval_dataloader_length: int | None,
    latest_loss: float | None,
    smoothed_loss: float | None,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    latest_eval_loss: float | None = None,
    best_eval_loss: float | None = None,
    best_eval_step: int | None = None,
    eval_runs_completed: int | None = None,
) -> TrainingProgressHeartbeat:
    """Build one immutable progress heartbeat from the trainer state."""
    return TrainingProgressHeartbeat(
        phase=phase,
        updated_at=_utc_now_iso(),
        current_epoch=current_epoch,
        current_step=current_optimizer_step,
        current_optimizer_step=current_optimizer_step,
        current_train_iteration=current_train_iteration,
        gradient_accumulation_steps=gradient_accumulation_steps,
        dataloader_length=dataloader_length,
        eval_dataloader_length=eval_dataloader_length,
        latest_loss=latest_loss,
        smoothed_loss=smoothed_loss,
        latest_eval_loss=latest_eval_loss,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        latest_durable_checkpoint_path=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.checkpoint_path
        ),
        latest_durable_checkpoint_step=(
            None
            if latest_durable_checkpoint is None
            else latest_durable_checkpoint.optimizer_steps_completed
        ),
        latest_durable_checkpoint_saved_at=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.saved_at
        ),
    )
