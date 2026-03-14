"""Detached interruption-and-resume proof for Qwen training on Hemma.

Purpose:
    Launch one bounded detached Qwen training run, interrupt it after a durable
    checkpoint appears, resume the same run, and persist deterministic proof
    artifacts under a local verification root.

Relationships:
    - Calls the public `qwen-train` CLI through the canonical `run-hemma`
      wrapper.
    - Reuses mixed-stdout JSON parsing from `ml.qwen.common.runtime`.
    - Used by the public `cli/ml/qwen_resume_proof.py` entrypoint.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import parse_json_object_from_mixed_stdout

DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training"
)
DEFAULT_LOCAL_PROOF_ROOT = Path("build/verification/qwen-training-resume-proof")
DEFAULT_MAX_STEPS = 24
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 2
DEFAULT_POLL_INTERVAL_SECONDS = 10
DEFAULT_POLL_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class ResumeProofSettings:
    """Configuration for one local interruption/resume proof."""

    local_output_root: Path
    remote_training_output_root: Path
    max_steps: int
    checkpoint_interval_steps: int
    poll_interval_seconds: int
    poll_timeout_seconds: int
    skip_build: bool


@dataclass(frozen=True)
class ResumeProofReport:
    """Machine-readable report for one completed resume proof."""

    generated_at: str
    proof_id: str
    remote_training_output_root: str
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
    return f"qwen-resume-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the live resume proof runner."""
    parser = argparse.ArgumentParser(
        description="Run the live Hemma interruption-and-resume proof for Qwen training."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_LOCAL_PROOF_ROOT)
    parser.add_argument(
        "--remote-training-output-root",
        type=Path,
        default=DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT,
    )
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--checkpoint-interval-steps",
        type=int,
        default=DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=int,
        default=DEFAULT_POLL_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip image build checks because the Qwen image already exists on Hemma.",
    )
    return parser


def proof_root(base_output_root: Path, proof_id: str) -> Path:
    """Return the immutable local verification root for one resume proof."""
    return base_output_root / proof_id


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def run_remote_training_json(args: list[str], *, label: str) -> dict[str, object]:
    """Run one remote Qwen training command and parse its JSON payload."""
    command = ["pdm", "run", "run-hemma", "--", "pdm", "run", "qwen-train", *args]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 and result.stdout.strip() == "":
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    try:
        payload = parse_json_object_from_mixed_stdout(result.stdout)
    except SystemExit as exc:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        ) from exc
    return payload


def poll_remote_training_status(
    *,
    remote_training_output_root: Path,
    launch_root: Path,
    poll_interval_seconds: int,
    poll_timeout_seconds: int,
    predicate: Callable[[dict[str, object]], bool],
) -> dict[str, object]:
    """Poll remote Qwen training status until one predicate matches or timeout."""
    deadline = time.monotonic() + poll_timeout_seconds
    last_status: dict[str, object] | None = None
    while time.monotonic() < deadline:
        status_payload = run_remote_training_json(
            [
                "status",
                "--output-root",
                remote_training_output_root.as_posix(),
                "--launch-root",
                launch_root.as_posix(),
            ],
            label="qwen training status poll",
        )
        last_status = status_payload
        if predicate(status_payload):
            return status_payload
        time.sleep(poll_interval_seconds)
    if last_status is None:
        raise SystemExit("Timed out before Qwen training returned any status payload.")
    raise SystemExit(
        "Timed out waiting for Qwen training status predicate.\n"
        f"last status:\n{json.dumps(last_status, indent=2, ensure_ascii=False)}"
    )


def checkpoint_ready_predicate(status_payload: dict[str, object]) -> bool:
    """Return True when a durable checkpoint is ready to interrupt."""
    latest_checkpoint_found = status_payload.get("latest_checkpoint_found") is True
    running = status_payload.get("running") is True
    pilot_report_found = status_payload.get("pilot_report_found") is True
    if latest_checkpoint_found and pilot_report_found:
        raise SystemExit(
            "Resume proof missed the interruption window because training already completed."
        )
    if status_payload.get("status") == "exited" and not latest_checkpoint_found:
        raise SystemExit("Resume proof launch exited before emitting a durable checkpoint.")
    return latest_checkpoint_found and running


def completion_predicate(status_payload: dict[str, object]) -> bool:
    """Return True when a resumed run has completed successfully."""
    if status_payload.get("pilot_report_found") is True and status_payload.get("exit_code") == 0:
        return True
    if status_payload.get("status") == "exited" and status_payload.get("exit_code") != 0:
        raise SystemExit(
            "Resumed Qwen training run exited unsuccessfully.\n"
            f"status:\n{json.dumps(status_payload, indent=2, ensure_ascii=False)}"
        )
    return False


