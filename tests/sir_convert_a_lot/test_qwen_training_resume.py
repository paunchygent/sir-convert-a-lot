"""Unit tests for Qwen trainer-state checkpoint helpers.

Purpose:
    Validate the durable checkpoint metadata and latest-checkpoint pointer
    contract introduced for `T115` without requiring a real GPU training run.

Relationships:
    - Exercises helper functions in `scripts/devops/qwen_finetuning_patches/sft_12hz.py`.
    - Complements the detached Task 101 runner tests by focusing on the inner
      trainer-state persistence semantics.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

SFT_PATCH_ROOT = Path(__file__).resolve().parents[2] / "scripts/devops/qwen_finetuning_patches"
if SFT_PATCH_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SFT_PATCH_ROOT.as_posix())

SFT_12HZ = importlib.import_module("scripts.devops.qwen_finetuning_patches.sft_12hz")
_checkpoint_resume_cursor = SFT_12HZ._checkpoint_resume_cursor
_checkpoint_advanced_since_latest_save = SFT_12HZ._checkpoint_advanced_since_latest_save
_load_durable_checkpoint_metadata = SFT_12HZ._load_durable_checkpoint_metadata
_save_durable_checkpoint = SFT_12HZ._save_durable_checkpoint
TrainingStopState = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).TrainingStopState
mark_stop_requested = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).mark_stop_requested
install_training_stop_handlers = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).install_training_stop_handlers


class _FakeAccelerator:
    """Minimal accelerator stub for durable checkpoint helper tests."""

    def __init__(self) -> None:
        self.is_main_process = True
        self.saved_paths: list[str] = []
        self.wait_count = 0

    def wait_for_everyone(self) -> None:
        """Record one barrier call."""
        self.wait_count += 1

    def save_state(self, output_dir: str | None = None, safe_serialization: bool = True) -> None:
        """Materialize a fake trainer-state marker file."""
        del safe_serialization
        if output_dir is None:
            raise AssertionError("Expected a checkpoint output directory.")
        self.saved_paths.append(output_dir)
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / "accelerate_state_marker.txt").write_text("saved\n", encoding="utf-8")


def test_checkpoint_resume_cursor_rolls_to_next_epoch_at_epoch_boundary() -> None:
    """A completed last batch should advance the resume cursor to the next epoch."""
    next_epoch, next_step = _checkpoint_resume_cursor(
        epoch=2,
        step_in_epoch=4,
        dataloader_length=5,
    )

    assert next_epoch == 3
    assert next_step == 0


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
    assert accelerator.saved_paths == [checkpoint_dir.as_posix()]


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


def test_mark_stop_requested_records_first_signal_only() -> None:
    """The first stop signal should win so the loop reports one stable cause."""
    stop_state = TrainingStopState()

    mark_stop_requested(stop_state, signal_number=15)
    mark_stop_requested(stop_state, signal_number=2)

    assert stop_state.stop_requested is True
    assert stop_state.signal_name == "SIGTERM"


def test_mark_stop_requested_falls_back_for_unknown_signal_number() -> None:
    """Unknown signal values should still be recorded deterministically."""
    stop_state = TrainingStopState()

    mark_stop_requested(stop_state, signal_number=999)

    assert stop_state.stop_requested is True
    assert stop_state.signal_name == "signal-999"


def test_install_training_stop_handlers_requires_main_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signal handler installation should reject worker-thread misuse explicitly."""
    stop_state = TrainingStopState()
    fake_main = object()
    fake_worker = object()

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.training_stop.threading.main_thread",
        lambda: fake_main,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.training_stop.threading.current_thread",
        lambda: fake_worker,
    )

    with pytest.raises(RuntimeError, match="main training thread"):
        install_training_stop_handlers(stop_state)
