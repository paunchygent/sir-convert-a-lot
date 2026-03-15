"""Focused tests for the Qwen launch control-plane use case.

Purpose:
    Verify the bounded launch-use-case settings builder so launch defaults and
    throughput normalization stay owned by the new control-plane package.

Relationships:
    - Exercises `control_plane.launch_use_case`.
    - Keeps launch-use-case assertions out of the broad orchestration test file.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.control_plane import build_parser
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.launch_use_case import (
    build_settings_from_args,
)


def test_build_settings_from_args_normalizes_the_launch_profile() -> None:
    """Launch settings should reflect the bounded control-plane defaults."""
    parser = build_parser()
    args = parser.parse_args(["launch"])
    args.repo_root = Path.cwd()
    args.default_dockerfile_path = Path("containers/qwen-finetune-hemma/Dockerfile")

    settings = build_settings_from_args(args)

    assert settings.batch_size == 8
    assert settings.throughput_profile_label == "hemma-throughput-balanced-v1"
    assert settings.checkpoint_interval_steps == 500
    assert settings.eval_interval_steps == 100
    assert settings.durable_checkpoint_retention == 3
