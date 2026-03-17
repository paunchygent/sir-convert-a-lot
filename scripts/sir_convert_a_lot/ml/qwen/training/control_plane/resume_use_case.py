"""Resume use case for detached Qwen training control-plane commands.

Purpose:
    Own checkpoint-backed resume behavior, including launch loading, bundle
    validation, runtime preparation, and resumed detached launch persistence.

Relationships:
    - Uses launch-loading, bundle-contract, and path-policy helpers.
    - Uses detached-runtime launch services to create the resumed run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    default_container_name,
    default_launch_id,
    launch_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    launch_metadata_path,
    launch_root,
    load_latest_checkpoint,
    resolve_launch_root,
    validate_resume_checkpoint_path,
    write_json,
    write_latest_pointer,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import settings_from_snapshot
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import launch_resource_monitor
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    resolve_text_embedding_assembly_mode,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    resolve_text_embedding_mask_policy,
)

from .bundle_contract import ensure_training_bundle_exists
from .launch_loader import load_training_launch
from .shared_runtime import prepare_runtime_dependencies


def handle_resume(args) -> int:
    """Execute the detached training resume use case."""
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
    settings = replace(
        settings,
        pilot_bundle_root=effective_bundle_root,
        gradient_accumulation_steps=resolve_gradient_accumulation_steps(
            getattr(args, "gradient_accumulation_steps", None),
            default=settings.gradient_accumulation_steps,
        ),
        text_embedding_assembly_mode=resolve_text_embedding_assembly_mode(
            getattr(args, "text_embedding_assembly_mode", None),
            default=settings.text_embedding_assembly_mode,
        ),
        text_embedding_mask_policy=resolve_text_embedding_mask_policy(
            getattr(args, "text_embedding_mask_policy", None),
            default=settings.text_embedding_mask_policy,
        ),
        num_epochs=(settings.num_epochs if args.num_epochs is None else int(args.num_epochs)),
        max_steps=(settings.max_steps if args.max_steps is None else int(args.max_steps)),
        checkpoint_interval_steps=(
            settings.checkpoint_interval_steps
            if args.checkpoint_interval_steps is None
            else int(args.checkpoint_interval_steps)
        ),
        eval_interval_steps=(
            settings.eval_interval_steps
            if args.eval_interval_steps is None
            else int(args.eval_interval_steps)
        ),
        durable_checkpoint_retention=(
            settings.durable_checkpoint_retention
            if args.durable_checkpoint_retention is None
            else int(args.durable_checkpoint_retention)
        ),
    )
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
    resume_checkpoint_candidate = (
        Path(args.checkpoint_path)
        if args.checkpoint_path is not None
        else load_latest_checkpoint(source_run_root)
    )
    resume_checkpoint_path = validate_resume_checkpoint_path(
        source_run_root,
        resume_checkpoint_candidate,
    )
    current_launch_id = str(args.launch_id or default_launch_id())
    current_launch_root = launch_root(output_root, current_launch_id)
    current_launch_root.mkdir(parents=True, exist_ok=True)
    launch = launch_detached_training(
        settings,
        repo_root=source_repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=current_launch_id,
        container_name=default_container_name(current_launch_id),
        launch_root=current_launch_root,
        dockerfile_path=dockerfile_path,
        run_root=source_run_root,
        resume_from_checkpoint=resume_checkpoint_path,
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
    write_latest_pointer(output_root, current_launch_root)
    print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
    return 0
