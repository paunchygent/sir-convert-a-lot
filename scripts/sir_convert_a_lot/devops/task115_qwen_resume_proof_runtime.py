"""Local orchestration helpers for the Task 115 Qwen resume proof.

Purpose:
    Drive one bounded live Hemma interruption-and-resume proof against the
    detached Task 101 operator surface so the resumable checkpoint contract is
    verified through committed repo commands instead of ad hoc shell usage.

Relationships:
    - Used by `run_task115_hemma_qwen_resume_proof.py`.
    - Calls the committed `task-101-pilot` launch/status/stop/resume commands
      on Hemma through the canonical `run-hemma` wrapper.
    - Produces local proof metadata while the canonical training artifacts stay
      under the remote Task 101 verification and run roots on SSD scratch.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

DEFAULT_REMOTE_TASK101_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot"
)
DEFAULT_LOCAL_PROOF_ROOT = Path("build/verification/task-115-qwen-training-resume-proof")
DEFAULT_MAX_STEPS = 24
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 2
DEFAULT_POLL_INTERVAL_SECONDS = 10
DEFAULT_POLL_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class Task115ProofSettings:
    """Configuration for one local Task 115 interruption/resume proof."""

    local_output_root: Path
    remote_task101_output_root: Path
    max_steps: int
    checkpoint_interval_steps: int
    poll_interval_seconds: int
    poll_timeout_seconds: int
    skip_build: bool


@dataclass(frozen=True)
class Task115ProofReport:
    """Machine-readable report for one completed Task 115 resume proof."""

    generated_at: str
    proof_id: str
    remote_task101_output_root: str
    initial_launch_root: str
    initial_run_root: str
    interrupted_checkpoint_path: str
    interrupted_checkpoint_step: int
    resumed_launch_root: str
    resumed_from_checkpoint_path: str
    final_status: str
    final_exit_code: int
    final_optimizer_steps_completed: int
    final_latest_checkpoint_path: str
    final_latest_checkpoint_step: int


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_proof_id() -> str:
    """Return one deterministic proof identifier."""
    return f"task115-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def run_local_checked(command: list[str], *, label: str) -> str:
    """Run one local command and return stdout or raise with diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def run_remote_task101_json(args: list[str], *, label: str) -> dict[str, object]:
    """Run one committed remote Task 101 command and parse its JSON stdout."""
    stdout = run_local_checked(
        ["pdm", "run", "run-hemma", "--", "pdm", "run", "task-101-pilot", *args],
        label=label,
    )
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} returned malformed JSON output.")
    return payload


def poll_remote_task101_status(
    *,
    remote_task101_output_root: Path,
    launch_root: Path,
    poll_interval_seconds: int,
    poll_timeout_seconds: int,
    predicate: Callable[[dict[str, object]], bool],
) -> dict[str, object]:
    """Poll detached Task 101 status until one predicate matches or times out."""
    deadline = time.monotonic() + poll_timeout_seconds
    last_status: dict[str, object] | None = None
    while time.monotonic() < deadline:
        status_payload = run_remote_task101_json(
            [
                "status",
                "--output-root",
                remote_task101_output_root.as_posix(),
                "--launch-root",
                launch_root.as_posix(),
            ],
            label="task101 status poll",
        )
        last_status = status_payload
        if predicate(status_payload):
            return status_payload
        time.sleep(poll_interval_seconds)
    if last_status is None:
        raise SystemExit("Timed out before Task 101 returned any status payload.")
    raise SystemExit(
        "Timed out waiting for Task 101 status predicate.\n"
        f"last status:\n{json.dumps(last_status, indent=2, ensure_ascii=False)}"
    )


def checkpoint_ready_predicate(status_payload: dict[str, object]) -> bool:
    """Return True when a live Task 101 run has a durable checkpoint ready to interrupt."""
    latest_checkpoint_found = status_payload.get("latest_checkpoint_found") is True
    running = status_payload.get("running") is True
    pilot_report_found = status_payload.get("pilot_report_found") is True
    if latest_checkpoint_found and pilot_report_found:
        raise SystemExit(
            "Task 115 proof missed the interruption window because Task 101 already completed."
        )
    if status_payload.get("status") == "exited" and not latest_checkpoint_found:
        raise SystemExit(
            "Task 115 proof launch exited before emitting a durable checkpoint."
        )
    return latest_checkpoint_found and running


def completion_predicate(status_payload: dict[str, object]) -> bool:
    """Return True when a resumed Task 101 run has completed successfully."""
    if status_payload.get("pilot_report_found") is True and status_payload.get("exit_code") == 0:
        return True
    if status_payload.get("status") == "exited" and status_payload.get("exit_code") != 0:
        raise SystemExit(
            "Resumed Task 101 run exited unsuccessfully.\n"
            f"status:\n{json.dumps(status_payload, indent=2, ensure_ascii=False)}"
        )
    return False


def render_report_markdown(report: Task115ProofReport) -> str:
    """Render one concise markdown report for the Task 115 proof."""
    return "\n".join(
        [
            "# Task 115 Qwen Resume Proof",
            "",
            f"- generated_at: `{report.generated_at}`",
            f"- proof_id: `{report.proof_id}`",
            f"- remote_task101_output_root: `{report.remote_task101_output_root}`",
            f"- initial_launch_root: `{report.initial_launch_root}`",
            f"- initial_run_root: `{report.initial_run_root}`",
            f"- interrupted_checkpoint_path: `{report.interrupted_checkpoint_path}`",
            f"- interrupted_checkpoint_step: `{report.interrupted_checkpoint_step}`",
            f"- resumed_launch_root: `{report.resumed_launch_root}`",
            f"- resumed_from_checkpoint_path: `{report.resumed_from_checkpoint_path}`",
            f"- final_status: `{report.final_status}`",
            f"- final_exit_code: `{report.final_exit_code}`",
            f"- final_optimizer_steps_completed: `{report.final_optimizer_steps_completed}`",
            f"- final_latest_checkpoint_path: `{report.final_latest_checkpoint_path}`",
            f"- final_latest_checkpoint_step: `{report.final_latest_checkpoint_step}`",
        ]
    )
