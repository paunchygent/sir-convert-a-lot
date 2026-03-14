"""Detached orchestration for Qwen training on Hemma.

Purpose:
    Provide host-side logic for launching, inspecting, and stopping detached
    Qwen training containers.

Relationships:
    - Consumes base infrastructure from `ml.qwen.common.runtime`.
    - Consumes resource monitoring from `ml.qwen.training.monitoring`.
    - Consumes metadata helpers from `ml.qwen.training.metadata`.
    - Reuses data contracts from `ml.qwen.training.models`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    MountResolution,
    docker_checked,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import load_optional_training_bundle_summary
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import boolean_flag
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    DetachedStatus,
    DetachedStop,
    TrainingSettings,
    TrainingSettingsSnapshot,
)
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import (
    inspect_resource_monitor,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)

CONTAINER_BUILD_ROOT = Path("/app/build")
DEFAULT_TRACKER_PROJECT_NAME = "qwen-training"
DEFAULT_MLFLOW_EXPERIMENT_NAME = "qwen-training"
DEFAULT_TRACKER_BACKENDS = ("mlflow", "tensorboard")


def default_container_name(launch_id: str) -> str:
    """Return the deterministic container name for one training launch."""
    return f"qwen-train-{launch_id}"


def default_launch_id() -> str:
    """Return one deterministic launch id for a new training run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def run_root_for_launch(settings: TrainingSettings, *, launch_id: str) -> Path:
    """Return the canonical host-side run root for one training launch."""
    return settings.runs_root / launch_id


def snapshot_settings(settings: TrainingSettings) -> TrainingSettingsSnapshot:
    """Create one JSON-serializable snapshot of the current training settings."""
    return TrainingSettingsSnapshot(
        output_root=settings.output_root.as_posix(),
        image=settings.image,
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        hf_cache_home_mount=settings.hf_cache_home_mount.as_posix(),
        scratch_build_root=settings.scratch_build_root.as_posix(),
        scratch_build_home_mount=settings.scratch_build_home_mount.as_posix(),
        pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
        runs_root=settings.runs_root.as_posix(),
        model_id=settings.model_id,
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        batch_size=settings.batch_size,
        throughput_profile_label=settings.throughput_profile_label,
        lr=settings.lr,
        num_epochs=settings.num_epochs,
        max_steps=settings.max_steps,
        checkpoint_interval_steps=settings.checkpoint_interval_steps,
        durable_checkpoint_retention=settings.durable_checkpoint_retention,
        durable_checkpoint_min_free_bytes=settings.durable_checkpoint_min_free_bytes,
        dataloader_num_workers=settings.dataloader_num_workers,
        dataloader_pin_memory=settings.dataloader_pin_memory,
        dataloader_persistent_workers=settings.dataloader_persistent_workers,
        dataloader_prefetch_factor=settings.dataloader_prefetch_factor,
        non_blocking_transfer=settings.non_blocking_transfer,
        data_path_proof_mode=settings.data_path_proof_mode,
        heartbeat_interval_optimizer_steps=settings.heartbeat_interval_optimizer_steps,
        finite_loss_max_consecutive_steps=settings.finite_loss_max_consecutive_steps,
        ref_mel_cache_enabled=settings.ref_mel_cache_enabled,
        ref_mel_cache_max_items=settings.ref_mel_cache_max_items,
        torch_profiler_enabled=settings.torch_profiler_enabled,
        torch_profiler_wait_steps=settings.torch_profiler_wait_steps,
        torch_profiler_warmup_steps=settings.torch_profiler_warmup_steps,
        torch_profiler_active_steps=settings.torch_profiler_active_steps,
        torch_profiler_repeat=settings.torch_profiler_repeat,
        torch_profiler_record_shapes=settings.torch_profiler_record_shapes,
        torch_profiler_profile_memory=settings.torch_profiler_profile_memory,
        torch_profiler_with_stack=settings.torch_profiler_with_stack,
        rocm_profiler_enabled=settings.rocm_profiler_enabled,
    )


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def _train_manifest_path(settings: TrainingSettings) -> Path:
    """Return the selected prepared-manifest path for training."""
    return (
        settings.pilot_bundle_root
        / "manifests"
        / f"{settings.train_manifest_family}.prepared.jsonl"
    )


