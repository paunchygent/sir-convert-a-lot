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
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    MountResolution,
    docker_checked,
)

CONTAINER_BUILD_ROOT = Path("/app/build")


@dataclass(frozen=True)
class Task101PilotSettings:
    """Normalized settings for the detached Task 101 Hemma pilot."""

    output_root: Path
    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    scratch_build_root: Path
    scratch_build_home_mount: Path
    pilot_bundle_root: Path
    runs_root: Path
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int
    checkpoint_interval_steps: int


@dataclass(frozen=True)
class Task101PilotSettingsSnapshot:
    """JSON-serializable snapshot of one Task 101 pilot configuration."""

    output_root: str
    image: str
    hf_cache_dir: str
    hf_cache_home_mount: str
    scratch_build_root: str
    scratch_build_home_mount: str
    pilot_bundle_root: str
    runs_root: str
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int
    checkpoint_interval_steps: int


@dataclass(frozen=True)
class Task101DetachedLaunch:
    """Deterministic launch metadata for one detached Task 101 pilot."""

    generated_at: str
    launch_id: str
    container_name: str
    container_id: str
    repo_root: str
    run_root: str
    pilot_bundle_root: str
    train_jsonl: str
    eval_jsonl: str
    train_manifest_family: str
    eval_manifest_family: str
    dockerfile_path: str | None
    resumed_from_checkpoint_path: str | None
    settings: Task101PilotSettingsSnapshot
    command: list[str]


@dataclass(frozen=True)
class Task101DetachedStatus:
    """Deterministic status view for one detached Task 101 pilot."""

    checked_at: str
    launch_id: str
    container_name: str
    container_id: str
    status: str
    running: bool
    exit_code: int
    oom_killed: bool
    started_at: str
    finished_at: str
    pilot_status_found: bool
    pilot_status: dict[str, object] | None
    pilot_report_found: bool
    pilot_report: dict[str, object] | None
    latest_checkpoint_found: bool
    latest_checkpoint: dict[str, object] | None
    logs_tail: str


@dataclass(frozen=True)
class Task101DetachedStop:
    """Deterministic stop result for one detached Task 101 pilot container."""

    stopped_at: str
    launch_id: str
    container_name: str
    container_id: str
    stop_output: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_launch_id() -> str:
    """Return one deterministic launch identifier for the detached pilot."""
    return f"task101-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def default_container_name(launch_id: str) -> str:
    """Return the canonical detached container name for one launch id."""
    return f"{launch_id}-container"


def run_root_for_launch(settings: Task101PilotSettings, *, launch_id: str) -> Path:
    """Return the scratch-backed run root for one detached pilot launch."""
    return settings.runs_root / launch_id


def snapshot_settings(settings: Task101PilotSettings) -> Task101PilotSettingsSnapshot:
    """Convert one runtime settings object into a JSON-safe snapshot."""
    return Task101PilotSettingsSnapshot(
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
        lr=settings.lr,
        num_epochs=settings.num_epochs,
        max_steps=settings.max_steps,
        checkpoint_interval_steps=settings.checkpoint_interval_steps,
    )


def settings_from_snapshot(snapshot: Task101PilotSettingsSnapshot) -> Task101PilotSettings:
    """Rehydrate runtime settings from one launch metadata snapshot."""
    return Task101PilotSettings(
        output_root=Path(snapshot.output_root),
        image=snapshot.image,
        hf_cache_dir=Path(snapshot.hf_cache_dir),
        hf_cache_home_mount=Path(snapshot.hf_cache_home_mount),
        scratch_build_root=Path(snapshot.scratch_build_root),
        scratch_build_home_mount=Path(snapshot.scratch_build_home_mount),
        pilot_bundle_root=Path(snapshot.pilot_bundle_root),
        runs_root=Path(snapshot.runs_root),
        model_id=snapshot.model_id,
        train_manifest_family=snapshot.train_manifest_family,
        eval_manifest_family=snapshot.eval_manifest_family,
        batch_size=snapshot.batch_size,
        lr=snapshot.lr,
        num_epochs=snapshot.num_epochs,
        max_steps=snapshot.max_steps,
        checkpoint_interval_steps=snapshot.checkpoint_interval_steps,
    )


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
        settings.pilot_bundle_root
        / "manifests"
        / f"{settings.eval_manifest_family}.prepared.jsonl"
    )


def build_detached_pilot_command(
    settings: Task101PilotSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
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
        "--model-id",
        settings.model_id,
        "--train-jsonl",
        container_train_jsonl,
        "--eval-jsonl",
        container_eval_jsonl,
        "--output-dir",
        container_run_root,
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
        run_root=run_root,
        resume_from_checkpoint=resume_from_checkpoint,
    )
    container_id = docker_checked(
        command,
        label="docker run task101 detached pilot",
    ).strip()
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


def _load_optional_json(path: Path) -> dict[str, object] | None:
    """Load one optional JSON object from disk, retrying via sudo if needed."""
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except PermissionError:
        raw_payload = subprocess_checked(
            ["sudo", "-n", "cat", path.as_posix()],
            label="sudo cat task101 detached artifact",
        )
        loaded = json.loads(raw_payload)
    if not isinstance(loaded, dict):
        raise SystemExit(f"Expected one JSON object in `{path.as_posix()}`.")
    return loaded


def subprocess_checked(command: list[str], *, label: str) -> str:
    """Run one subprocess command and return stdout or raise on failure."""
    import subprocess

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Detached Task 101 inspect payload returned malformed `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Detached Task 101 inspect payload returned malformed `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Detached Task 101 inspect payload returned malformed `{key}`.")
    return value
