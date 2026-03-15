"""Path and container-path helpers for detached Qwen training runtime.

Purpose:
    Own run-root, manifest, tracker, profiler, and container-path resolution
    for detached training and diagnostic launches.

Relationships:
    - Used by detached command builders and launch services.
    - Shared across schedule, diagnostic, and normal training launch flows.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings

CONTAINER_BUILD_ROOT = Path("/app/build")


def run_root_for_launch(settings: TrainingSettings, *, launch_id: str) -> Path:
    """Return the canonical host-side run root for one training launch."""
    return settings.runs_root / launch_id


def containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def train_manifest_path(settings: TrainingSettings) -> Path:
    """Return the selected prepared-manifest path for training."""
    return (
        settings.pilot_bundle_root
        / "manifests"
        / f"{settings.train_manifest_family}.prepared.jsonl"
    )


def eval_manifest_path(settings: TrainingSettings) -> Path:
    """Return the selected held-out eval-manifest path for training."""
    return (
        settings.pilot_bundle_root / "manifests" / f"{settings.eval_manifest_family}.prepared.jsonl"
    )


def tracker_root(run_root: Path) -> Path:
    """Return the tracker root for one training run root."""
    return run_root / "trackers"


def mlflow_tracking_uri(run_root: Path) -> str:
    """Return the MLflow SQLite tracking URI for one training run root."""
    return f"sqlite:///{(tracker_root(run_root) / 'mlflow' / 'mlflow.db').as_posix()}"


def mlflow_artifact_root(run_root: Path) -> Path:
    """Return the MLflow artifact root for one training run root."""
    return tracker_root(run_root) / "mlflow" / "artifacts"


def tensorboard_logging_dir(run_root: Path) -> Path:
    """Return the TensorBoard logging directory for one training run root."""
    return tracker_root(run_root) / "tensorboard"


def pytorch_profiling_dir(run_root: Path) -> Path:
    """Return the PyTorch profiler trace directory for one training run root."""
    return run_root / "profiling" / "pytorch"


def rocm_profiling_dir(run_root: Path) -> Path:
    """Return the ROCm profiler trace directory for one training run root."""
    return run_root / "profiling" / "rocm"