def _eval_manifest_path(settings: TrainingSettings) -> Path:
    """Return the selected held-out eval-manifest path for training."""
    return (
        settings.pilot_bundle_root / "manifests" / f"{settings.eval_manifest_family}.prepared.jsonl"
    )


def _tracker_root(run_root: Path) -> Path:
    """Return the tracker root for one training run root."""
    return run_root / "trackers"


def _mlflow_tracking_uri(run_root: Path) -> str:
    """Return the MLflow SQLite tracking URI for one training run root."""
    return f"sqlite:///{(_tracker_root(run_root) / 'mlflow' / 'mlflow.db').as_posix()}"


def _mlflow_artifact_root(run_root: Path) -> Path:
    """Return the MLflow artifact root for one training run root."""
    return _tracker_root(run_root) / "mlflow" / "artifacts"


def _tensorboard_logging_dir(run_root: Path) -> Path:
    """Return the TensorBoard logging directory for one training run root."""
    return _tracker_root(run_root) / "tensorboard"


def _pytorch_profiling_dir(run_root: Path) -> Path:
    """Return the PyTorch profiler trace directory for one training run root."""
    return run_root / "profiling" / "pytorch"


def _rocm_profiling_dir(run_root: Path) -> Path:
    """Return the ROCm profiler trace directory for one training run root."""
    return run_root / "profiling" / "rocm"


