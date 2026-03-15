"""Tests for durable checkpoint save, prune, load, and space-guard lifecycle.

Purpose:
    Validate the durable checkpoint metadata, retention pruning, pointer
    consistency, retry semantics, free-space guard, and metadata rehydration
    contract introduced for T115 without requiring a real GPU training run.

Relationships:
    - Exercises helper functions in
      `scripts/devops/qwen_finetuning_patches/sft_12hz_checkpointing.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.sir_convert_a_lot.ml.qwen.training.test_support import (
    DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES,
    SFT_12HZ_CHECKPOINTING,
    _checkpoint_advanced_since_latest_save,
    _current_durable_checkpoint_paths,
    _durable_checkpoint_staging_dir,
    _FakeAccelerator,
    _load_durable_checkpoint_metadata,
    _save_durable_checkpoint,
)


def test_save_durable_checkpoint_writes_metadata_and_latest_pointer(tmp_path: Path) -> None:
    """Saving one durable checkpoint should persist metadata plus latest pointer."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"

    metadata = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=8,
        epoch=0,
        step_in_epoch=7,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    checkpoint_dir = output_model_path / "state-step-00000008"
    assert metadata.checkpoint_path == checkpoint_dir.as_posix()
    assert checkpoint_dir.exists() is True
    assert (checkpoint_dir / "accelerate_state_marker.txt").exists() is True
    saved_metadata = json.loads(
        (checkpoint_dir / "training_state.json").read_text(encoding="utf-8")
    )
    latest_pointer = json.loads(
        (output_model_path.parent / "latest_checkpoint.json").read_text(encoding="utf-8")
    )
    assert saved_metadata["optimizer_steps_completed"] == 8
    assert saved_metadata["next_epoch"] == 0
    assert saved_metadata["next_step_in_epoch"] == 8
    assert latest_pointer["checkpoint_path"] == checkpoint_dir.as_posix()
    assert accelerator.saved_paths == [
        _durable_checkpoint_staging_dir(output_model_path, 8).as_posix()
    ]


def test_save_durable_checkpoint_prunes_older_paths_after_validation(tmp_path: Path) -> None:
    """Retention should keep the newest durable checkpoints only after a valid new save."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"
    epoch_checkpoint = output_model_path / "checkpoint-epoch-0"
    final_checkpoint = output_model_path / "checkpoint-final"
    epoch_checkpoint.mkdir(parents=True, exist_ok=True)
    final_checkpoint.mkdir(parents=True, exist_ok=True)
    first_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=2,
        epoch=0,
        step_in_epoch=1,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    second_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    latest_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=6,
        epoch=0,
        step_in_epoch=5,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    retained_paths = _current_durable_checkpoint_paths(output_model_path)
    latest_pointer = json.loads(
        (output_model_path.parent / "latest_checkpoint.json").read_text(encoding="utf-8")
    )
    assert first_checkpoint.checkpoint_path not in retained_paths
    assert retained_paths == [
        second_checkpoint.checkpoint_path,
        latest_checkpoint.checkpoint_path,
    ]
    assert latest_pointer["checkpoint_path"] == latest_checkpoint.checkpoint_path
    assert epoch_checkpoint.exists() is True
    assert final_checkpoint.exists() is True


def test_save_durable_checkpoint_retention_three_keeps_newest_three_after_fourth_save(
    tmp_path: Path,
) -> None:
    """The shipped retention-3 contract should keep the newest three durable saves."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"

    first_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=2,
        epoch=0,
        step_in_epoch=1,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    second_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    third_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=6,
        epoch=0,
        step_in_epoch=5,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    latest_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=8,
        epoch=0,
        step_in_epoch=7,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    retained_paths = _current_durable_checkpoint_paths(output_model_path)
    latest_pointer = json.loads(
        (output_model_path.parent / "latest_checkpoint.json").read_text(encoding="utf-8")
    )

    assert first_checkpoint.checkpoint_path not in retained_paths
    assert retained_paths == [
        second_checkpoint.checkpoint_path,
        third_checkpoint.checkpoint_path,
        latest_checkpoint.checkpoint_path,
    ]
    assert latest_pointer["checkpoint_path"] == latest_checkpoint.checkpoint_path


