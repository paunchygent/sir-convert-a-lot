"""Detached host-process helpers for the Story 30 backward-lineage proof.

Purpose:
    Launch and inspect one detached Hemma host worker that runs the bounded
    backward-lineage proof so GPU evidence collection survives the local
    client session.

Relationships:
    - Launches `story30_backward_lineage_detached_worker.py`.
    - Used by `story30_backward_lineage_proof.py` for remote launch/status.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso

_WORKER_MODULE = (
    "scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_detached_worker"
)
_DEFAULT_LOG_NAME = "proof.log"
_DEFAULT_WORKER_STATUS_NAME = "worker-status.json"
_REPORT_NAME = "report.json"
_FAILURE_NAME = "failure.txt"


@dataclass(frozen=True)
class DetachedBackwardLineageLaunch:
    """Deterministic launch metadata for one detached T212 proof run."""

    generated_at: str
    launch_id: str
    pid: int
    repo_root: str
    output_root: str
    log_path: str
    worker_status_path: str
    report_path: str
    failure_path: str
    proof_args: list[str]
    command: list[str]


@dataclass(frozen=True)
class DetachedBackwardLineageStatus:
    """Deterministic status view for one detached T212 proof run."""

    checked_at: str
    launch_id: str
    pid: int
    running: bool
    exit_code: int | None
    started_at: str
    finished_at: str | None
    report_found: bool
    failure_found: bool
    report: dict[str, object] | None
    failure_text: str | None
    logs_tail: str


def log_path(output_root: Path) -> Path:
    """Return the canonical detached proof log path."""
    return output_root / _DEFAULT_LOG_NAME


def worker_status_path(output_root: Path) -> Path:
    """Return the canonical detached proof worker-status path."""
    return output_root / _DEFAULT_WORKER_STATUS_NAME


def report_path(output_root: Path) -> Path:
    """Return the canonical proof report artifact path."""
    return output_root / _REPORT_NAME


def failure_path(output_root: Path) -> Path:
    """Return the canonical proof failure artifact path."""
    return output_root / _FAILURE_NAME


def normalize_proof_args(output_root: Path, raw_proof_args: Sequence[str]) -> tuple[str, ...]:
    """Normalize pass-through proof args and ensure the output root is explicit."""
    proof_args = list(raw_proof_args)
    if len(proof_args) > 0 and proof_args[0] == "--":
        proof_args = proof_args[1:]
    if "--output-root" not in proof_args and not any(
        argument.startswith("--output-root=") for argument in proof_args
    ):
        proof_args = ["--output-root", output_root.as_posix(), *proof_args]
    return tuple(proof_args)


def build_detached_worker_command(output_root: Path, proof_args: Sequence[str]) -> list[str]:
    """Build the background worker command for one detached T212 proof run."""
    normalized_proof_args = normalize_proof_args(output_root, proof_args)
    return [
        sys.executable,
        "-m",
        _WORKER_MODULE,
        "--output-root",
        output_root.as_posix(),
        "--",
        *normalized_proof_args,
    ]


def launch_detached_backward_lineage_proof(
    *,
    output_root: Path,
    repo_root: Path,
    proof_args: Sequence[str],
    launch_id: str,
) -> DetachedBackwardLineageLaunch:
    """Launch one detached T212 proof worker and return launch metadata."""
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_log_path = log_path(output_root)
    resolved_worker_status_path = worker_status_path(output_root)
    with suppress(FileNotFoundError):
        resolved_worker_status_path.unlink()
    command = build_detached_worker_command(output_root, proof_args)
    with resolved_log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=repo_root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    return DetachedBackwardLineageLaunch(
        generated_at=utc_now_iso(),
        launch_id=launch_id,
        pid=int(process.pid),
        repo_root=repo_root.as_posix(),
        output_root=output_root.as_posix(),
        log_path=resolved_log_path.as_posix(),
        worker_status_path=resolved_worker_status_path.as_posix(),
        report_path=report_path(output_root).as_posix(),
        failure_path=failure_path(output_root).as_posix(),
        proof_args=list(normalize_proof_args(output_root, proof_args)),
        command=command,
    )


def inspect_detached_backward_lineage_proof(
    launch: DetachedBackwardLineageLaunch,
) -> DetachedBackwardLineageStatus:
    """Inspect one detached T212 proof worker plus its canonical artifacts."""
    resolved_output_root = Path(launch.output_root)
    report = _load_optional_json(report_path(resolved_output_root))
    failure_text = _load_optional_text(failure_path(resolved_output_root))
    worker_status = _load_optional_json(worker_status_path(resolved_output_root))
    exit_code: int | None = None
    finished_at: str | None = None
    if worker_status is not None:
        exit_code = _optional_int(worker_status, "exit_code")
        finished_at = _optional_str(worker_status, "finished_at")
    running = False if exit_code is not None else _pid_is_running(launch.pid)
    return DetachedBackwardLineageStatus(
        checked_at=utc_now_iso(),
        launch_id=launch.launch_id,
        pid=launch.pid,
        running=running,
        exit_code=exit_code,
        started_at=launch.generated_at,
        finished_at=finished_at,
        report_found=report is not None,
        failure_found=failure_text is not None,
        report=report,
        failure_text=failure_text,
        logs_tail=_tail_text(Path(launch.log_path), max_lines=200),
    )


def _load_optional_json(path: Path) -> dict[str, object] | None:
    """Load one optional JSON artifact when present and well-formed."""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Detached backward-lineage artifact was malformed at `{path}`.")
    return payload


def _load_optional_text(path: Path) -> str | None:
    """Load one optional text artifact when present."""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return one optional integer value from a worker-status payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise SystemExit(f"Detached backward-lineage worker status returned malformed `{key}`.")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    """Return one optional string value from a worker-status payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SystemExit(f"Detached backward-lineage worker status returned malformed `{key}`.")
    return value


def _pid_is_running(pid: int) -> bool:
    """Return whether one detached worker pid is still alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _tail_text(path: Path, *, max_lines: int) -> str:
    """Return the trailing log text for one detached worker."""
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-max_lines:])
