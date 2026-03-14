"""Training-loop execution helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Execute the bounded Qwen fine-tuning loop and build the summary payload in
    a focused module so the public trainer facade stays small.

Relationships:
    - Imported by `sft_12hz.py`.
    - Consumes prepared runtime state from `sft_12hz_setup.py` and emits the
      shared `TrainingSummary` contract.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
    _checkpoint_advanced_since_latest_save,
    _current_durable_checkpoint_paths,
    _load_durable_checkpoint_metadata,
    _save_durable_checkpoint,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_cli import tracker_config_payload
from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    fuse_auxiliary_codebook_embeddings,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    dataloader_tuning_payload,
    to_device_with_optional_non_blocking,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_export import save_checkpoint
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import observe_loss
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import (
    TrainingProgressHeartbeat,
    build_training_progress_heartbeat,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun
from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import (
    TrainingTrackerSummary,
    initialize_training_trackers,
    log_training_metrics,
    refresh_training_tracker_summary,
    update_smoothed_loss,
)
from scripts.devops.qwen_finetuning_patches.training_stop import (
    TrainingStopState,
    install_training_stop_handlers,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    throughput_policy_payload,
)


def execute_training_loop(
    prepared: PreparedTrainingRun,
    *,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None = None,
    tracker_ready_callback: Callable[[TrainingTrackerSummary], None] | None = None,
) -> TrainingSummary:
    """Run one bounded Qwen fine-tuning loop from prepared runtime state."""
    args = prepared.args
    accelerator = prepared.accelerator
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
    durable_checkpoint_paths: list[str] = []
    latest_durable_checkpoint: DurableCheckpointMetadata | None = None
    resumed_from_checkpoint_path: str | None = None
    starting_epoch = 0
    resume_step_in_epoch = 0
    model.train()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    optimizer_steps_completed = 0
    train_iterations_completed = 0
    last_loss: float | None = None
    smoothed_loss: float | None = None
    checkpoint_paths: list[str] = []
    stop_state = TrainingStopState()
    install_training_stop_handlers(stop_state)
    if args.resume_from_checkpoint is not None:
        resume_checkpoint_path = Path(args.resume_from_checkpoint)
        latest_durable_checkpoint = _load_durable_checkpoint_metadata(resume_checkpoint_path)
        accelerator.load_state(resume_checkpoint_path.as_posix())
        resumed_from_checkpoint_path = resume_checkpoint_path.as_posix()
        optimizer_steps_completed = latest_durable_checkpoint.optimizer_steps_completed
        starting_epoch = latest_durable_checkpoint.next_epoch
        resume_step_in_epoch = latest_durable_checkpoint.next_step_in_epoch
        durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
        train_iterations_completed = (
            starting_epoch * prepared.dataloader_length
        ) + resume_step_in_epoch
    if progress_callback is not None:
        progress_callback(
            build_training_progress_heartbeat(
                phase="startup",
                current_epoch=starting_epoch,
                current_optimizer_step=optimizer_steps_completed,
                current_train_iteration=train_iterations_completed,
                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                latest_loss=last_loss,
                smoothed_loss=smoothed_loss,
                latest_durable_checkpoint=latest_durable_checkpoint,
            )
        )
    reached_max_steps = False
    stop_requested_during_training = False
    epoch = starting_epoch
    step = 0
    torch_profiler_session.start()
    try:
        for epoch in range(starting_epoch, args.num_epochs):
            epoch_dataloader = train_dataloader
            epoch_start_step = 0
            if epoch == starting_epoch and resume_step_in_epoch > 0:
                epoch_dataloader = accelerator.skip_first_batches(
                    train_dataloader,
                    resume_step_in_epoch,
                )
                epoch_start_step = resume_step_in_epoch
            for step, batch in enumerate(epoch_dataloader, start=epoch_start_step):
                train_iterations_completed += 1
                with accelerator.accumulate(model):
                    with torch_profiler_session.phase("task101.batch-preparation"):
                        input_ids = batch["input_ids"]
                        codec_ids = batch["codec_ids"]
                        ref_mels = batch["ref_mels"]
                        text_embedding_mask = batch["text_embedding_mask"]
                        codec_embedding_mask = batch["codec_embedding_mask"]
                        attention_mask = batch["attention_mask"]
                        codec_0_labels = batch["codec_0_labels"]
                        codec_mask = batch["codec_mask"]
                        speaker_embedding = model.speaker_encoder(
                            to_device_with_optional_non_blocking(
                                ref_mels,
                                device=model.device,
                                dtype=model.dtype,
                                non_blocking_transfer=prepared.effective_dataloader_tuning.non_blocking_transfer,
                            )
                        ).detach()
                    with torch_profiler_session.phase("task101.forward-backward"):
                        input_text_ids = input_ids[:, :, 0]
                        input_codec_ids = input_ids[:, :, 1]
                        input_text_embedding = (
                            model.talker.model.text_embedding(input_text_ids) * text_embedding_mask
                        )
                        if hasattr(model.talker.model, "text_projection"):
                            input_text_embedding = model.talker.model.text_projection(
                                input_text_embedding
                            )
                        input_codec_embedding = (
                            model.talker.model.codec_embedding(input_codec_ids)
                            * codec_embedding_mask
                        )
                        input_codec_embedding[:, 6, :] = speaker_embedding
                        input_embeddings = (
                            input_text_embedding
                            + input_codec_embedding
                            + fuse_auxiliary_codebook_embeddings(
                                codebook_embeddings=model.talker.code_predictor.get_input_embeddings(),
                                codec_ids=codec_ids,
                                codec_mask=codec_mask,
                            )
                        )
                        outputs = model.talker(
                            inputs_embeds=input_embeddings[:, :-1, :],
                            attention_mask=attention_mask[:, :-1],
                            labels=codec_0_labels[:, 1:],
                            output_hidden_states=True,
                        )
                        hidden_states = outputs.hidden_states[0][-1]
                        talker_hidden_states = hidden_states[codec_mask[:, 1:]]
                        talker_codec_ids = codec_ids[codec_mask]
                        _, sub_talker_loss = model.talker.forward_sub_talker_finetune(
                            talker_codec_ids,
                            talker_hidden_states,
                        )
                        loss = outputs.loss + 0.3 * sub_talker_loss
                        accelerator.backward(loss)
                        completed_optimizer_step = accelerator.sync_gradients
                        if completed_optimizer_step:
                            accelerator.clip_grad_norm_(model.parameters(), 1.0)
                    with torch_profiler_session.phase("task101.optimizer-step"):
                        optimizer.step()
                        optimizer.zero_grad()
                    if completed_optimizer_step:
                        optimizer_steps_completed += 1
                        loss_observation = observe_loss(loss)
                        prepared.finite_loss_guard.observe(
                            loss_observation,
                            optimizer_step=optimizer_steps_completed,
                        )
                        last_loss = loss_observation.loss_value
                        smoothed_loss = update_smoothed_loss(smoothed_loss, last_loss)
                        if prepared.heartbeat_policy.should_emit_train_update(
                            optimizer_steps_completed
                        ):
                            log_training_metrics(
                                accelerator,
                                raw_loss=last_loss,
                                smoothed_loss=smoothed_loss,
                                current_epoch=epoch,
                                current_optimizer_step=optimizer_steps_completed,
                                current_train_iteration=train_iterations_completed,
                                checkpoint_interval_steps=int(args.checkpoint_interval_steps),
                                ref_mel_cache_metrics=prepared.ref_mel_cache.payload(),
                            )
                            if progress_callback is not None:
                                progress_callback(
                                    build_training_progress_heartbeat(
                                        phase="train",
                                        current_epoch=epoch,
                                        current_optimizer_step=optimizer_steps_completed,
                                        current_train_iteration=train_iterations_completed,
                                        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                                        latest_loss=last_loss,
                                        smoothed_loss=smoothed_loss,
                                        latest_durable_checkpoint=latest_durable_checkpoint,
                                    )
                                )
                            accelerator.print(
                                "Epoch "
                                f"{epoch} | Optimizer Step {optimizer_steps_completed} | "
                                f"Loss: {last_loss:.4f}"
                            )
                if (
                    completed_optimizer_step
                    and optimizer_steps_completed > 0
                    and optimizer_steps_completed % int(args.checkpoint_interval_steps) == 0
                ):
                    with torch_profiler_session.phase("task101.checkpoint-save"):
                        latest_durable_checkpoint = _save_durable_checkpoint(
                            accelerator=accelerator,
                            output_model_path=output_model_path,
                            optimizer_steps_completed=optimizer_steps_completed,
                            epoch=epoch,
                            step_in_epoch=step,
                            dataloader_length=prepared.dataloader_length,
                            reason="interval",
                            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
                            durable_checkpoint_min_free_bytes=int(
                                args.durable_checkpoint_min_free_bytes
                            ),
                        )
                    durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
                    if progress_callback is not None:
                        progress_callback(
                            build_training_progress_heartbeat(
                                phase="checkpoint-save",
                                current_epoch=epoch,
                                current_optimizer_step=optimizer_steps_completed,
                                current_train_iteration=train_iterations_completed,
                                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                                latest_loss=last_loss,
                                smoothed_loss=smoothed_loss,
                                latest_durable_checkpoint=latest_durable_checkpoint,
                            )
                        )
                if stop_state.stop_requested:
                    stop_requested_during_training = True
                    if progress_callback is not None:
                        progress_callback(
                            build_training_progress_heartbeat(
                                phase="signal-stop",
                                current_epoch=epoch,
                                current_optimizer_step=optimizer_steps_completed,
                                current_train_iteration=train_iterations_completed,
                                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                                latest_loss=last_loss,
                                smoothed_loss=smoothed_loss,
                                latest_durable_checkpoint=latest_durable_checkpoint,
                            )
                        )
                    accelerator.print(
                        "Received stop request; saving one final durable checkpoint before exit."
                    )
                    break
                if (
                    args.max_steps is not None
                    and completed_optimizer_step
                    and optimizer_steps_completed >= args.max_steps
                ):
                    reached_max_steps = True
                    break
                torch_profiler_session.step()
            if accelerator.is_main_process:
                output_dir = output_model_path / f"checkpoint-epoch-{epoch}"
                checkpoint_paths.append(
                    save_checkpoint(
                        accelerator=accelerator,
                        model=model,
                        model_path=prepared.model_path,
                        output_dir=output_dir,
                    )
                )
            if reached_max_steps or stop_requested_during_training:
                break
        if _checkpoint_advanced_since_latest_save(
            latest_durable_checkpoint,
            optimizer_steps_completed=optimizer_steps_completed,
        ):
            with torch_profiler_session.phase("task101.checkpoint-save"):
                latest_durable_checkpoint = _save_durable_checkpoint(
                    accelerator=accelerator,
                    output_model_path=output_model_path,
                    optimizer_steps_completed=optimizer_steps_completed,
                    epoch=epoch,
                    step_in_epoch=step,
                    dataloader_length=prepared.dataloader_length,
                    reason="signal-stop" if stop_requested_during_training else "final-step",
                    durable_checkpoint_retention=int(args.durable_checkpoint_retention),
                    durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
                )
            durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
            if progress_callback is not None:
                progress_callback(
                    build_training_progress_heartbeat(
                        phase="checkpoint-save",
                        current_epoch=epoch,
                        current_optimizer_step=optimizer_steps_completed,
                        current_train_iteration=train_iterations_completed,
                        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                        latest_loss=last_loss,
                        smoothed_loss=smoothed_loss,
                        latest_durable_checkpoint=latest_durable_checkpoint,
                    )
                )
        if accelerator.is_main_process:
            final_output_dir = output_model_path / "checkpoint-final"
            checkpoint_paths.append(
                save_checkpoint(
                    accelerator=accelerator,
                    model=model,
                    model_path=prepared.model_path,
                    output_dir=final_output_dir,
                )
            )
        peak_memory_allocated_bytes = (
            int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
        )
        peak_memory_reserved_bytes = (
            int(torch.cuda.max_memory_reserved()) if torch.cuda.is_available() else None
        )
    finally:
        torch_profiler_session.stop()
        accelerator.end_training()
        tracker_summary = refresh_training_tracker_summary(
            accelerator,
            tracker_config=prepared.tracker_config,
            system_metrics_enabled=tracker_summary.mlflow_system_metrics_enabled,
        )
    return _build_training_summary(
        args=args,
        prepared=prepared,
        optimizer_steps_completed=optimizer_steps_completed,
        train_iterations_completed=train_iterations_completed,
        last_loss=last_loss,
        smoothed_loss=smoothed_loss,
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


def _build_training_summary(
    *,
    args: argparse.Namespace,
    prepared: PreparedTrainingRun,
    optimizer_steps_completed: int,
    train_iterations_completed: int,
    last_loss: float | None,
    smoothed_loss: float | None,
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
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        optimizer_steps_completed=optimizer_steps_completed,
        train_iterations_completed=train_iterations_completed,
        last_loss=last_loss,
        smoothed_loss=smoothed_loss,
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
        throughput_profile=throughput_policy_payload(prepared.throughput_batch_policy),
        dataloader_tuning=dataloader_tuning_payload(prepared.effective_dataloader_tuning),
        heartbeat_policy=prepared.heartbeat_policy.payload(),
        finite_loss_guard=prepared.finite_loss_guard.payload(),
        acceptance_measurement_valid=True,
        ref_mel_cache=prepared.ref_mel_cache.payload(),
        profiling=profiling_payload,
        tracking=tracker_summary,
    )
