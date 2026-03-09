"""Run the live Task 115 Qwen interruption-and-resume proof on Hemma.

Purpose:
    Provide the committed local orchestration surface for the final Task 115
    acceptance proof: launch a bounded detached Task 101 pilot on Hemma, wait
    for one durable checkpoint, interrupt it intentionally, resume from the
    latest durable checkpoint, and record deterministic verification artifacts.

Relationships:
    - Uses `task115_qwen_resume_proof_runtime.py` for local polling and report
      helpers.
    - Drives the remote `task-101-pilot` launch/status/stop/resume surfaces
      through the canonical `run-hemma` wrapper.
    - Writes proof artifacts under `build/verification/task-115-qwen-training-resume-proof/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task115_qwen_resume_proof_runtime import (
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_LOCAL_PROOF_ROOT,
    DEFAULT_MAX_STEPS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    DEFAULT_REMOTE_TASK101_OUTPUT_ROOT,
    Task115ProofReport,
    Task115ProofSettings,
    checkpoint_ready_predicate,
    completion_predicate,
    default_proof_id,
    poll_remote_task101_status,
    render_report_markdown,
    run_remote_task101_json,
    utc_now_iso,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the Task 115 live proof runner."""
    parser = argparse.ArgumentParser(
        description="Run the live Hemma interruption-and-resume proof for Task 115."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_LOCAL_PROOF_ROOT)
    parser.add_argument(
        "--remote-task101-output-root",
        type=Path,
        default=DEFAULT_REMOTE_TASK101_OUTPUT_ROOT,
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
        help="Skip image build checks because the Task 100 image already exists on Hemma.",
    )
    return parser


def _proof_root(base_output_root: Path, proof_id: str) -> Path:
    """Return the immutable local verification root for one Task 115 proof."""
    return base_output_root / proof_id


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _require_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Task 115 proof expected integer field `{key}`.")
    return value


def _require_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Task 115 proof expected string field `{key}`.")
    return value


def main(argv: list[str] | None = None) -> int:
    """Run the committed live Task 115 interruption-and-resume proof."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = Task115ProofSettings(
        local_output_root=Path(args.output_root),
        remote_task101_output_root=Path(args.remote_task101_output_root),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        poll_interval_seconds=int(args.poll_interval_seconds),
        poll_timeout_seconds=int(args.poll_timeout_seconds),
        skip_build=bool(args.skip_build),
    )
    proof_id = default_proof_id()
    proof_root = _proof_root(settings.local_output_root, proof_id)
    proof_root.mkdir(parents=True, exist_ok=True)

    initial_launch_id = f"{proof_id}-initial"
    resumed_launch_id = f"{proof_id}-resume"

    initial_launch = run_remote_task101_json(
        [
            "launch",
            "--output-root",
            settings.remote_task101_output_root.as_posix(),
            "--launch-id",
            initial_launch_id,
            "--max-steps",
            str(settings.max_steps),
            "--checkpoint-interval-steps",
            str(settings.checkpoint_interval_steps),
            *([] if not settings.skip_build else ["--skip-build"]),
        ],
        label="task115 launch initial task101 pilot",
    )
    _write_json(proof_root / "initial_launch.json", initial_launch)

    initial_launch_metadata_root = settings.remote_task101_output_root / initial_launch_id
    checkpoint_ready_status = poll_remote_task101_status(
        remote_task101_output_root=settings.remote_task101_output_root,
        launch_root=initial_launch_metadata_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=checkpoint_ready_predicate,
    )
    _write_json(proof_root / "checkpoint_ready_status.json", checkpoint_ready_status)
    latest_checkpoint_payload = checkpoint_ready_status.get("latest_checkpoint")
    if not isinstance(latest_checkpoint_payload, dict):
        raise SystemExit("Task 115 proof expected latest checkpoint metadata before stop.")

    stopped = run_remote_task101_json(
        [
            "stop",
            "--output-root",
            settings.remote_task101_output_root.as_posix(),
            "--launch-root",
            initial_launch_metadata_root.as_posix(),
        ],
        label="task115 stop initial task101 pilot",
    )
    _write_json(proof_root / "stop.json", stopped)

    interrupted_status = poll_remote_task101_status(
        remote_task101_output_root=settings.remote_task101_output_root,
        launch_root=initial_launch_metadata_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=lambda payload: payload.get("running") is False,
    )
    _write_json(proof_root / "interrupted_status.json", interrupted_status)

    resumed_launch = run_remote_task101_json(
        [
            "resume",
            "--output-root",
            settings.remote_task101_output_root.as_posix(),
            "--launch-root",
            initial_launch_metadata_root.as_posix(),
            "--launch-id",
            resumed_launch_id,
            *([] if not settings.skip_build else ["--skip-build"]),
        ],
        label="task115 resume task101 pilot",
    )
    _write_json(proof_root / "resumed_launch.json", resumed_launch)

    resumed_launch_root = settings.remote_task101_output_root / resumed_launch_id
    final_status = poll_remote_task101_status(
        remote_task101_output_root=settings.remote_task101_output_root,
        launch_root=resumed_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=completion_predicate,
    )
    _write_json(proof_root / "final_status.json", final_status)
    final_report_payload = final_status.get("pilot_report")
    if not isinstance(final_report_payload, dict):
        raise SystemExit("Task 115 proof expected a final Task 101 pilot report payload.")
    training_summary = final_report_payload.get("training_summary")
    if not isinstance(training_summary, dict):
        raise SystemExit("Task 115 proof expected training_summary in the final Task 101 report.")
    final_latest_checkpoint = final_status.get("latest_checkpoint")
    if not isinstance(final_latest_checkpoint, dict):
        raise SystemExit("Task 115 proof expected final latest-checkpoint metadata.")

    report = Task115ProofReport(
        generated_at=utc_now_iso(),
        proof_id=proof_id,
        remote_task101_output_root=settings.remote_task101_output_root.as_posix(),
        initial_launch_root=initial_launch_metadata_root.as_posix(),
        initial_run_root=_require_str(initial_launch, "run_root"),
        interrupted_checkpoint_path=_require_str(latest_checkpoint_payload, "checkpoint_path"),
        interrupted_checkpoint_step=_require_int(
            latest_checkpoint_payload,
            "optimizer_steps_completed",
        ),
        resumed_launch_root=resumed_launch_root.as_posix(),
        resumed_from_checkpoint_path=_require_str(
            resumed_launch,
            "resumed_from_checkpoint_path",
        ),
        final_status=_require_str(final_status, "status"),
        final_exit_code=_require_int(final_status, "exit_code"),
        final_optimizer_steps_completed=_require_int(
            training_summary,
            "optimizer_steps_completed",
        ),
        final_latest_checkpoint_path=_require_str(final_latest_checkpoint, "checkpoint_path"),
        final_latest_checkpoint_step=_require_int(
            final_latest_checkpoint,
            "optimizer_steps_completed",
        ),
    )
    _write_json(proof_root / "report.json", asdict(report))
    _write_markdown(proof_root / "report.md", render_report_markdown(report))
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
