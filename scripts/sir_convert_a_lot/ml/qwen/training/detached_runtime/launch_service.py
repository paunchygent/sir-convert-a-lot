"""Detached launch service for Qwen training and diagnostics.

Purpose:
    Execute detached Docker launches and materialize truthful `DetachedLaunch`
    metadata without owning inspection or stop behavior.

Relationships:
    - Consumes Docker command construction from `command_builder`.
    - Consumes snapshot and path helpers from the detached runtime package.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import MountResolution, docker_checked
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import load_optional_training_bundle_summary
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, TrainingSettings
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)

from .command_builder import build_detached_training_command
from .paths import mlflow_artifact_root, mlflow_tracking_uri, tensorboard_logging_dir, tracker_root
from .settings_snapshot import snapshot_settings

DEFAULT_TRACKER_PROJECT_NAME = "qwen-training"
DEFAULT_MLFLOW_EXPERIMENT_NAME = "qwen-training"
DEFAULT_TRACKER_BACKENDS = ("mlflow", "tensorboard")


def launch_detached_training(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
    launch_root: Path,
    dockerfile_path: Path | None = None,
    run_root: Path | None = None,
    resume_from_checkpoint: Path | None = None,
    launch_kind: str = "training",
    trainer_module: str = "scripts.sir_convert_a_lot.ml.qwen.training.trainer",
    extra_probe_args: list[str] | None = None,
    diagnostic: dict[str, object] | None = None,
) -> DetachedLaunch:
    """Launch one detached training run and return deterministic metadata."""
    command, effective_run_root = build_detached_training_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=launch_id,
        container_name=container_name,
        launch_root=launch_root,
        run_root=run_root,
        resume_from_checkpoint=resume_from_checkpoint,
        trainer_module=trainer_module,
        extra_probe_args=extra_probe_args,
    )
    container_id = docker_checked(
        command,
        label="docker run qwen detached training",
    ).strip()
    tracking_root = tracker_root(effective_run_root)
    bundle_summary = load_optional_training_bundle_summary(settings.pilot_bundle_root)
    throughput_policy = resolve_throughput_batch_policy(
        profile_label=settings.throughput_profile_label,
        max_batch_size=settings.batch_size,
    )
    return DetachedLaunch(
        generated_at=_utc_now_iso(),
        launch_kind=launch_kind,
        launch_id=launch_id,
        container_name=container_name,
        container_id=container_id,
        repo_root=repo_root.as_posix(),
        run_root=effective_run_root.as_posix(),
        pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
        train_jsonl=(
            settings.pilot_bundle_root
            / "manifests"
            / f"{settings.train_manifest_family}.prepared.jsonl"
        ).as_posix(),
        eval_jsonl=(
            settings.pilot_bundle_root
            / "manifests"
            / f"{settings.eval_manifest_family}.prepared.jsonl"
        ).as_posix(),
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        dockerfile_path=None if dockerfile_path is None else dockerfile_path.as_posix(),
        resumed_from_checkpoint_path=(
            None if resume_from_checkpoint is None else resume_from_checkpoint.as_posix()
        ),
        settings=snapshot_settings(settings),
        command=["sudo", "-n", "docker", *command],
        bundle_precomputed_reference_input=(
            None
            if bundle_summary is None
            else {
                "kind": bundle_summary.precomputed_reference_input.kind,
                "version": bundle_summary.precomputed_reference_input.version,
                "source_field": bundle_summary.precomputed_reference_input.source_field,
                "artifact_root": bundle_summary.precomputed_reference_input.artifact_root,
                "artifact_count": bundle_summary.precomputed_reference_input.artifact_count,
            }
        ),
        throughput_profile=throughput_policy_payload(throughput_policy),
        tracking={
            "tracker_backends": list(DEFAULT_TRACKER_BACKENDS),
            "project_name": DEFAULT_TRACKER_PROJECT_NAME,
            "run_name": launch_id,
            "mlflow_experiment_name": DEFAULT_MLFLOW_EXPERIMENT_NAME,
            "mlflow_tracking_uri": mlflow_tracking_uri(effective_run_root),
            "mlflow_artifact_root": mlflow_artifact_root(effective_run_root).as_posix(),
            "tensorboard_logging_dir": tensorboard_logging_dir(effective_run_root).as_posix(),
            "tracker_root": tracking_root.as_posix(),
        },
        diagnostic=None if diagnostic is None else dict(diagnostic),
    )


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
