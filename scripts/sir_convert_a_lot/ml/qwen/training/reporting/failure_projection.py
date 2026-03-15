"""Failure-projection helpers for Qwen training reporting.

Purpose:
    Normalize terminal progress, extract typed failure fields, and keep failure
    payload interpretation separate from status/report assembly.

Relationships:
    - Used by status payload builders and status writers.
    - Consumes optimizer-boundary and finite-loss exception contracts.
"""

from __future__ import annotations

from collections.abc import Mapping

from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import NonFiniteLossError
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    OptimizerBoundaryCorruptionError,
)


def optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return one optional integer payload field."""
    value = payload.get(key)
    if value is None or not isinstance(value, int):
        return None
    return value


def required_progress_int(payload: Mapping[str, object | None], key: str) -> int:
    """Return one required integer field from resolved terminal progress."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Reporter encountered malformed live progress `{key}`.")
    return value


def resolve_terminal_progress(
    *,
    live_progress: dict[str, object] | None,
) -> dict[str, object | None] | None:
    """Return one normalized terminal-progress view from the latest heartbeat."""
    if live_progress is None:
        return None
    current_step = optional_int(live_progress, "current_step")
    current_optimizer_step = optional_int(live_progress, "current_optimizer_step")
    resolved_optimizer_step = (
        current_step if current_optimizer_step is None else current_optimizer_step
    )
    current_train_iteration = optional_int(live_progress, "current_train_iteration")
    return {
        "current_epoch": optional_int(live_progress, "current_epoch"),
        "current_step": current_step,
        "current_optimizer_step": resolved_optimizer_step,
        "current_train_iteration": (
            resolved_optimizer_step if current_train_iteration is None else current_train_iteration
        ),
        "gradient_accumulation_steps": optional_int(live_progress, "gradient_accumulation_steps"),
        "latest_loss": live_progress.get("latest_loss"),
        "smoothed_loss": live_progress.get("smoothed_loss"),
        "latest_eval_loss": live_progress.get("latest_eval_loss"),
        "best_eval_loss": live_progress.get("best_eval_loss"),
        "best_eval_step": optional_int(live_progress, "best_eval_step"),
        "eval_runs_completed": optional_int(live_progress, "eval_runs_completed"),
        "latest_durable_checkpoint_path": live_progress.get("latest_durable_checkpoint_path"),
        "latest_durable_checkpoint_step": live_progress.get("latest_durable_checkpoint_step"),
        "latest_durable_checkpoint_saved_at": live_progress.get(
            "latest_durable_checkpoint_saved_at"
        ),
    }


def resolve_failed_progress(
    *,
    live_progress: dict[str, object] | None,
    exc: BaseException,
) -> dict[str, object | None] | None:
    """Return terminal progress with exception-derived counters overriding stale heartbeat data."""
    resolved_progress = resolve_terminal_progress(live_progress=live_progress)
    if not isinstance(exc, NonFiniteLossError | OptimizerBoundaryCorruptionError):
        return resolved_progress
    if resolved_progress is None:
        gradient_accumulation_steps = None
        smoothed_loss = None
        latest_eval_loss = None
        best_eval_loss = None
        best_eval_step = None
        eval_runs_completed = None
        latest_durable_checkpoint_path = None
        latest_durable_checkpoint_step = None
        latest_durable_checkpoint_saved_at = None
    else:
        gradient_accumulation_steps = optional_mapping_int(
            resolved_progress,
            "gradient_accumulation_steps",
        )
        smoothed_loss = optional_mapping_float(resolved_progress, "smoothed_loss")
        latest_eval_loss = optional_mapping_float(resolved_progress, "latest_eval_loss")
        best_eval_loss = optional_mapping_float(resolved_progress, "best_eval_loss")
        best_eval_step = optional_mapping_int(resolved_progress, "best_eval_step")
        eval_runs_completed = optional_mapping_int(resolved_progress, "eval_runs_completed")
        latest_durable_checkpoint_path = optional_mapping_string(
            resolved_progress,
            "latest_durable_checkpoint_path",
        )
        latest_durable_checkpoint_step = optional_mapping_int(
            resolved_progress,
            "latest_durable_checkpoint_step",
        )
        latest_durable_checkpoint_saved_at = optional_mapping_string(
            resolved_progress,
            "latest_durable_checkpoint_saved_at",
        )
    return {
        "current_epoch": exc.current_epoch,
        "current_step": exc.optimizer_step,
        "current_optimizer_step": exc.optimizer_step,
        "current_train_iteration": exc.current_train_iteration,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "latest_loss": exc.loss_value,
        "smoothed_loss": smoothed_loss,
        "latest_eval_loss": latest_eval_loss,
        "best_eval_loss": best_eval_loss,
        "best_eval_step": best_eval_step,
        "eval_runs_completed": eval_runs_completed,
        "latest_durable_checkpoint_path": latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
    }


def required_string(payload: Mapping[str, object], key: str) -> str:
    """Return one required string field from a mapping."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Reporter encountered malformed required string `{key}`.")
    return value


def optional_mapping_int(payload: Mapping[str, object], key: str) -> int | None:
    """Return one optional integer field from a generic mapping."""
    value = payload.get(key)
    if value is None or not isinstance(value, int):
        return None
    return value


def optional_mapping_float(payload: Mapping[str, object], key: str) -> float | None:
    """Return one optional float field from a generic mapping."""
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def optional_mapping_string(payload: Mapping[str, object], key: str) -> str | None:
    """Return one optional string field from a generic mapping."""
    value = payload.get(key)
    if value is None or not isinstance(value, str):
        return None
    return value


def optional_mapping_bool(payload: Mapping[str, object], key: str) -> bool | None:
    """Return one optional boolean field from a generic mapping."""
    value = payload.get(key)
    if value is None or not isinstance(value, bool):
        return None
    return value


def optional_mapping_dict(payload: Mapping[str, object], key: str) -> dict[str, object] | None:
    """Return one optional shallow dict[str, object] field from a generic mapping."""
    value = payload.get(key)
    if not isinstance(value, dict):
        return None
    return {str(mapping_key): mapping_value for mapping_key, mapping_value in value.items()}
