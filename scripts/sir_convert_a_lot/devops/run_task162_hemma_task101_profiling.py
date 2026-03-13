"""Run one bounded Task 162 profiling capture on Hemma.

Purpose:
    Provide a committed operator surface that launches one bounded Task 101 run
    with PyTorch and optional ROCm profiling enabled, then records trace
    artifact paths under `build/verification/`.

Relationships:
    - Uses Task 101 detached launcher/status surfaces via `run-hemma`.
    - Uses `task162_qwen_profile_artifacts.py` for deterministic artifact
      collection.
    - Reuses Task 161 runtime helpers for remote JSON/poll orchestration.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    parse_json_object_from_mixed_stdout,
)
from scripts.sir_convert_a_lot.devops.task161_qwen_ref_mel_cache_runtime import (
    DEFAULT_TASK161_REMOTE_TASK101_OUTPUT_ROOT,
    completed_task101_predicate,
    poll_remote_task101_status,
    run_remote_task101_json,
    utc_now_iso,
)

DEFAULT_TASK162_LOCAL_OUTPUT_ROOT = Path("build/verification/task-162-task101-profiling")
DEFAULT_TASK162_MAX_STEPS = 80
DEFAULT_TASK162_CHECKPOINT_INTERVAL_STEPS = 100
DEFAULT_TASK162_POLL_INTERVAL_SECONDS = 15
DEFAULT_TASK162_POLL_TIMEOUT_SECONDS = 3600
DEFAULT_TASK162_TORCH_PROFILER_WAIT_STEPS = 1
DEFAULT_TASK162_TORCH_PROFILER_WARMUP_STEPS = 1
DEFAULT_TASK162_TORCH_PROFILER_ACTIVE_STEPS = 6
DEFAULT_TASK162_TORCH_PROFILER_REPEAT = 1


@dataclass(frozen=True)
class Task162ProfilingReport:
    """Machine-readable report for one bounded Task 162 profiling run."""

    generated_at: str
    profiling_id: str
    remote_task101_output_root: str
    launch_id: str
    launch_root: str
    run_root: str
    status: str
    exit_code: int
    torch_profiling_enabled: bool
    rocm_profiling_enabled: bool
    training_summary_profiling: dict[str, object] | None
    artifact_summary: dict[str, object]


def _build_parser() -> argparse.ArgumentParser:
    """Build the Task 162 profiling runner parser."""
    parser = argparse.ArgumentParser(
        description="Run one bounded Task 101 profiling launch on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_TASK162_LOCAL_OUTPUT_ROOT)
    parser.add_argument(
        "--remote-task101-output-root",
        type=Path,
        default=DEFAULT_TASK161_REMOTE_TASK101_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--pilot-bundle-root",
        type=Path,
        default=None,
        help="Explicit Task 101 pilot-bundle root on Hemma.",
    )
    parser.add_argument("--max-steps", type=int, default=DEFAULT_TASK162_MAX_STEPS)
    parser.add_argument(
        "--checkpoint-interval-steps",
        type=int,
        default=DEFAULT_TASK162_CHECKPOINT_INTERVAL_STEPS,
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_TASK162_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=int,
        default=DEFAULT_TASK162_POLL_TIMEOUT_SECONDS,
    )
    parser.add_argument("--torch-profiler-enabled", choices=("true", "false"), default="true")
    parser.add_argument("--rocm-profiler-enabled", choices=("true", "false"), default="true")
    parser.add_argument(
        "--torch-profiler-wait-steps",
        type=int,
        default=DEFAULT_TASK162_TORCH_PROFILER_WAIT_STEPS,
    )
    parser.add_argument(
        "--torch-profiler-warmup-steps",
        type=int,
        default=DEFAULT_TASK162_TORCH_PROFILER_WARMUP_STEPS,
    )
    parser.add_argument(
        "--torch-profiler-active-steps",
        type=int,
        default=DEFAULT_TASK162_TORCH_PROFILER_ACTIVE_STEPS,
    )
    parser.add_argument(
        "--torch-profiler-repeat",
        type=int,
        default=DEFAULT_TASK162_TORCH_PROFILER_REPEAT,
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip image build checks because Task 100 image already exists on Hemma.",
    )
    return parser


def _profile_root(output_root: Path, profiling_id: str) -> Path:
    """Return one immutable Task 162 local output root."""
    return output_root / profiling_id


def _default_profiling_id() -> str:
    """Return one deterministic profiling identifier."""
    return f"task162-{utc_now_iso().replace(':', '').replace('-', '').lower()}"


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


def _run_remote_profile_artifacts(run_root: str, *, label: str) -> dict[str, object]:
    """Collect remote profiling artifact paths through a committed script surface."""
    command = [
        "pdm",
        "run",
        "run-hemma",
        "--",
        "pdm",
        "run",
        "python",
        "-m",
        "scripts.sir_convert_a_lot.devops.task162_qwen_profile_artifacts",
        "--run-root",
        run_root,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    payload = parse_json_object_from_mixed_stdout(result.stdout)
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} returned malformed JSON.")
    return payload


def _report_markdown(report: Task162ProfilingReport) -> str:
    """Render one concise markdown report."""
    artifact_summary = report.artifact_summary
    pytorch_files = artifact_summary.get("pytorch_trace_files")
    rocm_files = artifact_summary.get("rocm_trace_files")
    pytorch_count = len(pytorch_files) if isinstance(pytorch_files, list) else None
    rocm_count = len(rocm_files) if isinstance(rocm_files, list) else None
    return "\n".join(
        [
            "# Task 162 Task 101 Profiling Report",
            "",
            f"- generated_at: `{report.generated_at}`",
            f"- profiling_id: `{report.profiling_id}`",
            f"- launch_id: `{report.launch_id}`",
            f"- launch_root: `{report.launch_root}`",
            f"- run_root: `{report.run_root}`",
            f"- status: `{report.status}`",
            f"- exit_code: `{report.exit_code}`",
            f"- torch_profiling_enabled: `{report.torch_profiling_enabled}`",
            f"- rocm_profiling_enabled: `{report.rocm_profiling_enabled}`",
            f"- pytorch_trace_file_count: `{pytorch_count}`",
            f"- rocm_trace_file_count: `{rocm_count}`",
        ]
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Task 162 expected string field `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Task 162 expected integer field `{key}`.")
    return value


def _optional_object(payload: dict[str, object], key: str) -> dict[str, object] | None:
    """Return one optional object field."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SystemExit(f"Task 162 expected object field `{key}` when provided.")
    return dict(value)


