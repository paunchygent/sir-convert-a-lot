"""Reusable trainer-native diagnostic-state capture use case for Qwen training.

Purpose:
    Mint one deterministic checkpoint on the clean side of a known failure
    boundary so later RCA runs can replay only the relevant micro-window
    instead of paying the full resume cost from an older checkpoint.

Relationships:
    - Uses launch loading, path policy, and runtime preparation helpers.
    - Reuses detached launch/inspect services while delegating the exact
      save-and-exit boundary to the in-container trainer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from time import sleep

from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    inspect_detached_training,
    launch_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.ids import default_launch_id
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.paths import (
    containerize_scratch_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostic_artifacts import (
    diagnostic_state_capture_path,
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

DEFAULT_CAPTURE_POLL_INTERVAL_SECONDS = 15.0


def handle_capture_diagnostic_state(args) -> int:
    """Execute the detached reusable-state capture use case."""
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root = resolve_launch_root(output_root, args.launch_root)
    source_launch = load_training_launch(source_launch_root)
    source_repo_root = Path(source_launch.repo_root)
    source_run_root = Path(source_launch.run_root)
    settings = settings_from_snapshot(source_launch.settings)
    effective_bundle_root = (
        settings.pilot_bundle_root
        if args.pilot_bundle_root is None
        else Path(args.pilot_bundle_root)
    )
    target_optimizer_step = int(args.target_optimizer_step)
    if target_optimizer_step <= 0:
        raise SystemExit("`--target-optimizer-step` must be positive.")
    effective_checkpoint_interval_steps = (
        target_optimizer_step + 1
        if args.checkpoint_interval_steps is None
        else int(args.checkpoint_interval_steps)
    )
    if effective_checkpoint_interval_steps <= target_optimizer_step:
        raise SystemExit(
            "Trainer-native capture requires `checkpoint_interval_steps` to be greater "
            f"than the target optimizer step `{target_optimizer_step}`."
        )
    effective_eval_interval_steps = (
        target_optimizer_step + 1
        if args.eval_interval_steps is None
        else int(args.eval_interval_steps)
    )
    if effective_eval_interval_steps <= target_optimizer_step:
        raise SystemExit(
            "Trainer-native capture requires `eval_interval_steps` to be greater than "
            f"the target optimizer step `{target_optimizer_step}`."
        )
    settings = replace(
        settings,
        pilot_bundle_root=effective_bundle_root,
        checkpoint_interval_steps=effective_checkpoint_interval_steps,
        eval_interval_steps=effective_eval_interval_steps,
        max_steps=target_optimizer_step,
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
    resume_checkpoint_candidate = (
        Path(args.checkpoint_path)
        if args.checkpoint_path is not None
        else load_latest_checkpoint(source_run_root)
    )
    resume_checkpoint_path = require_under_scratch_root(
        settings,
        validate_resume_checkpoint_path(source_run_root, resume_checkpoint_candidate),
        label="checkpoint_path",
    )
    settings = replace(
        settings,
        pilot_bundle_root=require_existing_path(
            require_under_scratch_root(
                settings,
                settings.pilot_bundle_root,
                label="pilot_bundle_root",
            ),
            label="pilot_bundle_root",
        ),
    )
    current_launch_id = str(args.launch_id or default_launch_id())
    current_launch_root = launch_root(output_root, current_launch_id)
    current_launch_root.mkdir(parents=True, exist_ok=True)
    current_run_root = current_launch_root / "diagnostic-state"
    current_run_root.mkdir(parents=True, exist_ok=True)
    expected_checkpoint_path = (
        current_run_root / "checkpoints" / f"state-step-{target_optimizer_step:08d}"
    )
    capture_artifact_path = diagnostic_state_capture_path(current_launch_root)
    launch = launch_detached_training(
        settings,
        repo_root=source_repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=current_launch_id,
        container_name=f"qwen-capture-{current_launch_id}",
        launch_root=current_launch_root,
        dockerfile_path=dockerfile_path,
        run_root=current_run_root,
        resume_from_checkpoint=resume_checkpoint_path,
        launch_kind="capture-diagnostic-state",
        extra_probe_args=[
            "--diagnostic-kind",
            "capture-diagnostic-state",
            "--diagnostic-source-launch-root",
            source_launch_root.as_posix(),
            "--diagnostic-source-checkpoint-path",
            resume_checkpoint_path.as_posix(),
            "--diagnostic-target-optimizer-step",
            str(target_optimizer_step),
            "--diagnostic-capture-artifact-path",
            containerize_scratch_path(
                capture_artifact_path,
                scratch_root=settings.scratch_build_root,
            ),
            "--diagnostic-capture-launch-root-host-path",
            current_launch_root.as_posix(),
            "--diagnostic-capture-checkpoint-path",
            expected_checkpoint_path.as_posix(),
        ],
        diagnostic={
            "kind": "capture-diagnostic-state",
            "source_launch_root": source_launch_root.as_posix(),
            "source_checkpoint_path": resume_checkpoint_path.as_posix(),
            "target_optimizer_step": target_optimizer_step,
        },
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
    launch_payload = {
        **asdict(launch),
        "image_id": image_id,
        "build_performed": build_performed,
        "source_launch_root": source_launch_root.as_posix(),
    }
    write_json(launch_metadata_path(current_launch_root), launch_payload)
    final_status = _monitor_to_capture_completion(
        launch_root=current_launch_root,
        poll_interval_seconds=float(args.poll_interval_seconds),
    )
    if not capture_artifact_path.is_file():
        final_optimizer_step = _current_optimizer_step(final_status)
        raise SystemExit(
            "Trainer-native capture run exited without writing the capture artifact "
            f"(target={target_optimizer_step}, final_optimizer_step={final_optimizer_step}, "
            f"exit_code={final_status.get('exit_code')})."
        )
    capture_payload = json.loads(capture_artifact_path.read_text(encoding="utf-8"))
    captured_checkpoint_step = capture_payload.get("captured_checkpoint_step")
    if captured_checkpoint_step != target_optimizer_step:
        raise SystemExit(
            "Trainer-native capture artifact did not record the requested target step "
            f"(target={target_optimizer_step}, captured={captured_checkpoint_step})."
        )
    print(json.dumps(capture_payload, indent=2, ensure_ascii=False))
    return 0


def _monitor_to_capture_completion(
    *,
    launch_root: Path,
    poll_interval_seconds: float,
) -> dict[str, object]:
    """Poll the detached launch until the trainer-native capture run exits."""
    launch = load_training_launch(launch_root)
    while True:
        status = inspect_detached_training(launch)
        status_payload = asdict(status)
        if not status.running:
            return status_payload
        sleep(poll_interval_seconds)


def _current_optimizer_step(status_payload: dict[str, object]) -> int | None:
    """Return the current optimizer step from one detached status payload."""
    pilot_status = status_payload.get("pilot_status")
    if not isinstance(pilot_status, dict):
        return None
    value = pilot_status.get("current_optimizer_step")
    return value if isinstance(value, int) else None
