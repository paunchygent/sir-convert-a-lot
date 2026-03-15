"""CLI parser construction for Qwen training control-plane commands.

Purpose:
    Build the committed `qwen-train` parser while keeping command behavior and
    defaults out of the CLI composition root.

Relationships:
    - Imported by `scripts/sir_convert_a_lot/cli/ml/qwen_train.py`.
    - Reuses shared defaults and boolean flag helpers from the training domain.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import add_boolean_argument

from .defaults import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_DATA_PATH_PROOF_MODE,
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP,
    DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    DEFAULT_EVAL_INTERVAL_STEPS_CLI,
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    DEFAULT_IMAGE,
    DEFAULT_LR,
    DEFAULT_MAX_STEPS,
    DEFAULT_MODEL_ID,
    DEFAULT_NON_BLOCKING_TRANSFER,
    DEFAULT_NUM_EPOCHS,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PILOT_BUNDLE_ROOT,
    DEFAULT_REF_MEL_CACHE_ENABLED,
    DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    DEFAULT_ROCM_PROFILER_ENABLED,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SCHEDULE_POLL_INTERVAL_SECONDS,
    DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
    DEFAULT_SCRATCH_BUILD_ROOT,
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    DEFAULT_TORCH_PROFILER_ENABLED,
    DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    DEFAULT_TORCH_PROFILER_REPEAT,
    DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    DEFAULT_TORCH_PROFILER_WITH_STACK,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    default_hf_cache_dir,
    default_hf_cache_home_mount,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for detached Qwen training."""
    parser = argparse.ArgumentParser(description="Launch or inspect detached Qwen training.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch the detached training run.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    launch.add_argument("--pilot-bundle-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
    launch.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    launch.add_argument("--image", default=DEFAULT_IMAGE)
    launch.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    launch.add_argument("--hf-cache-home-mount", type=Path, default=default_hf_cache_home_mount())
    launch.add_argument("--scratch-build-root", type=Path, default=DEFAULT_SCRATCH_BUILD_ROOT)
    launch.add_argument(
        "--scratch-build-home-mount", type=Path, default=DEFAULT_SCRATCH_BUILD_HOME_MOUNT
    )
    launch.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    launch.add_argument("--train-manifest-family", default=DEFAULT_TRAIN_MANIFEST_FAMILY)
    launch.add_argument("--eval-manifest-family", default=DEFAULT_EVAL_MANIFEST_FAMILY)
    launch.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    launch.add_argument("--throughput-profile-label", default=DEFAULT_THROUGHPUT_PROFILE_LABEL)
    launch.add_argument("--lr", type=float, default=DEFAULT_LR)
    launch.add_argument("--num-epochs", type=int, default=DEFAULT_NUM_EPOCHS)
    launch.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    launch.add_argument(
        "--checkpoint-interval-steps", type=int, default=DEFAULT_CHECKPOINT_INTERVAL_STEPS
    )
    launch.add_argument("--eval-interval-steps", type=int, default=DEFAULT_EVAL_INTERVAL_STEPS_CLI)
    launch.add_argument(
        "--durable-checkpoint-retention", type=int, default=DEFAULT_DURABLE_CHECKPOINT_RETENTION
    )
    launch.add_argument(
        "--durable-checkpoint-min-free-bytes",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    )
    launch.add_argument(
        "--dataloader-num-workers", type=int, default=DEFAULT_DATALOADER_NUM_WORKERS
    )
    add_boolean_argument(launch, "--dataloader-pin-memory", default=DEFAULT_DATALOADER_PIN_MEMORY)
    add_boolean_argument(
        launch, "--dataloader-persistent-workers", default=DEFAULT_DATALOADER_PERSISTENT_WORKERS
    )
    launch.add_argument(
        "--dataloader-prefetch-factor", type=int, default=DEFAULT_DATALOADER_PREFETCH_FACTOR
    )
    add_boolean_argument(launch, "--non-blocking-transfer", default=DEFAULT_NON_BLOCKING_TRANSFER)
    add_boolean_argument(launch, "--data-path-proof-mode", default=DEFAULT_DATA_PATH_PROOF_MODE)
    launch.add_argument(
        "--heartbeat-interval-optimizer-steps",
        type=int,
        default=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    )
    launch.add_argument(
        "--finite-loss-max-consecutive-steps",
        type=int,
        default=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    )
    add_boolean_argument(launch, "--ref-mel-cache-enabled", default=DEFAULT_REF_MEL_CACHE_ENABLED)
    launch.add_argument(
        "--ref-mel-cache-max-items", type=int, default=DEFAULT_REF_MEL_CACHE_MAX_ITEMS
    )
    add_boolean_argument(launch, "--torch-profiler-enabled", default=DEFAULT_TORCH_PROFILER_ENABLED)
    launch.add_argument(
        "--torch-profiler-wait-steps", type=int, default=DEFAULT_TORCH_PROFILER_WAIT_STEPS
    )
    launch.add_argument(
        "--torch-profiler-warmup-steps", type=int, default=DEFAULT_TORCH_PROFILER_WARMUP_STEPS
    )
    launch.add_argument(
        "--torch-profiler-active-steps", type=int, default=DEFAULT_TORCH_PROFILER_ACTIVE_STEPS
    )
    launch.add_argument("--torch-profiler-repeat", type=int, default=DEFAULT_TORCH_PROFILER_REPEAT)
    add_boolean_argument(
        launch, "--torch-profiler-record-shapes", default=DEFAULT_TORCH_PROFILER_RECORD_SHAPES
    )
    add_boolean_argument(
        launch, "--torch-profiler-profile-memory", default=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY
    )
    add_boolean_argument(
        launch, "--torch-profiler-with-stack", default=DEFAULT_TORCH_PROFILER_WITH_STACK
    )
    add_boolean_argument(launch, "--rocm-profiler-enabled", default=DEFAULT_ROCM_PROFILER_ENABLED)
    launch.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    launch.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    )
    launch.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    launch.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )
    launch.add_argument("--launch-id", default=None)
    launch.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    resume = subparsers.add_parser("resume", help="Resume from the latest durable checkpoint.")
    resume.add_argument("resume_mode", nargs="?", choices=["latest"], default="latest")
    resume.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    resume.add_argument("--launch-root", type=Path, default=None)
    resume.add_argument("--checkpoint-path", type=Path, default=None)
    resume.add_argument("--pilot-bundle-root", type=Path, default=None)
    resume.add_argument("--checkpoint-interval-steps", type=int, default=None)
    resume.add_argument("--eval-interval-steps", type=int, default=None)
    resume.add_argument("--durable-checkpoint-retention", type=int, default=None)
    resume.add_argument("--launch-id", default=None)
    resume.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    resume.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    )
    resume.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    resume.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )
    resume.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    diagnose = subparsers.add_parser(
        "diagnose-non-finite",
        help="Launch a detached bounded replay to inspect one non-finite window.",
    )
    diagnose.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    diagnose.add_argument("--launch-root", type=Path, default=None)
    diagnose.add_argument("--checkpoint-path", type=Path, default=None)
    diagnose.add_argument("--pilot-bundle-root", type=Path, default=None)
    diagnose.add_argument(
        "--start-optimizer-step", type=int, default=DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP
    )
    diagnose.add_argument(
        "--end-optimizer-step", type=int, default=DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP
    )
    diagnose.add_argument("--launch-id", default=None)
    diagnose.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    diagnose.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    )
    diagnose.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    diagnose.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )
    diagnose.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    standalone_eval = subparsers.add_parser(
        "eval", help="Run standalone held-out eval against a durable checkpoint."
    )
    standalone_eval.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    standalone_eval.add_argument("--launch-root", type=Path, default=None)
    standalone_eval.add_argument("--checkpoint-path", type=Path, default=None)
    standalone_eval.add_argument("--eval-jsonl", type=Path, default=None)
    standalone_eval.add_argument("--pilot-bundle-root", type=Path, default=None)
    standalone_eval.add_argument("--eval-output-dir", type=Path, default=None)
    standalone_eval.add_argument("--eval-id", default=None)
    standalone_eval.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    schedule = subparsers.add_parser(
        "schedule", help="Run one epoch-aware train-stop-eval-resume control cycle."
    )
    schedule.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    schedule.add_argument("--launch-root", type=Path, default=None)
    schedule.add_argument("--checkpoint-path", type=Path, default=None)
    schedule.add_argument("--eval-jsonl", type=Path, default=None)
    schedule.add_argument("--pilot-bundle-root", type=Path, default=None)
    schedule.add_argument("--epochs-per-segment", type=int, default=1)
    schedule.add_argument(
        "--poll-interval-seconds", type=float, default=DEFAULT_SCHEDULE_POLL_INTERVAL_SECONDS
    )
    schedule.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    schedule.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    )
    schedule.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    schedule.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )
    schedule.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    status = subparsers.add_parser("status", help="Inspect one detached training launch.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--launch-root", type=Path, default=None)

    stop = subparsers.add_parser("stop", help="Stop one detached training launch intentionally.")
    stop.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    stop.add_argument("--launch-root", type=Path, default=None)
    return parser
