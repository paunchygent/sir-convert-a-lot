"""Reusable near-boundary diagnostic-state capture use case for Qwen training.

Purpose:
    Mint one deterministic checkpoint on the clean side of a known failure
    boundary so later RCA runs can replay only the relevant micro-window
    instead of paying the full resume cost from an older checkpoint.

Relationships:
    - Uses launch loading, path policy, and runtime preparation helpers.
    - Reuses detached launch/inspect/stop services to automate step-threshold
      capture without manual sleep-based operator timing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from time import sleep

from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    inspect_detached_training,
    launch_detached_training,
    stop_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.ids import default_launch_id
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostic_artifacts import (
    build_diagnostic_state_capture,
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

DEFAULT_CAPTURE_CHECKPOINT_INTERVAL_STEPS = 1
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
    settings = replace(
        settings,
        pilot_bundle_root=effective_bundle_root,
        checkpoint_interval_steps=int(
            args.checkpoint_interval_steps or DEFAULT_CAPTURE_CHECKPOINT_INTERVAL_STEPS
        ),
        eval_interval_steps=int(
            args.eval_interval_steps
            if args.eval_interval_steps is not None
            else target_optimizer_step + 1
        ),
        max_steps=max(int(settings.max_steps), target_optimizer_step + 1),
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
    final_status = _monitor_to_target_and_stop(
        launch_root=current_launch_root,
        target_optimizer_step=target_optimizer_step,
        poll_interval_seconds=float(args.poll_interval_seconds),
    )
    latest_checkpoint_path = load_latest_checkpoint(current_run_root)
    latest_checkpoint_step = _checkpoint_step_from_path(latest_checkpoint_path)
    if latest_checkpoint_step < target_optimizer_step:
        raise SystemExit(
            "Capture run stopped before minting the requested optimizer-step checkpoint "
            f"(`{target_optimizer_step}` -> `{latest_checkpoint_step}`)."
        )
    capture_payload = build_diagnostic_state_capture(
        source_launch_root=source_launch_root,
        source_checkpoint_path=resume_checkpoint_path,
        target_optimizer_step=target_optimizer_step,
        launch_root=current_launch_root,
        run_root=current_run_root,
        checkpoint_path=latest_checkpoint_path,
        checkpoint_step=latest_checkpoint_step,
        final_status=final_status,
    )
    write_json(diagnostic_state_capture_path(current_launch_root), capture_payload)
    print(json.dumps(capture_payload, indent=2, ensure_ascii=False))
    return 0


def _monitor_to_target_and_stop(
    *,
    launch_root: Path,
    target_optimizer_step: int,
    poll_interval_seconds: float,
) -> dict[str, object]:
    """Poll the detached launch until the target step is reached, then stop it."""
    launch = load_training_launch(launch_root)
    stop_issued = False
    while True:
        status = inspect_detached_training(launch)
        status_payload = asdict(status)
        current_optimizer_step = _current_optimizer_step(status_payload)
        if (
            not stop_issued
            and current_optimizer_step is not None
            and current_optimizer_step >= target_optimizer_step
        ):
            stop_detached_training(launch)
            stop_issued = True
        if stop_issued and not status.running:
            return status_payload
        if not status.running and not stop_issued:
            raise SystemExit(
                "Diagnostic-state capture stopped before reaching the target optimizer step "
                f"`{target_optimizer_step}`."
            )
        sleep(poll_interval_seconds)


def _current_optimizer_step(status_payload: dict[str, object]) -> int | None:
    """Return the current optimizer step from one detached status payload."""
    pilot_status = status_payload.get("pilot_status")
    if not isinstance(pilot_status, dict):
        return None
    value = pilot_status.get("current_optimizer_step")
    return value if isinstance(value, int) else None


def _checkpoint_step_from_path(checkpoint_path: Path) -> int:
    """Extract the durable optimizer step from one checkpoint path."""
    checkpoint_name = checkpoint_path.name
    prefix = "state-step-"
    if not checkpoint_name.startswith(prefix):
        raise SystemExit(
            "Latest checkpoint path did not follow the durable checkpoint naming contract: "
            f"`{checkpoint_path.as_posix()}`."
        )
    try:
        return int(checkpoint_name.removeprefix(prefix))
    except ValueError as exc:
        raise SystemExit(
            "Latest checkpoint path did not expose an integer optimizer step: "
            f"`{checkpoint_path.as_posix()}`."
        ) from exc
