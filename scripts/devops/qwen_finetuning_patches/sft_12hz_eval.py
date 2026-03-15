"""Held-out evaluation helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Provide a real in-training held-out evaluation pass for the patched Qwen
    trainer so the main training loop can stay focused on optimizer progress
    while still emitting truthful eval loss artifacts.

Relationships:
    - Imported by `sft_12hz_loop.py`.
    - Consumes prepared runtime state from `sft_12hz_setup.py`.
    - Emits eval heartbeats via `sft_12hz_progress.py` and eval tracker metrics
      via `sft_12hz_tracking.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    fuse_auxiliary_codebook_embeddings,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    to_device_with_optional_non_blocking,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import (
    TrainingProgressHeartbeat,
    build_training_progress_heartbeat,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import log_eval_metrics

if TYPE_CHECKING:
    from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun

DEFAULT_EVAL_INTERVAL_STEPS = 100


@dataclass(frozen=True)
class EvalPassResult:
    """Summary of one real held-out evaluation pass."""

    latest_eval_loss: float
    latest_eval_step: int
    best_eval_loss: float
    best_eval_step: int
    eval_runs_completed: int
    eval_batches_completed: int


def run_eval_pass(
    *,
    prepared: PreparedTrainingRun,
    current_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    latest_loss: float | None,
    smoothed_loss: float | None,
    latest_durable_checkpoint: object | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    eval_batches_completed: int,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None,
) -> EvalPassResult:
    """Run one bounded held-out evaluation pass and return updated eval state."""
    model = prepared.model
    accelerator = prepared.accelerator
    previous_training_mode = model.training
    if progress_callback is not None:
        progress_callback(
            build_training_progress_heartbeat(
                phase="eval",
                current_epoch=current_epoch,
                current_optimizer_step=current_optimizer_step,
                current_train_iteration=current_train_iteration,
                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                latest_loss=latest_loss,
                smoothed_loss=smoothed_loss,
                latest_durable_checkpoint=latest_durable_checkpoint,
                latest_eval_loss=latest_eval_loss,
                best_eval_loss=best_eval_loss,
                best_eval_step=best_eval_step,
                eval_runs_completed=eval_runs_completed,
            )
        )
    model.eval()
    total_eval_loss = 0.0
    completed_batches = 0
    try:
        with torch.no_grad(), prepared.torch_profiler_session.phase("task101.eval"):
            for batch in prepared.eval_dataloader:
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
                        non_blocking_transfer=(
                            prepared.effective_dataloader_tuning.non_blocking_transfer
                        ),
                    )
                ).detach()
                input_text_ids = input_ids[:, :, 0]
                input_codec_ids = input_ids[:, :, 1]
                input_text_embedding = (
                    model.talker.model.text_embedding(input_text_ids) * text_embedding_mask
                )
                if hasattr(model.talker.model, "text_projection"):
                    input_text_embedding = model.talker.model.text_projection(input_text_embedding)
                input_codec_embedding = (
                    model.talker.model.codec_embedding(input_codec_ids) * codec_embedding_mask
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
                total_eval_loss += float(loss.detach().float().item())
                completed_batches += 1
    finally:
        if previous_training_mode:
            model.train()
    if completed_batches <= 0:
        raise SystemExit("Held-out eval dataloader produced zero batches.")
    resolved_eval_loss = total_eval_loss / completed_batches
    resolved_best_eval_loss = resolved_eval_loss
    resolved_best_eval_step = current_optimizer_step
    if best_eval_loss is not None and best_eval_step is not None:
        resolved_best_eval_loss = best_eval_loss
        resolved_best_eval_step = best_eval_step
        if resolved_eval_loss < best_eval_loss:
            resolved_best_eval_loss = resolved_eval_loss
            resolved_best_eval_step = current_optimizer_step
    log_eval_metrics(
        accelerator,
        eval_loss=resolved_eval_loss,
        best_eval_loss=resolved_best_eval_loss,
        best_eval_step=resolved_best_eval_step,
        current_epoch=current_epoch,
        current_optimizer_step=current_optimizer_step,
        current_train_iteration=current_train_iteration,
        eval_runs_completed=eval_runs_completed + 1,
    )
    if progress_callback is not None:
        progress_callback(
            build_training_progress_heartbeat(
                phase="eval",
                current_epoch=current_epoch,
                current_optimizer_step=current_optimizer_step,
                current_train_iteration=current_train_iteration,
                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                latest_loss=latest_loss,
                smoothed_loss=smoothed_loss,
                latest_durable_checkpoint=latest_durable_checkpoint,
                latest_eval_loss=resolved_eval_loss,
                best_eval_loss=resolved_best_eval_loss,
                best_eval_step=resolved_best_eval_step,
                eval_runs_completed=eval_runs_completed + 1,
            )
        )
    return EvalPassResult(
        latest_eval_loss=resolved_eval_loss,
        latest_eval_step=current_optimizer_step,
        best_eval_loss=resolved_best_eval_loss,
        best_eval_step=resolved_best_eval_step,
        eval_runs_completed=eval_runs_completed + 1,
        eval_batches_completed=eval_batches_completed + completed_batches,
    )
