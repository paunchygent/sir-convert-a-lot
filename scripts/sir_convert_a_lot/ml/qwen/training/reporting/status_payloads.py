"""Status payload builders for Qwen training artifacts.

Purpose:
    Build live, completed, and failed `status.json` payloads without owning
    file I/O or reporter state transitions.

Relationships:
    - Used by `status_writer`.
    - Depends on failure projection and step-semantics helpers.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import NonFiniteLossError
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    OptimizerBoundaryCorruptionError,
)

from .artifact_io import utc_now_iso
from .failure_projection import (
    optional_mapping_int,
    resolve_failed_progress,
)
from .step_semantics import step_semantics_payload


def running_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    dataloader_length: int | None,
    eval_dataloader_length: int | None,
    checkpoint_interval_steps: int,
    eval_interval_steps: int,
    gradient_accumulation_steps: int,
    durable_checkpoint_retention: int,
    durable_checkpoint_min_free_bytes: int,
    dataloader_tuning: dict[str, object] | None,
    heartbeat_policy: dict[str, object] | None,
    finite_loss_guard_config: dict[str, object] | None,
    ref_mel_cache_config: dict[str, object] | None,
    bundle_precomputed_reference_input: dict[str, object] | None,
    throughput_profile: dict[str, object] | None,
    profiling_plan: dict[str, object] | None,
    diagnostic: dict[str, object] | None,
    talker_runtime: dict[str, object] | None,
    resume_from_checkpoint: Path | None,
    tracking_plan: dict[str, object] | None = None,
    tracking: dict[str, object] | None = None,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build the running-status payload written before training starts."""
    current_phase = None if live_progress is None else live_progress.get("phase")
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    raw_current_optimizer_step = (
        None if live_progress is None else live_progress.get("current_optimizer_step")
    )
    current_optimizer_step = (
        current_step if raw_current_optimizer_step is None else raw_current_optimizer_step
    )
    raw_current_train_iteration = (
        None if live_progress is None else live_progress.get("current_train_iteration")
    )
    current_train_iteration = (
        current_optimizer_step
        if raw_current_train_iteration is None
        else raw_current_train_iteration
    )
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_eval_loss = None if live_progress is None else live_progress.get("latest_eval_loss")
    best_eval_loss = None if live_progress is None else live_progress.get("best_eval_loss")
    best_eval_step = None if live_progress is None else live_progress.get("best_eval_step")
    eval_runs_completed = (
        None if live_progress is None else live_progress.get("eval_runs_completed")
    )
    latest_durable_checkpoint_path = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_path")
    )
    latest_durable_checkpoint_step = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_step")
    )
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    resolved_dataloader_length = (
        dataloader_length
        if dataloader_length is not None
        else None
        if live_progress is None
        else live_progress.get("dataloader_length")
    )
    resolved_eval_dataloader_length = (
        eval_dataloader_length
        if eval_dataloader_length is not None
        else None
        if live_progress is None
        else live_progress.get("eval_dataloader_length")
    )
    return {
        "status": "running",
        "stage": "training",
        "updated_at": utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "dataloader_length": resolved_dataloader_length,
        "eval_dataloader_length": resolved_eval_dataloader_length,
        "upstream_trainer_uses_eval_manifest": True,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "step_semantics": step_semantics_payload(gradient_accumulation_steps),
        "checkpoint_interval_steps": checkpoint_interval_steps,
        "eval_interval_steps": eval_interval_steps,
        "durable_checkpoint_retention": durable_checkpoint_retention,
        "durable_checkpoint_min_free_bytes": durable_checkpoint_min_free_bytes,
        "dataloader_tuning": dataloader_tuning,
        "heartbeat_policy": heartbeat_policy,
        "finite_loss_guard": finite_loss_guard_config,
        "ref_mel_cache": ref_mel_cache_config,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "throughput_profile": throughput_profile,
        "profiling": profiling_plan,
        "diagnostic": diagnostic,
        "talker_runtime": talker_runtime,
        "resumed_from_checkpoint_path": (
            None if resume_from_checkpoint is None else resume_from_checkpoint.as_posix()
        ),
        "current_phase": current_phase,
        "current_epoch": current_epoch,
        "current_step": current_step,
        "current_optimizer_step": current_optimizer_step,
        "current_train_iteration": current_train_iteration,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "latest_eval_loss": latest_eval_loss,
        "best_eval_loss": best_eval_loss,
        "best_eval_step": best_eval_step,
        "eval_runs_completed": eval_runs_completed,
        "latest_durable_checkpoint_path": latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "tracking_plan": tracking_plan,
        "tracking": tracking,
        "phase_history": [] if phase_history is None else phase_history,
    }


