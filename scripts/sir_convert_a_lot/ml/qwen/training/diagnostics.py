"""Detached diagnostic orchestration for bounded Qwen non-finite replay.

Purpose:
    Launch one bounded detached replay against a known checkpoint so operators
    can inspect optimizer-boundary corruption on the same trusted launch/status
    surfaces as the main training lane without mutating the canonical
    latest-launch pointer.

Relationships:
    - Imported by `qwen_train.py` for the public `diagnose-non-finite`
      subcommand.
    - Reuses the shared detached Docker launch machinery from
      `detached_runtime`.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import launch_detached_training
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, TrainingSettings

DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP = 1405
DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP = 1406


def default_diagnostic_container_name(launch_id: str) -> str:
    """Return the deterministic container name for one detached diagnostic launch."""
    return f"qwen-diagnose-{launch_id}"


def diagnostic_run_root(launch_root: Path) -> Path:
    """Return the canonical run root for one detached diagnostic launch."""
    return launch_root / "diagnostic-run"


def launch_detached_non_finite_diagnosis(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    launch_root: Path,
    container_name: str,
    source_launch_root: Path,
    checkpoint_path: Path,
    start_optimizer_step: int,
    end_optimizer_step: int,
    dockerfile_path: Path | None = None,
) -> DetachedLaunch:
    """Launch one detached bounded diagnostic replay for Task 101."""
    if start_optimizer_step <= 0:
        raise ValueError("`start_optimizer_step` must be positive.")
    if end_optimizer_step < start_optimizer_step:
        raise ValueError("`end_optimizer_step` must be >= `start_optimizer_step`.")
    diagnostic_settings = replace(
        settings,
        max_steps=end_optimizer_step,
    )
    diagnostic = {
        "kind": "diagnose-non-finite",
        "source_launch_root": source_launch_root.as_posix(),
        "source_checkpoint_path": checkpoint_path.as_posix(),
        "start_optimizer_step": start_optimizer_step,
        "end_optimizer_step": end_optimizer_step,
    }
    return launch_detached_training(
        diagnostic_settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=launch_id,
        container_name=container_name,
        launch_root=launch_root,
        dockerfile_path=dockerfile_path,
        run_root=diagnostic_run_root(launch_root),
        resume_from_checkpoint=checkpoint_path,
        launch_kind="diagnose-non-finite",
        extra_probe_args=[
            "--diagnostic-kind",
            "diagnose-non-finite",
            "--diagnostic-source-launch-root",
            source_launch_root.as_posix(),
            "--diagnostic-source-checkpoint-path",
            checkpoint_path.as_posix(),
            "--diagnostic-start-optimizer-step",
            str(start_optimizer_step),
            "--diagnostic-end-optimizer-step",
            str(end_optimizer_step),
        ],
        diagnostic=diagnostic,
    )
