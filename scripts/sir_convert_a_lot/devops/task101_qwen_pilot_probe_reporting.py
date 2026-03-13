"""Report and status payload helpers for the Task 101 in-container probe.

Purpose:
    Keep the inner Task 101 probe focused on running training while this module
    owns deterministic JSON artifact writing plus the status/report payload
    assembly shared across success and failure paths.

Relationships:
    - Imported by `task101_qwen_pilot_probe.py`.
    - Mirrors the status/report artifact contract consumed by the detached
      Task 101 runtime inspection path.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz import TrainingSummary


@dataclass(frozen=True)
class Task101PilotProbeReport:
    """Machine-readable report emitted by the detached Task 101 probe."""

    generated_at: str
    model_id: str
    train_jsonl: str
    eval_jsonl: str
    output_dir: str
    train_row_count: int
    eval_row_count: int
    upstream_trainer_uses_eval_manifest: bool
    torch_version: str
    torchaudio_version: str | None
    torch_cuda_available: bool
    torch_cuda_device_count: int
    torch_hip_version: str | None
    flash_attn_importable: bool
    flash_attn_version: str | None
    tracking: dict[str, object] | None
    training_summary: dict[str, object]


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_version(distribution_name: str) -> str | None:
    """Return one installed package version, or `None` when it is absent."""
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _count_jsonl_rows(path: Path) -> int:
    """Count rows in one deterministic JSONL manifest."""
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def _running_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    checkpoint_interval_steps: int,
    durable_checkpoint_retention: int,
    durable_checkpoint_min_free_bytes: int,
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
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_path = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_path")
    )
    latest_durable_checkpoint_step = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_step")
    )
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    return {
        "status": "running",
        "stage": "training",
        "updated_at": _utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "upstream_trainer_uses_eval_manifest": False,
        "checkpoint_interval_steps": checkpoint_interval_steps,
        "durable_checkpoint_retention": durable_checkpoint_retention,
        "durable_checkpoint_min_free_bytes": durable_checkpoint_min_free_bytes,
        "resumed_from_checkpoint_path": (
            None if resume_from_checkpoint is None else resume_from_checkpoint.as_posix()
        ),
        "current_phase": current_phase,
        "current_epoch": current_epoch,
        "current_step": current_step,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "latest_durable_checkpoint_path": latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "tracking_plan": tracking_plan,
        "tracking": tracking,
        "phase_history": [] if phase_history is None else phase_history,
    }


def _completed_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    training_summary: TrainingSummary,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build the terminal success payload for the probe status artifact."""
    current_phase = "signal-stop" if training_summary.stopped_early else "completed"
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    return {
        "status": "stopped" if training_summary.stopped_early else "completed",
        "stage": "training",
        "updated_at": _utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "upstream_trainer_uses_eval_manifest": False,
        "current_phase": current_phase,
        "current_epoch": current_epoch,
        "current_step": current_step,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "optimizer_steps_completed": training_summary.optimizer_steps_completed,
        "checkpoint_interval_steps": training_summary.checkpoint_interval_steps,
        "durable_checkpoint_retention": training_summary.durable_checkpoint_retention,
        "durable_checkpoint_min_free_bytes": training_summary.durable_checkpoint_min_free_bytes,
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


def _failed_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    exc: Exception,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
    tracking: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the terminal failure payload for the probe status artifact."""
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_path = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_path")
    )
    latest_durable_checkpoint_step = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_step")
    )
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    return {
        "status": "failed",
        "stage": "training",
        "updated_at": _utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "upstream_trainer_uses_eval_manifest": False,
        "current_phase": "failed",
        "current_epoch": current_epoch,
        "current_step": current_step,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "latest_durable_checkpoint_path": latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "tracking": tracking,
        "phase_history": [] if phase_history is None else phase_history,
        "error": f"{type(exc).__name__}: {exc}",
    }


def _build_probe_report(
    *,
    model_id: str,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    training_summary: TrainingSummary,
) -> Task101PilotProbeReport:
    """Build the machine-readable probe report from one completed training run."""
    return Task101PilotProbeReport(
        generated_at=_utc_now_iso(),
        model_id=model_id,
        train_jsonl=train_jsonl.as_posix(),
        eval_jsonl=eval_jsonl.as_posix(),
        output_dir=output_dir.as_posix(),
        train_row_count=train_row_count,
        eval_row_count=eval_row_count,
        upstream_trainer_uses_eval_manifest=False,
        torch_version=str(torch.__version__),
        torchaudio_version=_package_version("torchaudio"),
        torch_cuda_available=True,
        torch_cuda_device_count=int(torch.cuda.device_count()),
        torch_hip_version=str(torch.version.hip),
        flash_attn_importable=importlib.util.find_spec("flash_attn") is not None,
        flash_attn_version=_package_version("flash-attn"),
        tracking=None if training_summary.tracking is None else asdict(training_summary.tracking),
        training_summary=asdict(training_summary),
    )


def _merge_launch_tracking_metadata(
    launch_metadata_path: Path,
    *,
    tracking: dict[str, object],
) -> None:
    """Merge live tracker metadata into the detached launch artifact."""
    if not launch_metadata_path.exists():
        return
    payload = json.loads(launch_metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Task 101 launch metadata was malformed while merging tracking data.")
    payload["tracking"] = tracking
    _write_json(launch_metadata_path, payload)
