"""Tests for canonical boolean CLI flag parsing on Qwen training surfaces."""

from __future__ import annotations

import argparse

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import add_boolean_argument, boolean_flag


def _build_parser() -> argparse.ArgumentParser:
    """Build one minimal parser that exercises the shared boolean helper."""
    parser = argparse.ArgumentParser()
    add_boolean_argument(
        parser,
        "--feature-enabled",
        default=True,
        help="Toggle one feature.",
    )
    return parser


def test_add_boolean_argument_accepts_explicit_true_and_false() -> None:
    """Shared boolean helpers should accept explicit true/false values."""
    parser = _build_parser()

    true_args = parser.parse_args(["--feature-enabled", "true"])
    false_args = parser.parse_args(["--feature-enabled", "false"])

    assert true_args.feature_enabled is True
    assert false_args.feature_enabled is False


def test_add_boolean_argument_accepts_negated_form() -> None:
    """Shared boolean helpers should keep the canonical `--no-...` form."""
    parser = _build_parser()

    args = parser.parse_args(["--no-feature-enabled"])

    assert args.feature_enabled is False


def test_add_boolean_argument_rejects_invalid_explicit_values() -> None:
    """Shared boolean helpers should fail closed on malformed explicit values."""
    parser = _build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--feature-enabled", "maybe"])


def test_boolean_flag_renders_canonical_tokens() -> None:
    """Rendered boolean tokens should stay deterministic for detached launch commands."""
    assert boolean_flag("--feature-enabled", True) == "--feature-enabled"
    assert boolean_flag("--feature-enabled", False) == "--no-feature-enabled"
