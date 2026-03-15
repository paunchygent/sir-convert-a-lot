"""Diagnostic replay use case for detached Qwen training control-plane commands.

Purpose:
    Own the bounded non-finite diagnostic launch flow for
    `qwen-train diagnose-non-finite`.

Relationships:
    - Uses launch loading, bundle validation, and path policy helpers.
    - Delegates detached diagnostic launch execution to `diagnostics.py`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import default_launch_id
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostics import (
    default_diagnostic_container_name,
    launch_detached_non_finite_diagnosis,
)
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    launch_metadata_path,
    launch_root,
    load_latest_checkpoint,
    resolve_launch_root,
    validate_resume_checkpoint_path,
    write_json,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import settings_from_snapshot
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import launch_resource_monitor

from .bundle_contract import ensure_training_bundle_exists
from .launch_loader import load_training_launch
from .path_policy import require_existing_path, require_under_scratch_root
from .shared_runtime import prepare_runtime_dependencies


def handle_diagnose(args) -> int:
    """Execute the bounded non-finite diagnostic launch use case."""
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root = resolve_launch_root(output_root, args.launch_root)
    source_launch = load_training_launch(source_launch_root)
    source_repo_root = Path(source_launch.repo_root)
    settings = settings_from_snapshot(source_launch.settings)
    effective_bundle_root = (
        settings.pilot_bundle_root
        if args.pilot_bundle_root is None
        else Path(args.pilot_bundle_root)
    )
    settings = replace(settings, pilot_bundle_root=effective_bundle_root)
    ensure_training_bundle_exists(
        settings.pilot_bundle_root,
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
    )
    dockerfile_path = Path(source_launch.dockerfile_path or args.default_dockerfile_path)
    build_performed, image_id, hf_mount, scratch_mount = prepare_runtime_dependencies(
        settings=settings,
        dockerfile_path=dockerfile_path,
        skip_build=bool(args.skip_build),
    )
    source_run_root = Path(source_launch.run_root)
    diagnostic_checkpoint_path = require_under_scratch_root(
        settings,
        validate_resume_checkpoint_path(
            source_run_root,
            load_latest_checkpoint(source_run_root)
            if args.checkpoint_path is None
            else Path(args.checkpoint_path),
        ),
        label="checkpoint_path",
    )
    settings = replace(
        settings,
        pilot_bundle_root=require_existing_path(
            require_under_scratch_root(
                settings, settings.pilot_bundle_root, label="pilot_bundle_root"
            ),
            label="pilot_bundle_root",
        ),
    )
    current_launch_id = str(args.launch_id or default_launch_id())
    current_launch_root = launch_root(output_root, current_launch_id)
    current_launch_root.mkdir(parents=True, exist_ok=True)
    launch = launch_detached_non_finite_diagnosis(
        settings,
        repo_root=source_repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=current_launch_id,
        launch_root=current_launch_root,
        container_name=default_diagnostic_container_name(current_launch_id),
        source_launch_root=source_launch_root,
        checkpoint_path=diagnostic_checkpoint_path,
        start_optimizer_step=int(args.start_optimizer_step),
        end_optimizer_step=int(args.end_optimizer_step),
        dockerfile_path=dockerfile_path,
    )
    if not bool(args.disable_resource_monitor):
        resource_monitor = launch_resource_monitor(
            training_launch_id=current_launch_id,
            training_launch_root=current_launch_root,
            runtime_kind=args.resource_monitor_runtime_kind,
            interval_seconds=float(args.resource_monitor_interval_seconds),
            duration_seconds=(
                None
                if args.resource_monitor_duration_seconds is None
                else float(args.resource_monitor_duration_seconds)
            ),
        )
        launch = replace(launch, resource_monitor=resource_monitor)
    write_json(
        launch_metadata_path(current_launch_root),
        {
            **asdict(launch),
            "image_id": image_id,
            "build_performed": build_performed,
            "source_launch_root": source_launch_root.as_posix(),
        },
    )
    print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
    return 0
