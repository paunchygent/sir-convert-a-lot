"""Tests for training stop state and signal handler installation.

Purpose:
    Validate that stop signals are recorded correctly, the first signal
    wins, unknown signal numbers fall back gracefully, and signal handler
    installation rejects worker-thread misuse.

Relationships:
    - Exercises `TrainingStopState`, `mark_stop_requested`, and
      `install_training_stop_handlers` in
      `scripts/devops/qwen_finetuning_patches/training_stop.py`.
"""

from __future__ import annotations

import pytest

from tests.training.training_test_support import (
    TrainingStopState,
    install_training_stop_handlers,
    mark_stop_requested,
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
