"""Boolean CLI flag helpers for the Qwen training surfaces.

Purpose:
    Provide one canonical way to declare and render boolean command-line flags
    across the detached launcher, detached orchestrator, and in-container
    trainer.

Relationships:
    - Imported by `cli/ml/qwen_train.py` for launch-argument parsing.
    - Imported by `ml.qwen.training.orchestrator` when materializing Docker args.
    - Imported by `ml.qwen.training.trainer` for in-container argument parsing.
"""

from __future__ import annotations

import argparse


def add_boolean_argument(
    parser: argparse.ArgumentParser,
    flag: str,
    *,
    default: bool,
    help: str | None = None,
) -> None:
    """Register one canonical `--flag` / `--no-flag` boolean option."""
    parser.add_argument(
        flag,
        action=argparse.BooleanOptionalAction,
        default=default,
        help=help,
    )


def boolean_flag(flag: str, enabled: bool) -> str:
    """Render the canonical CLI token for one boolean option state."""
    if not flag.startswith("--"):
        raise ValueError("Boolean flags must use long-option syntax.")
    return flag if enabled else f"--no-{flag[2:]}"
