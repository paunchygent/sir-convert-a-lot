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


def _parse_explicit_bool(raw_value: str) -> bool:
    """Parse one explicit boolean CLI value."""
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(
        "Expected one boolean value: true/false, yes/no, on/off, or 1/0."
    )


def add_boolean_argument(
    parser: argparse.ArgumentParser,
    flag: str,
    *,
    default: bool,
    help: str | None = None,
) -> None:
    """Register one canonical boolean option with explicit-value support."""
    if not flag.startswith("--"):
        raise ValueError("Boolean flags must use long-option syntax.")
    dest = flag[2:].replace("-", "_")
    rendered_help = (
        help if help is None else f"{help} Also accepts explicit values like `{flag} false`."
    )
    parser.add_argument(
        flag,
        dest=dest,
        nargs="?",
        const=True,
        type=_parse_explicit_bool,
        default=default,
        metavar="BOOL",
        help=rendered_help,
    )
    parser.add_argument(
        f"--no-{flag[2:]}",
        dest=dest,
        action="store_false",
        help=argparse.SUPPRESS,
    )


def boolean_flag(flag: str, enabled: bool) -> str:
    """Render the canonical CLI token for one boolean option state."""
    if not flag.startswith("--"):
        raise ValueError("Boolean flags must use long-option syntax.")
    return flag if enabled else f"--no-{flag[2:]}"
