"""Detached runtime helpers for the Task 101 Qwen Hemma pilot lane.

Purpose:
    Launch and inspect one detached bounded Swedish Qwen fine-tuning pilot on
    Hemma so training is fully decoupled from the client session and persists
    machine-readable evidence under SSD scratch.

Relationships:
    - Used by `run_task101_hemma_qwen_pilot.py`.
    - Reuses the shared Task 100 image-build and cache-mount helpers.
    - Executes `task101_qwen_pilot_probe.py` inside the shared Qwen runtime
      image.
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
    promoted_corpus_root: Path
    runs_root: Path
    model_id: str
    train_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int


@dataclass(frozen=True)
class Task101DetachedLaunch:
    """Deterministic launch metadata for one detached Task 101 pilot."""

    generated_at: str
    launch_id: str
    container_name: str
    container_id: str
    repo_root: str
    run_root: str
    promoted_corpus_root: str
    train_manifest_family: str
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
    logs_tail: str


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


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def _train_manifest_path(settings: Task101PilotSettings) -> Path:
    """Return the selected prepared-manifest path for the detached pilot."""
    return (
        settings.promoted_corpus_root
        / "manifests"
        / f"{settings.train_manifest_family}.prepared.jsonl"
    )


def build_detached_pilot_command(
    settings: Task101PilotSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
) -> tuple[list[str], Path]:
    """Build the detached Docker command for one Task 101 pilot run."""
    run_root = run_root_for_launch(settings, launch_id=launch_id)
    container_run_root = _containerize_scratch_path(
        run_root,
        scratch_root=settings.scratch_build_root,
    )
    container_train_jsonl = _containerize_scratch_path(
        _train_manifest_path(settings),
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
    ]
    return command, run_root


def launch_detached_pilot(
    settings: Task101PilotSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
) -> Task101DetachedLaunch:
    """Launch one detached Task 101 pilot and return deterministic metadata."""
    command, run_root = build_detached_pilot_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id=launch_id,
        container_name=container_name,
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
        promoted_corpus_root=settings.promoted_corpus_root.as_posix(),
        train_manifest_family=settings.train_manifest_family,
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
        logs_tail=logs_tail,
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