def completed_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    bundle_precomputed_reference_input: dict[str, object] | None,
    throughput_profile: dict[str, object] | None,
    training_summary: TrainingSummary,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build the terminal success payload for the training status artifact."""
    current_phase = "signal-stop" if training_summary.stopped_early else "completed"
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    raw_current_optimizer_step = (
        None if live_progress is None else live_progress.get("current_optimizer_step")
    )
    current_optimizer_step = (
        current_step if raw_current_optimizer_step is None else raw_current_optimizer_step
    )
    raw_current_train_iteration = (
        None if live_progress is None else live_progress.get("current_train_iteration")
    )
    current_train_iteration = (
        current_optimizer_step
        if raw_current_train_iteration is None
        else raw_current_train_iteration
    )
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    return {
        "status": "stopped" if training_summary.stopped_early else "completed",
        "stage": "training",
        "updated_at": utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "dataloader_length": training_summary.dataloader_length,
        "eval_dataloader_length": training_summary.eval_dataloader_length,
        "upstream_trainer_uses_eval_manifest": True,
        "gradient_accumulation_steps": training_summary.gradient_accumulation_steps,
        "step_semantics": step_semantics_payload(training_summary.gradient_accumulation_steps),
        "current_phase": current_phase,
        "current_epoch": current_epoch,
        "current_step": current_step,
        "current_optimizer_step": current_optimizer_step,
        "current_train_iteration": current_train_iteration,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "latest_eval_loss": training_summary.latest_eval_loss,
        "best_eval_loss": training_summary.best_eval_loss,
        "best_eval_step": training_summary.best_eval_step,
        "eval_runs_completed": training_summary.eval_runs_completed,
        "eval_batches_completed": training_summary.eval_batches_completed,
        "optimizer_steps_completed": training_summary.optimizer_steps_completed,
        "train_iterations_completed": training_summary.train_iterations_completed,
        "checkpoint_interval_steps": training_summary.checkpoint_interval_steps,
        "eval_interval_steps": training_summary.eval_interval_steps,
        "durable_checkpoint_retention": training_summary.durable_checkpoint_retention,
        "durable_checkpoint_min_free_bytes": training_summary.durable_checkpoint_min_free_bytes,
        "dataloader_tuning": training_summary.dataloader_tuning,
        "heartbeat_policy": training_summary.heartbeat_policy,
        "finite_loss_guard": training_summary.finite_loss_guard,
        "optimizer_boundary_guard": None,
        "ref_mel_cache": training_summary.ref_mel_cache,
        "talker_runtime": training_summary.talker_runtime,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "throughput_profile": throughput_profile,
        "batch_occupancy": training_summary.batch_occupancy,
        "data_path_attribution": training_summary.data_path_attribution,
        "acceptance_measurement_valid": training_summary.acceptance_measurement_valid,
        "resumed_from_checkpoint_path": training_summary.resumed_from_checkpoint_path,
        "latest_durable_checkpoint_path": training_summary.latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": training_summary.latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "stop_requested": training_summary.stop_requested,
        "stop_signal": training_summary.stop_signal,
        "stopped_early": training_summary.stopped_early,
        "tracking": None
        if training_summary.tracking is None
        else asdict(training_summary.tracking),
        "phase_history": [] if phase_history is None else phase_history,
    }


def failed_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    dataloader_length: int | None,
    eval_dataloader_length: int | None,
    bundle_precomputed_reference_input: dict[str, object] | None = None,
    throughput_profile: dict[str, object] | None = None,
    diagnostic: dict[str, object] | None = None,
    exc: BaseException,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
    tracking: dict[str, object] | None = None,
    talker_runtime: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the terminal failure payload for the training status artifact."""
    resolved_progress = resolve_failed_progress(live_progress=live_progress, exc=exc)
    finite_loss_guard_payload = None
    optimizer_boundary_guard_payload = None
    acceptance_measurement_valid = None
    if isinstance(exc, NonFiniteLossError):
        finite_loss_guard_payload = exc.payload()
        acceptance_measurement_valid = False
    if isinstance(exc, OptimizerBoundaryCorruptionError):
        optimizer_boundary_guard_payload = exc.payload()
        acceptance_measurement_valid = False
    return {
        "status": "failed",
        "stage": "training",
        "updated_at": utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "dataloader_length": dataloader_length,
        "eval_dataloader_length": eval_dataloader_length,
        "upstream_trainer_uses_eval_manifest": True,
        "gradient_accumulation_steps": (
            None
            if resolved_progress is None
            else resolved_progress.get("gradient_accumulation_steps")
        ),
        "step_semantics": step_semantics_payload(
            None
            if resolved_progress is None
            else optional_mapping_int(resolved_progress, "gradient_accumulation_steps")
        ),
        "current_phase": "failed",
        "current_epoch": (
            None if resolved_progress is None else resolved_progress.get("current_epoch")
        ),
        "current_step": None
        if resolved_progress is None
        else resolved_progress.get("current_step"),
        "current_optimizer_step": (
            None if resolved_progress is None else resolved_progress.get("current_optimizer_step")
        ),
        "current_train_iteration": (
            None if resolved_progress is None else resolved_progress.get("current_train_iteration")
        ),
        "latest_loss": None if resolved_progress is None else resolved_progress.get("latest_loss"),
        "smoothed_loss": (
            None if resolved_progress is None else resolved_progress.get("smoothed_loss")
        ),
        "latest_eval_loss": (
            None if resolved_progress is None else resolved_progress.get("latest_eval_loss")
        ),
        "best_eval_loss": (
            None if resolved_progress is None else resolved_progress.get("best_eval_loss")
        ),
        "best_eval_step": (
            None if resolved_progress is None else resolved_progress.get("best_eval_step")
        ),
        "eval_runs_completed": (
            None if resolved_progress is None else resolved_progress.get("eval_runs_completed")
        ),
        "latest_durable_checkpoint_path": (
            None
            if resolved_progress is None
            else resolved_progress.get("latest_durable_checkpoint_path")
        ),
        "latest_durable_checkpoint_step": (
            None
            if resolved_progress is None
            else resolved_progress.get("latest_durable_checkpoint_step")
        ),
        "latest_durable_checkpoint_saved_at": (
            None
            if resolved_progress is None
            else resolved_progress.get("latest_durable_checkpoint_saved_at")
        ),
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "throughput_profile": throughput_profile,
        "diagnostic": diagnostic,
        "finite_loss_guard": finite_loss_guard_payload,
        "optimizer_boundary_guard": optimizer_boundary_guard_payload,
        "talker_runtime": None if talker_runtime is None else dict(talker_runtime),
        "acceptance_measurement_valid": acceptance_measurement_valid,
        "tracking": tracking,
        "phase_history": [] if phase_history is None else phase_history,
        "error": f"{type(exc).__name__}: {exc}",
    }
