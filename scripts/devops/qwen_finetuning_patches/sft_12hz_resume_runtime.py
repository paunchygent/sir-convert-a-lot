"""Resume-runtime helpers for the patched Qwen training loop.

Purpose:
    Own durable-checkpoint resume validation and resume-state restoration so
    the main training loop only orchestrates the epoch flow.

Relationships:
    - Imported by `sft_12hz_loop.py`.
    - Consumes checkpoint metadata from `sft_12hz_checkpointing.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from accelerate import Accelerator

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
    _current_durable_checkpoint_paths,
    _load_durable_checkpoint_metadata,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun


@dataclass(frozen=True)
class ResumeRuntimeState:
    """Resolved resume state for one prepared Qwen training run."""

    durable_checkpoint_paths: list[str]
    latest_durable_checkpoint: DurableCheckpointMetadata | None
    resumed_from_checkpoint_path: str | None
    starting_epoch: int
    resume_step_in_epoch: int
    optimizer_steps_completed: int
    train_iterations_completed: int


def initialize_resume_runtime(
    prepared: PreparedTrainingRun,
    *,
    accelerator: Accelerator,
) -> ResumeRuntimeState:
    """Restore durable-checkpoint state when the run starts from a checkpoint."""
    durable_checkpoint_paths: list[str] = []
    latest_durable_checkpoint: DurableCheckpointMetadata | None = None
    resumed_from_checkpoint_path: str | None = None
    starting_epoch = 0
    resume_step_in_epoch = 0
    optimizer_steps_completed = 0
    train_iterations_completed = 0
    if prepared.args.resume_from_checkpoint is None:
        return ResumeRuntimeState(
            durable_checkpoint_paths=durable_checkpoint_paths,
            latest_durable_checkpoint=latest_durable_checkpoint,
            resumed_from_checkpoint_path=resumed_from_checkpoint_path,
            starting_epoch=starting_epoch,
            resume_step_in_epoch=resume_step_in_epoch,
            optimizer_steps_completed=optimizer_steps_completed,
            train_iterations_completed=train_iterations_completed,
        )
    resume_checkpoint_path = Path(prepared.args.resume_from_checkpoint)
    latest_durable_checkpoint = _load_durable_checkpoint_metadata(resume_checkpoint_path)
    validate_resume_cursor_compatibility(
        checkpoint_metadata=latest_durable_checkpoint,
        dataloader_length=prepared.dataloader_length,
    )
    accelerator.load_state(resume_checkpoint_path.as_posix())
    resumed_from_checkpoint_path = resume_checkpoint_path.as_posix()
    optimizer_steps_completed = latest_durable_checkpoint.optimizer_steps_completed
    starting_epoch = latest_durable_checkpoint.next_epoch
    resume_step_in_epoch = latest_durable_checkpoint.next_step_in_epoch
    durable_checkpoint_paths = _current_durable_checkpoint_paths(prepared.output_model_path)
    train_iterations_completed = (
        starting_epoch * prepared.dataloader_length
    ) + resume_step_in_epoch
    return ResumeRuntimeState(
        durable_checkpoint_paths=durable_checkpoint_paths,
        latest_durable_checkpoint=latest_durable_checkpoint,
        resumed_from_checkpoint_path=resumed_from_checkpoint_path,
        starting_epoch=starting_epoch,
        resume_step_in_epoch=resume_step_in_epoch,
        optimizer_steps_completed=optimizer_steps_completed,
        train_iterations_completed=train_iterations_completed,
    )


def validate_resume_cursor_compatibility(
    *,
    checkpoint_metadata: DurableCheckpointMetadata,
    dataloader_length: int,
) -> None:
    """Fail closed when one saved resume cursor is impossible for the current bundle."""
    if checkpoint_metadata.next_step_in_epoch < 0:
        raise SystemExit(
            "Durable checkpoint metadata contained a negative "
            "`next_step_in_epoch`; refusing resume."
        )
    if checkpoint_metadata.next_step_in_epoch > dataloader_length:
        raise SystemExit(
            "Durable checkpoint resume cursor exceeded the current dataloader length. "
            f"checkpoint_next_step_in_epoch={checkpoint_metadata.next_step_in_epoch} "
            f"dataloader_length={dataloader_length}. "
            "This usually means the checkpoint is being resumed against a different bundle "
            "or a stale cursor contract. Run standalone eval first and only resume when the "
            "checkpoint cursor matches the current bundle."
        )
