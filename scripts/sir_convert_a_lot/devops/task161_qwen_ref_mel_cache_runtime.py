"""Runtime helpers for Task 161 ref-mel cache comparison on Hemma.

Purpose:
    Provide local orchestration helpers that launch two bounded remote Task 101
    runs (cache-off and cache-on), poll deterministic status payloads, and
    compute one machine-readable comparison report.

Relationships:
    - Used by `run_task161_hemma_ref_mel_cache_comparison.py`.
    - Calls `task-101-pilot` over the canonical `run-hemma` wrapper.
    - Parses mixed stdout JSON through shared Task 100 runtime helpers.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    parse_json_object_from_mixed_stdout,
)

DEFAULT_TASK161_REMOTE_TASK101_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/task-101-qwen3-tts-swedish-hemma-pilot"
)
DEFAULT_TASK161_LOCAL_OUTPUT_ROOT = Path("build/verification/task-161-ref-mel-cache-comparison")
DEFAULT_TASK161_MAX_STEPS = 240
DEFAULT_TASK161_CHECKPOINT_INTERVAL_STEPS = 100
DEFAULT_TASK161_BATCH_SIZE = 1
DEFAULT_TASK161_NUM_EPOCHS = 1
DEFAULT_TASK161_POLL_INTERVAL_SECONDS = 20
DEFAULT_TASK161_POLL_TIMEOUT_SECONDS = 5400
DEFAULT_TASK161_REF_MEL_CACHE_MAX_ITEMS = 2048
DEFAULT_TASK161_RESOURCE_MONITOR_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True)
class Task161ComparisonSettings:
    """Configuration for one bounded Task 161 cache comparison run."""

    local_output_root: Path
    remote_task101_output_root: Path
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
class Task161VariantSummary:
    """Summary metrics for one Task 161 comparison variant."""

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
class Task161ComparisonReport:
    """Machine-readable Task 161 comparison report."""

    generated_at: str
    comparison_id: str
    remote_task101_output_root: str
    max_steps: int
    checkpoint_interval_steps: int
    cache_off: Task161VariantSummary
    cache_on: Task161VariantSummary
    delta_train_gpu_busy_percent_median: float | None
    delta_steady_state_gpu_busy_percent_median: float | None


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_comparison_id() -> str:
    """Return one deterministic Task 161 comparison identifier."""
    return f"task161-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def run_remote_task101_json(args: list[str], *, label: str) -> dict[str, object]:
    """Run one remote Task 101 command and parse its JSON payload."""
    command = ["pdm", "run", "run-hemma", "--", "pdm", "run", "task-101-pilot", *args]
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
    """Poll remote Task 101 status until one predicate matches or timeout."""
    deadline = time.monotonic() + poll_timeout_seconds
    last_status: dict[str, object] | None = None
    while time.monotonic() < deadline:
        payload = run_remote_task101_json(
            [
                "status",
                "--output-root",
                remote_task101_output_root.as_posix(),
                "--launch-root",
                launch_root.as_posix(),
            ],
            label="task161 status poll",
        )
        last_status = payload
        if predicate(payload):
            return payload
        time.sleep(poll_interval_seconds)
    if last_status is None:
        raise SystemExit("Task 161 timed out before receiving any Task 101 status payload.")
    raise SystemExit(
        "Task 161 timed out waiting for Task 101 completion.\n"
        f"last status:\n{json.dumps(last_status, indent=2, ensure_ascii=False)}"
    )


def completed_task101_predicate(status_payload: dict[str, object]) -> bool:
    """Return True when one Task 101 run completed successfully."""
    if status_payload.get("pilot_report_found") is True and status_payload.get("exit_code") == 0:
        return True
    if status_payload.get("status") == "exited" and status_payload.get("exit_code") != 0:
        raise SystemExit(
            "Task 161 observed a failed Task 101 run.\n"
            f"status:\n{json.dumps(status_payload, indent=2, ensure_ascii=False)}"
        )
    return False


def render_report_markdown(report: Task161ComparisonReport) -> str:
    """Render one concise markdown report for Task 161 comparison output."""
    return "\n".join(
        [
            "# Task 161 Ref-Mel Cache Comparison",
            "",
            f"- generated_at: `{report.generated_at}`",
            f"- comparison_id: `{report.comparison_id}`",
            f"- remote_task101_output_root: `{report.remote_task101_output_root}`",
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


def variant_summary_from_payloads(
    *,
    variant_id: str,
    ref_mel_cache_enabled: bool,
    launch_payload: dict[str, object],
    final_status_payload: dict[str, object],
) -> Task161VariantSummary:
    """Build one typed variant summary from launch/final-status payloads."""
    run_root = required_str(launch_payload, "run_root")
    launch_id = required_str(launch_payload, "launch_id")
    pilot_report = required_object(final_status_payload, "pilot_report")
    training_summary = required_object(pilot_report, "training_summary")
    ref_mel_cache = optional_object(training_summary, "ref_mel_cache")
    resource_monitor = optional_object(final_status_payload, "resource_monitor")
    summary_train = (
        None if resource_monitor is None else optional_object(resource_monitor, "summary_train")
    )
    return Task161VariantSummary(
        variant_id=variant_id,
        launch_id=launch_id,
        launch_root=(
            Path(required_str(launch_payload, "launch_root")).as_posix()
            if "launch_root" in launch_payload
            else ""
        ),
        run_root=run_root,
        ref_mel_cache_enabled=ref_mel_cache_enabled,
        exit_code=required_int(final_status_payload, "exit_code"),
        optimizer_steps_completed=required_int(training_summary, "optimizer_steps_completed"),
        train_iterations_completed=required_int(training_summary, "train_iterations_completed"),
        ref_mel_cache_hits=(
            None if ref_mel_cache is None else optional_int(ref_mel_cache, "cache_hits")
        ),
        ref_mel_cache_misses=(
            None if ref_mel_cache is None else optional_int(ref_mel_cache, "cache_misses")
        ),
        ref_mel_cache_hit_rate=(
            None if ref_mel_cache is None else optional_float(ref_mel_cache, "cache_hit_rate")
        ),
        train_gpu_busy_percent_median=(
            None
            if summary_train is None
            else optional_float(summary_train, "gpu_busy_percent_median")
        ),
        steady_state_gpu_busy_percent_median=(
            None
            if resource_monitor is None
            else optional_float(resource_monitor, "steady_state_train_gpu_busy_median_percent")
        ),
        steady_state_sample_count=(
            None
            if resource_monitor is None
            else optional_int(resource_monitor, "steady_state_train_sample_count")
        ),
        steady_state_gate_met=(
            None
            if resource_monitor is None
            else optional_bool(resource_monitor, "steady_state_gpu_busy_gate_met")
        ),
    )


def delta(lhs: float | None, rhs: float | None) -> float | None:
    """Return one arithmetic delta when both sides are present."""
    if lhs is None or rhs is None:
        return None
    return lhs - rhs


def required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Task 161 expected string field `{key}`.")
    return value


def required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Task 161 expected integer field `{key}`.")
    return value


def required_object(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return one required object field from a payload."""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"Task 161 expected object field `{key}`.")
    return dict(value)


def optional_object(payload: dict[str, object], key: str) -> dict[str, object] | None:
    """Return one optional object field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SystemExit(f"Task 161 expected object field `{key}` when provided.")
    return dict(value)


def optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return one optional integer field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise SystemExit(f"Task 161 expected integer field `{key}` when provided.")
    return value


def optional_float(payload: dict[str, object], key: str) -> float | None:
    """Return one optional float field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise SystemExit(f"Task 161 expected float field `{key}` when provided.")
    return float(value)


def optional_bool(payload: dict[str, object], key: str) -> bool | None:
    """Return one optional boolean field from a payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise SystemExit(f"Task 161 expected boolean field `{key}` when provided.")
    return value