def test_save_durable_checkpoint_maintains_pointer_and_retained_paths_when_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed validation must not flip the latest pointer or prune older checkpoints."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"
    first_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=2,
        epoch=0,
        step_in_epoch=1,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    second_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    latest_pointer_path = output_model_path.parent / "latest_checkpoint.json"
    before_failure_pointer = json.loads(latest_pointer_path.read_text(encoding="utf-8"))
    original_validate = SFT_12HZ_CHECKPOINTING._validate_saved_durable_checkpoint

    def _fail_validation(
        checkpoint_dir: Path,
        *,
        expected_metadata: object,
    ) -> None:
        if checkpoint_dir.name == ".state-step-00000006.incomplete":
            raise RuntimeError("simulated validation failure")
        original_validate(checkpoint_dir, expected_metadata=expected_metadata)

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing._validate_saved_durable_checkpoint",
        _fail_validation,
    )

    with pytest.raises(RuntimeError, match="simulated validation failure"):
        _save_durable_checkpoint(
            accelerator=accelerator,
            output_model_path=output_model_path,
            optimizer_steps_completed=6,
            epoch=0,
            step_in_epoch=5,
            dataloader_length=10,
            reason="interval",
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        )

    assert _current_durable_checkpoint_paths(output_model_path) == [
        first_checkpoint.checkpoint_path,
        second_checkpoint.checkpoint_path,
    ]
    assert json.loads(latest_pointer_path.read_text(encoding="utf-8")) == before_failure_pointer
    assert (output_model_path / "state-step-00000006").exists() is False
    assert _durable_checkpoint_staging_dir(output_model_path, 6).exists() is False


def test_save_durable_checkpoint_cleans_partial_state_and_allows_retry(
    tmp_path: Path,
) -> None:
    """A failed save should clean staging artifacts so the same step can be retried."""
    output_model_path = tmp_path / "run" / "checkpoints"

    class _FailOnceAccelerator(_FakeAccelerator):
        """Fake accelerator that fails once after materializing a partial save."""

        def __init__(self) -> None:
            super().__init__()
            self.fail_next = True

        def save_state(
            self, output_dir: str | None = None, safe_serialization: bool = True
        ) -> None:
            super().save_state(output_dir=output_dir, safe_serialization=safe_serialization)
            if self.fail_next:
                self.fail_next = False
                raise RuntimeError("simulated save failure")

    accelerator = _FailOnceAccelerator()

    with pytest.raises(RuntimeError, match="simulated save failure"):
        _save_durable_checkpoint(
            accelerator=accelerator,
            output_model_path=output_model_path,
            optimizer_steps_completed=4,
            epoch=0,
            step_in_epoch=3,
            dataloader_length=10,
            reason="interval",
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        )

    assert (output_model_path / "state-step-00000004").exists() is False
    assert _durable_checkpoint_staging_dir(output_model_path, 4).exists() is False

    metadata = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    assert metadata.checkpoint_path == (output_model_path / "state-step-00000004").as_posix()


def test_save_durable_checkpoint_fails_closed_for_first_checkpoint_when_free_space_is_low(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first durable checkpoint save should use the conservative fallback estimate."""
    output_model_path = tmp_path / "run" / "checkpoints"
    required_free_bytes = DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES + (16 * 1024**3)

    class _FakeDiskUsage:
        """Minimal disk-usage record for the free-space guard test."""

        def __init__(self, free: int) -> None:
            self.total = free * 2
            self.used = free
            self.free = free

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing.shutil.disk_usage",
        lambda _path: _FakeDiskUsage(required_free_bytes - 1),
    )

    with pytest.raises(RuntimeError, match="enough free space"):
        _save_durable_checkpoint(
            accelerator=_FakeAccelerator(),
            output_model_path=output_model_path,
            optimizer_steps_completed=4,
            epoch=0,
            step_in_epoch=3,
            dataloader_length=10,
            reason="interval",
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        )


def test_load_durable_checkpoint_metadata_rehydrates_resume_cursor(tmp_path: Path) -> None:
    """Loading durable checkpoint metadata should preserve resume fields exactly."""
    checkpoint_dir = tmp_path / "checkpoints" / "state-step-00000012"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "training_state.json").write_text(
        json.dumps(
            {
                "checkpoint_path": checkpoint_dir.as_posix(),
                "saved_at": "2026-03-09T12:00:00Z",
                "reason": "final-step",
                "optimizer_steps_completed": 12,
                "epoch": 1,
                "next_epoch": 2,
                "next_step_in_epoch": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    metadata = _load_durable_checkpoint_metadata(checkpoint_dir)

    assert metadata.optimizer_steps_completed == 12
    assert metadata.epoch == 1
    assert metadata.next_epoch == 2
    assert metadata.next_step_in_epoch == 0


def test_checkpoint_advanced_since_latest_save_detects_unsaved_progress(tmp_path: Path) -> None:
    """Unsaved optimizer progress should request one more durable checkpoint."""
    latest_checkpoint = _save_durable_checkpoint(
        accelerator=_FakeAccelerator(),
        output_model_path=tmp_path / "run" / "checkpoints",
        optimizer_steps_completed=12,
        epoch=1,
        step_in_epoch=4,
        dataloader_length=5,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    assert (
        _checkpoint_advanced_since_latest_save(
            latest_checkpoint,
            optimizer_steps_completed=13,
        )
        is True
    )
    assert (
        _checkpoint_advanced_since_latest_save(
            latest_checkpoint,
            optimizer_steps_completed=12,
        )
        is False
    )
