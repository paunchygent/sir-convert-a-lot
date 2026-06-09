"""Reusable parser argument groups for Qwen training control-plane commands.

Purpose:
    Keep the committed `qwen-train` parser under the Qwen architecture boundary hot-path size
    cap by centralizing repeated argument groups such as text-embedding runtime
    contract flags, resource-monitor controls, and detached build toggles.

Relationships:
    - Imported by `control_plane/parser.py`.
    - Reuses domain choice sets from the training package.
"""

from __future__ import annotations

import argparse

from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    TEXT_EMBEDDING_MASK_POLICY_CHOICES,
)


def add_text_embedding_contract_arguments(
    parser: argparse.ArgumentParser,
    *,
    mask_policy_default: str | None,
    assembly_mode_default: str | None,
) -> None:
    """Add the shared text-embedding mask/assembly contract arguments."""
    parser.add_argument(
        "--text-embedding-mask-policy",
        choices=TEXT_EMBEDDING_MASK_POLICY_CHOICES,
        default=mask_policy_default,
    )
    parser.add_argument(
        "--text-embedding-assembly-mode",
        choices=TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES,
        default=assembly_mode_default,
    )


def add_resource_monitor_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_interval_seconds: float,
    default_runtime_kind: str,
) -> None:
    """Add the detached resource-monitor controls shared by training commands."""
    parser.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=default_interval_seconds,
    )
    parser.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=default_runtime_kind,
    )
    parser.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    parser.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )


def add_skip_build_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared detached-runtime build-skip toggle."""
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )
