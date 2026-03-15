"""Launch use case for detached Qwen training control-plane commands.

Purpose:
    Own host-side validation, settings construction, runtime preparation, and
    detached launch persistence for `qwen-train launch`.

Relationships:
    - Consumes bundle validation and runtime preparation helpers.
    - Uses detached-runtime services to materialize the launch.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import run_checked
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    default_container_name,
    default_launch_id,
    launch_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    launch_metadata_path,
    launch_root,
    write_json,
    write_latest_pointer,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import launch_resource_monitor
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    resolve_throughput_batch_policy,
)

from .bundle_contract import ensure_training_bundle_exists
from .shared_runtime import prepare_runtime_dependencies


def handle_launch(args) -> int:
    """Execute the detached training launch use case."""
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    rocm_smi_before = run_checked(
        ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
        label="rocm-smi qwen training preflight",
    )
    settings = build_settings_from_args(args)
    ensure_training_bundle_exists(
        settings.pilot_bundle_root,
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
    )
    build_performed, image_id, hf_mount, scratch_mount = prepare_runtime_dependencies(
        settings=settings,
        dockerfile_path=args.dockerfile_path,
        skip_build=bool(args.skip_build),
    )
    current_launch_id = str(args.launch_id or default_launch_id())
    current_launch_root = launch_root(output_root, current_launch_id)
    current_launch_root.mkdir(parents=True, exist_ok=True)
    launch = launch_detached_training(
        settings,
        repo_root=args.repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=current_launch_id,
        container_name=default_container_name(current_launch_id),
        launch_root=current_launch_root,
        dockerfile_path=args.dockerfile_path,
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
            "rocm_smi_before": rocm_smi_before,
        },
    )
    write_latest_pointer(output_root, current_launch_root)
    print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
    return 0


def build_settings_from_args(args) -> TrainingSettings:
    """Build one normalized training settings object from parsed launch args."""
    throughput_batch_policy = resolve_throughput_batch_policy(
        profile_label=str(args.throughput_profile_label),
        max_batch_size=int(args.batch_size),
    )
    return TrainingSettings(
        output_root=args.output_root,
        image=str(args.image),
        hf_cache_dir=args.hf_cache_dir,
        hf_cache_home_mount=args.hf_cache_home_mount,
        scratch_build_root=args.scratch_build_root,
        scratch_build_home_mount=args.scratch_build_home_mount,
        pilot_bundle_root=args.pilot_bundle_root,
        runs_root=args.runs_root,
        model_id=str(args.model_id),
        train_manifest_family=str(args.train_manifest_family),
        eval_manifest_family=str(args.eval_manifest_family),
        batch_size=throughput_batch_policy.max_batch_size,
        throughput_profile_label=throughput_batch_policy.profile_label,
        lr=float(args.lr),
        num_epochs=int(args.num_epochs),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        eval_interval_steps=int(args.eval_interval_steps),
        durable_checkpoint_retention=int(args.durable_checkpoint_retention),
        durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
        dataloader_num_workers=int(args.dataloader_num_workers),
        dataloader_pin_memory=bool(args.dataloader_pin_memory),
        dataloader_persistent_workers=bool(args.dataloader_persistent_workers),
        dataloader_prefetch_factor=int(args.dataloader_prefetch_factor),
        non_blocking_transfer=bool(args.non_blocking_transfer),
        data_path_proof_mode=bool(args.data_path_proof_mode),
        heartbeat_interval_optimizer_steps=int(args.heartbeat_interval_optimizer_steps),
        finite_loss_max_consecutive_steps=int(args.finite_loss_max_consecutive_steps),
        ref_mel_cache_enabled=bool(args.ref_mel_cache_enabled),
        ref_mel_cache_max_items=int(args.ref_mel_cache_max_items),
        torch_profiler_enabled=bool(args.torch_profiler_enabled),
        torch_profiler_wait_steps=int(args.torch_profiler_wait_steps),
        torch_profiler_warmup_steps=int(args.torch_profiler_warmup_steps),
        torch_profiler_active_steps=int(args.torch_profiler_active_steps),
        torch_profiler_repeat=int(args.torch_profiler_repeat),
        torch_profiler_record_shapes=bool(args.torch_profiler_record_shapes),
        torch_profiler_profile_memory=bool(args.torch_profiler_profile_memory),
        torch_profiler_with_stack=bool(args.torch_profiler_with_stack),
        rocm_profiler_enabled=bool(args.rocm_profiler_enabled),
    )
