"""Run the live Task 161 ref-mel cache comparison on Hemma.

Purpose:
    Launch two bounded Task 101 runs through governed surfaces (cache-off and
    cache-on), collect deterministic final status payloads, and write one
    machine-readable comparison report under `build/verification/`.

Relationships:
    - Uses `task161_qwen_ref_mel_cache_runtime.py` for polling/parsing helpers.
    - Calls remote Task 101 through `run-hemma` plus `task-101-pilot`.
    - Produces evidence used by Story 26 Task 161 acceptance.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task161_qwen_ref_mel_cache_runtime import (
    DEFAULT_TASK161_BATCH_SIZE,
    DEFAULT_TASK161_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_TASK161_LOCAL_OUTPUT_ROOT,
    DEFAULT_TASK161_MAX_STEPS,
    DEFAULT_TASK161_NUM_EPOCHS,
    DEFAULT_TASK161_POLL_INTERVAL_SECONDS,
    DEFAULT_TASK161_POLL_TIMEOUT_SECONDS,
    DEFAULT_TASK161_REF_MEL_CACHE_MAX_ITEMS,
    DEFAULT_TASK161_REMOTE_TASK101_OUTPUT_ROOT,
    DEFAULT_TASK161_RESOURCE_MONITOR_INTERVAL_SECONDS,
    Task161ComparisonReport,
    Task161ComparisonSettings,
    completed_task101_predicate,
    default_comparison_id,
    delta,
    poll_remote_task101_status,
    render_report_markdown,
    run_remote_task101_json,
    utc_now_iso,
    variant_summary_from_payloads,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed Task 161 comparison CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run bounded cache-off/cache-on Task 101 comparison on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_TASK161_LOCAL_OUTPUT_ROOT)
    parser.add_argument(
        "--remote-task101-output-root",
        type=Path,
        default=DEFAULT_TASK161_REMOTE_TASK101_OUTPUT_ROOT,
    )
    parser.add_argument("--max-steps", type=int, default=DEFAULT_TASK161_MAX_STEPS)
    parser.add_argument(
        "--checkpoint-interval-steps",
        type=int,
        default=DEFAULT_TASK161_CHECKPOINT_INTERVAL_STEPS,
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_TASK161_BATCH_SIZE)
    parser.add_argument("--num-epochs", type=int, default=DEFAULT_TASK161_NUM_EPOCHS)
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_TASK161_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=int,
        default=DEFAULT_TASK161_POLL_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--ref-mel-cache-max-items",
        type=int,
        default=DEFAULT_TASK161_REF_MEL_CACHE_MAX_ITEMS,
    )
    parser.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_TASK161_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    parser.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip image build checks because the Task 100 image already exists on Hemma.",
    )
    return parser


def _comparison_root(base_output_root: Path, comparison_id: str) -> Path:
    """Return the immutable local verification root for one Task 161 comparison."""
    return base_output_root / comparison_id


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


def _launch_variant(
    *,
    settings: Task161ComparisonSettings,
    comparison_id: str,
    variant_id: str,
    ref_mel_cache_enabled: bool,
) -> dict[str, object]:
    """Launch one Task 101 variant and return the launch payload."""
    launch_id = f"{comparison_id}-{variant_id}"
    command = [
        "launch",
        "--output-root",
        settings.remote_task101_output_root.as_posix(),
        "--launch-id",
        launch_id,
        "--max-steps",
        str(settings.max_steps),
        "--checkpoint-interval-steps",
        str(settings.checkpoint_interval_steps),
        "--batch-size",
        str(settings.batch_size),
        "--num-epochs",
        str(settings.num_epochs),
        "--ref-mel-cache-enabled",
        "true" if ref_mel_cache_enabled else "false",
        "--ref-mel-cache-max-items",
        str(settings.ref_mel_cache_max_items),
        "--resource-monitor-interval-seconds",
        str(settings.resource_monitor_interval_seconds),
    ]
    if settings.resource_monitor_duration_seconds is not None:
        command.extend(
            [
                "--resource-monitor-duration-seconds",
                str(settings.resource_monitor_duration_seconds),
            ]
        )
    if settings.skip_build:
        command.append("--skip-build")
    return run_remote_task101_json(command, label=f"task161 launch {variant_id}")


def main(argv: list[str] | None = None) -> int:
    """Run the committed Task 161 live Hemma comparison."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = Task161ComparisonSettings(
        local_output_root=Path(args.output_root),
        remote_task101_output_root=Path(args.remote_task101_output_root),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        batch_size=int(args.batch_size),
        num_epochs=int(args.num_epochs),
        poll_interval_seconds=int(args.poll_interval_seconds),
        poll_timeout_seconds=int(args.poll_timeout_seconds),
        ref_mel_cache_max_items=int(args.ref_mel_cache_max_items),
        resource_monitor_interval_seconds=float(args.resource_monitor_interval_seconds),
        resource_monitor_duration_seconds=(
            None
            if args.resource_monitor_duration_seconds is None
            else float(args.resource_monitor_duration_seconds)
        ),
        skip_build=bool(args.skip_build),
    )
    comparison_id = default_comparison_id()
    comparison_root = _comparison_root(settings.local_output_root, comparison_id)
    comparison_root.mkdir(parents=True, exist_ok=True)

    cache_off_launch = _launch_variant(
        settings=settings,
        comparison_id=comparison_id,
        variant_id="cache-off",
        ref_mel_cache_enabled=False,
    )
    cache_off_launch_root = settings.remote_task101_output_root / f"{comparison_id}-cache-off"
    cache_off_status = poll_remote_task101_status(
        remote_task101_output_root=settings.remote_task101_output_root,
        launch_root=cache_off_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=completed_task101_predicate,
    )
    _write_json(comparison_root / "cache_off_launch.json", cache_off_launch)
    _write_json(comparison_root / "cache_off_final_status.json", cache_off_status)

    cache_on_launch = _launch_variant(
        settings=settings,
        comparison_id=comparison_id,
        variant_id="cache-on",
        ref_mel_cache_enabled=True,
    )
    cache_on_launch_root = settings.remote_task101_output_root / f"{comparison_id}-cache-on"
    cache_on_status = poll_remote_task101_status(
        remote_task101_output_root=settings.remote_task101_output_root,
        launch_root=cache_on_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=completed_task101_predicate,
    )
    _write_json(comparison_root / "cache_on_launch.json", cache_on_launch)
    _write_json(comparison_root / "cache_on_final_status.json", cache_on_status)

    cache_off_summary = variant_summary_from_payloads(
        variant_id="cache-off",
        ref_mel_cache_enabled=False,
        launch_payload={
            **cache_off_launch,
            "launch_root": cache_off_launch_root.as_posix(),
        },
        final_status_payload=cache_off_status,
    )
    cache_on_summary = variant_summary_from_payloads(
        variant_id="cache-on",
        ref_mel_cache_enabled=True,
        launch_payload={
            **cache_on_launch,
            "launch_root": cache_on_launch_root.as_posix(),
        },
        final_status_payload=cache_on_status,
    )
    report = Task161ComparisonReport(
        generated_at=utc_now_iso(),
        comparison_id=comparison_id,
        remote_task101_output_root=settings.remote_task101_output_root.as_posix(),
        max_steps=settings.max_steps,
        checkpoint_interval_steps=settings.checkpoint_interval_steps,
        cache_off=cache_off_summary,
        cache_on=cache_on_summary,
        delta_train_gpu_busy_percent_median=delta(
            cache_on_summary.train_gpu_busy_percent_median,
            cache_off_summary.train_gpu_busy_percent_median,
        ),
        delta_steady_state_gpu_busy_percent_median=delta(
            cache_on_summary.steady_state_gpu_busy_percent_median,
            cache_off_summary.steady_state_gpu_busy_percent_median,
        ),
    )
    _write_json(comparison_root / "report.json", asdict(report))
    _write_markdown(comparison_root / "report.md", render_report_markdown(report))
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
