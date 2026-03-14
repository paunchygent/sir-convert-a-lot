"""Ref-mel cache comparison runner for detached Qwen training on Hemma.

Purpose:
    Launch paired cache-off and cache-on Qwen training variants, collect final
    status payloads, and render a deterministic comparison report.

Relationships:
    - Calls the public `qwen-train` CLI through the canonical `run-hemma`
      wrapper.
    - Reuses mixed-stdout JSON parsing from `ml.qwen.common.runtime`.
    - Used by the public `cli/ml/qwen_ref_mel_cache_comparison.py` entrypoint.
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
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import boolean_flag

DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training"
)
DEFAULT_LOCAL_OUTPUT_ROOT = Path("build/verification/qwen-ref-mel-cache-comparison")
DEFAULT_MAX_STEPS = 240
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 100
DEFAULT_BATCH_SIZE = 1
DEFAULT_NUM_EPOCHS = 1
DEFAULT_POLL_INTERVAL_SECONDS = 20
DEFAULT_POLL_TIMEOUT_SECONDS = 5400
DEFAULT_REF_MEL_CACHE_MAX_ITEMS = 2048
DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True)
class ComparisonSettings:
    """Configuration for one bounded ref-mel cache comparison run."""

    local_output_root: Path
    remote_training_output_root: Path
    training_bundle_root: Path | None
    max_steps: int
    checkpoint_interval_steps: int
    batch_size: int
    num_epochs: int
    poll_interval_seconds: int
    poll_timeout_seconds: int
    ref_mel_cache_max_items: int
    resource_monitor_interval_seconds: float
    resource_monitor_duration_seconds: float | None
    skip_build: bool


@dataclass(frozen=True)
class VariantSummary:
    """Summary metrics for one cache comparison variant."""

    variant_id: str
    launch_id: str
    launch_root: str
    run_root: str
    ref_mel_cache_enabled: bool
    exit_code: int
    optimizer_steps_completed: int
    train_iterations_completed: int
    ref_mel_cache_hits: int | None
    ref_mel_cache_misses: int | None
    ref_mel_cache_hit_rate: float | None
    train_gpu_busy_percent_median: float | None
    steady_state_gpu_busy_percent_median: float | None
    steady_state_sample_count: int | None
    steady_state_gate_met: bool | None


@dataclass(frozen=True)
class ComparisonReport:
    """Machine-readable ref-mel cache comparison report."""

    generated_at: str
    comparison_id: str
    remote_training_output_root: str
    max_steps: int
    checkpoint_interval_steps: int
    cache_off: VariantSummary
    cache_on: VariantSummary
    delta_train_gpu_busy_percent_median: float | None
    delta_steady_state_gpu_busy_percent_median: float | None


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_comparison_id() -> str:
    """Return one deterministic comparison identifier."""
    return f"qwen-ref-mel-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def build_parser() -> argparse.ArgumentParser:
    """Build the committed comparison CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run bounded cache-off/cache-on Qwen training comparison on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_LOCAL_OUTPUT_ROOT)
    parser.add_argument(
        "--remote-training-output-root",
        type=Path,
        default=DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--training-bundle-root",
        type=Path,
        default=None,
        help="Explicit training-bundle root on Hemma.",
    )
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--checkpoint-interval-steps",
        type=int,
        default=DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--num-epochs", type=int, default=DEFAULT_NUM_EPOCHS)
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
        "--ref-mel-cache-max-items",
        type=int,
        default=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    )
    parser.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    parser.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip image build checks because the Qwen image already exists on Hemma.",
    )
    return parser


def comparison_root(base_output_root: Path, comparison_id: str) -> Path:
    """Return the immutable local verification root for one comparison."""
    return base_output_root / comparison_id


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
        payload = run_remote_training_json(
            [
                "status",
                "--output-root",
                remote_training_output_root.as_posix(),
                "--launch-root",
                launch_root.as_posix(),
            ],
            label="ref-mel comparison status poll",
        )
        last_status = payload
        if predicate(payload):
            return payload
        time.sleep(poll_interval_seconds)
    if last_status is None:
        raise SystemExit(
            "Ref-mel comparison timed out before receiving any training status payload."
        )
    raise SystemExit(
        "Ref-mel comparison timed out waiting for training completion.\n"
        f"last status:\n{json.dumps(last_status, indent=2, ensure_ascii=False)}"
    )


def completed_training_predicate(status_payload: dict[str, object]) -> bool:
    """Return True when one training run completed successfully."""
    if status_payload.get("pilot_report_found") is True and status_payload.get("exit_code") == 0:
        return True
    if status_payload.get("status") == "exited" and status_payload.get("exit_code") != 0:
        raise SystemExit(
            "Ref-mel comparison observed a failed Qwen training run.\n"
            f"status:\n{json.dumps(status_payload, indent=2, ensure_ascii=False)}"
        )
    return False


