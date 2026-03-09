"""Runtime helpers for detached Task 113 Hemma Docker storage remediation.

Purpose:
    Launch and inspect the Task 113 Docker storage migration through a detached
    remote tmux session so host-wide Hemma maintenance work does not depend on
    the local client session remaining attached.

Relationships:
    - Used by `run_task113_hemma_docker_storage_detached.py`.
    - Wraps the committed `task-113-docker-storage-remediation` runner.
    - Writes local launch/status metadata while the canonical migration report
      is still produced by the remote Task 113 runner.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_REMOTE_REPO_ROOT = Path("/home/paunchygent/apps/sir-convert-a-lot")
DEFAULT_REMOTE_OUTPUT_ROOT = DEFAULT_REMOTE_REPO_ROOT / "build" / "verification" / (
    "task-113-hemma-docker-storage-remediation"
)
DEFAULT_SESSION_NAME_PREFIX = "task113-docker-storage"


@dataclass(frozen=True)
class Task113DetachedLaunch:
    """Deterministic launch metadata for one detached Task 113 migration run."""

    generated_at: str
    session_name: str
    remote_repo_root: str
    remote_output_root: str
    remote_log_path: str
    remote_exit_code_path: str
    remote_command: str


@dataclass(frozen=True)
class Task113DetachedStatus:
    """Deterministic status snapshot for one detached Task 113 migration run."""

    checked_at: str
    session_name: str
    session_exists: bool
    exit_code: int | None
    report_found: bool
    report_payload: dict[str, object] | None
    log_tail: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_session_name(prefix: str) -> str:
    """Build one deterministic tmux session name with a UTC timestamp."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}".lower()


def run_local_checked(command: list[str], *, label: str) -> str:
    """Run one local command and return stdout or fail with diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def run_local_optional(command: list[str]) -> tuple[int, str, str]:
    """Run one local command and return returncode/stdout/stderr without failing."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def build_remote_shell_command(*, output_root: Path) -> tuple[str, Path, Path]:
    """Build the remote shell command for one detached Task 113 migration run."""
    log_path = output_root / "live.log"
    exit_code_path = output_root / "exit_code.txt"
    remote_command = " ".join(
        [
            f"mkdir -p {shlex.quote(output_root.as_posix())}",
            "&&",
            f"cd {shlex.quote(DEFAULT_REMOTE_REPO_ROOT.as_posix())}",
            "&&",
            (
                "pdm run task-113-docker-storage-remediation "
                f"--output-root {shlex.quote(output_root.as_posix())}"
            ),
            f"> {shlex.quote(log_path.as_posix())} 2>&1",
            ";",
            f"printf '%s\\n' $? > {shlex.quote(exit_code_path.as_posix())}",
        ]
    )
    return remote_command, log_path, exit_code_path


def launch_detached_task113_migration(
    *,
    session_name: str,
    output_root: Path,
) -> Task113DetachedLaunch:
    """Launch one detached remote tmux session for Task 113."""
    remote_command, log_path, exit_code_path = build_remote_shell_command(output_root=output_root)
    run_local_checked(
        [
            "pdm",
            "run",
            "run-hemma",
            "--",
            "tmux",
            "new-session",
            "-d",
            "-s",
            session_name,
            "/bin/bash",
            "-lc",
            remote_command,
        ],
        label="launch detached task113 tmux session",
    )
    return Task113DetachedLaunch(
        generated_at=utc_now_iso(),
        session_name=session_name,
        remote_repo_root=DEFAULT_REMOTE_REPO_ROOT.as_posix(),
        remote_output_root=output_root.as_posix(),
        remote_log_path=log_path.as_posix(),
        remote_exit_code_path=exit_code_path.as_posix(),
        remote_command=remote_command,
    )


def inspect_detached_task113_migration(
    launch: Task113DetachedLaunch,
) -> Task113DetachedStatus:
    """Inspect one detached Task 113 tmux session plus report/log artifacts."""
    session_returncode, _, _ = run_local_optional(
        [
            "pdm",
            "run",
            "run-hemma",
            "--",
            "tmux",
            "has-session",
            "-t",
            launch.session_name,
        ]
    )
    session_exists = session_returncode == 0

    exit_code = _read_optional_remote_int(Path(launch.remote_exit_code_path))
    report_path = Path(launch.remote_output_root) / "report.json"
    report_payload = _read_optional_remote_json(report_path)
    log_tail = _read_optional_remote_tail(Path(launch.remote_log_path), line_count=200)

    return Task113DetachedStatus(
        checked_at=utc_now_iso(),
        session_name=launch.session_name,
        session_exists=session_exists,
        exit_code=exit_code,
        report_found=report_payload is not None,
        report_payload=report_payload,
        log_tail=log_tail,
    )


def _read_optional_remote_int(path: Path) -> int | None:
    """Read one optional remote integer file."""
    payload = _read_optional_remote_file(path)
    if payload is None:
        return None
    stripped = payload.strip()
    if stripped == "":
        return None
    try:
        return int(stripped)
    except ValueError as exc:
        raise SystemExit(f"Detached Task 113 exit code file was malformed: {stripped}") from exc


def _read_optional_remote_json(path: Path) -> dict[str, object] | None:
    """Read one optional remote JSON file as a dictionary."""
    payload = _read_optional_remote_file(path)
    if payload is None:
        return None
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        raise SystemExit("Detached Task 113 remote JSON payload was malformed.")
    return loaded


def _read_optional_remote_tail(path: Path, *, line_count: int) -> str:
    """Read one optional remote file tail."""
    command = (
        f"if [ -f {shlex.quote(path.as_posix())} ]; then "
        f"tail -n {line_count} {shlex.quote(path.as_posix())}; "
        "fi"
    )
    return run_local_checked(
        ["pdm", "run", "run-hemma", "--", "/bin/bash", "-lc", command],
        label="read optional remote log tail task113",
    )


def _read_optional_remote_file(path: Path) -> str | None:
    """Read one optional remote file and return its contents."""
    command = (
        f"if [ -f {shlex.quote(path.as_posix())} ]; then "
        f"cat {shlex.quote(path.as_posix())}; "
        "fi"
    )
    payload = run_local_checked(
        ["pdm", "run", "run-hemma", "--", "/bin/bash", "-lc", command],
        label="read optional remote file task113",
    )
    return payload if payload != "" else None
