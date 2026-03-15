"""Tracking helpers for the patched Qwen Swedish fine-tuning trainer.

Purpose:
    Keep MLflow and TensorBoard tracker initialization, metadata capture, and
    per-step scalar logging out of `sft_12hz.py` so the trainer entrypoint can
    stay focused on model orchestration and checkpoint control.

Relationships:
    - Imported by `sft_12hz.py` inside the same patch directory.
    - Uses Accelerate tracker integration as the canonical logging surface.
    - Produces machine-readable tracker metadata that the detached Task 101
      probe can mirror into status and report artifacts.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from accelerate import Accelerator

DEFAULT_TRACKER_BACKENDS = ("mlflow", "tensorboard")
DEFAULT_TRACKER_PROJECT_NAME = "task101-qwen-pilot"
DEFAULT_MLFLOW_EXPERIMENT_NAME = "task101-qwen-pilot"
DEFAULT_MLFLOW_SYSTEM_METRICS_INTERVAL_SECONDS = 10


@dataclass(frozen=True)
class TrainingTrackerConfig:
    """Normalized tracker configuration for one Qwen training run."""

    project_name: str
    run_name: str
    tracker_backends: tuple[str, ...]
    mlflow_experiment_name: str
    mlflow_tracking_uri: str
    mlflow_artifact_root: str
    mlflow_system_metrics_interval_seconds: int
    tensorboard_logging_dir: str


@dataclass(frozen=True)
class TrainingTrackerSummary:
    """Machine-readable tracker metadata for one bounded training run."""

    tracker_backends: list[str]
    project_name: str
    run_name: str
    mlflow_experiment_name: str
    mlflow_tracking_uri: str
    mlflow_artifact_root: str
    mlflow_experiment_id: str | None
    mlflow_run_id: str | None
    mlflow_artifact_uri: str | None
    mlflow_system_metrics_enabled: bool
    mlflow_system_metrics_interval_seconds: int
    tensorboard_logging_dir: str
    tensorboard_run_dir: str
    tensorboard_event_files: list[str]


def build_training_tracker_config(
    *,
    output_model_path: Path,
    tracker_run_name: str | None,
    tracker_project_name: str | None,
    mlflow_experiment_name: str | None,
    mlflow_tracking_uri: str | None,
    mlflow_artifact_root: str | None,
    tensorboard_logging_dir: str | None,
) -> TrainingTrackerConfig:
    """Build the canonical tracker configuration for one training run."""
    run_root = output_model_path.resolve().parent
    tracker_root = run_root / "trackers"
    resolved_run_name = tracker_run_name or run_root.name
    resolved_project_name = tracker_project_name or DEFAULT_TRACKER_PROJECT_NAME
    resolved_mlflow_root = tracker_root / "mlflow"
    resolved_tensorboard_root = tracker_root / "tensorboard"
    resolved_tracking_uri = (
        mlflow_tracking_uri
        if mlflow_tracking_uri is not None
        else f"sqlite:///{(resolved_mlflow_root / 'mlflow.db').as_posix()}"
    )
    resolved_artifact_root = (
        mlflow_artifact_root
        if mlflow_artifact_root is not None
        else (resolved_mlflow_root / "artifacts").as_posix()
    )
    resolved_tensorboard_logging_dir = (
        tensorboard_logging_dir
        if tensorboard_logging_dir is not None
        else resolved_tensorboard_root.as_posix()
    )
    return TrainingTrackerConfig(
        project_name=resolved_project_name,
        run_name=resolved_run_name,
        tracker_backends=DEFAULT_TRACKER_BACKENDS,
        mlflow_experiment_name=(mlflow_experiment_name or DEFAULT_MLFLOW_EXPERIMENT_NAME),
        mlflow_tracking_uri=resolved_tracking_uri,
        mlflow_artifact_root=resolved_artifact_root,
        mlflow_system_metrics_interval_seconds=DEFAULT_MLFLOW_SYSTEM_METRICS_INTERVAL_SECONDS,
        tensorboard_logging_dir=resolved_tensorboard_logging_dir,
    )


@contextmanager
def _temporary_env_var(name: str, value: str) -> Iterator[None]:
    """Temporarily set one environment variable while trackers initialize."""
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            del os.environ[name]
        else:
            os.environ[name] = previous


def _ensure_tracker_directories(tracker_config: TrainingTrackerConfig) -> None:
    """Create the local tracker directories required for one run."""
    Path(tracker_config.mlflow_artifact_root).mkdir(parents=True, exist_ok=True)
    Path(tracker_config.tensorboard_logging_dir).mkdir(parents=True, exist_ok=True)
    tracking_uri = tracker_config.mlflow_tracking_uri.removeprefix("sqlite:///")
    Path(tracking_uri).parent.mkdir(parents=True, exist_ok=True)


def _enable_mlflow_system_metrics(
    *,
    sampling_interval_seconds: int,
) -> bool:
    """Enable MLflow system metrics when the installed runtime supports them."""
    import mlflow

    try:
        mlflow.enable_system_metrics_logging()
        mlflow.set_system_metrics_sampling_interval(sampling_interval_seconds)
        mlflow.set_system_metrics_samples_before_logging(1)
    except Exception:
        return False
    return True


def initialize_training_trackers(
    accelerator: Accelerator,
    *,
    tracker_config: TrainingTrackerConfig,
    config: dict[str, bool | float | int | str | None],
    tags: dict[str, str],
) -> TrainingTrackerSummary:
    """Initialize Accelerate trackers and return the active tracker metadata."""
    import mlflow

    _ensure_tracker_directories(tracker_config)
    mlflow.set_tracking_uri(tracker_config.mlflow_tracking_uri)
    system_metrics_enabled = _enable_mlflow_system_metrics(
        sampling_interval_seconds=tracker_config.mlflow_system_metrics_interval_seconds
    )
    with _temporary_env_var("MLFLOW_EXPERIMENT_NAME", tracker_config.mlflow_experiment_name):
        accelerator.init_trackers(
            tracker_config.project_name,
            config=config,
            init_kwargs={
                "mlflow": {
                    "logging_dir": tracker_config.mlflow_artifact_root,
                    "run_name": tracker_config.run_name,
                    "description": (
                        "Detached Task 101 Swedish Qwen fine-tune tracked via Accelerate."
                    ),
                    "tags": tags,
                },
            },
        )
    return refresh_training_tracker_summary(
        accelerator,
        tracker_config=tracker_config,
        system_metrics_enabled=system_metrics_enabled,
    )


def refresh_training_tracker_summary(
    accelerator: Accelerator,
    *,
    tracker_config: TrainingTrackerConfig,
    system_metrics_enabled: bool,
) -> TrainingTrackerSummary:
    """Capture the current tracker metadata visible to the training process."""
    mlflow_run_id: str | None = None
    mlflow_experiment_id: str | None = None
    mlflow_artifact_uri: str | None = None
    if accelerator.is_main_process:
        active_run = accelerator.get_tracker("mlflow", unwrap=True)
        run_info = getattr(active_run, "info", None)
        if run_info is not None:
            mlflow_run_id = getattr(run_info, "run_id", None)
            mlflow_experiment_id = getattr(run_info, "experiment_id", None)
            mlflow_artifact_uri = getattr(run_info, "artifact_uri", None)
    tensorboard_run_dir = Path(tracker_config.tensorboard_logging_dir) / tracker_config.project_name
    event_files = sorted(
        path.as_posix()
        for path in tensorboard_run_dir.glob("events.out.tfevents.*")
        if path.is_file()
    )
    return TrainingTrackerSummary(
        tracker_backends=list(tracker_config.tracker_backends),
        project_name=tracker_config.project_name,
        run_name=tracker_config.run_name,
        mlflow_experiment_name=tracker_config.mlflow_experiment_name,
        mlflow_tracking_uri=tracker_config.mlflow_tracking_uri,
        mlflow_artifact_root=tracker_config.mlflow_artifact_root,
        mlflow_experiment_id=mlflow_experiment_id,
        mlflow_run_id=mlflow_run_id,
        mlflow_artifact_uri=mlflow_artifact_uri,
        mlflow_system_metrics_enabled=system_metrics_enabled,
        mlflow_system_metrics_interval_seconds=(
            tracker_config.mlflow_system_metrics_interval_seconds
        ),
        tensorboard_logging_dir=tracker_config.tensorboard_logging_dir,
        tensorboard_run_dir=tensorboard_run_dir.as_posix(),
        tensorboard_event_files=event_files,
    )


def update_smoothed_loss(
    previous_value: float | None,
    current_value: float,
    *,
    alpha: float = 0.1,
) -> float:
    """Update one exponential moving average of training loss."""
    if previous_value is None:
        return current_value
    return (alpha * current_value) + ((1.0 - alpha) * previous_value)


def log_training_metrics(
    accelerator: Accelerator,
    *,
    raw_loss: float,
    smoothed_loss: float,
    current_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    checkpoint_interval_steps: int,
    ref_mel_cache_metrics: dict[str, bool | float | int | None] | None = None,
) -> None:
    """Log one flat scalar payload to all configured trackers."""
    payload: dict[str, bool | float | int | None] = {
        "train/loss": raw_loss,
        "train/loss_ema": smoothed_loss,
        "train/current_step": current_optimizer_step,
        "train/current_optimizer_step": current_optimizer_step,
        "train/current_train_iteration": current_train_iteration,
        "train/current_epoch": current_epoch,
        "train/checkpoint_interval_steps": checkpoint_interval_steps,
    }
    if ref_mel_cache_metrics is not None:
        payload["train/ref_mel_cache_enabled"] = ref_mel_cache_metrics.get("enabled")
        payload["train/ref_mel_cache_max_items"] = ref_mel_cache_metrics.get("max_items")
        payload["train/ref_mel_cache_hits"] = ref_mel_cache_metrics.get("cache_hits")
        payload["train/ref_mel_cache_misses"] = ref_mel_cache_metrics.get("cache_misses")
        payload["train/ref_mel_cache_size"] = ref_mel_cache_metrics.get("cache_size")
        payload["train/ref_mel_cache_hit_rate"] = ref_mel_cache_metrics.get("cache_hit_rate")
    accelerator.log(payload, step=current_optimizer_step)


def log_eval_metrics(
    accelerator: Accelerator,
    *,
    eval_loss: float,
    best_eval_loss: float,
    best_eval_step: int,
    current_epoch: int,
    current_optimizer_step: int,
    current_train_iteration: int,
    eval_runs_completed: int,
) -> None:
    """Log one held-out eval payload to all configured trackers."""
    accelerator.log(
        {
            "eval/loss": eval_loss,
            "eval/best_loss": best_eval_loss,
            "eval/best_step": best_eval_step,
            "eval/current_step": current_optimizer_step,
            "eval/current_optimizer_step": current_optimizer_step,
            "eval/current_train_iteration": current_train_iteration,
            "eval/current_epoch": current_epoch,
            "eval/runs_completed": eval_runs_completed,
        },
        step=current_optimizer_step,
    )
