"""Standalone eval use case for detached Qwen training control-plane commands.

Purpose:
    Own the host-side path validation and runtime preparation for
    `qwen-train eval`.

Relationships:
    - Uses launch loading and path policy helpers.
    - Delegates actual held-out eval execution to the eval orchestrator.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.eval_orchestrator import (
    default_eval_id,
    default_eval_output_dir,
    run_standalone_eval,
)
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    load_latest_checkpoint,
    resolve_launch_root,
    validate_resume_checkpoint_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import settings_from_snapshot
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    resolve_text_embedding_mask_policy,
)

from .launch_loader import load_training_launch
from .path_policy import require_existing_path, require_under_scratch_root
from .shared_runtime import prepare_runtime_dependencies


def handle_eval(args) -> int:
    """Execute the standalone held-out eval use case."""
    output_root = args.output_root
    source_launch_root = resolve_launch_root(output_root, args.launch_root)
    source_launch = load_training_launch(source_launch_root)
    source_repo_root = Path(source_launch.repo_root)
    settings = settings_from_snapshot(source_launch.settings)
    settings = replace(
        settings,
        gradient_accumulation_steps=resolve_gradient_accumulation_steps(
            getattr(args, "gradient_accumulation_steps", None),
            default=settings.gradient_accumulation_steps,
        ),
        text_embedding_mask_policy=resolve_text_embedding_mask_policy(
            getattr(args, "text_embedding_mask_policy", None),
            default=settings.text_embedding_mask_policy,
        ),
    )
    dockerfile_path = Path(source_launch.dockerfile_path or args.default_dockerfile_path)
    _, _, hf_mount, scratch_mount = prepare_runtime_dependencies(
        settings=settings,
        dockerfile_path=dockerfile_path,
        skip_build=bool(args.skip_build),
    )
    source_run_root = Path(source_launch.run_root)
    resolved_checkpoint_path = validate_resume_checkpoint_path(
        source_run_root,
        load_latest_checkpoint(source_run_root)
        if args.checkpoint_path is None
        else Path(args.checkpoint_path),
    )
    resolved_eval_jsonl = (
        Path(source_launch.eval_jsonl) if args.eval_jsonl is None else Path(args.eval_jsonl)
    )
    resolved_bundle_root = (
        settings.pilot_bundle_root
        if args.pilot_bundle_root is None
        else Path(args.pilot_bundle_root)
    )
    resolved_checkpoint_path = require_under_scratch_root(
        settings, resolved_checkpoint_path, label="checkpoint_path"
    )
    resolved_eval_jsonl = require_existing_path(
        require_under_scratch_root(settings, resolved_eval_jsonl, label="eval_jsonl"),
        label="eval_jsonl",
    )
    resolved_eval_output_dir = (
        default_eval_output_dir(source_launch_root, eval_id=str(args.eval_id or default_eval_id()))
        if args.eval_output_dir is None
        else Path(args.eval_output_dir)
    )
    resolved_eval_output_dir = require_under_scratch_root(
        settings,
        resolved_eval_output_dir,
        label="eval_output_dir",
    )
    if resolved_bundle_root is not None:
        resolved_bundle_root = require_existing_path(
            require_under_scratch_root(settings, resolved_bundle_root, label="pilot_bundle_root"),
            label="pilot_bundle_root",
        )
    eval_report = run_standalone_eval(
        settings,
        repo_root=source_repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        output_dir=resolved_eval_output_dir,
        checkpoint_path=resolved_checkpoint_path,
        eval_jsonl=resolved_eval_jsonl,
        pilot_bundle_root=resolved_bundle_root,
    )
    print(json.dumps(asdict(eval_report), indent=2, ensure_ascii=False))
    return 0
