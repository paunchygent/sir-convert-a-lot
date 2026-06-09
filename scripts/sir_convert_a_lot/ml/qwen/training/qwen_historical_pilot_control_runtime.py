"""Runtime helpers for the historical Qwen pilot training control lane.

Purpose:
    Recreate the documented historical Qwen pilot training launch contract as faithfully
    as the current repo can support by launching a dedicated detached training
    run that mounts the surviving historical bundle directly instead of routing
    through the newer scratch-only training control plane.

Relationships:
    - Used by `qwen_historical_pilot_control.py` for the committed launch and
      status surface.
    - Reuses shared Docker/runtime helpers from `ml.qwen.common.runtime`.
    - Reuses detached training metadata contracts from `ml.qwen.training` so
      status inspection stays consistent with the rest of the Qwen lane.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    docker_checked,
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import load_optional_training_bundle_summary
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.paths import (
    mlflow_artifact_root,
    mlflow_tracking_uri,
    run_root_for_launch,
    tensorboard_logging_dir,
    tracker_root,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.settings_snapshot import (
    snapshot_settings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, TrainingSettings
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)

CONTAINER_BUILD_ROOT = Path("/app/build")
CONTAINER_HISTORICAL_BUNDLE_ROOT = Path("/app/historical-qwen-pilot-bundle")
DEFAULT_TRACKER_PROJECT_NAME = "qwen-historical-pilot"
DEFAULT_MLFLOW_EXPERIMENT_NAME = "qwen-historical-pilot"
DEFAULT_TRACKER_BACKENDS = ("mlflow", "tensorboard")
DEFAULT_TRAINER_MODULE = "scripts.sir_convert_a_lot.ml.qwen.training.trainer"


@dataclass(frozen=True)
class HistoricalControlImageSettings:
    """Image-build settings for the dedicated historical control lane."""

    dockerfile_path: Path
    image: str
    build_image: bool


def prepare_runtime_dependencies(
    *,
    settings: TrainingSettings,
    dockerfile_path: Path,
    build_image: bool,
    historical_bundle_root: Path,
    historical_bundle_home_mount: Path,
) -> tuple[bool, str, MountResolution, MountResolution, MountResolution]:
    """Prepare image, cache, scratch, and historical-bundle mounts."""
    build_performed, image_id = prepare_qwen_image(
        HistoricalControlImageSettings(
            dockerfile_path=dockerfile_path,
            image=settings.image,
            build_image=build_image,
        )
    )
    hf_mount = resolve_effective_hf_cache_dir(settings)
    scratch_mount = resolve_effective_bind_root(
        settings.scratch_build_root,
        settings.scratch_build_home_mount,
        image=settings.image,
        sync_home_into_canonical=False,
    )
    bundle_mount = resolve_effective_bind_root(
        historical_bundle_root,
        historical_bundle_home_mount,
        image=settings.image,
        sync_home_into_canonical=False,
    )
    return build_performed, image_id, hf_mount, scratch_mount, bundle_mount


def build_detached_historical_control_command(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    bundle_mount: MountResolution,
    launch_id: str,
    container_name: str,
    launch_root: Path,
    trainer_module: str = DEFAULT_TRAINER_MODULE,
) -> tuple[list[str], Path]:
    """Build the detached Docker argv for one historical-control run."""
    effective_run_root = run_root_for_launch(settings, launch_id=launch_id)
    container_run_root = _containerize_scratch_path(
        effective_run_root,
        scratch_root=settings.scratch_build_root,
    )
    container_launch_metadata_path = _containerize_scratch_path(
        launch_root / "launch.json",
        scratch_root=settings.scratch_build_root,
    )
    command = [
        "run",
        "-d",
        "--name",
        container_name,
        "--label",
        "sir_convert_a_lot.domain=qwen-training",
        "--label",
        "sir_convert_a_lot.lane=qwen-historical-pilot-control",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--ipc=host",
        "--cap-add=SYS_PTRACE",
        "--security-opt",
        "seccomp=unconfined",
        "-e",
        "HF_HUB_DISABLE_XET=1",
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-e",
        f"HUGGINGFACE_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
        "-e",
        f"TORCH_HOME={CONTAINER_TORCH_HOME}",
        "-v",
        f"{repo_root.as_posix()}:/app",
        "-v",
        f"{scratch_mount.effective_root.as_posix()}:{CONTAINER_BUILD_ROOT.as_posix()}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "-v",
        (
            f"{bundle_mount.effective_root.as_posix()}:{CONTAINER_HISTORICAL_BUNDLE_ROOT.as_posix()}:ro"
        ),
        "--workdir",
        "/app",
        "--entrypoint",
        "python",
        settings.image,
        "-m",
        trainer_module,
        "--launch-id",
        launch_id,
        "--launch-metadata-path",
        container_launch_metadata_path,
        "--model-id",
        settings.model_id,
        "--train-jsonl",
        _container_manifest_path(settings.train_manifest_family),
        "--eval-jsonl",
        _container_manifest_path(settings.eval_manifest_family),
        "--pilot-bundle-root",
        CONTAINER_HISTORICAL_BUNDLE_ROOT.as_posix(),
        "--train-manifest-family",
        settings.train_manifest_family,
        "--eval-manifest-family",
        settings.eval_manifest_family,
        "--text-embedding-assembly-mode",
        settings.text_embedding_assembly_mode,
        "--text-embedding-mask-policy",
        settings.text_embedding_mask_policy,
        "--output-dir",
        container_run_root,
        "--tracker-project-name",
        DEFAULT_TRACKER_PROJECT_NAME,
        "--mlflow-experiment-name",
        DEFAULT_MLFLOW_EXPERIMENT_NAME,
        "--mlflow-tracking-uri",
        mlflow_tracking_uri(effective_run_root),
        "--mlflow-artifact-root",
        _containerize_scratch_path(
            mlflow_artifact_root(effective_run_root),
            scratch_root=settings.scratch_build_root,
        ),
        "--tensorboard-logging-dir",
        _containerize_scratch_path(
            tensorboard_logging_dir(effective_run_root),
            scratch_root=settings.scratch_build_root,
        ),
        "--tracker-run-name",
        launch_id,
        "--batch-size",
        str(settings.batch_size),
        "--throughput-profile-label",
        settings.throughput_profile_label,
        "--lr",
        str(settings.lr),
        "--num-epochs",
        str(settings.num_epochs),
        "--max-steps",
        str(settings.max_steps),
        "--gradient-accumulation-steps",
        str(settings.gradient_accumulation_steps),
        "--checkpoint-interval-steps",
        str(settings.checkpoint_interval_steps),
        "--eval-interval-steps",
        str(settings.eval_interval_steps),
        "--durable-checkpoint-retention",
        str(settings.durable_checkpoint_retention),
        "--durable-checkpoint-min-free-bytes",
        str(settings.durable_checkpoint_min_free_bytes),
    ]
    return command, effective_run_root


def launch_detached_historical_control(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    bundle_mount: MountResolution,
    launch_id: str,
    container_name: str,
    launch_root: Path,
    dockerfile_path: Path,
    documented_bundle_root: Path,
    historical_bundle_home_mount: Path,
) -> DetachedLaunch:
    """Launch one detached historical-control run and return metadata."""
    command, effective_run_root = build_detached_historical_control_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        bundle_mount=bundle_mount,
        launch_id=launch_id,
        container_name=container_name,
        launch_root=launch_root,
    )
    container_id = docker_checked(
        command,
        label="docker run historical pilot control",
    ).strip()
    bundle_summary = load_optional_training_bundle_summary(settings.pilot_bundle_root)
    throughput_policy = resolve_throughput_batch_policy(
        profile_label=settings.throughput_profile_label,
        max_batch_size=settings.batch_size,
    )
    tracking_root = tracker_root(effective_run_root)
    return DetachedLaunch(
        generated_at=_utc_now_iso(),
        launch_kind="historical-control",
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
        dockerfile_path=dockerfile_path.as_posix(),
        resumed_from_checkpoint_path=None,
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
        diagnostic={
            "kind": "qwen_historical_pilot_control",
            "documented_bundle_root": documented_bundle_root.as_posix(),
            "historical_bundle_home_mount": historical_bundle_home_mount.as_posix(),
            "effective_bundle_mount_root": bundle_mount.effective_root.as_posix(),
            "container_bundle_root": CONTAINER_HISTORICAL_BUNDLE_ROOT.as_posix(),
            "compatibility_mode": "current_trainer_full_channel_masked_no_in_training_eval",
        },
    )


def _container_manifest_path(manifest_family: str) -> str:
    """Return the in-container manifest path for one historical bundle family."""
    return (
        CONTAINER_HISTORICAL_BUNDLE_ROOT / "manifests" / f"{manifest_family}.prepared.jsonl"
    ).as_posix()


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
