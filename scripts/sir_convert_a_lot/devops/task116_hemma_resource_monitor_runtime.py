"""Runtime helpers for the detached Task 116 Hemma resource monitor.

Purpose:
    Provide the worker loop, detached-process spawn helper, and deterministic
    artifact handling for the committed Hemma resource monitor used during
    sustained Qwen preprocessing windows.

Relationships:
    - Used by `run_task116_hemma_resource_monitor.py`.
    - Reuses `gpu_utilization_snapshot` for bounded host GPU samples.
    - Reuses `system_resource_snapshot` for bounded host CPU and RAM samples.
    - Reuses Task 103 atomic artifact writers so live operator reads do not see
      truncated JSON/JSONL during monitor updates.
"""

from __future__ import annotations

import os
import signal
import statistics
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    write_json,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task116_hemma_resource_monitor_models import (
    RuntimeKind,
    Task116ResourceMonitorLaunch,
    Task116ResourceMonitorRunState,
    Task116ResourceMonitorStatus,
    Task116ResourceMonitorSummary,
    Task116ResourceSample,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_utilization_snapshot import (
    GpuUtilizationSnapshot,
    sample_gpu_utilization_snapshot,
)
from scripts.sir_convert_a_lot.infrastructure.system_resource_snapshot import (
    HostResourceSampler,
)


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_launch_id() -> str:
    """Build one deterministic launch id for the resource monitor."""
    return datetime.now(UTC).strftime("task116-resource-%Y%m%dt%H%M%Sz").lower()


def launch_metadata_path(launch_root: Path) -> Path:
    """Return the launch metadata path for one resource monitor launch."""
    return launch_root / "launch.json"


def status_metadata_path(launch_root: Path) -> Path:
    """Return the status metadata path for one resource monitor launch."""
    return launch_root / "status.json"


def summary_metadata_path(launch_root: Path) -> Path:
    """Return the summary metadata path for one resource monitor launch."""
    return launch_root / "summary.json"


def latest_pointer_path(output_root: Path) -> Path:
    """Return the latest-launch pointer path."""
    return output_root / "latest-launch.json"


def worker_state_path(launch_root: Path) -> Path:
    """Return the worker state path."""
    return launch_root / "worker-state.json"


def samples_path(launch_root: Path) -> Path:
    """Return the JSONL sample path."""
    return launch_root / "samples.jsonl"


def stop_request_path(launch_root: Path) -> Path:
    """Return the stop-request marker path."""
    return launch_root / "stop.json"


def stdout_log_path(launch_root: Path) -> Path:
    """Return the worker stdout log path."""
    return launch_root / "worker.stdout.log"


def stderr_log_path(launch_root: Path) -> Path:
    """Return the worker stderr log path."""
    return launch_root / "worker.stderr.log"


def load_json(path: Path) -> dict[str, object]:
    """Load one JSON object from disk."""
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected one JSON object in `{path.as_posix()}`.")
    return payload


def load_samples(launch_root: Path) -> list[Task116ResourceSample]:
    """Load all recorded samples for one launch root."""
    import json

    path = samples_path(launch_root)
    if not path.exists():
        return []
    samples: list[Task116ResourceSample] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip() == "":
            continue
        payload = json.loads(raw_line)
        if not isinstance(payload, dict):
            raise SystemExit(f"Malformed resource sample in `{path.as_posix()}`.")
        samples.append(
            Task116ResourceSample(
                captured_at=required_str(payload, "captured_at"),
                runtime_kind=required_runtime_kind(payload, "runtime_kind"),
                gpu_busy_percent=optional_int(payload, "gpu_busy_percent"),
                gpu_memory_used_percent=optional_int(payload, "gpu_memory_used_percent"),
                host_cpu_busy_percent=optional_int(payload, "host_cpu_busy_percent"),
                host_memory_used_percent=optional_int(payload, "host_memory_used_percent"),
            )
        )
    return samples


def _summarize_int_values(values: list[int | None]) -> tuple[int | None, float | None, int | None]:
    """Return min/median/max for one optional integer sample sequence."""
    present_values = [value for value in values if value is not None]
    if len(present_values) == 0:
        return None, None, None
    return (
        min(present_values),
        float(statistics.median(present_values)),
        max(present_values),
    )


def summarize_samples(
    launch_id: str, samples: list[Task116ResourceSample]
) -> Task116ResourceMonitorSummary:
    """Summarize one sequence of resource monitor samples."""
    gpu_busy_min, gpu_busy_median, gpu_busy_max = _summarize_int_values(
        [sample.gpu_busy_percent for sample in samples]
    )
    gpu_memory_min, gpu_memory_median, gpu_memory_max = _summarize_int_values(
        [sample.gpu_memory_used_percent for sample in samples]
    )
    host_cpu_min, host_cpu_median, host_cpu_max = _summarize_int_values(
        [sample.host_cpu_busy_percent for sample in samples]
    )
    host_memory_min, host_memory_median, host_memory_max = _summarize_int_values(
        [sample.host_memory_used_percent for sample in samples]
    )
    return Task116ResourceMonitorSummary(
        launch_id=launch_id,
        sample_count=len(samples),
        first_sample_at=samples[0].captured_at if len(samples) > 0 else None,
        last_sample_at=samples[-1].captured_at if len(samples) > 0 else None,
        gpu_busy_percent_min=gpu_busy_min,
        gpu_busy_percent_median=gpu_busy_median,
        gpu_busy_percent_max=gpu_busy_max,
        gpu_memory_used_percent_min=gpu_memory_min,
        gpu_memory_used_percent_median=gpu_memory_median,
        gpu_memory_used_percent_max=gpu_memory_max,
        host_cpu_busy_percent_min=host_cpu_min,
        host_cpu_busy_percent_median=host_cpu_median,
        host_cpu_busy_percent_max=host_cpu_max,
        host_memory_used_percent_min=host_memory_min,
        host_memory_used_percent_median=host_memory_median,
        host_memory_used_percent_max=host_memory_max,
    )


def write_launch_metadata(path: Path, payload: Task116ResourceMonitorLaunch) -> None:
    """Write one launch metadata artifact."""
    write_json(path, asdict(payload))


def write_worker_state(path: Path, payload: Task116ResourceMonitorRunState) -> None:
    """Write one worker-state artifact."""
    write_json(path, asdict(payload))


def write_summary(path: Path, payload: Task116ResourceMonitorSummary) -> None:
    """Write one summary artifact."""
    write_json(path, asdict(payload))


def write_status(path: Path, payload: Task116ResourceMonitorStatus) -> None:
    """Write one status artifact."""
    write_json(path, asdict(payload))


def write_latest_pointer(output_root: Path, launch_root: Path) -> None:
    """Persist the latest launch pointer for operator convenience."""
    write_json(latest_pointer_path(output_root), {"launch_root": launch_root.as_posix()})


def spawn_detached_worker(
    command: list[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    """Spawn one detached worker process and return its process id."""
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.fork()
    if pid != 0:
        return pid
    try:
        os.setsid()
        stdin_handle = open(os.devnull, "r", encoding="utf-8")
        stdout_handle = open(stdout_path, "a", encoding="utf-8")
        stderr_handle = open(stderr_path, "a", encoding="utf-8")
        os.dup2(stdin_handle.fileno(), sys.stdin.fileno())
        os.dup2(stdout_handle.fileno(), sys.stdout.fileno())
        os.dup2(stderr_handle.fileno(), sys.stderr.fileno())
        os.execv(command[0], command)
    except BaseException:
        os._exit(1)


def process_is_running(pid: int) -> bool:
    """Return whether one process id appears to still be alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def build_status(launch_root: Path) -> Task116ResourceMonitorStatus:
    """Build one status payload from launch metadata and recorded samples."""
    launch_payload = load_json(launch_metadata_path(launch_root))
    samples = load_samples(launch_root)
    summary = summarize_samples(required_str(launch_payload, "launch_id"), samples)
    worker_state = (
        load_json(worker_state_path(launch_root))
        if worker_state_path(launch_root).exists()
        else None
    )
    return Task116ResourceMonitorStatus(
        checked_at=utc_now_iso(),
        launch_id=required_str(launch_payload, "launch_id"),
        pid=required_int(launch_payload, "pid"),
        running=process_is_running(required_int(launch_payload, "pid")),
        runtime_kind=required_runtime_kind(launch_payload, "runtime_kind"),
        interval_seconds=required_float(launch_payload, "interval_seconds"),
        duration_seconds=optional_float(launch_payload, "duration_seconds"),
        stop_requested=stop_request_path(launch_root).exists(),
        worker_state_found=worker_state is not None,
        worker_state=worker_state,
        summary=asdict(summary),
    )


def run_worker(
    *,
    launch_root: Path,
    launch_id: str,
    started_at: str,
    runtime_kind: RuntimeKind,
    interval_seconds: float,
    duration_seconds: float | None,
) -> int:
    """Run the detached sampling loop until stopped or timed out."""
    state_path = worker_state_path(launch_root)
    stop_path = stop_request_path(launch_root)
    samples = load_samples(launch_root)
    sample_count = len(samples)
    latest_sample = samples[-1] if len(samples) > 0 else None
    host_resource_sampler = HostResourceSampler()
    finished = False

    def _finish(reason: str, error: str | None = None) -> int:
        nonlocal finished
        if finished:
            return 0
        finished = True
        write_worker_state(
            state_path,
            Task116ResourceMonitorRunState(
                launch_id=launch_id,
                started_at=started_at,
                finished_at=utc_now_iso(),
                exit_reason=reason,
                sample_count=sample_count,
                latest_sample_at=latest_sample.captured_at if latest_sample is not None else None,
                latest_gpu_busy_percent=(
                    latest_sample.gpu_busy_percent if latest_sample is not None else None
                ),
                latest_gpu_memory_used_percent=(
                    latest_sample.gpu_memory_used_percent if latest_sample is not None else None
                ),
                latest_host_cpu_busy_percent=(
                    latest_sample.host_cpu_busy_percent if latest_sample is not None else None
                ),
                latest_host_memory_used_percent=(
                    latest_sample.host_memory_used_percent if latest_sample is not None else None
                ),
                error=error,
            ),
        )
        return 0 if error is None else 1

    def _handle_signal(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    started_monotonic = time.monotonic()
    write_worker_state(
        state_path,
        Task116ResourceMonitorRunState(
            launch_id=launch_id,
            started_at=started_at,
            finished_at=None,
            exit_reason=None,
            sample_count=sample_count,
            latest_sample_at=latest_sample.captured_at if latest_sample is not None else None,
            latest_gpu_busy_percent=latest_sample.gpu_busy_percent
            if latest_sample is not None
            else None,
            latest_gpu_memory_used_percent=(
                latest_sample.gpu_memory_used_percent if latest_sample is not None else None
            ),
            latest_host_cpu_busy_percent=(
                latest_sample.host_cpu_busy_percent if latest_sample is not None else None
            ),
            latest_host_memory_used_percent=(
                latest_sample.host_memory_used_percent if latest_sample is not None else None
            ),
            error=None,
        ),
    )
    try:
        while True:
            if stop_path.exists():
                return _finish("stop_requested")
            if (
                duration_seconds is not None
                and (time.monotonic() - started_monotonic) >= duration_seconds
            ):
                return _finish("duration_elapsed")
            snapshot: GpuUtilizationSnapshot | None = sample_gpu_utilization_snapshot(
                runtime_kind=runtime_kind
            )
            host_resource_snapshot = host_resource_sampler.sample()
            latest_sample = Task116ResourceSample(
                captured_at=utc_now_iso(),
                runtime_kind=runtime_kind,
                gpu_busy_percent=snapshot.gpu_busy_percent if snapshot is not None else None,
                gpu_memory_used_percent=snapshot.gpu_memory_used_percent
                if snapshot is not None
                else None,
                host_cpu_busy_percent=host_resource_snapshot.host_cpu_busy_percent,
                host_memory_used_percent=host_resource_snapshot.host_memory_used_percent,
            )
            samples.append(latest_sample)
            rendered_samples: list[object] = [asdict(sample) for sample in samples]
            write_jsonl(samples_path(launch_root), rendered_samples)
            sample_count = len(samples)
            write_worker_state(
                state_path,
                Task116ResourceMonitorRunState(
                    launch_id=launch_id,
                    started_at=started_at,
                    finished_at=None,
                    exit_reason=None,
                    sample_count=sample_count,
                    latest_sample_at=latest_sample.captured_at,
                    latest_gpu_busy_percent=latest_sample.gpu_busy_percent,
                    latest_gpu_memory_used_percent=latest_sample.gpu_memory_used_percent,
                    latest_host_cpu_busy_percent=latest_sample.host_cpu_busy_percent,
                    latest_host_memory_used_percent=latest_sample.host_memory_used_percent,
                    error=None,
                ),
            )
            time.sleep(max(1.0, interval_seconds))
    except KeyboardInterrupt:
        return _finish("signal_interrupted")
    except Exception as exc:  # pragma: no cover - defensive operator safeguard
        return _finish("worker_error", error=str(exc))


def required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field."""
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise SystemExit(f"Expected non-empty string `{key}`.")
    return value


def required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Expected integer `{key}`.")
    return value


def required_float(payload: dict[str, object], key: str) -> float:
    """Return one required float-like field."""
    value = payload.get(key)
    if isinstance(value, int):
        return float(value)
    if not isinstance(value, float):
        raise SystemExit(f"Expected float `{key}`.")
    return value


def optional_float(payload: dict[str, object], key: str) -> float | None:
    """Return one optional float-like field."""
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    raise SystemExit(f"Expected float or null `{key}`.")


def optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return one optional integer field."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise SystemExit(f"Expected integer or null `{key}`.")
    return value


def required_runtime_kind(payload: dict[str, object], key: str) -> RuntimeKind:
    """Return one required runtime-kind field."""
    value = payload.get(key)
    if value == "rocm":
        return "rocm"
    if value == "cuda":
        return "cuda"
    if value == "none":
        return "none"
    raise SystemExit(f"Expected runtime kind `{key}` to be one of rocm/cuda/none.")
