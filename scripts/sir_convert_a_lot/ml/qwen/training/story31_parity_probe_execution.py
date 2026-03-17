"""Execution helpers for the Story 31 deterministic parity probe.

Purpose:
    Keep runtime setup, exact-row selection, one-step execution, and cleanup
    separate from the path-report orchestration layer.
"""

from __future__ import annotations

import argparse
import gc
import random
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path

import numpy as np
import torch

from scripts.devops.qwen_finetuning_patches.dataset import (
    BatchTensors,
    TTSDataset,
    require_batch_tensors,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    build_microbatch_forensics,
    build_optimizer_step_forensics_window,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces import (
    ForwardBatchInputs,
    execute_talker_forward_pass,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_gradient_rca import (
    build_gradient_rca_forensics,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import (
    NonFiniteLossError,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    OptimizerBoundaryCorruptionError,
    build_clip_boundary_optimizer_failure,
    build_post_step_optimizer_boundary_failure,
    build_pre_step_optimizer_boundary_failure,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard_probes import (
    capture_pre_step_optimizer_boundary_probes,
    capture_targeted_gradient_probes,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun
from scripts.devops.qwen_finetuning_patches.sft_12hz_train_step import (
    execute_train_iteration,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_artifacts import (
    ExecutionArtifacts,
    SelectedRow,
    execution_artifacts_from_failure_payload,
    execution_artifacts_from_payload,
    optional_mapping,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_contracts import (
    Story31ParityProbeSettings,
)


def build_runtime_args(
    settings: Story31ParityProbeSettings,
    *,
    output_model_path: Path,
) -> argparse.Namespace:
    """Return the CLI-style runtime args for one prepared parity path."""
    train_jsonl = (
        settings.source_bundle_root / "manifests" / f"{settings.train_manifest_family}.prepared.jsonl"
    )
    eval_jsonl = (
        settings.source_bundle_root / "manifests" / f"{settings.eval_manifest_family}.prepared.jsonl"
    )
    return argparse.Namespace(
        init_model_path=settings.model_id,
        output_model_path=output_model_path.as_posix(),
        train_jsonl=train_jsonl.as_posix(),
        eval_jsonl=eval_jsonl.as_posix(),
        batch_size=settings.batch_size,
        throughput_profile_label=settings.throughput_profile_label,
        lr=settings.lr,
        num_epochs=settings.num_epochs,
        max_steps=settings.max_steps,
        gradient_accumulation_steps=settings.gradient_accumulation_steps,
        checkpoint_interval_steps=settings.checkpoint_interval_steps,
        eval_interval_steps=settings.eval_interval_steps,
        durable_checkpoint_retention=settings.durable_checkpoint_retention,
        durable_checkpoint_min_free_bytes=settings.durable_checkpoint_min_free_bytes,
        resume_from_checkpoint=None,
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        dataloader_persistent_workers=True,
        dataloader_prefetch_factor=4,
        non_blocking_transfer=True,
        data_path_proof_mode=False,
        heartbeat_interval_optimizer_steps=20,
        finite_loss_max_consecutive_steps=3,
        ref_mel_cache_enabled=True,
        ref_mel_cache_max_items=2048,
        torch_profiler_enabled=False,
        torch_profiler_wait_steps=1,
        torch_profiler_warmup_steps=1,
        torch_profiler_active_steps=4,
        torch_profiler_repeat=1,
        torch_profiler_record_shapes=True,
        torch_profiler_profile_memory=True,
        torch_profiler_with_stack=False,
        torch_profiler_trace_dir=None,
        metrics_output_json=None,
        tracker_project_name="task101-qwen-pilot",
        mlflow_experiment_name="task101-qwen-pilot",
        mlflow_tracking_uri=None,
        mlflow_artifact_root=None,
        tensorboard_logging_dir=None,
        tracker_run_name=output_model_path.parent.name,
        pilot_bundle_root=settings.source_bundle_root.as_posix(),
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        diagnostic_kind=None,
        diagnostic_source_launch_root=None,
        diagnostic_source_checkpoint_path=None,
        diagnostic_target_optimizer_step=None,
        diagnostic_capture_artifact_path=None,
        diagnostic_capture_launch_root_host_path=None,
        diagnostic_capture_checkpoint_path=None,
        diagnostic_start_optimizer_step=None,
        diagnostic_end_optimizer_step=None,
        text_embedding_assembly_mode=settings.text_embedding_assembly_mode,
        text_embedding_mask_policy=settings.text_embedding_mask_policy,
    )


def require_training_dataset(prepared: PreparedTrainingRun) -> TTSDataset:
    """Return the patched TTSDataset from the prepared training runtime."""
    dataset = getattr(prepared.train_dataloader, "dataset", None)
    if not isinstance(dataset, TTSDataset):
        raise TypeError("Story 31 parity probe requires the patched TTSDataset training surface.")
    return dataset


def select_rows(
    dataset: TTSDataset,
    *,
    manifest_lines: Sequence[int],
) -> tuple[SelectedRow, ...]:
    """Return the exact ordered manifest rows requested by the parity contract."""
    rows_by_line: dict[int, SelectedRow] = {}
    for dataset_index, row in enumerate(dataset.data_list):
        line_number = row.get("manifest_line_number")
        if isinstance(line_number, int):
            rows_by_line.setdefault(
                line_number,
                SelectedRow(dataset_index=dataset_index, row=row),
            )
    selected_rows: list[SelectedRow] = []
    missing_lines: list[int] = []
    for line_number in manifest_lines:
        selected = rows_by_line.get(line_number)
        if selected is None:
            missing_lines.append(int(line_number))
            continue
        selected_rows.append(selected)
    if missing_lines:
        raise SystemExit(
            "Story 31 parity probe could not find all required manifest lines in the selected "
            f"train manifest: missing_lines={missing_lines}."
        )
    return tuple(selected_rows)


def run_current_train_step_window(
    prepared: PreparedTrainingRun,
    batches: Sequence[BatchTensors],
) -> ExecutionArtifacts:
    """Execute the real train-step window against the fixed microbatch family."""
    optimizer_steps_completed = 0
    train_iterations_completed = 0
    last_loss: float | None = None
    smoothed_loss: float | None = None
    emitted_train_progress = False
    optimizer_step_microbatches: list[dict[str, object]] = []
    for batch in batches:
        try:
            result = execute_train_iteration(
                accelerator=prepared.accelerator,
                prepared=prepared,
                model=prepared.model,
                optimizer=prepared.optimizer,
                epoch=0,
                batch=batch,
                train_iterations_completed=train_iterations_completed,
                optimizer_steps_completed=optimizer_steps_completed,
                last_loss=last_loss,
                smoothed_loss=smoothed_loss,
                latest_eval_loss=None,
                best_eval_loss=None,
                best_eval_step=None,
                eval_runs_completed=0,
                latest_durable_checkpoint=None,
                emitted_train_progress=emitted_train_progress,
                optimizer_step_microbatches=optimizer_step_microbatches,
                checkpoint_interval_steps=prepared.args.checkpoint_interval_steps,
                progress_callback=None,
            )
        except OptimizerBoundaryCorruptionError as error:
            return execution_artifacts_from_failure_payload(
                status="optimizer_boundary_failure",
                payload=error.payload(),
            )
        except NonFiniteLossError as error:
            return execution_artifacts_from_failure_payload(
                status="non_finite_loss_failure",
                payload=error.payload(),
            )
        train_iterations_completed = result.train_iterations_completed
        optimizer_steps_completed = result.optimizer_steps_completed
        last_loss = result.last_loss
        smoothed_loss = result.smoothed_loss
        emitted_train_progress = result.emitted_train_progress
        optimizer_step_microbatches = result.optimizer_step_microbatches
        if result.completed_optimizer_step:
            observation = latest_loss_observation(prepared)
            step_forensics = (
                None if observation is None else optional_mapping(observation, "step_forensics")
            )
            return execution_artifacts_from_payload(
                payload={
                    "status": "completed_optimizer_step",
                    "optimizer_steps_completed": optimizer_steps_completed,
                    "train_iterations_completed": train_iterations_completed,
                    "loss_value": last_loss,
                    "combined_loss_value": last_loss,
                    "smoothed_loss": smoothed_loss,
                    "step_forensics": step_forensics,
                }
            )
    step_forensics = (
        None
        if not optimizer_step_microbatches
        else build_optimizer_step_forensics_window(microbatches=optimizer_step_microbatches)
    )
    return execution_artifacts_from_payload(
        payload={
            "status": "partial_window",
            "optimizer_steps_completed": optimizer_steps_completed,
            "train_iterations_completed": train_iterations_completed,
            "loss_value": last_loss,
            "combined_loss_value": last_loss,
            "smoothed_loss": smoothed_loss,
            "step_forensics": step_forensics,
        }
    )


def run_reconstructed_shared_window(
    prepared: PreparedTrainingRun,
    batches: Sequence[BatchTensors],
) -> ExecutionArtifacts:
    """Execute the reconstructed shared-forward parity window."""
    optimizer_steps_completed = 0
    train_iterations_completed = 0
    optimizer_step_microbatches: list[dict[str, object]] = []
    prepared.optimizer.zero_grad()
    for batch in batches:
        resolved_batch = require_batch_tensors(batch)
        train_iterations_completed += 1
        current_optimizer_step = optimizer_steps_completed + 1
        with prepared.accelerator.accumulate(prepared.model):
            forward_surfaces = execute_talker_forward_pass(
                model=prepared.model,
                batch=ForwardBatchInputs(
                    input_ids=resolved_batch["input_ids"],
                    codec_ids=resolved_batch["codec_ids"],
                    semantic_text_ids=resolved_batch["semantic_text_ids"],
                    semantic_text_positions=resolved_batch["semantic_text_positions"],
                    semantic_text_mask=resolved_batch["semantic_text_mask"],
                    text_embedding_mask=resolved_batch["text_embedding_mask"],
                    ref_mels=resolved_batch["ref_mels"],
                    codec_embedding_mask=resolved_batch["codec_embedding_mask"],
                    attention_mask=resolved_batch["attention_mask"],
                    codec_0_labels=resolved_batch["codec_0_labels"],
                    codec_mask=resolved_batch["codec_mask"],
                ),
                non_blocking_transfer=prepared.effective_dataloader_tuning.non_blocking_transfer,
                text_embedding_assembly_mode=prepared.text_embedding_assembly_mode,
            )
            diagnostic_window = getattr(prepared, "diagnostic_window", None)
            diagnostic_step_active = (
                diagnostic_window is not None
                and diagnostic_window.includes_optimizer_step(current_optimizer_step)
            )
            if diagnostic_step_active:
                forward_surfaces.input_text_embedding.retain_grad()
            prepared.accelerator.backward(forward_surfaces.combined_loss)
            completed_optimizer_step = prepared.accelerator.sync_gradients
            pre_step_probes = None
            post_clip_gradient_probes: dict[str, object] | None = None
            grad_norm: torch.Tensor | float | None = None
            if completed_optimizer_step:
                pre_step_probes = capture_pre_step_optimizer_boundary_probes(
                    model=prepared.model,
                    optimizer=prepared.optimizer,
                )
                grad_norm = prepared.accelerator.clip_grad_norm_(prepared.model.parameters(), 1.0)
            optimizer_step_microbatches = [
                *optimizer_step_microbatches,
                build_microbatch_forensics(
                    train_iteration=train_iterations_completed,
                    microbatch_index_in_optimizer_step=len(optimizer_step_microbatches) + 1,
                    batch_provenance=resolved_batch["batch_provenance"],
                    gradient_forensics=(
                        build_gradient_rca_forensics(
                            model=prepared.model,
                            input_text_ids=resolved_batch["input_ids"][:, :, 0],
                            input_text_embedding=forward_surfaces.input_text_embedding,
                            batch_provenance=resolved_batch["batch_provenance"],
                        )
                        if diagnostic_step_active
                        else None
                    ),
                    probes=[
                        ("ref_mels", forward_surfaces.ref_mels_on_device),
                        ("speaker_embedding", forward_surfaces.speaker_embedding),
                        ("semantic_text_embeddings", forward_surfaces.semantic_text_embeddings),
                        ("input_text_embedding", forward_surfaces.input_text_embedding),
                        ("input_codec_embedding", forward_surfaces.input_codec_embedding),
                        ("fused_auxiliary_embedding", forward_surfaces.fused_auxiliary_embedding),
                        ("input_embeddings", forward_surfaces.input_embeddings),
                        ("talker_hidden_states", forward_surfaces.talker_hidden_states),
                        ("main_loss", forward_surfaces.main_loss),
                        ("sub_talker_loss", forward_surfaces.sub_talker_loss),
                        ("combined_loss", forward_surfaces.combined_loss),
                        (
                            "grad_norm",
                            grad_norm_tensor(grad_norm, device=forward_surfaces.combined_loss.device),
                        ),
                    ],
                ),
            ]
            step_forensics = (
                None
                if not completed_optimizer_step
                else build_optimizer_step_forensics_window(microbatches=optimizer_step_microbatches)
            )
            if completed_optimizer_step:
                assert pre_step_probes is not None
                pre_clip_failure = build_pre_step_optimizer_boundary_failure(
                    model=prepared.model,
                    optimizer=prepared.optimizer,
                    optimizer_step=current_optimizer_step,
                    current_epoch=0,
                    current_train_iteration=train_iterations_completed,
                    loss=forward_surfaces.combined_loss,
                    main_loss=forward_surfaces.main_loss,
                    sub_talker_loss=forward_surfaces.sub_talker_loss,
                    step_forensics=step_forensics,
                    pre_step_probes=pre_step_probes,
                )
                if pre_clip_failure is not None:
                    return execution_artifacts_from_failure_payload(
                        status="optimizer_boundary_failure",
                        payload=pre_clip_failure.payload(),
                    )
                post_clip_gradient_probes = capture_targeted_gradient_probes(model=prepared.model)
                clip_failure = build_clip_boundary_optimizer_failure(
                    optimizer_step=current_optimizer_step,
                    current_epoch=0,
                    current_train_iteration=train_iterations_completed,
                    loss=forward_surfaces.combined_loss,
                    main_loss=forward_surfaces.main_loss,
                    sub_talker_loss=forward_surfaces.sub_talker_loss,
                    grad_norm=grad_norm,
                    step_forensics=step_forensics,
                    pre_step_probes=pre_step_probes,
                    post_clip_gradient_probes=post_clip_gradient_probes,
                )
                if clip_failure is not None:
                    return execution_artifacts_from_failure_payload(
                        status="optimizer_boundary_failure",
                        payload=clip_failure.payload(),
                    )
            prepared.optimizer.step()
            if not completed_optimizer_step:
                prepared.optimizer.zero_grad()
                continue
        assert pre_step_probes is not None
        assert post_clip_gradient_probes is not None
        post_step_failure = build_post_step_optimizer_boundary_failure(
            model=prepared.model,
            optimizer=prepared.optimizer,
            optimizer_step=current_optimizer_step,
            current_epoch=0,
            current_train_iteration=train_iterations_completed,
            loss=forward_surfaces.combined_loss,
            main_loss=forward_surfaces.main_loss,
            sub_talker_loss=forward_surfaces.sub_talker_loss,
            grad_norm=grad_norm,
            step_forensics=step_forensics,
            pre_step_parameter_probes=pre_step_probes.parameter_probes,
            pre_clip_gradient_probes=pre_step_probes.pre_clip_gradient_probes,
            post_clip_gradient_probes=post_clip_gradient_probes,
            pre_step_optimizer_state_probes=pre_step_probes.optimizer_state_probes,
        )
        if post_step_failure is not None:
            return execution_artifacts_from_failure_payload(
                status="optimizer_boundary_failure",
                payload=post_step_failure.payload(),
            )
        prepared.optimizer.zero_grad()
        optimizer_steps_completed += 1
        return execution_artifacts_from_payload(
            payload={
                "status": "completed_optimizer_step",
                "optimizer_steps_completed": optimizer_steps_completed,
                "train_iterations_completed": train_iterations_completed,
                "loss_value": optional_scalar(forward_surfaces.combined_loss),
                "combined_loss_value": optional_scalar(forward_surfaces.combined_loss),
                "main_loss_value": optional_scalar(forward_surfaces.main_loss),
                "sub_talker_loss_value": optional_scalar(forward_surfaces.sub_talker_loss),
                "grad_norm_value": optional_scalar(grad_norm),
                "pre_step_parameter_probes": pre_step_probes.parameter_probes,
                "pre_clip_gradient_probes": pre_step_probes.pre_clip_gradient_probes,
                "post_clip_gradient_probes": post_clip_gradient_probes,
                "pre_step_optimizer_state_probes": pre_step_probes.optimizer_state_probes,
                "step_forensics": step_forensics,
            }
        )
    step_forensics = (
        None
        if not optimizer_step_microbatches
        else build_optimizer_step_forensics_window(microbatches=optimizer_step_microbatches)
    )
    return execution_artifacts_from_payload(
        payload={
            "status": "partial_window",
            "optimizer_steps_completed": optimizer_steps_completed,
            "train_iterations_completed": train_iterations_completed,
            "step_forensics": step_forensics,
        }
    )


def latest_loss_observation(prepared: PreparedTrainingRun) -> Mapping[str, object] | None:
    """Return the latest recorded loss observation when one exists."""
    observations = prepared.finite_loss_guard.recent_observations
    if not observations:
        return None
    observation = observations[-1]
    return observation if isinstance(observation, Mapping) else None
def optional_scalar(value: torch.Tensor | float | None) -> float | None:
    """Return one scalar-like value as a float when available."""
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().to(dtype=torch.float32).view(()).item())
    return float(value)


def grad_norm_tensor(
    value: torch.Tensor | float | None,
    *,
    device: torch.device,
) -> torch.Tensor | None:
    """Return the grad norm as a tensor for microbatch forensics."""
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return value
    return torch.tensor(float(value), dtype=torch.float32, device=device)


def seed_everything(seed: int) -> None:
    """Apply the deterministic seed across Python, NumPy, and Torch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def cleanup_prepared_run(prepared: PreparedTrainingRun) -> None:
    """Release accelerator state and GPU memory after one parity path."""
    with suppress(Exception):
        prepared.accelerator.end_training()
    del prepared
    gc.collect()
    if torch.cuda.is_available():
        with suppress(Exception):
            torch.cuda.empty_cache()
