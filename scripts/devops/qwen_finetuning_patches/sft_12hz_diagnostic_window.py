"""Diagnostic-window config helpers for bounded Qwen RCA runs.

Purpose:
    Keep diagnostic-window argument validation and step-range matching out of
    the main training setup/loop modules so targeted RCA flows remain explicit
    and reusable.

Relationships:
    - Imported by `sft_12hz_setup.py` to normalize diagnostic CLI settings.
    - Imported by train-step helpers to decide when richer RCA capture should
      run for one optimizer-step window.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticWindowConfig:
    """Resolved optimizer-step window for one bounded diagnostic run."""

    kind: str
    start_optimizer_step: int
    end_optimizer_step: int

    def includes_optimizer_step(self, optimizer_step: int) -> bool:
        """Return whether the optimizer step falls inside the RCA window."""
        return self.start_optimizer_step <= optimizer_step <= self.end_optimizer_step


def build_diagnostic_window_config(
    args: argparse.Namespace,
) -> DiagnosticWindowConfig | None:
    """Return the bounded diagnostic-window config from one trainer namespace."""
    diagnostic_kind = getattr(args, "diagnostic_kind", None)
    if diagnostic_kind is None:
        return None
    start_optimizer_step = _required_positive_int(
        getattr(args, "diagnostic_start_optimizer_step", None),
        name="diagnostic_start_optimizer_step",
    )
    end_optimizer_step = _required_positive_int(
        getattr(args, "diagnostic_end_optimizer_step", None),
        name="diagnostic_end_optimizer_step",
    )
    if end_optimizer_step < start_optimizer_step:
        raise ValueError(
            "`--diagnostic_end_optimizer_step` must be >= `--diagnostic_start_optimizer_step`."
        )
    return DiagnosticWindowConfig(
        kind=str(diagnostic_kind),
        start_optimizer_step=start_optimizer_step,
        end_optimizer_step=end_optimizer_step,
    )


def _required_positive_int(value: object, *, name: str) -> int:
    """Return one required positive integer diagnostic value."""
    if not isinstance(value, int):
        raise ValueError(f"`--{name}` is required when diagnostic mode is enabled.")
    if value <= 0:
        raise ValueError(f"`--{name}` must be positive.")
    return value
