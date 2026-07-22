"""Focused tests for the Qwen diagnose control-plane use case.

Purpose:
    Verify the public bounded replay parser surface that feeds
    `diagnose_use_case` so operators get the intended deterministic defaults.

Relationships:
    - Exercises `control_plane.parser`.
    - Complements the heavier detached replay tests with a small bounded check.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.control_plane import build_parser
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP,
    DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP,
)


def test_diagnose_parser_exposes_the_canonical_replay_window_defaults() -> None:
    """The diagnose parser should surface the committed replay-window defaults."""
    parser = build_parser()
    args = parser.parse_args(["diagnose-non-finite"])

    assert args.start_optimizer_step == DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP
    assert args.end_optimizer_step == DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP
    assert args.gradient_accumulation_steps is None
    assert args.disable_resource_monitor is False
    assert args.skip_build is False
