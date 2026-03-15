"""Loss-observation runtime helpers for the patched Qwen training loop.

Purpose:
    Own bounded loss-observation draining, heartbeat emission, finite-loss
    guarding, and tracker logging for completed optimizer steps.

Relationships:
    - Imported by `sft_12hz_loop.py` and `sft_12hz_train_step.py`.
    - Consumes tracker and progress helpers from the Qwen patch runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from accelerate import Accelerator

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import DurableCheckpointMetadata
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import LossObservation
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import TrainingProgressHeartbeat
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import (
    log_training_metrics,
    update_smoothed_loss,
)

from .sft_12hz_phase_runtime import emit_progress_phase


class _HeartbeatPolicyLike(Protocol):
    """Protocol for the heartbeat policy surface used by loss runtime helpers."""

    def should_emit_train_update(self, optimizer_step: int) -> bool: ...


class _FiniteLossGuardLike(Protocol):
    """Protocol for the finite-loss guard surface used by loss runtime helpers."""

    def observe(self, observation: LossObservation) -> None: ...


class _RefMelCacheLike(Protocol):
    """Protocol for the ref-mel cache payload surface used by loss runtime helpers."""

    def payload(self) -> dict[str, bool | float | int | None]: ...


class LossRuntimePrepared(Protocol):
    """Focused prepared-runtime surface needed by loss-observation helpers."""

    @property
    def heartbeat_policy(self) -> _HeartbeatPolicyLike: ...

    @property
    def finite_loss_guard(self) -> _FiniteLossGuardLike: ...

    @property
    def ref_mel_cache(self) -> _RefMelCacheLike: ...

    @property
    def dataloader_length(self) -> int: ...

    @property
    def eval_dataloader_length(self) -> int: ...


def consume_loss_observations(
    *,
    accelerator: Accelerator,
    prepared: LossRuntimePrepared,
    observations: list[LossObservation],
    checkpoint_interval_steps: int,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None,
    emitted_train_progress: bool,
    smoothed_loss: float | None,
    last_loss: float | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
) -> tuple[float | None, float | None, bool]:
    """Apply ready loss observations to guard, heartbeat, and tracker state."""
    for observation in observations:
        train_progress_should_emit = progress_callback is not None and (
            (not emitted_train_progress)
            or prepared.heartbeat_policy.should_emit_train_update(observation.optimizer_step)
        )
        if train_progress_should_emit:
            emit_progress_phase(
                progress_callback=progress_callback,
                phase="train",
                current_epoch=observation.current_epoch,
                current_optimizer_step=observation.optimizer_step,
                current_train_iteration=observation.current_train_iteration,
                dataloader_length=prepared.dataloader_length,
                eval_dataloader_length=prepared.eval_dataloader_length,
                latest_loss=observation.loss_value,
                smoothed_loss=smoothed_loss,
                latest_durable_checkpoint=latest_durable_checkpoint,
                latest_eval_loss=latest_eval_loss,
                best_eval_loss=best_eval_loss,
                best_eval_step=best_eval_step,
                eval_runs_completed=eval_runs_completed,
            )
            emitted_train_progress = True
        prepared.finite_loss_guard.observe(observation)
        last_loss = observation.loss_value
        smoothed_loss = update_smoothed_loss(smoothed_loss, last_loss)
        if prepared.heartbeat_policy.should_emit_train_update(observation.optimizer_step):
            log_training_metrics(
                accelerator,
                raw_loss=last_loss,
                smoothed_loss=smoothed_loss,
                current_epoch=observation.current_epoch,
                current_optimizer_step=observation.optimizer_step,
                current_train_iteration=observation.current_train_iteration,
                checkpoint_interval_steps=checkpoint_interval_steps,
                ref_mel_cache_metrics=prepared.ref_mel_cache.payload(),
            )
            if progress_callback is not None and not train_progress_should_emit:
                emit_progress_phase(
                    progress_callback=progress_callback,
                    phase="train",
                    current_epoch=observation.current_epoch,
                    current_optimizer_step=observation.optimizer_step,
                    current_train_iteration=observation.current_train_iteration,
                    dataloader_length=prepared.dataloader_length,
                    eval_dataloader_length=prepared.eval_dataloader_length,
                    latest_loss=last_loss,
                    smoothed_loss=smoothed_loss,
                    latest_durable_checkpoint=latest_durable_checkpoint,
                    latest_eval_loss=latest_eval_loss,
                    best_eval_loss=best_eval_loss,
                    best_eval_step=best_eval_step,
                    eval_runs_completed=eval_runs_completed,
                )
            accelerator.print(
                "Epoch "
                f"{observation.current_epoch} | Optimizer Step {observation.optimizer_step} | "
                f"Loss: {last_loss:.4f}"
            )
    return last_loss, smoothed_loss, emitted_train_progress
