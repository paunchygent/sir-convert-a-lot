"""Durable checkpoint helpers for the patched Qwen `sft_12hz.py` trainer.

Purpose:
    Hold the trainer-state metadata model, path conventions, free-space guard,
    validation, pruning, and resumable-save flow used by the Swedish Qwen
    fine-tuning patch set.

Relationships:
    - Imported by `sft_12hz.py`, which remains the training orchestration
      entrypoint.
    - Shares the durable checkpoint JSON/pointer contract exercised by
      `tests/sir_convert_a_lot/test_qwen_training_resume.py`.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

DEFAULT_DURABLE_CHECKPOINT_RETENTION = 2
DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES = 16 * 1024**3
# Conservative first-save fallback based on the measured Hemma trainer-state size.
DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES = 12 * 1024**3


@dataclass(frozen=True)
class DurableCheckpointMetadata:
    """Resume cursor metadata for one durable trainer-state checkpoint."""

    checkpoint_path: str
    saved_at: str
    reason: str
    optimizer_steps_completed: int
    epoch: int
    next_epoch: int
    next_step_in_epoch: int


class CheckpointAccelerator(Protocol):
    """Minimal accelerator protocol required for durable checkpoint persistence."""

    is_main_process: bool

    def wait_for_everyone(self) -> None:
        """Synchronize checkpointing across processes."""

    def save_state(self, output_dir: str | None = None, safe_serialization: bool = True) -> None:
        """Persist full trainer state to the selected checkpoint directory."""


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _latest_checkpoint_pointer_path(output_model_path: Path) -> Path:
    """Return the run-root pointer that tracks the latest durable checkpoint."""
    return output_model_path.parent / "latest_checkpoint.json"


def _durable_checkpoint_metadata_path(checkpoint_dir: Path) -> Path:
    """Return the metadata path stored alongside one durable checkpoint."""
    return checkpoint_dir / "training_state.json"


def _durable_checkpoint_dir(output_model_path: Path, optimizer_steps_completed: int) -> Path:
    """Return the durable checkpoint directory for one optimizer step."""
    return output_model_path / f"state-step-{optimizer_steps_completed:08d}"


def _durable_checkpoint_staging_dir(
    output_model_path: Path,
    optimizer_steps_completed: int,
) -> Path:
    """Return the staging directory used while one durable checkpoint is being written."""
    final_dir = _durable_checkpoint_dir(output_model_path, optimizer_steps_completed)
    return output_model_path / f".{final_dir.name}.incomplete"


def _durable_checkpoint_step(checkpoint_dir: Path) -> int:
    """Extract the durable checkpoint step from one checkpoint directory name."""
    prefix = "state-step-"
    if not checkpoint_dir.name.startswith(prefix):
        raise ValueError(f"Expected durable checkpoint directory name to start with `{prefix}`.")
    return int(checkpoint_dir.name[len(prefix) :])


def _current_durable_checkpoint_dirs(output_model_path: Path) -> list[Path]:
    """Return durable checkpoint directories sorted by optimizer step."""
    if not output_model_path.exists():
        return []
    checkpoint_dirs = [
        path
        for path in output_model_path.iterdir()
        if path.is_dir() and path.name.startswith("state-step-")
    ]
    return sorted(checkpoint_dirs, key=_durable_checkpoint_step)


def _current_durable_checkpoint_paths(output_model_path: Path) -> list[str]:
    """Return the retained durable checkpoint paths currently present on disk."""
    return [path.as_posix() for path in _current_durable_checkpoint_dirs(output_model_path)]


def _directory_size_bytes(path: Path) -> int:
    """Return the total size of one directory tree in bytes."""
    total_bytes = 0
    for child in path.rglob("*"):
        if child.is_file():
            total_bytes += child.stat().st_size
    return total_bytes


def _durable_checkpoint_required_free_bytes(
    output_model_path: Path,
    *,
    durable_checkpoint_min_free_bytes: int,
) -> int:
    """Estimate the minimum free space required before one new durable save starts."""
    existing_sizes = [
        _directory_size_bytes(checkpoint_dir)
        for checkpoint_dir in _current_durable_checkpoint_dirs(output_model_path)
    ]
    estimated_checkpoint_bytes = max(
        existing_sizes,
        default=DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES,
    )
    return estimated_checkpoint_bytes + durable_checkpoint_min_free_bytes


def _ensure_free_space_for_durable_checkpoint(
    output_model_path: Path,
    *,
    durable_checkpoint_min_free_bytes: int,
) -> None:
    """Fail closed when the checkpoint filesystem lacks safe write headroom."""
    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(output_model_path.parent).free
    required_free_bytes = _durable_checkpoint_required_free_bytes(
        output_model_path,
        durable_checkpoint_min_free_bytes=durable_checkpoint_min_free_bytes,
    )
    if free_bytes < required_free_bytes:
        raise RuntimeError(
            "Refusing durable checkpoint save because the target filesystem does not have "
            "enough free space. "
            f"free_bytes={free_bytes} required_free_bytes={required_free_bytes}"
        )


def _validate_saved_durable_checkpoint(
    checkpoint_dir: Path,
    *,
    expected_metadata: DurableCheckpointMetadata,
) -> None:
    """Validate one newly written durable checkpoint before pointer updates or pruning."""
    materialized_entries = [
        path for path in checkpoint_dir.iterdir() if path.name != "training_state.json"
    ]
    if not materialized_entries:
        raise RuntimeError(
            f"Durable checkpoint `{checkpoint_dir.as_posix()}` did not persist trainer state files."
        )
    actual_metadata = _load_durable_checkpoint_metadata(checkpoint_dir)
    if actual_metadata != expected_metadata:
        raise RuntimeError(
            f"Durable checkpoint `{checkpoint_dir.as_posix()}` metadata did not round-trip."
        )


def _remove_path_if_exists(path: Path) -> None:
    """Delete one file or directory tree if it already exists."""
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _durable_checkpoint_dir_is_valid(checkpoint_dir: Path) -> bool:
    """Return whether an existing durable checkpoint directory is safe to keep."""
    try:
        metadata = _load_durable_checkpoint_metadata(checkpoint_dir)
        _validate_saved_durable_checkpoint(checkpoint_dir, expected_metadata=metadata)
    except Exception:
        return False
    return True


def _prepare_durable_checkpoint_targets(
    *,
    checkpoint_dir: Path,
    staging_dir: Path,
) -> None:
    """Clean stale invalid checkpoint paths while refusing to overwrite a valid save."""
    _remove_path_if_exists(staging_dir)
    if not checkpoint_dir.exists():
        return
    if _durable_checkpoint_dir_is_valid(checkpoint_dir):
        raise RuntimeError(
            f"Durable checkpoint directory `{checkpoint_dir.as_posix()}` already exists."
        )
    _remove_path_if_exists(checkpoint_dir)


def _prune_durable_checkpoints(
    output_model_path: Path,
    *,
    retention: int,
) -> None:
    """Delete durable checkpoints older than the configured retained window."""
    checkpoint_dirs = _current_durable_checkpoint_dirs(output_model_path)
    delete_count = len(checkpoint_dirs) - retention
    if delete_count <= 0:
        return
    for checkpoint_dir in checkpoint_dirs[:delete_count]:
        shutil.rmtree(checkpoint_dir)


def _checkpoint_resume_cursor(
    *,
    epoch: int,
    step_in_epoch: int,
    dataloader_length: int,
) -> tuple[int, int]:
    """Return the next epoch and intra-epoch step after one completed batch."""
    next_step_in_epoch = step_in_epoch + 1
    next_epoch = epoch
    if next_step_in_epoch >= dataloader_length:
        next_epoch = epoch + 1
        next_step_in_epoch = 0
    return next_epoch, next_step_in_epoch


def _save_durable_checkpoint(
    *,
    accelerator: CheckpointAccelerator,
    output_model_path: Path,
    optimizer_steps_completed: int,
    epoch: int,
    step_in_epoch: int,
    dataloader_length: int,
    reason: str,
    durable_checkpoint_retention: int,
    durable_checkpoint_min_free_bytes: int,
) -> DurableCheckpointMetadata:
    """Persist one resumable trainer-state checkpoint and update the latest pointer."""
    checkpoint_dir = _durable_checkpoint_dir(output_model_path, optimizer_steps_completed)
    staging_dir = _durable_checkpoint_staging_dir(output_model_path, optimizer_steps_completed)
    _ensure_free_space_for_durable_checkpoint(
        output_model_path,
        durable_checkpoint_min_free_bytes=durable_checkpoint_min_free_bytes,
    )
    _prepare_durable_checkpoint_targets(
        checkpoint_dir=checkpoint_dir,
        staging_dir=staging_dir,
    )
    staging_dir.mkdir(parents=True, exist_ok=True)
    accelerator.wait_for_everyone()
    try:
        accelerator.save_state(staging_dir.as_posix())
        next_epoch, next_step_in_epoch = _checkpoint_resume_cursor(
            epoch=epoch,
            step_in_epoch=step_in_epoch,
            dataloader_length=dataloader_length,
        )
        metadata = DurableCheckpointMetadata(
            checkpoint_path=checkpoint_dir.as_posix(),
            saved_at=_utc_now_iso(),
            reason=reason,
            optimizer_steps_completed=optimizer_steps_completed,
            epoch=epoch,
            next_epoch=next_epoch,
            next_step_in_epoch=next_step_in_epoch,
        )
        if accelerator.is_main_process:
            _write_json(_durable_checkpoint_metadata_path(staging_dir), asdict(metadata))
            _validate_saved_durable_checkpoint(staging_dir, expected_metadata=metadata)
            staging_dir.replace(checkpoint_dir)
            _write_json(_latest_checkpoint_pointer_path(output_model_path), asdict(metadata))
            _prune_durable_checkpoints(
                output_model_path,
                retention=durable_checkpoint_retention,
            )
    except Exception:
        if accelerator.is_main_process:
            _remove_path_if_exists(staging_dir)
        raise
    accelerator.wait_for_everyone()
    return metadata


def _load_durable_checkpoint_metadata(checkpoint_path: Path) -> DurableCheckpointMetadata:
    """Load durable checkpoint metadata required for exact resume."""
    payload = json.loads(
        _durable_checkpoint_metadata_path(checkpoint_path).read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise ValueError("Expected durable checkpoint metadata to be a JSON object.")
    return DurableCheckpointMetadata(
        checkpoint_path=str(payload["checkpoint_path"]),
        saved_at=str(payload["saved_at"]),
        reason=str(payload["reason"]),
        optimizer_steps_completed=int(payload["optimizer_steps_completed"]),
        epoch=int(payload["epoch"]),
        next_epoch=int(payload["next_epoch"]),
        next_step_in_epoch=int(payload["next_step_in_epoch"]),
    )


def _checkpoint_advanced_since_latest_save(
    latest_durable_checkpoint: DurableCheckpointMetadata | None,
    *,
    optimizer_steps_completed: int,
) -> bool:
    """Return whether training advanced beyond the latest durable checkpoint."""
    if optimizer_steps_completed <= 0:
        return False
    if latest_durable_checkpoint is None:
        return True
    return latest_durable_checkpoint.optimizer_steps_completed != optimizer_steps_completed