def render_report_markdown(report: ComparisonReport) -> str:
    """Render one concise markdown report for the comparison output."""
    return "\n".join(
        [
            "# Qwen Ref-Mel Cache Comparison",
            "",
            f"- generated_at: `{report.generated_at}`",
            f"- comparison_id: `{report.comparison_id}`",
            f"- remote_training_output_root: `{report.remote_training_output_root}`",
            f"- max_steps: `{report.max_steps}`",
            f"- checkpoint_interval_steps: `{report.checkpoint_interval_steps}`",
            "",
            "## Cache Off",
            "",
            f"- launch_id: `{report.cache_off.launch_id}`",
            f"- optimizer_steps_completed: `{report.cache_off.optimizer_steps_completed}`",
            f"- train_iterations_completed: `{report.cache_off.train_iterations_completed}`",
            f"- ref_mel_cache_hit_rate: `{report.cache_off.ref_mel_cache_hit_rate}`",
            f"- train_gpu_busy_percent_median: `{report.cache_off.train_gpu_busy_percent_median}`",
            (
                "- steady_state_gpu_busy_percent_median: "
                f"`{report.cache_off.steady_state_gpu_busy_percent_median}`"
            ),
            "",
            "## Cache On",
            "",
            f"- launch_id: `{report.cache_on.launch_id}`",
            f"- optimizer_steps_completed: `{report.cache_on.optimizer_steps_completed}`",
            f"- train_iterations_completed: `{report.cache_on.train_iterations_completed}`",
            f"- ref_mel_cache_hit_rate: `{report.cache_on.ref_mel_cache_hit_rate}`",
            f"- train_gpu_busy_percent_median: `{report.cache_on.train_gpu_busy_percent_median}`",
            (
                "- steady_state_gpu_busy_percent_median: "
                f"`{report.cache_on.steady_state_gpu_busy_percent_median}`"
            ),
            "",
            "## Deltas",
            "",
            (
                "- delta_train_gpu_busy_percent_median (cache_on - cache_off): "
                f"`{report.delta_train_gpu_busy_percent_median}`"
            ),
            (
                "- delta_steady_state_gpu_busy_percent_median (cache_on - cache_off): "
                f"`{report.delta_steady_state_gpu_busy_percent_median}`"
            ),
        ]
    )


def launch_variant(
    *,
    settings: ComparisonSettings,
    comparison_id: str,
    variant_id: str,
    ref_mel_cache_enabled: bool,
) -> dict[str, object]:
    """Launch one training variant and return the launch payload."""
    launch_id = f"{comparison_id}-{variant_id}"
    command = [
        "launch",
        "--output-root",
        settings.remote_training_output_root.as_posix(),
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
        boolean_flag("--ref-mel-cache-enabled", ref_mel_cache_enabled),
        "--ref-mel-cache-max-items",
        str(settings.ref_mel_cache_max_items),
        "--resource-monitor-interval-seconds",
        str(settings.resource_monitor_interval_seconds),
    ]
    if settings.training_bundle_root is not None:
        command.extend(["--pilot-bundle-root", settings.training_bundle_root.as_posix()])
    if settings.resource_monitor_duration_seconds is not None:
        command.extend(
            [
                "--resource-monitor-duration-seconds",
                str(settings.resource_monitor_duration_seconds),
            ]
        )
    if settings.skip_build:
        command.append("--skip-build")
    return run_remote_training_json(command, label=f"ref-mel comparison launch {variant_id}")


def delta(lhs: float | None, rhs: float | None) -> float | None:
    """Return one arithmetic delta when both sides are present."""
    if lhs is None or rhs is None:
        return None
    return lhs - rhs


def required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Ref-mel comparison expected string field `{key}`.")
    return value


def required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Ref-mel comparison expected integer field `{key}`.")
    return value


