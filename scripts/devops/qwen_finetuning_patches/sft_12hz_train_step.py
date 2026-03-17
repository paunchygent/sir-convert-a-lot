"""Train-step execution helpers for the patched Qwen training loop.

Purpose:
    Own one accumulation window of forward/backward/update work so the main
    loop file only orchestrates epoch control, checkpoint/eval transitions, and
    terminal summary assembly.

Relationships:
    - Imported by `sft_12hz_loop.py`.
    - Consumes forensics, optimizer-guard, batching, and loss-runtime helpers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ContextManager, Protocol

import torch
from accelerate import Accelerator

from scripts.devops.qwen_finetuning_patches.dataset import require_batch_tensors
from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import DurableCheckpointMetadata
from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    fuse_auxiliary_codebook_embeddings,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    to_device_with_optional_non_blocking,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_diagnostic_window import (
    DiagnosticWindowConfig,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_diagnostic_window_artifacts import (
    write_diagnostic_window_artifact,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    build_microbatch_forensics,
    build_optimizer_step_forensics_window,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_gradient_rca import (
    build_gradient_rca_forensics,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import LossObservation
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    build_clip_boundary_optimizer_failure,
    build_post_step_optimizer_boundary_failure,
    build_pre_step_optimizer_boundary_failure,
    capture_pre_step_optimizer_boundary_probes,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard_probes import (
    capture_targeted_gradient_probes,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import TrainingProgressHeartbeat
from scripts.devops.qwen_finetuning_patches.sft_12hz_semantic_text_embeddings import (
    assemble_semantic_text_embedding,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    resolve_talker_codec_embedding,
    resolve_talker_text_embedding,
)

from .sft_12hz_loss_runtime import consume_loss_observations


class _ProfilerSessionLike(Protocol):
    """Protocol for the profiler session surface used during one train step."""

    def phase(self, name: str) -> ContextManager[object]: ...


class _DataloaderTuningLike(Protocol):
    """Protocol for the dataloader tuning surface used during one train step."""

    @property
    def non_blocking_transfer(self) -> bool: ...


class _LossObserverLike(Protocol):
    """Protocol for the loss observer surface used during one train step."""

    def submit(
        self,
        *,
        loss: torch.Tensor,
        main_loss: torch.Tensor,
        sub_talker_loss: torch.Tensor,
        grad_norm: torch.Tensor | float | None,
        step_forensics: dict[str, object] | None,
        optimizer_step: int,
        current_epoch: int,
        current_train_iteration: int,
    ) -> None: ...

    def drain_ready(self, *, force: bool) -> list[LossObservation]: ...


class _HeartbeatPolicyLike(Protocol):
    """Protocol for the heartbeat policy surface used during one train step."""

    def should_emit_train_update(self, optimizer_step: int) -> bool: ...


class _FiniteLossGuardLike(Protocol):
    """Protocol for the finite-loss guard surface used during one train step."""

    def observe(self, observation: LossObservation) -> None: ...


class _RefMelCacheLike(Protocol):
    """Protocol for the ref-mel cache surface used during one train step."""

    def payload(self) -> dict[str, bool | float | int | None]: ...


class TrainStepPreparedRuntime(Protocol):
    """Focused prepared-runtime surface needed by one train-step window."""

    @property
    def torch_profiler_session(self) -> _ProfilerSessionLike: ...

    @property
    def effective_dataloader_tuning(self) -> _DataloaderTuningLike: ...

    @property
    def loss_observer(self) -> _LossObserverLike: ...

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

    @property
    def gradient_accumulation_steps(self) -> int: ...

    @property
    def output_model_path(self) -> Path: ...

    @property
    def diagnostic_window(self) -> DiagnosticWindowConfig | None: ...


@dataclass(frozen=True)
class TrainStepResult:
    """Resolved state after one dataloader iteration in the training loop."""

    train_iterations_completed: int
    optimizer_steps_completed: int
    last_loss: float | None
    smoothed_loss: float | None
    emitted_train_progress: bool
    completed_optimizer_step: bool
    optimizer_step_microbatches: list[dict[str, object]]


def execute_train_iteration(
    *,
    accelerator: Accelerator,
    prepared: TrainStepPreparedRuntime,
    model,
    optimizer,
    epoch: int,
    batch: object,
    train_iterations_completed: int,
    optimizer_steps_completed: int,
    last_loss: float | None,
    smoothed_loss: float | None,
    latest_eval_loss: float | None,
    best_eval_loss: float | None,
    best_eval_step: int | None,
    eval_runs_completed: int,
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    emitted_train_progress: bool,
    optimizer_step_microbatches: list[dict[str, object]],
    checkpoint_interval_steps: int,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None,
) -> TrainStepResult:
    """Execute one dataloader iteration and return the updated loop state."""
    resolved_batch = require_batch_tensors(batch)
    current_train_iteration = train_iterations_completed + 1
    current_optimizer_step = optimizer_steps_completed + 1
    with accelerator.accumulate(model):
        grad_norm: torch.Tensor | float | None = None
        pre_step_probes = None
        post_clip_gradient_probes: dict[str, object] | None = None
        with prepared.torch_profiler_session.phase("task101.batch-preparation"):
            input_ids = resolved_batch["input_ids"]
            codec_ids = resolved_batch["codec_ids"]
            semantic_text_ids = resolved_batch["semantic_text_ids"]
            semantic_text_positions = resolved_batch["semantic_text_positions"]
            semantic_text_mask = resolved_batch["semantic_text_mask"]
            ref_mels = resolved_batch["ref_mels"]
            batch_provenance = resolved_batch["batch_provenance"]
            codec_embedding_mask = resolved_batch["codec_embedding_mask"]
            attention_mask = resolved_batch["attention_mask"]
            codec_0_labels = resolved_batch["codec_0_labels"]
            codec_mask = resolved_batch["codec_mask"]
            ref_mels_on_device = to_device_with_optional_non_blocking(
                ref_mels,
                device=model.device,
                dtype=model.dtype,
                non_blocking_transfer=prepared.effective_dataloader_tuning.non_blocking_transfer,
            )
            speaker_embedding = model.speaker_encoder(ref_mels_on_device).detach()
        with prepared.torch_profiler_session.phase("task101.forward-backward"):
            text_embedding = resolve_talker_text_embedding(model)
            codec_embedding = resolve_talker_codec_embedding(model)
            input_text_ids = input_ids[:, :, 0]
            input_codec_ids = input_ids[:, :, 1]
            input_text_embedding = assemble_semantic_text_embedding(
                text_embedding=text_embedding,
                semantic_text_ids=semantic_text_ids,
                semantic_text_positions=semantic_text_positions,
                semantic_text_mask=semantic_text_mask,
                sequence_length=input_ids.shape[1],
            )
            diagnostic_window = getattr(prepared, "diagnostic_window", None)
            diagnostic_step_active = (
                diagnostic_window is not None
                and diagnostic_window.includes_optimizer_step(current_optimizer_step)
            )
            if diagnostic_step_active:
                input_text_embedding.retain_grad()
            input_codec_embedding = codec_embedding(input_codec_ids) * codec_embedding_mask
            input_codec_embedding[:, 6, :] = speaker_embedding
            fused_auxiliary_embedding = fuse_auxiliary_codebook_embeddings(
                codebook_embeddings=model.talker.code_predictor.get_input_embeddings(),
                codec_ids=codec_ids,
                codec_mask=codec_mask,
            )
            input_embeddings = (
                input_text_embedding + input_codec_embedding + fused_auxiliary_embedding
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
            gradient_forensics = (
                None
                if not diagnostic_step_active
                else build_gradient_rca_forensics(
                    model=model,
                    input_text_ids=input_text_ids,
                    input_text_embedding=input_text_embedding,
                    batch_provenance=batch_provenance,
                )
            )
            if completed_optimizer_step:
                pre_step_probes = capture_pre_step_optimizer_boundary_probes(
                    model=model,
                    optimizer=optimizer,
                )
                grad_norm = accelerator.clip_grad_norm_(model.parameters(), 1.0)
            grad_norm_tensor = (
                None
                if grad_norm is None
                else grad_norm
                if isinstance(grad_norm, torch.Tensor)
                else torch.tensor(float(grad_norm), dtype=torch.float32, device=loss.device)
            )
            optimizer_step_microbatches = [
                *optimizer_step_microbatches,
                build_microbatch_forensics(
                    train_iteration=current_train_iteration,
                    microbatch_index_in_optimizer_step=len(optimizer_step_microbatches) + 1,
                    batch_provenance=batch_provenance,
                    gradient_forensics=gradient_forensics,
                    probes=[
                        ("ref_mels", ref_mels_on_device),
                        ("speaker_embedding", speaker_embedding),
                        ("input_text_embedding", input_text_embedding),
                        ("input_codec_embedding", input_codec_embedding),
                        ("fused_auxiliary_embedding", fused_auxiliary_embedding),
                        ("input_embeddings", input_embeddings),
                        ("talker_hidden_states", talker_hidden_states),
                        ("main_loss", outputs.loss),
                        ("sub_talker_loss", sub_talker_loss),
                        ("combined_loss", loss),
                        ("grad_norm", grad_norm_tensor),
                    ],
                ),
            ]
            if (
                diagnostic_step_active
                and accelerator.is_main_process
                and hasattr(prepared, "output_model_path")
            ):
                assert diagnostic_window is not None
                write_diagnostic_window_artifact(
                    output_model_path=prepared.output_model_path,
                    optimizer_step=current_optimizer_step,
                    current_train_iteration=current_train_iteration,
                    diagnostic_kind=diagnostic_window.kind,
                    start_optimizer_step=diagnostic_window.start_optimizer_step,
                    end_optimizer_step=diagnostic_window.end_optimizer_step,
                    step_forensics=build_optimizer_step_forensics_window(
                        microbatches=optimizer_step_microbatches,
                    ),
                )
        step_forensics = None
        if completed_optimizer_step:
            step_forensics = build_optimizer_step_forensics_window(
                microbatches=optimizer_step_microbatches,
            )
            if pre_step_probes is None:
                raise RuntimeError("Expected pre-step probes on a sync optimizer boundary.")
            pre_clip_failure = build_pre_step_optimizer_boundary_failure(
                model=model,
                optimizer=optimizer,
                optimizer_step=current_optimizer_step,
                current_epoch=epoch,
                current_train_iteration=current_train_iteration,
                loss=loss,
                main_loss=outputs.loss,
                sub_talker_loss=sub_talker_loss,
                step_forensics=step_forensics,
                pre_step_probes=pre_step_probes,
            )
            if pre_clip_failure is not None:
                raise pre_clip_failure
            post_clip_gradient_probes = capture_targeted_gradient_probes(model=model)
            clip_boundary_failure = build_clip_boundary_optimizer_failure(
                optimizer_step=current_optimizer_step,
                current_epoch=epoch,
                current_train_iteration=current_train_iteration,
                loss=loss,
                main_loss=outputs.loss,
                sub_talker_loss=sub_talker_loss,
                grad_norm=grad_norm,
                step_forensics=step_forensics,
                pre_step_probes=pre_step_probes,
                post_clip_gradient_probes=(
                    {} if post_clip_gradient_probes is None else post_clip_gradient_probes
                ),
            )
            if clip_boundary_failure is not None:
                raise clip_boundary_failure
        with prepared.torch_profiler_session.phase("task101.optimizer-step"):
            optimizer.step()
            if not completed_optimizer_step:
                optimizer.zero_grad()
        if not completed_optimizer_step:
            return TrainStepResult(
                train_iterations_completed=current_train_iteration,
                optimizer_steps_completed=optimizer_steps_completed,
                last_loss=last_loss,
                smoothed_loss=smoothed_loss,
                emitted_train_progress=emitted_train_progress,
                completed_optimizer_step=False,
                optimizer_step_microbatches=optimizer_step_microbatches,
            )
        post_step_failure = build_post_step_optimizer_boundary_failure(
            model=model,
            optimizer=optimizer,
            optimizer_step=current_optimizer_step,
            current_epoch=epoch,
            current_train_iteration=current_train_iteration,
            loss=loss,
            main_loss=outputs.loss,
            sub_talker_loss=sub_talker_loss,
            grad_norm=grad_norm,
            step_forensics=step_forensics,
            pre_step_parameter_probes=(
                None if pre_step_probes is None else pre_step_probes.parameter_probes
            ),
            pre_clip_gradient_probes=(
                None if pre_step_probes is None else pre_step_probes.pre_clip_gradient_probes
            ),
            post_clip_gradient_probes=post_clip_gradient_probes,
            pre_step_optimizer_state_probes=(
                None if pre_step_probes is None else pre_step_probes.optimizer_state_probes
            ),
        )
        if post_step_failure is not None:
            raise post_step_failure
        optimizer.zero_grad()
        next_optimizer_steps_completed = optimizer_steps_completed + 1
        prepared.loss_observer.submit(
            loss=loss,
            main_loss=outputs.loss,
            sub_talker_loss=sub_talker_loss,
            grad_norm=grad_norm,
            step_forensics=step_forensics,
            optimizer_step=next_optimizer_steps_completed,
            current_epoch=epoch,
            current_train_iteration=current_train_iteration,
        )
        next_last_loss, next_smoothed_loss, next_emitted_train_progress = consume_loss_observations(
            accelerator=accelerator,
            prepared=prepared,
            observations=prepared.loss_observer.drain_ready(
                force=(
                    (not emitted_train_progress)
                    or prepared.heartbeat_policy.should_emit_train_update(
                        next_optimizer_steps_completed
                    )
                )
            ),
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
        return TrainStepResult(
            train_iterations_completed=current_train_iteration,
            optimizer_steps_completed=next_optimizer_steps_completed,
            last_loss=next_last_loss,
            smoothed_loss=next_smoothed_loss,
            emitted_train_progress=next_emitted_train_progress,
            completed_optimizer_step=True,
            optimizer_step_microbatches=[],
        )
