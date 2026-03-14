"""Launch and inspect the detached Task 116 Hemma resource monitor.

Purpose:
    Provide the committed CLI entrypoint for a lightweight detached resource
    monitor that runs alongside sustained Hemma preprocessing windows and
    persists machine-readable host CPU, RAM, and GPU utilization history.

Relationships:
    - Uses `task116_hemma_resource_monitor_runtime.py` for worker execution,
      detached-process spawn, and artifact helpers.
    - Writes deterministic evidence under
      `build/verification/task-116-hemma-resource-monitor/`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task116_hemma_resource_monitor_models import (
    RuntimeKind,
    Task116ResourceMonitorLaunch,
    Task116ResourceMonitorStatus,
    Task116ResourceMonitorSummary,
)
from scripts.sir_convert_a_lot.devops.task116_hemma_resource_monitor_runtime import (
    build_status,
    default_launch_id,
    latest_pointer_path,
    launch_metadata_path,
    load_json,
    load_samples,
    required_str,
    run_worker,
    spawn_detached_worker,
    status_metadata_path,
    stderr_log_path,
    stdout_log_path,
    stop_request_path,
    summarize_samples,
    summary_metadata_path,
    utc_now_iso,
    write_latest_pointer,
    write_launch_metadata,
    write_status,
    write_summary,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import write_json

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-116-hemma-resource-monitor")


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed Task 116 resource monitor CLI."""
    parser = argparse.ArgumentParser(
        description="Launch and inspect a detached Hemma resource monitor for Task 116."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch one detached resource monitor.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--launch-id", default=None)
    launch.add_argument("--runtime-kind", choices=("rocm", "cuda", "none"), default="rocm")
    launch.add_argument("--interval-seconds", type=float, default=30.0)
    launch.add_argument("--duration-seconds", type=float, default=None)

    run = subparsers.add_parser("run", help="Internal detached worker entrypoint.")
    run.add_argument("--launch-root", type=Path, required=True)
    run.add_argument("--launch-id", required=True)
    run.add_argument("--started-at", required=True)
    run.add_argument("--runtime-kind", choices=("rocm", "cuda", "none"), default="rocm")
    run.add_argument("--interval-seconds", type=float, required=True)
    run.add_argument("--duration-seconds", type=float, default=None)

    status = subparsers.add_parser("status", help="Inspect one detached resource monitor.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--launch-root", type=Path, default=None)

    summary = subparsers.add_parser("summary", help="Render one resource monitor summary.")
    summary.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    summary.add_argument("--launch-root", type=Path, default=None)

    stop = subparsers.add_parser("stop", help="Request one detached resource monitor to stop.")
    stop.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    stop.add_argument("--launch-root", type=Path, default=None)

    return parser


def _launch_root(output_root: Path, launch_id: str) -> Path:
    """Return the canonical artifact root for one resource monitor launch."""
    return output_root / launch_id


def _status_markdown_path(launch_root: Path) -> Path:
    """Return the markdown status path for one resource monitor launch."""
    return launch_root / "status.md"


def _summary_markdown_path(launch_root: Path) -> Path:
    """Return the markdown summary path for one resource monitor launch."""
    return launch_root / "summary.md"


def _resolve_launch_root(output_root: Path, launch_root: Path | None) -> Path:
    """Resolve one explicit or latest launch root."""
    if launch_root is not None:
        return launch_root
    payload = load_json(latest_pointer_path(output_root))
    launch_root_obj = payload.get("launch_root")
    if not isinstance(launch_root_obj, str) or launch_root_obj.strip() == "":
        raise SystemExit("Task 116 resource monitor latest-launch metadata was malformed.")
    return Path(launch_root_obj)


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _summary_markdown(summary: Task116ResourceMonitorSummary) -> str:
    """Render one concise markdown summary."""
    lines = [
        "# Task 116 Hemma Resource Monitor Summary",
        "",
        f"- launch_id: `{summary.launch_id}`",
        f"- sample_count: `{summary.sample_count}`",
        f"- first_sample_at: `{summary.first_sample_at}`",
        f"- last_sample_at: `{summary.last_sample_at}`",
        f"- host_cpu_busy_percent_min: `{summary.host_cpu_busy_percent_min}`",
        f"- host_cpu_busy_percent_median: `{summary.host_cpu_busy_percent_median}`",
        f"- host_cpu_busy_percent_max: `{summary.host_cpu_busy_percent_max}`",
        f"- host_memory_used_percent_min: `{summary.host_memory_used_percent_min}`",
        f"- host_memory_used_percent_median: `{summary.host_memory_used_percent_median}`",
        f"- host_memory_used_percent_max: `{summary.host_memory_used_percent_max}`",
        f"- gpu_busy_percent_min: `{summary.gpu_busy_percent_min}`",
        f"- gpu_busy_percent_median: `{summary.gpu_busy_percent_median}`",
        f"- gpu_busy_percent_max: `{summary.gpu_busy_percent_max}`",
        f"- gpu_memory_used_percent_min: `{summary.gpu_memory_used_percent_min}`",
        f"- gpu_memory_used_percent_median: `{summary.gpu_memory_used_percent_median}`",
        f"- gpu_memory_used_percent_max: `{summary.gpu_memory_used_percent_max}`",
    ]
    return "\n".join(lines)


def _status_markdown(status: Task116ResourceMonitorStatus) -> str:
    """Render one concise markdown status summary."""
    summary_payload = status.summary
    host_cpu_median = summary_payload.get("host_cpu_busy_percent_median")
    host_cpu_max = summary_payload.get("host_cpu_busy_percent_max")
    host_cpu_min = summary_payload.get("host_cpu_busy_percent_min")
    host_memory_median = summary_payload.get("host_memory_used_percent_median")
    host_memory_max = summary_payload.get("host_memory_used_percent_max")
    host_memory_min = summary_payload.get("host_memory_used_percent_min")
    gpu_busy_median = summary_payload.get("gpu_busy_percent_median")
    gpu_busy_max = summary_payload.get("gpu_busy_percent_max")
    gpu_busy_min = summary_payload.get("gpu_busy_percent_min")
    gpu_memory_median = summary_payload.get("gpu_memory_used_percent_median")
    gpu_memory_max = summary_payload.get("gpu_memory_used_percent_max")
    gpu_memory_min = summary_payload.get("gpu_memory_used_percent_min")
    lines = [
        "# Task 116 Hemma Resource Monitor Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- launch_id: `{status.launch_id}`",
        f"- pid: `{status.pid}`",
        f"- running: `{status.running}`",
        f"- runtime_kind: `{status.runtime_kind}`",
        f"- interval_seconds: `{status.interval_seconds}`",
        f"- duration_seconds: `{status.duration_seconds}`",
        f"- stop_requested: `{status.stop_requested}`",
        f"- worker_state_found: `{status.worker_state_found}`",
        f"- sample_count: `{summary_payload.get('sample_count')}`",
        f"- host_cpu_busy_percent_median: `{host_cpu_median}`",
        f"- host_cpu_busy_percent_max: `{host_cpu_max}`",
        f"- host_cpu_busy_percent_min: `{host_cpu_min}`",
        f"- host_memory_used_percent_median: `{host_memory_median}`",
        f"- host_memory_used_percent_max: `{host_memory_max}`",
        f"- host_memory_used_percent_min: `{host_memory_min}`",
        f"- gpu_busy_percent_median: `{gpu_busy_median}`",
        f"- gpu_busy_percent_max: `{gpu_busy_max}`",
        f"- gpu_busy_percent_min: `{gpu_busy_min}`",
        f"- gpu_memory_used_percent_median: `{gpu_memory_median}`",
        f"- gpu_memory_used_percent_max: `{gpu_memory_max}`",
        f"- gpu_memory_used_percent_min: `{gpu_memory_min}`",
    ]
    return "\n".join(lines)


def _summary_for_launch_root(launch_root: Path) -> Task116ResourceMonitorSummary:
    """Build one summary payload for the selected launch root."""
    launch_payload = load_json(launch_metadata_path(launch_root))
    return summarize_samples(required_str(launch_payload, "launch_id"), load_samples(launch_root))


def _build_worker_command(
    *,
    launch_root: Path,
    launch_id: str,
    started_at: str,
    runtime_kind: RuntimeKind,
    interval_seconds: float,
    duration_seconds: float | None,
) -> list[str]:
    """Build the internal worker command for one detached launch."""
    command = [
        sys.executable,
        "-m",
        "scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor",
        "run",
        "--launch-root",
        launch_root.as_posix(),
        "--launch-id",
        launch_id,
        "--started-at",
        started_at,
        "--runtime-kind",
        runtime_kind,
        "--interval-seconds",
        str(interval_seconds),
    ]
    if duration_seconds is not None:
        command.extend(["--duration-seconds", str(duration_seconds)])
    return command


def main(argv: list[str] | None = None) -> int:
    """Run the committed Task 116 resource monitor CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_worker(
            launch_root=Path(args.launch_root),
            launch_id=str(args.launch_id),
            started_at=str(args.started_at),
            runtime_kind=args.runtime_kind,
            interval_seconds=float(args.interval_seconds),
            duration_seconds=(
                float(args.duration_seconds) if args.duration_seconds is not None else None
            ),
        )

    output_root = Path(args.output_root)
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)

    if args.command == "launch":
        if args.interval_seconds <= 0:
            raise SystemExit("`--interval-seconds` must be positive.")
        if args.duration_seconds is not None and args.duration_seconds <= 0:
            raise SystemExit("`--duration-seconds` must be positive when provided.")
        launch_id = str(args.launch_id or default_launch_id())
        launch_root = _launch_root(output_root, launch_id)
        launch_root.mkdir(parents=True, exist_ok=True)
        started_at = utc_now_iso()
        worker_command = _build_worker_command(
            launch_root=launch_root,
            launch_id=launch_id,
            started_at=started_at,
            runtime_kind=args.runtime_kind,
            interval_seconds=float(args.interval_seconds),
            duration_seconds=(
                float(args.duration_seconds) if args.duration_seconds is not None else None
            ),
        )
        pid = spawn_detached_worker(
            worker_command,
            stdout_path=stdout_log_path(launch_root),
            stderr_path=stderr_log_path(launch_root),
        )
        launch = Task116ResourceMonitorLaunch(
            generated_at=started_at,
            launch_id=launch_id,
            repo_root=Path.cwd().resolve().as_posix(),
            pid=pid,
            runtime_kind=args.runtime_kind,
            interval_seconds=float(args.interval_seconds),
            duration_seconds=(
                float(args.duration_seconds) if args.duration_seconds is not None else None
            ),
            command=worker_command,
        )
        write_launch_metadata(launch_metadata_path(launch_root), launch)
        write_latest_pointer(output_root, launch_root)
        print(json.dumps(launch.__dict__, indent=2, ensure_ascii=False))
        return 0

    launch_root = _resolve_launch_root(output_root, getattr(args, "launch_root", None))
    if args.command == "stop":
        write_json(
            stop_request_path(launch_root),
            {"requested_at": utc_now_iso(), "launch_root": launch_root.as_posix()},
        )
        print(
            json.dumps(
                {
                    "launch_root": launch_root.as_posix(),
                    "stop_requested": True,
                    "requested_at": utc_now_iso(),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    summary = _summary_for_launch_root(launch_root)
    write_summary(summary_metadata_path(launch_root), summary)
    _write_markdown(_summary_markdown_path(launch_root), _summary_markdown(summary))
    if args.command == "summary":
        print(json.dumps(summary.__dict__, indent=2, ensure_ascii=False))
        return 0

    status = build_status(launch_root)
    write_status(status_metadata_path(launch_root), status)
    _write_markdown(_status_markdown_path(launch_root), _status_markdown(status))
    print(json.dumps(status.__dict__, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
