"""Detached runtime helpers for the Task 101 Qwen Hemma pilot lane.

Purpose:
    Launch and inspect one detached bounded Swedish Qwen fine-tuning pilot on
    Hemma so training is fully decoupled from the client session and persists
    machine-readable evidence under SSD scratch.

Relationships:
    - Used by `run_task101_hemma_qwen_pilot.py`.
    - Reuses the shared Task 100 image-build and cache-mount helpers.
    - Consumes the deterministic pilot bundle materialized by
      `task101_qwen_pilot_bundle.py`.
    - Executes `task101_qwen_pilot_probe.py` inside the shared Qwen runtime image.
    - Reuses `task101_qwen_pilot_runtime_contract.py` for immutable data
      contracts and `task101_qwen_pilot_runtime_artifacts.py` for detached
      status/artifact parsing.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.devops import task101_qwen_pilot_runtime_contract as runtime_contract
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    MountResolution,
    docker_checked,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime_artifacts import (
    _load_optional_json,
    _required_bool,
    _required_int,
    _required_str,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime_contract import (
    Task101DetachedLaunch,
    Task101DetachedStatus,
    Task101DetachedStop,
    Task101PilotSettings,
    _utc_now_iso,
    run_root_for_launch,
    snapshot_settings,
)

CONTAINER_BUILD_ROOT = Path("/app/build")
DEFAULT_TRACKER_PROJECT_NAME = "task101-qwen-pilot"
DEFAULT_MLFLOW_EXPERIMENT_NAME = "task101-qwen-pilot"
DEFAULT_TRACKER_BACKENDS = ("mlflow", "tensorboard")
Task101PilotSettingsSnapshot = runtime_contract.Task101PilotSettingsSnapshot
default_container_name = runtime_contract.default_container_name
default_launch_id = runtime_contract.default_launch_id
settings_from_snapshot = runtime_contract.settings_from_snapshot


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def _train_manifest_path(settings: Task101PilotSettings) -> Path:
    """Return the selected prepared-manifest path for the detached pilot."""
    return (
        settings.pilot_bundle_root
        / "manifests"
        / f"{settings.train_manifest_family}.prepared.jsonl"
    )


def _eval_manifest_path(settings: Task101PilotSettings) -> Path:
    """Return the selected held-out eval-manifest path for the detached pilot."""
    return (
        settings.pilot_bundle_root / "manifests" / f"{settings.eval_manifest_family}.prepared.jsonl"
    )


def _tracker_root(run_root: Path) -> Path:
    """Return the tracker root for one Task 101 run root."""
    return run_root / "trackers"


def _mlflow_tracking_uri(run_root: Path) -> str:
    """Return the MLflow SQLite tracking URI for one Task 101 run root."""
    return f"sqlite:///{(_tracker_root(run_root) / 'mlflow' / 'mlflow.db').as_posix()}"


def _mlflow_artifact_root(run_root: Path) -> Path:
    """Return the MLflow artifact root for one Task 101 run root."""
    return _tracker_root(run_root) / "mlflow" / "artifacts"


def _tensorboard_logging_dir(run_root: Path) -> Path:
    """Return the TensorBoard logging directory for one Task 101 run root."""
    return _tracker_root(run_root) / "tensorboard"


def build_detached_pilot_command(
    settings: Task101PilotSettings,
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
    """Build the detached Docker command for one Task 101 pilot run."""
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
    container_resume_checkpoint = None
    if resume_from_checkpoint is not None:
        container_resume_checkpoint = _containerize_scratch_path(
            resume_from_checkpoint,
            scratch_root=settings.scratch_build_root,
        )
    command = [
        "run",
        "-d",
        "--name",
        container_name,
        "--label",
        "sir_convert_a_lot.task=task101-qwen-pilot",
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
        "-m",
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe",
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
    ]
    if container_resume_checkpoint is not None:
        command.extend(["--resume-from-checkpoint", container_resume_checkpoint])
    return command, effective_run_root


def launch_detached_pilot(
    settings: Task101PilotSettings,
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
) -> Task101DetachedLaunch:
    """Launch one detached Task 101 pilot and return deterministic metadata."""
    command, run_root = build_detached_pilot_command(
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
        label="docker run task101 detached pilot",
    ).strip()
    tracking_root = _tracker_root(run_root)
    return Task101DetachedLaunch(
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


def inspect_detached_pilot(launch: Task101DetachedLaunch) -> Task101DetachedStatus:
    """Inspect one detached Task 101 container and its training artifacts."""
    raw_inspect = docker_checked(
        ["inspect", launch.container_name],
        label="docker inspect task101 detached pilot",
    )
    payload = json.loads(raw_inspect)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise SystemExit("Detached Task 101 inspect payload was malformed.")
    inspect_payload = payload[0]
    state = inspect_payload.get("State")
    if not isinstance(state, dict):
        raise SystemExit("Detached Task 101 inspect payload lacked a valid `State` object.")
    run_root = Path(launch.run_root)
    pilot_status = _load_optional_json(run_root / "status.json")
    pilot_report = _load_optional_json(run_root / "report.json")
    latest_checkpoint = _load_optional_json(run_root / "latest_checkpoint.json")
    logs_tail = docker_checked(
        ["logs", "--tail", "200", launch.container_name],
        label="docker logs task101 detached pilot",
    )
    return Task101DetachedStatus(
        checked_at=_utc_now_iso(),
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=_required_str(inspect_payload, "Id"),
        status=_required_str(state, "Status"),
        running=_required_bool(state, "Running"),
        exit_code=_required_int(state, "ExitCode"),
        oom_killed=_required_bool(state, "OOMKilled"),
        started_at=_required_str(state, "StartedAt"),
        finished_at=_required_str(state, "FinishedAt"),
        pilot_status_found=pilot_status is not None,
        pilot_status=pilot_status,
        pilot_report_found=pilot_report is not None,
        pilot_report=pilot_report,
        latest_checkpoint_found=latest_checkpoint is not None,
        latest_checkpoint=latest_checkpoint,
        logs_tail=logs_tail,
    )


def stop_detached_pilot(launch: Task101DetachedLaunch) -> Task101DetachedStop:
    """Stop one detached Task 101 pilot container intentionally."""
    stop_output = docker_checked(
        ["stop", "--time", "300", launch.container_name],
        label="docker stop task101 detached pilot",
    )
    return Task101DetachedStop(
        stopped_at=_utc_now_iso(),
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=launch.container_id,
        stop_output=stop_output.strip(),
    )
