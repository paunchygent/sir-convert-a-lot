"""Resource-monitor helpers for Qwen training.

Purpose:
    Launch and inspect a high-resolution sibling resource monitor for each
    long-running training pilot so monitor evidence is discoverable from
    training artifacts.

Relationships:
    - Reuses infrastructure-level monitor runtime helpers.
    - Feeds monitor evidence into training status inspection surfaces.
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Sequence

# Note: These refer to the existing task116 infrastructure which is not yet moved
from scripts.sir_convert_a_lot.devops.task116_hemma_resource_monitor_models import (
    RuntimeKind,
    Task116ResourceMonitorLaunch,
    Task116ResourceSample,
)
from scripts.sir_convert_a_lot.devops.task116_hemma_resource_monitor_runtime import (
    build_status,
    launch_metadata_path,
    load_samples,
    spawn_detached_worker,
    stderr_log_path,
    stdout_log_path,
    summarize_samples,
    utc_now_iso,
    write_latest_pointer,
    write_launch_metadata,
)

DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS = 1.0
DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND: RuntimeKind = "rocm"


def default_resource_monitor_launch_id(training_launch_id: str) -> str:
    """Return the deterministic monitor launch id for one training launch."""
    return f"{training_launch_id}-resource-monitor"


def resource_monitor_output_root(training_launch_root: Path) -> Path:
    """Return the monitor output root for one training launch."""
    return training_launch_root / "resource-monitor"


def launch_resource_monitor(
    *,
    training_launch_id: str,
    training_launch_root: Path,
    runtime_kind: RuntimeKind,
    interval_seconds: float,
    duration_seconds: float | None,
) -> dict[str, object]:
    """Launch one detached resource monitor and return metadata."""
    if interval_seconds <= 0:
        raise ValueError("Resource monitor interval must be positive.")
    if duration_seconds is not None and duration_seconds <= 0:
        raise ValueError("Resource monitor duration must be positive when provided.")
    monitor_output_root = resource_monitor_output_root(training_launch_root)
    monitor_output_root.mkdir(parents=True, exist_ok=True)
    monitor_launch_id = default_resource_monitor_launch_id(training_launch_id)
    monitor_launch_root = monitor_output_root / monitor_launch_id
    monitor_launch_root.mkdir(parents=True, exist_ok=True)
    started_at = utc_now_iso()
    command = [
        sys.executable,
        "-m",
        "scripts.sir_convert_a_lot.devops.run_task116_hemma_resource_monitor",
        "run",
        "--launch-root",
        monitor_launch_root.as_posix(),
        "--launch-id",
        monitor_launch_id,
        "--started-at",
        started_at,
        "--runtime-kind",
        runtime_kind,
        "--interval-seconds",
        str(interval_seconds),
    ]
    if duration_seconds is not None:
        command.extend(["--duration-seconds", str(duration_seconds)])
    pid = spawn_detached_worker(
        command,
        stdout_path=stdout_log_path(monitor_launch_root),
        stderr_path=stderr_log_path(monitor_launch_root),
    )
    launch = Task116ResourceMonitorLaunch(
        generated_at=started_at,
        launch_id=monitor_launch_id,
        repo_root=Path.cwd().resolve().as_posix(),
        pid=pid,
        runtime_kind=runtime_kind,
        interval_seconds=interval_seconds,
        duration_seconds=duration_seconds,
        command=command,
    )
    write_launch_metadata(launch_metadata_path(monitor_launch_root), launch)
    write_latest_pointer(monitor_output_root, monitor_launch_root)
    return {
        "launch_id": monitor_launch_id,
        "launch_root": monitor_launch_root.as_posix(),
        "output_root": monitor_output_root.as_posix(),
        "runtime_kind": runtime_kind,
        "interval_seconds": interval_seconds,
        "duration_seconds": duration_seconds,
    }


def inspect_resource_monitor(
    resource_monitor: Mapping[str, object] | None,
    *,
    phase_history: Sequence[Mapping[str, object]] | None,
) -> dict[str, object] | None:
    """Inspect one linked resource monitor and compute phase summaries."""
    if resource_monitor is None:
        return None
    launch_root_value = resource_monitor.get("launch_root")
    if not isinstance(launch_root_value, str) or launch_root_value.strip() == "":
        return {"available": False, "error": "Monitor metadata lacked `launch_root`."}
    launch_root = Path(launch_root_value)
    if not launch_root.exists():
        return {
            "available": False,
            "error": (f"Monitor launch root does not exist: {launch_root.as_posix()}"),
        }

    status = build_status(launch_root)
    samples = load_samples(launch_root)
    overall_summary = summarize_samples(status.launch_id, samples)
    samples_by_phase = _group_samples_by_phase(
        samples=samples,
        phase_history=phase_history,
    )
    train_summary = summarize_samples(
        f"{status.launch_id}-train",
        samples_by_phase["train"],
    )
    checkpoint_summary = summarize_samples(
        f"{status.launch_id}-checkpoint-save",
        samples_by_phase["checkpoint-save"],
    )
    train_gpu_busy_median = train_summary.gpu_busy_percent_median
    return {
        "available": True,
        "launch_id": status.launch_id,
        "launch_root": launch_root.as_posix(),
        "runtime_kind": status.runtime_kind,
        "interval_seconds": status.interval_seconds,
        "duration_seconds": status.duration_seconds,
        "running": status.running,
        "stop_requested": status.stop_requested,
        "summary_overall": asdict(overall_summary),
        "summary_train": asdict(train_summary),
        "summary_checkpoint_save": asdict(checkpoint_summary),
        "steady_state_gpu_busy_threshold_percent": 90.0,
        "steady_state_train_gpu_busy_median_percent": train_gpu_busy_median,
        "steady_state_train_sample_count": train_summary.sample_count,
        "steady_state_gpu_busy_gate_met": (
            None if train_gpu_busy_median is None else train_gpu_busy_median >= 90.0
        ),
    }


def _group_samples_by_phase(
    *,
    samples: Sequence[Task116ResourceSample],
    phase_history: Sequence[Mapping[str, object]] | None,
) -> dict[str, list[Task116ResourceSample]]:
    """Group monitor samples by training phase-history timestamps."""
    grouped: dict[str, list[Task116ResourceSample]] = {
        "train": [],
        "checkpoint-save": [],
    }
    phase_events = _sorted_phase_events(phase_history)
    if len(phase_events) == 0:
        return grouped
    event_index = 0
    current_phase = phase_events[event_index][1]
    first_phase_timestamp = phase_events[0][0]
    for sample in samples:
        sample_time = _parse_iso_timestamp(sample.captured_at)
        if sample_time is None:
            continue
        if sample_time < first_phase_timestamp:
            continue
        while (
            event_index + 1 < len(phase_events) and phase_events[event_index + 1][0] <= sample_time
        ):
            event_index += 1
            current_phase = phase_events[event_index][1]
        if current_phase in grouped:
            grouped[current_phase].append(sample)
    return grouped


def _sorted_phase_events(
    phase_history: Sequence[Mapping[str, object]] | None,
) -> list[tuple[datetime, str]]:
    """Return sorted `(timestamp, phase)` events from training phase history."""
    if phase_history is None:
        return []
    events: list[tuple[datetime, str]] = []
    for event in phase_history:
        phase_value = event.get("phase")
        updated_at_value = event.get("updated_at")
        if not isinstance(phase_value, str):
            continue
        if phase_value not in {"train", "checkpoint-save"}:
            continue
        if not isinstance(updated_at_value, str):
            continue
        timestamp = _parse_iso_timestamp(updated_at_value)
        if timestamp is None:
            continue
        events.append((timestamp, phase_value))
    events.sort(key=lambda item: item[0])
    return events


def _parse_iso_timestamp(value: str) -> datetime | None:
    """Parse one RFC3339 timestamp into a UTC-aware datetime."""
    normalized = value.strip()
    if normalized == "":
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
