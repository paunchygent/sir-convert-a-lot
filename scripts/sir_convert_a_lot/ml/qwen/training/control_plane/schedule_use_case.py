"""Schedule use case for detached Qwen training control-plane commands.

Purpose:
    Own the host-side path validation and execution flow for one bounded
    train-stop-eval-resume schedule cycle.

Relationships:
    - Uses launch loading and path policy helpers.
    - Delegates the control loop itself to `schedule_runner.py`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    load_latest_checkpoint,
    resolve_launch_root,
    validate_resume_checkpoint_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import settings_from_snapshot
from scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner import run_schedule_cycle

from .launch_loader import load_training_launch
from .path_policy import require_existing_path, require_under_scratch_root


def handle_schedule(args) -> int:
    """Execute one epoch-aware train-stop-eval-resume schedule cycle."""
    output_root = args.output_root
    source_launch_root = resolve_launch_root(output_root, args.launch_root)
    source_launch = load_training_launch(source_launch_root)
    settings = settings_from_snapshot(source_launch.settings)
    source_run_root = Path(source_launch.run_root)
    schedule_checkpoint_path = require_under_scratch_root(
        settings,
        validate_resume_checkpoint_path(
            source_run_root,
            load_latest_checkpoint(source_run_root)
            if args.checkpoint_path is None
            else Path(args.checkpoint_path),
        ),
        label="checkpoint_path",
    )
    schedule_eval_jsonl = require_existing_path(
        require_under_scratch_root(
            settings,
            Path(source_launch.eval_jsonl) if args.eval_jsonl is None else Path(args.eval_jsonl),
            label="eval_jsonl",
        ),
        label="eval_jsonl",
    )
    schedule_bundle_root = require_existing_path(
        require_under_scratch_root(
            settings,
            settings.pilot_bundle_root
            if args.pilot_bundle_root is None
            else Path(args.pilot_bundle_root),
            label="pilot_bundle_root",
        ),
        label="pilot_bundle_root",
    )
    schedule_report = run_schedule_cycle(
        source_launch_root=source_launch_root,
        source_launch=source_launch,
        output_root=output_root,
        checkpoint_path=schedule_checkpoint_path,
        eval_jsonl=schedule_eval_jsonl,
        pilot_bundle_root=schedule_bundle_root,
        epochs_per_segment=int(args.epochs_per_segment),
        poll_interval_seconds=float(args.poll_interval_seconds),
        skip_build=bool(args.skip_build),
        disable_resource_monitor=bool(args.disable_resource_monitor),
        resource_monitor_interval_seconds=float(args.resource_monitor_interval_seconds),
        resource_monitor_runtime_kind=args.resource_monitor_runtime_kind,
        resource_monitor_duration_seconds=(
            None
            if args.resource_monitor_duration_seconds is None
            else float(args.resource_monitor_duration_seconds)
        ),
    )
    print(json.dumps(asdict(schedule_report), indent=2, ensure_ascii=False))
    return 0