def build_detached_training_command(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
    launch_root: Path,
    run_root: Path | None = None,
    resume_from_checkpoint: Path | None = None,
) -> tuple[list[str], Path]:
    """Build the detached Docker command for one training run."""
    effective_run_root = (
        run_root if run_root is not None else run_root_for_launch(settings, launch_id=launch_id)
    )
    container_run_root = _containerize_scratch_path(
        effective_run_root,
        scratch_root=settings.scratch_build_root,
    )
    container_train_jsonl = _containerize_scratch_path(
        _train_manifest_path(settings),
        scratch_root=settings.scratch_build_root,
    )
    container_eval_jsonl = _containerize_scratch_path(
        _eval_manifest_path(settings),
        scratch_root=settings.scratch_build_root,
    )
    container_launch_metadata_path = _containerize_scratch_path(
        launch_root / "launch.json",
        scratch_root=settings.scratch_build_root,
    )
    container_pilot_bundle_root = _containerize_scratch_path(
        settings.pilot_bundle_root,
        scratch_root=settings.scratch_build_root,
    )
    container_mlflow_artifact_root = _containerize_scratch_path(
        _mlflow_artifact_root(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_tensorboard_logging_dir = _containerize_scratch_path(
        _tensorboard_logging_dir(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_pytorch_profiling_dir = _containerize_scratch_path(
        _pytorch_profiling_dir(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_rocm_profiling_dir = _containerize_scratch_path(
        _rocm_profiling_dir(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_resume_checkpoint = None
    if resume_from_checkpoint is not None:
        container_resume_checkpoint = _containerize_scratch_path(
            resume_from_checkpoint,
            scratch_root=settings.scratch_build_root,
        )
    probe_args = [
        "--launch-id",
        launch_id,
        "--launch-metadata-path",
        container_launch_metadata_path,
        "--model-id",
        settings.model_id,
        "--train-jsonl",
        container_train_jsonl,
        "--eval-jsonl",
        container_eval_jsonl,
        "--pilot-bundle-root",
        container_pilot_bundle_root,
        "--train-manifest-family",
        settings.train_manifest_family,
        "--eval-manifest-family",
        settings.eval_manifest_family,
        "--output-dir",
        container_run_root,
        "--tracker-project-name",
        DEFAULT_TRACKER_PROJECT_NAME,
        "--mlflow-experiment-name",
        DEFAULT_MLFLOW_EXPERIMENT_NAME,
        "--mlflow-tracking-uri",
        _mlflow_tracking_uri(effective_run_root),
        "--mlflow-artifact-root",
        container_mlflow_artifact_root,
        "--tensorboard-logging-dir",
        container_tensorboard_logging_dir,
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
        "--checkpoint-interval-steps",
        str(settings.checkpoint_interval_steps),
        "--durable-checkpoint-retention",
        str(settings.durable_checkpoint_retention),
        "--durable-checkpoint-min-free-bytes",
        str(settings.durable_checkpoint_min_free_bytes),
        "--dataloader-num-workers",
        str(settings.dataloader_num_workers),
        boolean_flag("--dataloader-pin-memory", settings.dataloader_pin_memory),
        boolean_flag(
            "--dataloader-persistent-workers",
            settings.dataloader_persistent_workers,
        ),
        "--dataloader-prefetch-factor",
        str(settings.dataloader_prefetch_factor),
        boolean_flag("--non-blocking-transfer", settings.non_blocking_transfer),
        boolean_flag("--data-path-proof-mode", settings.data_path_proof_mode),
        "--heartbeat-interval-optimizer-steps",
        str(settings.heartbeat_interval_optimizer_steps),
        "--finite-loss-max-consecutive-steps",
        str(settings.finite_loss_max_consecutive_steps),
        boolean_flag("--ref-mel-cache-enabled", settings.ref_mel_cache_enabled),
        "--ref-mel-cache-max-items",
        str(settings.ref_mel_cache_max_items),
        boolean_flag("--torch-profiler-enabled", settings.torch_profiler_enabled),
        "--torch-profiler-wait-steps",
        str(settings.torch_profiler_wait_steps),
        "--torch-profiler-warmup-steps",
        str(settings.torch_profiler_warmup_steps),
        "--torch-profiler-active-steps",
        str(settings.torch_profiler_active_steps),
        "--torch-profiler-repeat",
        str(settings.torch_profiler_repeat),
        boolean_flag("--torch-profiler-record-shapes", settings.torch_profiler_record_shapes),
        boolean_flag("--torch-profiler-profile-memory", settings.torch_profiler_profile_memory),
        boolean_flag("--torch-profiler-with-stack", settings.torch_profiler_with_stack),
        "--torch-profiler-trace-dir",
        container_pytorch_profiling_dir,
    ]
    command = [
        "run",
        "-d",
        "--name",
        container_name,
        "--label",
        "sir_convert_a_lot.domain=qwen-training",
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
        "--workdir",
        "/app",
        "--entrypoint",
        "python",
        settings.image,
    ]
    if settings.rocm_profiler_enabled:
        command.extend(
            [
                "-m",
                "scripts.sir_convert_a_lot.ml.qwen.training.trainer_rocprof_wrapper",
                "--rocprof-output-dir",
                container_rocm_profiling_dir,
                "--rocprof-trace-name",
                launch_id,
                "--",
                *probe_args,
            ]
        )
    else:
        command.extend(
            [
                "-m",
                "scripts.sir_convert_a_lot.ml.qwen.training.trainer",
                *probe_args,
            ]
        )
    if container_resume_checkpoint is not None:
        command.extend(["--resume-from-checkpoint", container_resume_checkpoint])
    return command, effective_run_root


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
) -> DetachedLaunch:
    """Launch one detached training run and return deterministic metadata."""
    command, run_root = build_detached_training_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=launch_id,
        container_name=container_name,
        launch_root=launch_root,
        run_root=run_root,
        resume_from_checkpoint=resume_from_checkpoint,
    )
    container_id = docker_checked(
        command,
        label="docker run qwen detached training",
    ).strip()
    tracking_root = _tracker_root(run_root)
    bundle_summary = load_optional_training_bundle_summary(settings.pilot_bundle_root)
    throughput_policy = resolve_throughput_batch_policy(
        profile_label=settings.throughput_profile_label,
        max_batch_size=settings.batch_size,
    )
    return DetachedLaunch(
        generated_at=_utc_now_iso(),
        launch_id=launch_id,
        container_name=container_name,
        container_id=container_id,
        repo_root=repo_root.as_posix(),
        run_root=run_root.as_posix(),
        pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
        train_jsonl=_train_manifest_path(settings).as_posix(),
        eval_jsonl=_eval_manifest_path(settings).as_posix(),
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
            "mlflow_tracking_uri": _mlflow_tracking_uri(run_root),
            "mlflow_artifact_root": _mlflow_artifact_root(run_root).as_posix(),
            "tensorboard_logging_dir": _tensorboard_logging_dir(run_root).as_posix(),
            "tracker_root": tracking_root.as_posix(),
        },
    )


def inspect_detached_training(launch: DetachedLaunch) -> DetachedStatus:
    """Inspect one detached training container and its artifacts."""
    raw_inspect = docker_checked(
        ["inspect", launch.container_name],
        label="docker inspect qwen detached training",
    )
    payload = json.loads(raw_inspect)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise SystemExit("Detached training inspect payload was malformed.")
    inspect_payload = payload[0]
    state = inspect_payload.get("State")
    if not isinstance(state, dict):
        raise SystemExit("Detached training inspect payload lacked a valid `State` object.")
    run_root = Path(launch.run_root)
    pilot_status = _load_optional_json(run_root / "status.json")
    pilot_report = _load_optional_json(run_root / "report.json")
    latest_checkpoint = _load_optional_json(run_root / "latest_checkpoint.json")
    phase_history: list[Mapping[str, object]] | None = None
    if pilot_status is not None:
        raw_phase_history = pilot_status.get("phase_history")
        if isinstance(raw_phase_history, list):
            parsed_phase_history: list[Mapping[str, object]] = []
            for event in raw_phase_history:
                if isinstance(event, Mapping):
                    parsed_phase_history.append(event)
            phase_history = parsed_phase_history
    logs_tail = docker_checked(
        ["logs", "--tail", "200", launch.container_name],
        label="docker logs qwen detached training",
    )
    monitor_summary = inspect_resource_monitor(
        launch.resource_monitor,
        phase_history=phase_history,
    )
    return DetachedStatus(
        checked_at=_utc_now_iso(),
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=str(inspect_payload.get("Id", "")),
        status=str(state.get("Status", "")),
        running=bool(state.get("Running")),
        exit_code=int(state.get("ExitCode", 0)),
        oom_killed=bool(state.get("OOMKilled")),
        started_at=str(state.get("StartedAt", "")),
        finished_at=str(state.get("FinishedAt", "")),
        pilot_status_found=pilot_status is not None,
        pilot_status=pilot_status,
        pilot_report_found=pilot_report is not None,
        pilot_report=pilot_report,
        latest_checkpoint_found=latest_checkpoint is not None,
        latest_checkpoint=latest_checkpoint,
        resource_monitor=monitor_summary,
        logs_tail=logs_tail,
    )


def stop_detached_training(launch: DetachedLaunch) -> DetachedStop:
    """Stop one detached training container intentionally."""
    stop_output = docker_checked(
        ["stop", "--time", "300", launch.container_name],
        label="docker stop qwen detached training",
    )
    return DetachedStop(
        stopped_at=_utc_now_iso(),
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=launch.container_id,
        stop_output=stop_output.strip(),
    )


# --- Internal Helpers ---


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_optional_json(path: Path) -> dict[str, object] | None:
    """Load one optional JSON artifact, returning `None` when it is absent or malformed."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (json.JSONDecodeError, OSError):
        return None