def main(argv: list[str] | None = None) -> int:
    """Run one bounded Task 162 profiling capture."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    profiling_id = _default_profiling_id()
    output_root = Path(args.output_root)
    profile_root = _profile_root(output_root, profiling_id)
    profile_root.mkdir(parents=True, exist_ok=True)
    remote_task101_output_root = Path(args.remote_task101_output_root)
    launch_id = f"{profiling_id}-profile"
    torch_profiler_enabled = str(args.torch_profiler_enabled).lower() == "true"
    rocm_profiler_enabled = str(args.rocm_profiler_enabled).lower() == "true"
    launch_payload = run_remote_task101_json(
        [
            "launch",
            "--output-root",
            remote_task101_output_root.as_posix(),
            "--launch-id",
            launch_id,
            "--max-steps",
            str(int(args.max_steps)),
            "--checkpoint-interval-steps",
            str(int(args.checkpoint_interval_steps)),
            "--torch-profiler-enabled",
            "true" if torch_profiler_enabled else "false",
            "--torch-profiler-wait-steps",
            str(int(args.torch_profiler_wait_steps)),
            "--torch-profiler-warmup-steps",
            str(int(args.torch_profiler_warmup_steps)),
            "--torch-profiler-active-steps",
            str(int(args.torch_profiler_active_steps)),
            "--torch-profiler-repeat",
            str(int(args.torch_profiler_repeat)),
            "--rocm-profiler-enabled",
            "true" if rocm_profiler_enabled else "false",
            *(
                []
                if args.pilot_bundle_root is None
                else [
                    "--pilot-bundle-root",
                    args.pilot_bundle_root.as_posix(),
                ]
            ),
            *([] if not bool(args.skip_build) else ["--skip-build"]),
        ],
        label="task162 launch profiling run",
    )
    launch_root = remote_task101_output_root / launch_id
    final_status = poll_remote_task101_status(
        remote_task101_output_root=remote_task101_output_root,
        launch_root=launch_root,
        poll_interval_seconds=int(args.poll_interval_seconds),
        poll_timeout_seconds=int(args.poll_timeout_seconds),
        predicate=completed_task101_predicate,
    )
    run_root = _required_str(launch_payload, "run_root")
    artifacts_payload = _run_remote_profile_artifacts(
        run_root,
        label="task162 collect profile artifacts",
    )
    _write_json(profile_root / "launch.json", launch_payload)
    _write_json(profile_root / "final_status.json", final_status)
    _write_json(profile_root / "artifacts.json", artifacts_payload)
    pilot_report = _optional_object(final_status, "pilot_report")
    training_summary = (
        None if pilot_report is None else _optional_object(pilot_report, "training_summary")
    )
    report = Task162ProfilingReport(
        generated_at=utc_now_iso(),
        profiling_id=profiling_id,
        remote_task101_output_root=remote_task101_output_root.as_posix(),
        launch_id=launch_id,
        launch_root=launch_root.as_posix(),
        run_root=run_root,
        status=_required_str(final_status, "status"),
        exit_code=_required_int(final_status, "exit_code"),
        torch_profiling_enabled=torch_profiler_enabled,
        rocm_profiling_enabled=rocm_profiler_enabled,
        training_summary_profiling=(
            None if training_summary is None else _optional_object(training_summary, "profiling")
        ),
        artifact_summary=artifacts_payload,
    )
    _write_json(profile_root / "report.json", asdict(report))
    _write_markdown(profile_root / "report.md", _report_markdown(report))
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
