"""Runtime helpers for detached Task 108 Qwen preprocessing proofs on Hemma.

Purpose:
    Launch and inspect the bounded Task 108 public-corpus preprocessing proof
    as a detached Docker container so long-running Hemma work does not depend
    on the local client session.

Relationships:
    - Used by `run_task108_hemma_qwen_detached_proof.py`.
    - Reuses Task 100 Docker/image helpers and Task 109 command construction.
    - Reads the canonical Task 103 report written under the repo-mounted
      `build/reference/qwen3-tts-swedish-corpus/` artifact root.
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
from scripts.sir_convert_a_lot.devops.task109_qwen_containerized_preprocessing_runtime import (
    Task109ContainerizedPreprocessingSettings,
    build_containerized_preprocessing_command,
)

DEFAULT_T103_PROMOTED_ROOT = Path("build/reference/qwen3-tts-swedish-corpus")


@dataclass(frozen=True)
class Task108DetachedProofLaunch:
    """Deterministic launch metadata for one detached Task 108 proof."""

    generated_at: str
    container_name: str
    container_id: str
    repo_root: str
    task103_run_root: str
    task103_promoted_root: str
    command: list[str]


@dataclass(frozen=True)
class Task108DetachedProofStatus:
    """Deterministic status view for one detached Task 108 proof container."""

    checked_at: str
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
    logs_tail: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_container_name(prefix: str) -> str:
    """Build one deterministic detached container name with a UTC timestamp."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}".lower()


def build_detached_task108_command(
    settings: Task109ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
    scratch_mount: MountResolution,
    container_name: str,
) -> list[str]:
    """Build the detached Docker command for one Task 108 proof run."""
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
        "sir_convert_a_lot.task=task108-qwen-detached-proof",
    ]
    for token in attached_command[1:]:
        if token == "--rm":
            continue
        detached_command.append(token)
    return detached_command


def launch_detached_task108_proof(
    settings: Task109ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
    scratch_mount: MountResolution,
    container_name: str,
) -> Task108DetachedProofLaunch:
    """Launch one detached Task 108 proof container and return launch metadata."""
    command = build_detached_task108_command(
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
        task103_run_id = settings.task103_run_id or container_name
        task103_run_root = settings.task103_runs_root / task103_run_id
    container_id = docker_checked(
        command,
        label="docker run task108 detached preprocessing proof",
    ).strip()
    return Task108DetachedProofLaunch(
        generated_at=utc_now_iso(),
        container_name=container_name,
        container_id=container_id,
        repo_root=repo_root.as_posix(),
        task103_run_root=task103_run_root.as_posix(),
        task103_promoted_root=(repo_root / DEFAULT_T103_PROMOTED_ROOT).as_posix(),
        command=["sudo", "-n", "docker", *command],
    )


def inspect_detached_task108_proof(
    launch: Task108DetachedProofLaunch,
) -> Task108DetachedProofStatus:
    """Inspect one detached Task 108 proof container plus canonical report output."""
    raw_inspect = docker_checked(
        ["inspect", launch.container_name],
        label="docker inspect task108 detached preprocessing proof",
    )
    payload = json.loads(raw_inspect)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise SystemExit("Detached Task 108 inspect payload was malformed.")
    inspect_payload = payload[0]
    state = inspect_payload.get("State")
    if not isinstance(state, dict):
        raise SystemExit("Detached Task 108 inspect payload lacked a valid `State` object.")
    status = _required_str(state, "Status")
    running = _required_bool(state, "Running")
    exit_code = _required_int(state, "ExitCode")
    oom_killed = _required_bool(state, "OOMKilled")
    started_at = _required_str(state, "StartedAt")
    finished_at = _required_str(state, "FinishedAt")
    container_id = _required_str(inspect_payload, "Id")

    task103_report_path = Path(launch.task103_run_root) / "report.json"
    task103_report: dict[str, object] | None = None
    if task103_report_path.exists():
        loaded_report = json.loads(task103_report_path.read_text(encoding="utf-8"))
        if isinstance(loaded_report, dict):
            task103_report = loaded_report

    logs_tail = docker_checked(
        ["logs", "--tail", "200", launch.container_name],
        label="docker logs task108 detached preprocessing proof",
    )

    return Task108DetachedProofStatus(
        checked_at=utc_now_iso(),
        container_name=launch.container_name,
        container_id=container_id,
        status=status,
        running=running,
        exit_code=exit_code,
        oom_killed=oom_killed,
        started_at=started_at,
        finished_at=finished_at,
        task103_report_found=task103_report is not None,
        task103_report=task103_report,
        logs_tail=logs_tail,
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Detached Task 108 inspect payload returned malformed `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Detached Task 108 inspect payload returned malformed `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Detached Task 108 inspect payload returned malformed `{key}`.")
    return value
