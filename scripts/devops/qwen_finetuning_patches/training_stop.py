"""Signal-aware stop helpers for the patched Qwen fine-tuning loop.

Purpose:
    Keep signal-state handling out of `sft_12hz.py` so the patched training
    entrypoint can request graceful stop-and-checkpoint behavior without taking
    on more unrelated runtime plumbing.

Relationships:
    - Imported by `sft_12hz.py` in the same patch directory.
    - Tested via `tests/sir_convert_a_lot/test_qwen_training_resume.py`.
"""

from __future__ import annotations

import signal
import threading
from dataclasses import dataclass


@dataclass
class TrainingStopState:
    """Mutable stop-request state shared with the training loop."""

    stop_requested: bool = False
    signal_name: str | None = None


def mark_stop_requested(stop_state: TrainingStopState, signal_number: int) -> None:
    """Record the first requested stop signal for the active training loop."""
    if stop_state.stop_requested:
        return
    stop_state.stop_requested = True
    try:
        stop_state.signal_name = signal.Signals(signal_number).name
    except ValueError:
        stop_state.signal_name = f"signal-{signal_number}"


def install_training_stop_handlers(stop_state: TrainingStopState) -> None:
    """Install SIGINT/SIGTERM handlers from the main training thread only."""
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("install_training_stop_handlers must run on the main training thread.")

    def _handle_signal(signal_number: int, _frame: object | None) -> None:
        mark_stop_requested(stop_state, signal_number)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
