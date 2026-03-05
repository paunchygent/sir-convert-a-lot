"""Benchmark v2 telemetry overhead and saturation evidence for Story 20.

Purpose:
    Execute a deterministic, sustained queued-job workload and compare runtime
    throughput across full telemetry, sink-disabled telemetry, and runtime
    telemetry-call bypass modes to produce Task 73 overhead evidence.

Relationships:
    - Uses `infrastructure.runtime_engine_v2.ServiceRuntimeV2` directly.
    - Uses `infrastructure.runtime_telemetry_v2.RuntimeTelemetrySinkV2` for the
      `telemetry_full` benchmark variant.
    - Writes generated benchmark artifacts under `build/benchmarks/`.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

from prometheus_client import CollectorRegistry, generate_latest

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_telemetry_v2 import RuntimeTelemetrySinkV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult

DEFAULT_OUTPUT_JSON = Path("build/benchmarks/story-20/task-73-telemetry-overhead-local.json")
DEFAULT_DATA_ROOT = Path("build/benchmarks/story-20/task-73-telemetry-runtime")


class VariantSummary(TypedDict):
    """One workload variant summary."""

    variant: Literal["telemetry_full", "telemetry_sink_disabled", "telemetry_calls_bypassed"]
    total_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    duration_seconds: float
    throughput_jobs_per_minute: float
    metrics_summary: dict[str, float | int | bool]


class BenchmarkPayload(TypedDict):
    """Top-level benchmark payload."""

    benchmark_id: str
    generated_at: str
    config: dict[str, int | float]
    variants: list[VariantSummary]
    overhead_percent: dict[str, float]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _job_spec(filename: str) -> JobSpecV2:
    return JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": filename, "format": "md"},
            "conversion": {
                "output_format": "pdf",
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "retention": {"pin": False},
        }
    )


def _sum_counter_samples(metrics_text: str, prefix: str) -> float:
    pattern = re.compile(rf"^{re.escape(prefix)}\{{[^}}]*\}}\s+([0-9.eE+-]+)$", re.MULTILINE)
    values = [float(match.group(1)) for match in pattern.finditer(metrics_text)]
    return sum(values)


def _read_gauge_value(metrics_text: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s+([0-9.eE+-]+)$", metrics_text, re.MULTILINE)
    if match is None:
        return 0.0
    return float(match.group(1))


def _build_metrics_summary(metrics_text: str) -> dict[str, float | int | bool]:
    return {
        "stage_duration_samples": _sum_counter_samples(
            metrics_text,
            "sir_convert_a_lot_v2_stage_duration_seconds_count",
        ),
        "terminal_job_samples": _sum_counter_samples(
            metrics_text,
            "sir_convert_a_lot_v2_jobs_terminal_total",
        ),
        "retry_samples": _sum_counter_samples(
            metrics_text,
            "sir_convert_a_lot_v2_job_retries_total",
        ),
        "worker_saturation_ratio": _read_gauge_value(
            metrics_text,
            "sir_convert_a_lot_v2_worker_saturation_ratio",
        ),
        "gpu_concurrency_cap": _read_gauge_value(
            metrics_text,
            "sir_convert_a_lot_v2_gpu_concurrency_cap",
        ),
        "jobs_active_gauge": _read_gauge_value(
            metrics_text,
            "sir_convert_a_lot_v2_jobs_active",
        ),
        "jobs_queued_gauge": _read_gauge_value(
            metrics_text,
            "sir_convert_a_lot_v2_jobs_queued",
        ),
        "contains_job_id_label": "job_id=" in metrics_text or "jobv2_" in metrics_text,
    }


def _run_variant(
    *,
    variant: Literal["telemetry_full", "telemetry_sink_disabled", "telemetry_calls_bypassed"],
    total_jobs: int,
    max_workers: int,
    stub_work_seconds: float,
    data_root: Path,
) -> VariantSummary:
    registry: CollectorRegistry | None = None
    telemetry_sink: RuntimeTelemetrySinkV2 | None = None
    enable_runtime_telemetry_calls = True
    if variant == "telemetry_full":
        registry = CollectorRegistry()
        telemetry_sink = RuntimeTelemetrySinkV2(registry=registry)
    elif variant == "telemetry_calls_bypassed":
        enable_runtime_telemetry_calls = False

    runtime = ServiceRuntimeV2(
        ServiceConfig(
            api_key="benchmark-key",
            data_root=data_root,
            max_workers=max(1, max_workers),
            enable_supervisor=True,
            supervisor_poll_seconds=0.02,
            processing_delay_seconds=0.0,
            heartbeat_interval_seconds=0.05,
            enable_runtime_telemetry_calls=enable_runtime_telemetry_calls,
        ),
        telemetry_sink=telemetry_sink,
    )

    def _stub_execute(**_kwargs: object) -> V2ExecutionResult:
        if stub_work_seconds > 0:
            time.sleep(stub_work_seconds)
        return V2ExecutionResult(
            artifact_bytes=b"%PDF-1.4\n% telemetry benchmark\n%%EOF\n",
            pipeline_used="md_to_pdf_v2",
            backend_used="pandoc+weasyprint",
            acceleration_used="cpu",
            warnings=["docling_auto_ocr_retry_applied"],
            phase_timings_ms={
                "backend_convert_ms": 8,
                "normalize_ms": 3,
                "conversion_attempt_ms": int(max(0.0, stub_work_seconds) * 1000.0),
            },
            options_fingerprint="story20-telemetry-benchmark",
        )

    original_execute = runtime_engine_v2.execute_v2_job_conversion
    runtime_engine_v2.execute_v2_job_conversion = _stub_execute

    try:
        created_job_ids: list[str] = []
        peak_worker_saturation = 0.0
        peak_jobs_active = 0.0
        peak_jobs_queued = 0.0
        started = time.perf_counter()
        for index in range(total_jobs):
            created = runtime.create_job(
                spec=_job_spec(filename=f"story20-{index:03d}.md"),
                upload_bytes=b"# Benchmark\n\nTask 73 telemetry overhead benchmark.\n",
                resources_zip_bytes=None,
                reference_docx_bytes=None,
            )
            created_job_ids.append(created.job_id)

        deadline = time.monotonic() + max(10.0, float(total_jobs) * max(0.05, stub_work_seconds))
        while time.monotonic() < deadline:
            if registry is not None:
                polled_metrics = generate_latest(registry).decode("utf-8")
                peak_worker_saturation = max(
                    peak_worker_saturation,
                    _read_gauge_value(
                        polled_metrics, "sir_convert_a_lot_v2_worker_saturation_ratio"
                    ),
                )
                peak_jobs_active = max(
                    peak_jobs_active,
                    _read_gauge_value(polled_metrics, "sir_convert_a_lot_v2_jobs_active"),
                )
                peak_jobs_queued = max(
                    peak_jobs_queued,
                    _read_gauge_value(polled_metrics, "sir_convert_a_lot_v2_jobs_queued"),
                )
            statuses: list[JobStatus] = []
            for job_id in created_job_ids:
                record = runtime.get_job(job_id)
                if record is None:
                    raise RuntimeError(f"missing benchmark job record: {job_id}")
                statuses.append(record.status)
            if all(
                status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}
                for status in statuses
            ):
                break
            time.sleep(0.02)
        else:
            raise RuntimeError("benchmark variant timed out before all jobs reached terminal state")

        duration_seconds = max(1e-9, time.perf_counter() - started)
        terminal_statuses: list[JobStatus] = []
        for job_id in created_job_ids:
            record = runtime.get_job(job_id)
            if record is None:
                raise RuntimeError(f"missing benchmark job record during summary: {job_id}")
            terminal_statuses.append(record.status)
        succeeded_jobs = sum(1 for status in terminal_statuses if status == JobStatus.SUCCEEDED)
        failed_jobs = sum(1 for status in terminal_statuses if status == JobStatus.FAILED)
        metrics_summary: dict[str, float | int | bool] = {}
        if registry is not None:
            metrics_text = generate_latest(registry).decode("utf-8")
            metrics_summary = _build_metrics_summary(metrics_text)
            metrics_summary["worker_saturation_peak"] = round(peak_worker_saturation, 6)
            metrics_summary["jobs_active_peak"] = round(peak_jobs_active, 6)
            metrics_summary["jobs_queued_peak"] = round(peak_jobs_queued, 6)

        return {
            "variant": variant,
            "total_jobs": total_jobs,
            "succeeded_jobs": succeeded_jobs,
            "failed_jobs": failed_jobs,
            "duration_seconds": round(duration_seconds, 6),
            "throughput_jobs_per_minute": round((float(total_jobs) / duration_seconds) * 60.0, 6),
            "metrics_summary": metrics_summary,
        }
    finally:
        runtime_engine_v2.execute_v2_job_conversion = original_execute
        runtime.shutdown()


def run_benchmark(
    *,
    output_json: Path,
    data_root: Path,
    total_jobs: int,
    max_workers: int,
    stub_work_seconds: float,
) -> BenchmarkPayload:
    enforce_generated_output_path(output_json, label="output_json")
    enforce_generated_output_path(data_root, label="data_root")

    telemetry_full = _run_variant(
        variant="telemetry_full",
        total_jobs=total_jobs,
        max_workers=max_workers,
        stub_work_seconds=stub_work_seconds,
        data_root=data_root / "telemetry_full",
    )
    telemetry_sink_disabled = _run_variant(
        variant="telemetry_sink_disabled",
        total_jobs=total_jobs,
        max_workers=max_workers,
        stub_work_seconds=stub_work_seconds,
        data_root=data_root / "telemetry_sink_disabled",
    )
    telemetry_calls_bypassed = _run_variant(
        variant="telemetry_calls_bypassed",
        total_jobs=total_jobs,
        max_workers=max_workers,
        stub_work_seconds=stub_work_seconds,
        data_root=data_root / "telemetry_calls_bypassed",
    )

    sink_disabled_baseline = max(1e-9, telemetry_sink_disabled["duration_seconds"])
    bypassed_baseline = max(1e-9, telemetry_calls_bypassed["duration_seconds"])
    full_vs_sink_disabled = (
        (telemetry_full["duration_seconds"] - sink_disabled_baseline) / sink_disabled_baseline
    ) * 100.0
    full_vs_bypassed = (
        (telemetry_full["duration_seconds"] - bypassed_baseline) / bypassed_baseline
    ) * 100.0

    payload: BenchmarkPayload = {
        "benchmark_id": "task-73-telemetry-overhead",
        "generated_at": _utc_now_iso(),
        "config": {
            "total_jobs": total_jobs,
            "max_workers": max_workers,
            "stub_work_seconds": stub_work_seconds,
        },
        "variants": [telemetry_full, telemetry_sink_disabled, telemetry_calls_bypassed],
        "overhead_percent": {
            "full_vs_sink_disabled": round(full_vs_sink_disabled, 4),
            "full_vs_bypassed": round(full_vs_bypassed, 4),
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Task 73 telemetry overhead benchmark.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--total-jobs", type=int, default=40)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--stub-work-seconds", type=float, default=0.02)
    args = parser.parse_args()

    payload = run_benchmark(
        output_json=args.output_json,
        data_root=args.data_root,
        total_jobs=max(1, args.total_jobs),
        max_workers=max(1, args.max_workers),
        stub_work_seconds=max(0.0, args.stub_work_seconds),
    )
    print(
        "benchmark-written",
        args.output_json,
        f"full_vs_sink_disabled={payload['overhead_percent']['full_vs_sink_disabled']}",
        f"full_vs_bypassed={payload['overhead_percent']['full_vs_bypassed']}",
    )


if __name__ == "__main__":
    main()
