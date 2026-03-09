"""Detached stage orchestration helpers for isolated Qwen preprocessing on Hemma.

Purpose:
    Launch and inspect one detached containerized Task 103 stage at a time so
    Hemma never rolls directly from concurrent row-processing into GPU-heavy
    finalization inside one long-lived runtime.

Relationships:
    - Used by `run_task114_hemma_qwen_isolated_stages.py`.
    - Reuses Task 109 container command construction for stage-specific
      container execution.
    - Reads Task 103 run-root artifacts to decide whether row-processing or
      finalization should launch next.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    MountResolution,
    docker_checked,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import Task103Stage
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import spool_rows_dir
from scripts.sir_convert_a_lot.devops.task109_qwen_containerized_preprocessing_runtime import (
    Task109ContainerizedPreprocessingSettings,
    build_containerized_preprocessing_command,
)


@dataclass(frozen=True)
class Task114DetachedStageLaunch:
    """Deterministic launch metadata for one detached isolated stage."""

    generated_at: str
    launch_id: str
    stage: Task103Stage
    container_name: str
    container_id: str
    repo_root: str
    task103_run_root: str
    task103_promoted_root: str
    command: list[str]


@dataclass(frozen=True)
class Task114DetachedStageStatus:
    """Deterministic status view for one detached isolated-stage container."""

    checked_at: str
    launch_id: str
    stage: Task103Stage
    container_name: str
    container_id: str
    status: str
    running: bool
    exit_code: int
    oom_killed: bool
    started_at: str
    finished_at: str
    task103_report_found: bool
    task103_report: dict[str, object] | None
    task103_status_found: bool
    task103_status: dict[str, object] | None
    logs_tail: str


@dataclass(frozen=True)
class Task114DetachedStageStop:
    """Deterministic stop result for one detached isolated-stage container."""

    stopped_at: str
    launch_id: str
    stage: Task103Stage
    container_name: str
    container_id: str
    stop_output: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_launch_id(stage: Task103Stage) -> str:
    """Build one deterministic launch identifier for a detached stage."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"task114-{stage}-{timestamp}".lower()


def default_container_name(launch_id: str) -> str:
    """Build one deterministic detached container name for a launch id."""
    return f"{launch_id}-container"


def resolve_next_stage(
    *,
    run_root: Path,
) -> Task103Stage | None:
    """Resolve the next canonical stage for one existing run root."""
    has_spool_rows = any(spool_rows_dir(run_root).rglob("*.json"))
    has_prepared_manifests = any((run_root / "manifests").glob("*.prepared.jsonl"))
    has_report = (run_root / "report.json").exists()
    run_status = _load_optional_json(run_root / "status.json")
    if has_report:
        return None
    if not has_spool_rows:
        return "row-processing"
    if not has_prepared_manifests:
        return "finalization"
    if (
        run_status is not None
        and run_status.get("stage") == "finalization"
        and run_status.get("status") in {"completed", "promoted"}
    ):
        return "reports"
    return "finalization"


def build_detached_stage_command(
    settings: Task109ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
    scratch_mount: MountResolution,
    container_name: str,
) -> list[str]:
    """Build the detached Docker command for one isolated Task 103 stage."""
    attached_command = build_containerized_preprocessing_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
        scratch_mount=scratch_mount,
    )
    detached_command = [
        "run",
        "-d",
        "--name",
        container_name,
        "--label",
        "sir_convert_a_lot.task=task114-qwen-isolated-stage",
        "--label",
        f"sir_convert_a_lot.task103_stage={settings.task103_stage}",
    ]
    for token in attached_command[1:]:
        if token == "--rm":
            continue
        detached_command.append(token)
    return detached_command


def launch_detached_stage(
    settings: Task109ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
) -> Task114DetachedStageLaunch:
    """Launch one detached isolated stage and return deterministic metadata."""
    command = build_detached_stage_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
        scratch_mount=scratch_mount,
        container_name=container_name,
    )
    if settings.task103_run_root is not None:
        task103_run_root = settings.task103_run_root
    else:
        task103_run_id = settings.task103_run_id or launch_id
        task103_run_root = settings.task103_runs_root / task103_run_id
    container_id = docker_checked(
        command,
        label="docker run task114 detached isolated stage",
    ).strip()
    return Task114DetachedStageLaunch(
        generated_at=utc_now_iso(),
        launch_id=launch_id,
        stage=settings.task103_stage,
        container_name=container_name,
        container_id=container_id,
        repo_root=repo_root.as_posix(),
        task103_run_root=task103_run_root.as_posix(),
        task103_promoted_root=(
            settings.scratch_build_root / "reference" / "qwen3-tts-swedish-corpus"
        ).as_posix(),
        command=["sudo", "-n", "docker", *command],
    )


def inspect_detached_stage(launch: Task114DetachedStageLaunch) -> Task114DetachedStageStatus:
    """Inspect one detached isolated-stage container and its Task 103 outputs."""
    raw_inspect = docker_checked(
        ["inspect", launch.container_name],
        label="docker inspect task114 detached isolated stage",
    )
    payload = json.loads(raw_inspect)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise SystemExit("Detached Task 114 inspect payload was malformed.")
    inspect_payload = payload[0]
    state = inspect_payload.get("State")
    if not isinstance(state, dict):
        raise SystemExit("Detached Task 114 inspect payload lacked a valid `State` object.")
    task103_run_root = Path(launch.task103_run_root)
    task103_report = _load_optional_json(task103_run_root / "report.json")
    task103_status = _load_optional_json(task103_run_root / "status.json")
    logs_tail = docker_checked(
        ["logs", "--tail", "200", launch.container_name],
        label="docker logs task114 detached isolated stage",
    )
    return Task114DetachedStageStatus(
        checked_at=utc_now_iso(),
        launch_id=launch.launch_id,
        stage=launch.stage,
        container_name=launch.container_name,
        container_id=_required_str(inspect_payload, "Id"),
        status=_required_str(state, "Status"),
        running=_required_bool(state, "Running"),
        exit_code=_required_int(state, "ExitCode"),
        oom_killed=_required_bool(state, "OOMKilled"),
        started_at=_required_str(state, "StartedAt"),
        finished_at=_required_str(state, "FinishedAt"),
        task103_report_found=task103_report is not None,
        task103_report=task103_report,
        task103_status_found=task103_status is not None,
        task103_status=task103_status,
        logs_tail=logs_tail,
    )


def stop_detached_stage(launch: Task114DetachedStageLaunch) -> Task114DetachedStageStop:
    """Stop one detached isolated-stage container intentionally."""
    stop_output = docker_checked(
        ["stop", launch.container_name],
        label="docker stop task114 detached isolated stage",
    )
    return Task114DetachedStageStop(
        stopped_at=utc_now_iso(),
        launch_id=launch.launch_id,
        stage=launch.stage,
        container_name=launch.container_name,
        container_id=launch.container_id,
        stop_output=stop_output.strip(),
    )


def _load_optional_json(path: Path) -> dict[str, object] | None:
    """Load one optional JSON object from disk when present."""
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except PermissionError:
        raw_payload = subprocess_checked(
            ["sudo", "-n", "cat", path.as_posix()],
            label="sudo cat task114 detached artifact",
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
        raise SystemExit(f"Detached Task 114 inspect payload returned malformed `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Detached Task 114 inspect payload returned malformed `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Detached Task 114 inspect payload returned malformed `{key}`.")
    return value