def render_report_markdown(report: ResumeProofReport) -> str:
    """Render one concise markdown report for the resume proof."""
    return "\n".join(
        [
            "# Qwen Training Resume Proof",
            "",
            f"- generated_at: `{report.generated_at}`",
            f"- proof_id: `{report.proof_id}`",
            f"- remote_training_output_root: `{report.remote_training_output_root}`",
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


def required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Resume proof expected integer field `{key}`.")
    return value


def required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Resume proof expected string field `{key}`.")
    return value


def main(argv: list[str] | None = None) -> int:
    """Run the live interruption-and-resume proof."""
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = ResumeProofSettings(
        local_output_root=Path(args.output_root),
        remote_training_output_root=Path(args.remote_training_output_root),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        poll_interval_seconds=int(args.poll_interval_seconds),
        poll_timeout_seconds=int(args.poll_timeout_seconds),
        skip_build=bool(args.skip_build),
    )
    current_proof_id = default_proof_id()
    current_proof_root = proof_root(settings.local_output_root, current_proof_id)
    current_proof_root.mkdir(parents=True, exist_ok=True)

    initial_launch_id = f"{current_proof_id}-initial"
    resumed_launch_id = f"{current_proof_id}-resume"

    initial_launch = run_remote_training_json(
        [
            "launch",
            "--output-root",
            settings.remote_training_output_root.as_posix(),
            "--launch-id",
            initial_launch_id,
            "--max-steps",
            str(settings.max_steps),
            "--checkpoint-interval-steps",
            str(settings.checkpoint_interval_steps),
            *([] if not settings.skip_build else ["--skip-build"]),
        ],
        label="resume proof launch initial qwen training",
    )
    write_json(current_proof_root / "initial_launch.json", initial_launch)

    initial_launch_root = settings.remote_training_output_root / initial_launch_id
    checkpoint_ready_status = poll_remote_training_status(
        remote_training_output_root=settings.remote_training_output_root,
        launch_root=initial_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=checkpoint_ready_predicate,
    )
    write_json(current_proof_root / "checkpoint_ready_status.json", checkpoint_ready_status)
    latest_checkpoint_payload = checkpoint_ready_status.get("latest_checkpoint")
    if not isinstance(latest_checkpoint_payload, dict):
        raise SystemExit("Resume proof expected latest checkpoint metadata before stop.")

    stopped = run_remote_training_json(
        [
            "stop",
            "--output-root",
            settings.remote_training_output_root.as_posix(),
            "--launch-root",
            initial_launch_root.as_posix(),
        ],
        label="resume proof stop initial qwen training",
    )
    write_json(current_proof_root / "stop.json", stopped)

    interrupted_status = poll_remote_training_status(
        remote_training_output_root=settings.remote_training_output_root,
        launch_root=initial_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=lambda payload: payload.get("running") is False,
    )
    write_json(current_proof_root / "interrupted_status.json", interrupted_status)

    resumed_launch = run_remote_training_json(
        [
            "resume",
            "--output-root",
            settings.remote_training_output_root.as_posix(),
            "--launch-root",
            initial_launch_root.as_posix(),
            "--launch-id",
            resumed_launch_id,
            *([] if not settings.skip_build else ["--skip-build"]),
        ],
        label="resume proof resume qwen training",
    )
    write_json(current_proof_root / "resumed_launch.json", resumed_launch)

    resumed_launch_root = settings.remote_training_output_root / resumed_launch_id
    final_status = poll_remote_training_status(
        remote_training_output_root=settings.remote_training_output_root,
        launch_root=resumed_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=completion_predicate,
    )
    write_json(current_proof_root / "final_status.json", final_status)
    final_report_payload = final_status.get("pilot_report")
    if not isinstance(final_report_payload, dict):
        raise SystemExit("Resume proof expected a final Qwen training report payload.")
    training_summary = final_report_payload.get("training_summary")
    if not isinstance(training_summary, dict):
        raise SystemExit("Resume proof expected `training_summary` in the final report.")
    final_latest_checkpoint = final_status.get("latest_checkpoint")
    if not isinstance(final_latest_checkpoint, dict):
        raise SystemExit("Resume proof expected final latest-checkpoint metadata.")

    report = ResumeProofReport(
        generated_at=utc_now_iso(),
        proof_id=current_proof_id,
        remote_training_output_root=settings.remote_training_output_root.as_posix(),
        initial_launch_root=initial_launch_root.as_posix(),
        initial_run_root=required_str(initial_launch, "run_root"),
        interrupted_checkpoint_path=required_str(latest_checkpoint_payload, "checkpoint_path"),
        interrupted_checkpoint_step=required_int(
            latest_checkpoint_payload,
            "optimizer_steps_completed",
        ),
        resumed_launch_root=resumed_launch_root.as_posix(),
        resumed_from_checkpoint_path=required_str(
            resumed_launch,
            "resumed_from_checkpoint_path",
        ),
        final_status=required_str(final_status, "status"),
        final_exit_code=required_int(final_status, "exit_code"),
        final_optimizer_steps_completed=required_int(
            training_summary,
            "optimizer_steps_completed",
        ),
        final_latest_checkpoint_path=required_str(final_latest_checkpoint, "checkpoint_path"),
        final_latest_checkpoint_step=required_int(
            final_latest_checkpoint,
            "optimizer_steps_completed",
        ),
    )
    write_json(current_proof_root / "report.json", asdict(report))
    write_markdown(current_proof_root / "report.md", render_report_markdown(report))
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0
