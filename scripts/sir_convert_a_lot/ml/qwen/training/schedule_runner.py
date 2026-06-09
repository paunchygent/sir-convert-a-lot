"""Epoch-aware schedule control for detached Qwen training on Hemma.

Purpose:
    Orchestrate one bounded `train -> stop -> eval -> resume` cycle around the
    canonical detached Qwen training lane using durable checkpoints and real
    held-out eval.

Relationships:
    - Consumes detached launch/inspect/stop helpers from `detached_runtime`.
    - Reuses one-shot standalone eval from `eval_orchestrator.py`.
    - Persisted schedule artifacts are consumed by the public `qwen-train`
      command surface.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from math import ceil
from pathlib import Path
from time import sleep
from typing import Literal

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
    load_durable_checkpoint_metadata,
)
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    MountResolution,
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    default_container_name,
    default_launch_id,
    inspect_detached_training,
    launch_detached_training,
    stop_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.eval_orchestrator import (
    default_eval_id,
    default_eval_output_dir,
    run_standalone_eval,
)
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    launch_metadata_path,
    launch_root,
    load_latest_checkpoint,
    status_metadata_path,
    validate_resume_checkpoint_path,
    write_json,
    write_latest_pointer,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    DetachedStatus,
    ScheduleReport,
    ScheduleSegmentReport,
    StandaloneEvalReport,
    TrainingSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import (
    launch_resource_monitor,
)


def _write_schedule_failure_artifacts(
    *,
    schedule_output_dir: Path,
    source_launch_root: Path,
    source_run_root: Path,
    dataloader_length: int | None,
    epochs_per_segment: int,
    exc: BaseException,
    final_status: DetachedStatus | None,
) -> None:
    """Persist deterministic failure artifacts for one schedule-control run."""
    schedule_output_dir.mkdir(parents=True, exist_ok=True)
    failure_payload: dict[str, object] = {
        "generated_at": _generated_at(final_status),
        "status": "failed",
        "source_launch_root": source_launch_root.as_posix(),
        "source_run_root": source_run_root.as_posix(),
        "dataloader_length": dataloader_length,
        "epochs_per_segment": epochs_per_segment,
        "failure": {"error": f"{type(exc).__name__}: {exc}"},
    }
    if final_status is not None:
        failure_payload["final_status"] = asdict(final_status)
    write_json(schedule_output_dir / "report.json", failure_payload)
    write_json(
        schedule_output_dir / "status.json",
        {
            "status": "failed",
            "updated_at": _generated_at(final_status),
            "source_launch_root": source_launch_root.as_posix(),
            "source_run_root": source_run_root.as_posix(),
            "error": f"{type(exc).__name__}: {exc}",
            "final_status": None if final_status is None else asdict(final_status),
        },
    )


def default_schedule_id() -> str:
    """Return one deterministic schedule identifier."""
    return default_eval_id().replace("eval-", "schedule-")


def default_schedule_output_dir(output_root: Path, *, schedule_id: str) -> Path:
    """Return the canonical output dir for one schedule control cycle."""
    return output_root / "schedules" / schedule_id


def run_schedule_cycle(
    *,
    source_launch_root: Path,
    source_launch: DetachedLaunch,
    output_root: Path,
    checkpoint_path: Path | None,
    eval_jsonl: Path | None,
    pilot_bundle_root: Path | None,
    epochs_per_segment: int,
    poll_interval_seconds: float,
    skip_build: bool,
    disable_resource_monitor: bool,
    resource_monitor_interval_seconds: float,
    resource_monitor_runtime_kind: Literal["rocm", "cuda", "none"],
    resource_monitor_duration_seconds: float | None,
) -> ScheduleReport:
    """Run one bounded epoch-aware train-stop-eval-resume cycle."""
    if epochs_per_segment <= 0:
        raise ValueError("`epochs_per_segment` must be positive.")
    output_root.mkdir(parents=True, exist_ok=True)
    source_run_root = Path(source_launch.run_root)
    schedule_output_dir = default_schedule_output_dir(
        output_root,
        schedule_id=default_schedule_id(),
    )
    dataloader_length: int | None = None
    final_status: DetachedStatus | None = None
    try:
        settings = _settings_from_launch(source_launch)
        dockerfile_path = Path(
            source_launch.dockerfile_path or "containers/qwen-finetune-hemma/Dockerfile"
        )
        dataloader_length = _resolve_dataloader_length(source_launch_root, source_launch)
        resolved_checkpoint_path = _require_under_scratch_root(
            settings,
            validate_resume_checkpoint_path(
                source_run_root,
                load_latest_checkpoint(source_run_root)
                if checkpoint_path is None
                else checkpoint_path,
            ),
            label="checkpoint_path",
        )
        checkpoint_metadata = load_durable_checkpoint_metadata(resolved_checkpoint_path)
        resolved_eval_jsonl = _require_existing_path(
            _require_under_scratch_root(
                settings,
                Path(source_launch.eval_jsonl) if eval_jsonl is None else eval_jsonl,
                label="eval_jsonl",
            ),
            label="eval_jsonl",
        )
        resolved_pilot_bundle_root = _require_existing_path(
            _require_under_scratch_root(
                settings,
                settings.pilot_bundle_root if pilot_bundle_root is None else pilot_bundle_root,
                label="pilot_bundle_root",
            ),
            label="pilot_bundle_root",
        )
        target_optimizer_step = _target_optimizer_step(
            checkpoint_metadata=checkpoint_metadata,
            dataloader_length=dataloader_length,
            epochs_per_segment=epochs_per_segment,
            gradient_accumulation_steps=settings.gradient_accumulation_steps,
        )

        rocm_smi_before = run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi qwen schedule preflight",
        )
        build_performed, image_id = prepare_qwen_image(
            argparse.Namespace(
                dockerfile_path=dockerfile_path,
                image=settings.image,
                build_image=not skip_build,
            )
        )
        hf_mount = resolve_effective_hf_cache_dir(
            argparse.Namespace(
                image=settings.image,
                hf_cache_dir=settings.hf_cache_dir,
                hf_cache_home_mount=settings.hf_cache_home_mount,
            )
        )
        scratch_mount = resolve_effective_bind_root(
            settings.scratch_build_root,
            settings.scratch_build_home_mount,
            image=settings.image,
            sync_home_into_canonical=False,
        )

        active_launch_root = source_launch_root
        active_launch = source_launch
        active_status = inspect_detached_training(active_launch)
        if not active_status.running:
            active_launch_root, active_launch = _resume_from_checkpoint(
                source_launch_root=source_launch_root,
                source_run_root=source_run_root,
                settings=settings,
                repo_root=Path(source_launch.repo_root),
                dockerfile_path=dockerfile_path,
                output_root=output_root,
                resume_checkpoint_path=resolved_checkpoint_path,
                skip_build=skip_build,
                build_performed=build_performed,
                image_id=image_id,
                hf_mount=hf_mount,
                scratch_mount=scratch_mount,
                disable_resource_monitor=disable_resource_monitor,
                resource_monitor_interval_seconds=resource_monitor_interval_seconds,
                resource_monitor_runtime_kind=resource_monitor_runtime_kind,
                resource_monitor_duration_seconds=resource_monitor_duration_seconds,
            )
            active_status = inspect_detached_training(active_launch)

        final_status, stop_requested_by_schedule = _monitor_to_target_and_stop(
            launch=active_launch,
            target_optimizer_step=target_optimizer_step,
            poll_interval_seconds=poll_interval_seconds,
        )
        _ensure_schedule_target_reached(
            final_status=final_status,
            target_optimizer_step=target_optimizer_step,
            stop_requested_by_schedule=stop_requested_by_schedule,
        )
        latest_checkpoint_path = validate_resume_checkpoint_path(
            source_run_root,
            load_latest_checkpoint(source_run_root),
        )
        latest_checkpoint_metadata = load_durable_checkpoint_metadata(latest_checkpoint_path)
        eval_id = default_eval_id()
        eval_output_dir = default_eval_output_dir(active_launch_root, eval_id=eval_id)
        eval_report = run_standalone_eval(
            settings,
            repo_root=Path(source_launch.repo_root),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            output_dir=eval_output_dir,
            checkpoint_path=latest_checkpoint_path,
            eval_jsonl=resolved_eval_jsonl,
            pilot_bundle_root=resolved_pilot_bundle_root,
        )
        resumed_launch_root, resumed_launch = _resume_from_checkpoint(
            source_launch_root=active_launch_root,
            source_run_root=source_run_root,
            settings=settings,
            repo_root=Path(source_launch.repo_root),
            dockerfile_path=dockerfile_path,
            output_root=output_root,
            resume_checkpoint_path=latest_checkpoint_path,
            skip_build=True,
            build_performed=build_performed,
            image_id=image_id,
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            disable_resource_monitor=disable_resource_monitor,
            resource_monitor_interval_seconds=resource_monitor_interval_seconds,
            resource_monitor_runtime_kind=resource_monitor_runtime_kind,
            resource_monitor_duration_seconds=resource_monitor_duration_seconds,
        )
        segment_report = ScheduleSegmentReport(
            segment_index=1,
            source_launch_root=active_launch_root.as_posix(),
            resume_launch_root=resumed_launch_root.as_posix(),
            target_optimizer_step=target_optimizer_step,
            checkpoint_path=latest_checkpoint_path.as_posix(),
            eval_output_dir=eval_output_dir.as_posix(),
            eval_loss=_required_eval_loss(eval_report),
            checkpoint_next_epoch=latest_checkpoint_metadata.next_epoch,
            checkpoint_next_step_in_epoch=latest_checkpoint_metadata.next_step_in_epoch,
        )
        report = ScheduleReport(
            generated_at=_generated_at(final_status),
            source_launch_root=source_launch_root.as_posix(),
            source_run_root=source_run_root.as_posix(),
            dataloader_length=dataloader_length,
            epochs_per_segment=epochs_per_segment,
            segments_completed=1,
            final_checkpoint_path=latest_checkpoint_path.as_posix(),
            segment_reports=[segment_report],
        )
        schedule_output_dir.mkdir(parents=True, exist_ok=True)
        write_json(schedule_output_dir / "report.json", asdict(report))
        write_json(
            schedule_output_dir / "status.json",
            {
                "status": "completed",
                "rocm_smi_before": rocm_smi_before,
                "build_performed": build_performed,
                "image_id": image_id,
                "final_status": asdict(final_status),
                "resumed_launch_root": resumed_launch_root.as_posix(),
                "resumed_launch_id": resumed_launch.launch_id,
            },
        )
        return report
    except BaseException as exc:
        _write_schedule_failure_artifacts(
            schedule_output_dir=schedule_output_dir,
            source_launch_root=source_launch_root,
            source_run_root=source_run_root,
            dataloader_length=dataloader_length,
            epochs_per_segment=epochs_per_segment,
            exc=exc,
            final_status=final_status,
        )
        raise


def _settings_from_launch(source_launch: DetachedLaunch) -> TrainingSettings:
    """Return normalized settings for one previously recorded launch."""
    from scripts.sir_convert_a_lot.ml.qwen.training.models import settings_from_snapshot

    return settings_from_snapshot(source_launch.settings)


def _require_under_scratch_root(settings: TrainingSettings, path: Path, *, label: str) -> Path:
    """Fail closed when one schedule-control path escapes the mounted scratch root."""
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(settings.scratch_build_root.resolve())
    except ValueError as exc:
        raise SystemExit(
            f"`{label}` must live under `{settings.scratch_build_root.as_posix()}`."
        ) from exc
    return resolved_path


def _require_existing_path(path: Path, *, label: str) -> Path:
    """Fail closed when one required schedule-control path does not exist."""
    resolved_path = path.resolve()
    if not resolved_path.exists():
        raise SystemExit(f"`{label}` did not exist: {resolved_path.as_posix()}")
    return resolved_path


def _resolve_dataloader_length(source_launch_root: Path, source_launch: DetachedLaunch) -> int:
    """Read the canonical train dataloader length from status or report artifacts."""
    status_path = status_metadata_path(source_launch_root)
    if status_path.exists():
        import json

        status_payload = json.loads(status_path.read_text(encoding="utf-8"))
        value = status_payload.get("dataloader_length")
        if isinstance(value, int) and value > 0:
            return value
    report_path = Path(source_launch.run_root) / "report.json"
    if report_path.exists():
        import json

        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        training_summary = report_payload.get("training_summary")
        if isinstance(training_summary, dict):
            value = training_summary.get("dataloader_length")
            if isinstance(value, int) and value > 0:
                return value
    raise SystemExit(
        "Schedule runner could not resolve `dataloader_length` from the source launch artifacts. "
        "Run the source launch with the epoch-aware schedule contract before using "
        "epoch-aware schedule control."
    )


def _target_optimizer_step(
    *,
    checkpoint_metadata: DurableCheckpointMetadata,
    dataloader_length: int,
    epochs_per_segment: int,
    gradient_accumulation_steps: int,
) -> int:
    """Return the optimizer-step boundary for the next scheduled stop."""
    remaining_microbatches = dataloader_length - checkpoint_metadata.next_step_in_epoch
    if checkpoint_metadata.next_step_in_epoch == 0:
        remaining_microbatches = dataloader_length
    total_microbatches = remaining_microbatches + max(epochs_per_segment - 1, 0) * dataloader_length
    return checkpoint_metadata.optimizer_steps_completed + ceil(
        total_microbatches / gradient_accumulation_steps
    )


def _monitor_to_target_and_stop(
    *,
    launch: DetachedLaunch,
    target_optimizer_step: int,
    poll_interval_seconds: float,
) -> tuple[DetachedStatus, bool]:
    """Poll one detached launch until the target step is reached, then stop it."""
    stop_issued = False
    while True:
        status = inspect_detached_training(launch)
        current_step = _status_optimizer_step(status)
        if not stop_issued and current_step is not None and current_step >= target_optimizer_step:
            stop_detached_training(launch)
            stop_issued = True
        if stop_issued and not status.running:
            return status, True
        if not status.running and not stop_issued:
            return status, False
        sleep(poll_interval_seconds)


def _ensure_schedule_target_reached(
    *,
    final_status: DetachedStatus,
    target_optimizer_step: int,
    stop_requested_by_schedule: bool,
) -> None:
    """Fail closed when the controlled training segment did not end cleanly."""
    if not stop_requested_by_schedule:
        raise SystemExit(
            "Schedule-controlled training stopped before reaching the planned optimizer-step "
            f"boundary `{target_optimizer_step}`."
        )
    pilot_status = final_status.pilot_status
    if isinstance(pilot_status, dict):
        current_phase = pilot_status.get("current_phase")
        status_value = pilot_status.get("status")
        if current_phase == "failed" or status_value == "failed":
            raise SystemExit(
                "Schedule-controlled training reached the stop boundary but ended in a failed "
                "trainer state; refusing standalone eval/resume."
            )
    if final_status.exit_code not in (0,):
        raise SystemExit(
            "Schedule-controlled training reached the stop boundary but the container exited "
            f"non-zero (`{final_status.exit_code}`); refusing standalone eval/resume."
        )


def _status_optimizer_step(status) -> int | None:
    """Extract the current optimizer step from one detached status payload."""
    pilot_status = status.pilot_status
    if not isinstance(pilot_status, dict):
        return None
    value = pilot_status.get("current_optimizer_step")
    return value if isinstance(value, int) else None


def _resume_from_checkpoint(
    *,
    source_launch_root: Path,
    source_run_root: Path,
    settings: TrainingSettings,
    repo_root: Path,
    dockerfile_path: Path,
    output_root: Path,
    resume_checkpoint_path: Path,
    skip_build: bool,
    build_performed: bool,
    image_id: str,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    disable_resource_monitor: bool,
    resource_monitor_interval_seconds: float,
    resource_monitor_runtime_kind: Literal["rocm", "cuda", "none"],
    resource_monitor_duration_seconds: float | None,
) -> tuple[Path, DetachedLaunch]:
    """Launch one resumed detached training container from a durable checkpoint."""
    launch_id = default_launch_id()
    current_launch_root = launch_root(output_root, launch_id)
    current_launch_root.mkdir(parents=True, exist_ok=True)
    launch = launch_detached_training(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=launch_id,
        container_name=default_container_name(launch_id),
        launch_root=current_launch_root,
        dockerfile_path=dockerfile_path,
        run_root=source_run_root,
        resume_from_checkpoint=resume_checkpoint_path,
    )
    resource_monitor = None
    if not disable_resource_monitor:
        resource_monitor = launch_resource_monitor(
            training_launch_id=launch_id,
            training_launch_root=current_launch_root,
            runtime_kind=resource_monitor_runtime_kind,
            interval_seconds=resource_monitor_interval_seconds,
            duration_seconds=resource_monitor_duration_seconds,
        )
        from dataclasses import replace

        launch = replace(launch, resource_monitor=resource_monitor)
    write_json(
        launch_metadata_path(current_launch_root),
        {
            **asdict(launch),
            "image_id": image_id,
            "build_performed": build_performed and not skip_build,
            "source_launch_root": source_launch_root.as_posix(),
        },
    )
    write_latest_pointer(output_root, current_launch_root)
    return current_launch_root, launch


def _required_eval_loss(eval_report: StandaloneEvalReport) -> float:
    """Return the resolved eval loss from one standalone eval report."""
    eval_summary = eval_report.eval_summary
    if not isinstance(eval_summary, dict):
        raise SystemExit("Standalone eval report did not carry `eval_summary`.")
    eval_loss = eval_summary.get("eval_loss")
    if not isinstance(eval_loss, float):
        raise SystemExit("Standalone eval report did not carry a float `eval_loss`.")
    return eval_loss


def _generated_at(final_status: DetachedStatus | None) -> str:
    """Return the best available report timestamp for schedule artifacts."""
    if final_status is None:
        from datetime import UTC, datetime

        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return final_status.checked_at
