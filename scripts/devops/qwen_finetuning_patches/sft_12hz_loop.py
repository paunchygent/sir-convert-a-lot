"""Training-loop orchestration for the patched Qwen fine-tuning trainer.

Purpose:
    Orchestrate resume handling, epoch flow, checkpoint/eval boundaries, and
    final summary projection while keeping batch execution and reporting logic
    in focused runtime modules.

Relationships:
    - Imported by `sft_12hz.py`.
    - Delegates resume, train-step, phase, loss, and summary work to bounded
      patch modules introduced by Story 28.
"""

from __future__ import annotations

from collections.abc import Callable

import torch
from accelerate import Accelerator

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_cli import tracker_config_payload
from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.devops.qwen_finetuning_patches.sft_12hz_diagnostic_capture import (
    diagnostic_capture_config_from_args,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_phase_runtime import (
    emit_progress_phase,
    set_dataloader_epoch_if_supported,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import (
    TrainingPhase,
    TrainingProgressHeartbeat,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_resume_runtime import (
    initialize_resume_runtime,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun
from scripts.devops.qwen_finetuning_patches.sft_12hz_summary import (
    build_training_summary,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import (
    TrainingTrackerSummary,
    initialize_training_trackers,
    refresh_training_tracker_summary,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_train_step import (
    execute_train_iteration,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_transition_runtime import (
    finalize_training_runtime,
    handle_interval_boundaries,
    save_epoch_export_checkpoint,
)
from scripts.devops.qwen_finetuning_patches.training_stop import (
    TrainingStopState,
    install_training_stop_handlers,
)


def execute_training_loop(
    prepared: PreparedTrainingRun,
    *,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None = None,
    tracker_ready_callback: Callable[[TrainingTrackerSummary], None] | None = None,
) -> TrainingSummary:
    """Run one bounded Qwen fine-tuning loop from prepared runtime state."""
    args = prepared.args
    accelerator: Accelerator = prepared.accelerator
    model = prepared.model
    optimizer = prepared.optimizer
    train_dataloader = prepared.train_dataloader
    output_model_path = prepared.output_model_path
    torch_profiler_session = prepared.torch_profiler_session
    tracker_summary = initialize_training_trackers(
        accelerator,
        tracker_config=prepared.tracker_config,
        config=tracker_config_payload(args),
        tags={
            "task": "task-101",
            "story": "story-26",
            "lane": "qwen-finetune",
            "run_name": prepared.tracker_config.run_name,
        },
    )
    if tracker_ready_callback is not None:
        tracker_ready_callback(tracker_summary)

    model.train()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    resume_state = initialize_resume_runtime(prepared, accelerator=accelerator)
    durable_checkpoint_paths = list(resume_state.durable_checkpoint_paths)
    latest_durable_checkpoint: DurableCheckpointMetadata | None = (
        resume_state.latest_durable_checkpoint
    )
    resumed_from_checkpoint_path = resume_state.resumed_from_checkpoint_path
    starting_epoch = resume_state.starting_epoch
    resume_step_in_epoch = resume_state.resume_step_in_epoch
    optimizer_steps_completed = resume_state.optimizer_steps_completed
    train_iterations_completed = resume_state.train_iterations_completed

    last_loss: float | None = None
    smoothed_loss: float | None = None
    latest_eval_loss: float | None = None
    latest_eval_step: int | None = None
    best_eval_loss: float | None = None
    best_eval_step: int | None = None
    eval_runs_completed = 0
    eval_batches_completed = 0
    checkpoint_paths: list[str] = []
    stop_state = TrainingStopState()
    install_training_stop_handlers(stop_state)
    reached_max_steps = False
    stop_requested_during_training = False
    emitted_train_progress = False
    optimizer_step_microbatches: list[dict[str, object]] = []
    diagnostic_capture_config = diagnostic_capture_config_from_args(args)
    epoch = starting_epoch
    step = 0

    def emit_loop_phase(phase: TrainingPhase) -> None:
        """Emit one progress heartbeat for the current loop state."""
        emit_progress_phase(
            progress_callback=progress_callback,
            phase=phase,
            current_epoch=epoch,
            current_optimizer_step=optimizer_steps_completed,
            current_train_iteration=train_iterations_completed,
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

    emit_loop_phase("startup")

    torch_profiler_session.start()
    try:
        for epoch in range(starting_epoch, args.num_epochs):
            set_dataloader_epoch_if_supported(train_dataloader, epoch=epoch)
            epoch_dataloader = train_dataloader
            epoch_start_step = 0
            if epoch == starting_epoch and resume_step_in_epoch > 0:
                epoch_dataloader = accelerator.skip_first_batches(
                    train_dataloader,
                    resume_step_in_epoch,
                )
                epoch_start_step = resume_step_in_epoch
            for step, batch in enumerate(epoch_dataloader, start=epoch_start_step):
                step_result = execute_train_iteration(
                    accelerator=accelerator,
                    prepared=prepared,
                    model=model,
                    optimizer=optimizer,
                    epoch=epoch,
                    batch=batch,
                    train_iterations_completed=train_iterations_completed,
                    optimizer_steps_completed=optimizer_steps_completed,
                    last_loss=last_loss,
                    smoothed_loss=smoothed_loss,
                    latest_eval_loss=latest_eval_loss,
                    best_eval_loss=best_eval_loss,
                    best_eval_step=best_eval_step,
                    eval_runs_completed=eval_runs_completed,
                    latest_durable_checkpoint=latest_durable_checkpoint,
                    emitted_train_progress=emitted_train_progress,
                    optimizer_step_microbatches=optimizer_step_microbatches,
                    checkpoint_interval_steps=int(args.checkpoint_interval_steps),
                    progress_callback=progress_callback,
                )
                train_iterations_completed = step_result.train_iterations_completed
                optimizer_steps_completed = step_result.optimizer_steps_completed
                last_loss = step_result.last_loss
                smoothed_loss = step_result.smoothed_loss
                emitted_train_progress = step_result.emitted_train_progress
                optimizer_step_microbatches = step_result.optimizer_step_microbatches
                interval_result = handle_interval_boundaries(
                    accelerator=accelerator,
                    prepared=prepared,
                    output_model_path=output_model_path,
                    checkpoint_interval_steps=int(args.checkpoint_interval_steps),
                    eval_interval_steps=int(args.eval_interval_steps),
                    durable_checkpoint_retention=int(args.durable_checkpoint_retention),
                    durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
                    current_epoch=epoch,
                    step_in_epoch=step,
                    current_optimizer_step=optimizer_steps_completed,
                    current_train_iteration=train_iterations_completed,
                    last_loss=last_loss,
                    smoothed_loss=smoothed_loss,
                    latest_eval_loss=latest_eval_loss,
                    best_eval_loss=best_eval_loss,
                    best_eval_step=best_eval_step,
                    eval_runs_completed=eval_runs_completed,
                    eval_batches_completed=eval_batches_completed,
                    latest_durable_checkpoint=latest_durable_checkpoint,
                    durable_checkpoint_paths=durable_checkpoint_paths,
                    completed_optimizer_step=step_result.completed_optimizer_step,
                    progress_callback=progress_callback,
                )
                latest_eval_loss = interval_result.latest_eval_loss
                latest_eval_step = interval_result.latest_eval_step
                best_eval_loss = interval_result.best_eval_loss
                best_eval_step = interval_result.best_eval_step
                eval_runs_completed = interval_result.eval_runs_completed
                eval_batches_completed = interval_result.eval_batches_completed
                latest_durable_checkpoint = interval_result.latest_durable_checkpoint
                durable_checkpoint_paths = interval_result.durable_checkpoint_paths
                if (
                    interval_result.interval_transition_occurred
                    and not stop_state.stop_requested
                    and not (
                        args.max_steps is not None and optimizer_steps_completed >= args.max_steps
                    )
                ):
                    emit_loop_phase("train")
                if stop_state.stop_requested:
                    stop_requested_during_training = True
                    emit_loop_phase("signal-stop")
                    accelerator.print(
                        "Received stop request; saving one final durable checkpoint before exit."
                    )
                    break
                if (
                    args.max_steps is not None
                    and step_result.completed_optimizer_step
                    and optimizer_steps_completed >= args.max_steps
                ):
                    reached_max_steps = True
                    break
                torch_profiler_session.step()
            if not diagnostic_capture_config.enabled:
                checkpoint_paths = save_epoch_export_checkpoint(
                    accelerator=accelerator,
                    prepared=prepared,
                    checkpoint_paths=checkpoint_paths,
                    output_model_path=output_model_path,
                    current_epoch=epoch,
                    current_optimizer_step=optimizer_steps_completed,
                    current_train_iteration=train_iterations_completed,
                    last_loss=last_loss,
                    smoothed_loss=smoothed_loss,
                    latest_eval_loss=latest_eval_loss,
                    best_eval_loss=best_eval_loss,
                    best_eval_step=best_eval_step,
                    eval_runs_completed=eval_runs_completed,
                    latest_durable_checkpoint=latest_durable_checkpoint,
                    progress_callback=progress_callback,
                )
            if (
                accelerator.is_main_process
                and not reached_max_steps
                and not stop_requested_during_training
            ):
                emit_loop_phase("train")
            if reached_max_steps or stop_requested_during_training:
                break
        terminal_result = finalize_training_runtime(
            accelerator=accelerator,
            prepared=prepared,
            output_model_path=output_model_path,
            checkpoint_interval_steps=int(args.checkpoint_interval_steps),
            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
            durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
            current_epoch=epoch,
            step_in_epoch=step,
            current_optimizer_step=optimizer_steps_completed,
            current_train_iteration=train_iterations_completed,
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
            stop_requested_during_training=stop_requested_during_training,
            capture_mode_enabled=diagnostic_capture_config.enabled,
            progress_callback=progress_callback,
        )
        last_loss = terminal_result.last_loss
        smoothed_loss = terminal_result.smoothed_loss
        emitted_train_progress = terminal_result.emitted_train_progress
        latest_eval_loss = terminal_result.latest_eval_loss
        latest_eval_step = terminal_result.latest_eval_step
        best_eval_loss = terminal_result.best_eval_loss
        best_eval_step = terminal_result.best_eval_step
        eval_runs_completed = terminal_result.eval_runs_completed
        eval_batches_completed = terminal_result.eval_batches_completed
        latest_durable_checkpoint = terminal_result.latest_durable_checkpoint
        durable_checkpoint_paths = terminal_result.durable_checkpoint_paths
        checkpoint_paths = terminal_result.checkpoint_paths
        peak_memory_allocated_bytes = terminal_result.peak_memory_allocated_bytes
        peak_memory_reserved_bytes = terminal_result.peak_memory_reserved_bytes
    finally:
        torch_profiler_session.stop()
        accelerator.end_training()
        tracker_summary = refresh_training_tracker_summary(
            accelerator,
            tracker_config=prepared.tracker_config,
            system_metrics_enabled=tracker_summary.mlflow_system_metrics_enabled,
        )
    return build_training_summary(
        args=args,
        prepared=prepared,
        optimizer_steps_completed=optimizer_steps_completed,
        train_iterations_completed=train_iterations_completed,
        last_loss=last_loss,
        smoothed_loss=smoothed_loss,
        latest_eval_loss=latest_eval_loss,
        best_eval_loss=best_eval_loss,
        best_eval_step=best_eval_step,
        eval_runs_completed=eval_runs_completed,
        eval_batches_completed=eval_batches_completed,
        peak_memory_allocated_bytes=peak_memory_allocated_bytes,
        peak_memory_reserved_bytes=peak_memory_reserved_bytes,
        resumed_from_checkpoint_path=resumed_from_checkpoint_path,
        latest_durable_checkpoint=latest_durable_checkpoint,
        durable_checkpoint_paths=durable_checkpoint_paths,
        checkpoint_paths=checkpoint_paths,
        stop_requested_during_training=stop_requested_during_training,
        stop_signal=stop_state.signal_name,
        tracker_summary=tracker_summary,
    )