def required_object(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return one required object field from a payload."""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"Ref-mel comparison expected object field `{key}`.")
    return dict(value)


def optional_object(payload: dict[str, object], key: str) -> dict[str, object] | None:
    """Return one optional object field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SystemExit(f"Ref-mel comparison expected object field `{key}` when provided.")
    return dict(value)


def optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return one optional integer field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise SystemExit(f"Ref-mel comparison expected integer field `{key}` when provided.")
    return value


def optional_float(payload: dict[str, object], key: str) -> float | None:
    """Return one optional float field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise SystemExit(f"Ref-mel comparison expected float field `{key}` when provided.")
    return float(value)


def optional_bool(payload: dict[str, object], key: str) -> bool | None:
    """Return one optional boolean field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise SystemExit(f"Ref-mel comparison expected boolean field `{key}` when provided.")
    return value


def variant_summary_from_payloads(
    *,
    variant_id: str,
    ref_mel_cache_enabled: bool,
    launch_payload: dict[str, object],
    final_status_payload: dict[str, object],
) -> VariantSummary:
    """Build one typed variant summary from launch and final-status payloads."""
    run_root = required_str(launch_payload, "run_root")
    launch_id = required_str(launch_payload, "launch_id")
    pilot_report = required_object(final_status_payload, "pilot_report")
    training_summary = required_object(pilot_report, "training_summary")
    ref_mel_cache = optional_object(training_summary, "ref_mel_cache")
    resource_monitor = optional_object(final_status_payload, "resource_monitor")
    summary_train = (
        None if resource_monitor is None else optional_object(resource_monitor, "summary_train")
    )
    return VariantSummary(
        variant_id=variant_id,
        launch_id=launch_id,
        launch_root=required_str(launch_payload, "launch_root"),
        run_root=run_root,
        ref_mel_cache_enabled=ref_mel_cache_enabled,
        exit_code=required_int(final_status_payload, "exit_code"),
        optimizer_steps_completed=required_int(training_summary, "optimizer_steps_completed"),
        train_iterations_completed=required_int(training_summary, "train_iterations_completed"),
        ref_mel_cache_hits=None
        if ref_mel_cache is None
        else optional_int(ref_mel_cache, "cache_hits"),
        ref_mel_cache_misses=None
        if ref_mel_cache is None
        else optional_int(ref_mel_cache, "cache_misses"),
        ref_mel_cache_hit_rate=None
        if ref_mel_cache is None
        else optional_float(ref_mel_cache, "cache_hit_rate"),
        train_gpu_busy_percent_median=None
        if summary_train is None
        else optional_float(summary_train, "gpu_busy_percent_median"),
        steady_state_gpu_busy_percent_median=None
        if resource_monitor is None
        else optional_float(resource_monitor, "steady_state_train_gpu_busy_median_percent"),
        steady_state_sample_count=None
        if resource_monitor is None
        else optional_int(resource_monitor, "steady_state_train_sample_count"),
        steady_state_gate_met=None
        if resource_monitor is None
        else optional_bool(resource_monitor, "steady_state_gpu_busy_gate_met"),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the live Hemma comparison."""
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = ComparisonSettings(
        local_output_root=Path(args.output_root),
        remote_training_output_root=Path(args.remote_training_output_root),
        training_bundle_root=args.training_bundle_root,
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
    current_comparison_id = default_comparison_id()
    current_comparison_root = comparison_root(settings.local_output_root, current_comparison_id)
    current_comparison_root.mkdir(parents=True, exist_ok=True)

    cache_off_launch = launch_variant(
        settings=settings,
        comparison_id=current_comparison_id,
        variant_id="cache-off",
        ref_mel_cache_enabled=False,
    )
    cache_off_launch_root = (
        settings.remote_training_output_root / f"{current_comparison_id}-cache-off"
    )
    cache_off_status = poll_remote_training_status(
        remote_training_output_root=settings.remote_training_output_root,
        launch_root=cache_off_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=completed_training_predicate,
    )
    write_json(current_comparison_root / "cache_off_launch.json", cache_off_launch)
    write_json(current_comparison_root / "cache_off_final_status.json", cache_off_status)

    cache_on_launch = launch_variant(
        settings=settings,
        comparison_id=current_comparison_id,
        variant_id="cache-on",
        ref_mel_cache_enabled=True,
    )
    cache_on_launch_root = (
        settings.remote_training_output_root / f"{current_comparison_id}-cache-on"
    )
    cache_on_status = poll_remote_training_status(
        remote_training_output_root=settings.remote_training_output_root,
        launch_root=cache_on_launch_root,
        poll_interval_seconds=settings.poll_interval_seconds,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        predicate=completed_training_predicate,
    )
    write_json(current_comparison_root / "cache_on_launch.json", cache_on_launch)
    write_json(current_comparison_root / "cache_on_final_status.json", cache_on_status)

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
    report = ComparisonReport(
        generated_at=utc_now_iso(),
        comparison_id=current_comparison_id,
        remote_training_output_root=settings.remote_training_output_root.as_posix(),
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
    write_json(current_comparison_root / "report.json", asdict(report))
    write_markdown(current_comparison_root / "report.md", render_report_markdown(report))
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0
