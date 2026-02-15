"""Benchmark GPU governance behavior for Story 003b.

Purpose:
    Execute a deterministic benchmark corpus against the v1 HTTP contract and
    emit machine-readable evidence for GPU-first rollout governance.

Relationships:
    - Uses `scripts.sir_convert_a_lot.service.create_app` as the benchmark API.
    - Produces artifacts referenced by Story 003b and benchmark reference docs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.service import ServiceConfig, create_app

DEFAULT_FIXTURES_DIR = Path("tests/fixtures/benchmark_pdfs")
DEFAULT_OUTPUT_JSON = Path(
    "build/benchmarks/story-003b/benchmark-story-003b-gpu-governance-local.json"
)
DEFAULT_DATA_ROOT = Path("build/benchmarks/story-003b-local")


class BenchmarkJobRecord(TypedDict):
    """One benchmark job result entry."""

    source_file: str
    source_size_bytes: int
    job_id: str | None
    status: str
    error_code: str | None
    latency_seconds: float
    backend_used: str | None
    acceleration_used: str | None


class BenchmarkLatencySummary(TypedDict):
    """Latency summary shape for benchmark artifacts."""

    min: float
    mean: float
    p50: float
    p95: float
    max: float


class BenchmarkSummary(TypedDict):
    """Top-level benchmark summary shape."""

    total_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    success_rate: float
    throughput_jobs_per_minute: float
    latency_seconds: BenchmarkLatencySummary


class RuntimeConfigSummary(TypedDict):
    """Runtime configuration echo included in benchmark output."""

    gpu_available: bool
    allow_cpu_only: bool
    allow_cpu_fallback: bool
    acceleration_policy: str
    processing_delay_seconds: float


class ResourceProfileSummary(TypedDict):
    """Observed resource profile for benchmark output."""

    fixtures_count: int
    fixtures_total_bytes: int
    acceleration_observed: list[str]
    backend_observed: list[str]


class BenchmarkPayload(TypedDict):
    """Canonical benchmark payload shape."""

    benchmark_id: str
    stage: str
    generated_at: str
    fixtures_dir: str
    runtime_config: RuntimeConfigSummary
    summary: BenchmarkSummary
    resource_profile: ResourceProfileSummary
    jobs: list[BenchmarkJobRecord]


def _utc_now_iso() -> str:
    """Return current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _job_spec(filename: str, acceleration_policy: str) -> dict[str, object]:
    """Return a v1 job spec payload for benchmark submissions."""
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": "fast",
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def _percentile(values: list[float], percentile: float) -> float:
    """Compute percentile using linear interpolation on sorted values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return round(sorted_values[0], 6)
    rank = (len(sorted_values) - 1) * percentile
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    interpolated = lower_value + (upper_value - lower_value) * (rank - lower_index)
    return round(interpolated, 6)


def _wait_for_terminal_status(
    client: TestClient, *, api_key: str, job_id: str, max_poll_seconds: float
) -> JobStatus:
    """Poll job status until terminal state is reached or timeout occurs."""
    deadline = time.monotonic() + max_poll_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/v1/convert/jobs/{job_id}",
            headers={"X-API-Key": api_key, "X-Correlation-ID": "corr_benchmark_poll"},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Status polling failed for {job_id}: {response.status_code}")
        status = JobStatus(response.json()["job"]["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return status
        time.sleep(0.05)
    raise RuntimeError(f"Status polling timed out for {job_id}.")


def run_benchmark(
    *,
    fixtures_dir: Path,
    output_json: Path,
    stage: str,
    acceleration_policy: str,
    api_key: str,
    gpu_available: bool,
    allow_cpu_only: bool,
    allow_cpu_fallback: bool,
    processing_delay_seconds: float,
    max_poll_seconds: float,
    data_root: Path,
) -> BenchmarkPayload:
    """Run benchmark jobs and return the output payload."""
    enforce_generated_output_path(output_json, label="output_json")
    enforce_generated_output_path(data_root, label="data_root")

    fixture_paths = sorted(fixtures_dir.glob("*.pdf"))
    if not fixture_paths:
        raise ValueError(f"No PDF fixtures found in {fixtures_dir}")

    runtime = ServiceConfig(
        api_key=api_key,
        data_root=data_root,
        gpu_available=gpu_available,
        allow_cpu_only=allow_cpu_only,
        allow_cpu_fallback=allow_cpu_fallback,
        processing_delay_seconds=processing_delay_seconds,
    )
    client = TestClient(create_app(runtime))

    jobs: list[BenchmarkJobRecord] = []
    batch_start = time.monotonic()
    total_fixture_bytes = sum(path.stat().st_size for path in fixture_paths)

    for index, fixture_path in enumerate(fixture_paths, start=1):
        file_bytes = fixture_path.read_bytes()
        start_time = time.monotonic()

        create_response = client.post(
            "/v1/convert/jobs?wait_seconds=0",
            headers={
                "X-API-Key": api_key,
                "Idempotency-Key": f"benchmark-{stage}-{index:03d}",
                "X-Correlation-ID": f"corr_benchmark_{index:03d}",
            },
            files={
                "file": (fixture_path.name, file_bytes, "application/pdf"),
                "job_spec": (None, json.dumps(_job_spec(fixture_path.name, acceleration_policy))),
            },
        )

        job_record: BenchmarkJobRecord = {
            "source_file": fixture_path.name,
            "source_size_bytes": len(file_bytes),
            "job_id": None,
            "status": "failed",
            "error_code": None,
            "latency_seconds": 0.0,
            "backend_used": None,
            "acceleration_used": None,
        }

        if create_response.status_code not in {200, 202}:
            error_payload = create_response.json()
            job_record["error_code"] = error_payload.get("error", {}).get("code")
            job_record["latency_seconds"] = round(time.monotonic() - start_time, 6)
            jobs.append(job_record)
            continue

        create_payload = create_response.json()
        job_id = str(create_payload["job"]["job_id"])
        job_record["job_id"] = job_id

        status = _wait_for_terminal_status(
            client, api_key=api_key, job_id=job_id, max_poll_seconds=max_poll_seconds
        )
        job_record["status"] = status.value
        job_record["latency_seconds"] = round(time.monotonic() - start_time, 6)

        if status == JobStatus.SUCCEEDED:
            result_response = client.get(
                f"/v1/convert/jobs/{job_id}/result",
                headers={"X-API-Key": api_key, "X-Correlation-ID": f"corr_result_{index:03d}"},
            )
            if result_response.status_code == 200:
                result_payload = result_response.json()
                conversion_metadata = result_payload["result"]["conversion_metadata"]
                job_record["backend_used"] = conversion_metadata["backend_used"]
                job_record["acceleration_used"] = conversion_metadata["acceleration_used"]
            else:
                job_record["status"] = JobStatus.FAILED.value
                job_record["error_code"] = result_response.json()["error"]["code"]
        elif status == JobStatus.FAILED:
            result_response = client.get(
                f"/v1/convert/jobs/{job_id}/result",
                headers={"X-API-Key": api_key, "X-Correlation-ID": f"corr_result_{index:03d}"},
            )
            if result_response.status_code != 409:
                raise RuntimeError(
                    f"Expected 409 for failed job result lookup, got {result_response.status_code}"
                )
            job_record["error_code"] = result_response.json()["error"]["code"]

        jobs.append(job_record)

    total_duration_seconds = max(time.monotonic() - batch_start, 1e-9)
    latencies = [job["latency_seconds"] for job in jobs]
    succeeded = [job for job in jobs if job["status"] == JobStatus.SUCCEEDED.value]
    failed = [job for job in jobs if job["status"] == JobStatus.FAILED.value]

    payload: BenchmarkPayload = {
        "benchmark_id": "story-003b-gpu-governance",
        "stage": stage,
        "generated_at": _utc_now_iso(),
        "fixtures_dir": str(fixtures_dir.resolve()),
        "runtime_config": {
            "gpu_available": gpu_available,
            "allow_cpu_only": allow_cpu_only,
            "allow_cpu_fallback": allow_cpu_fallback,
            "acceleration_policy": acceleration_policy,
            "processing_delay_seconds": processing_delay_seconds,
        },
        "summary": {
            "total_jobs": len(jobs),
            "succeeded_jobs": len(succeeded),
            "failed_jobs": len(failed),
            "success_rate": round(len(succeeded) / len(jobs), 6) if jobs else 0.0,
            "throughput_jobs_per_minute": round((len(jobs) / total_duration_seconds) * 60.0, 6),
            "latency_seconds": {
                "min": round(min(latencies), 6) if latencies else 0.0,
                "mean": round(statistics.mean(latencies), 6) if latencies else 0.0,
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
                "max": round(max(latencies), 6) if latencies else 0.0,
            },
        },
        "resource_profile": {
            "fixtures_count": len(fixture_paths),
            "fixtures_total_bytes": total_fixture_bytes,
            "acceleration_observed": sorted(
                {
                    str(job["acceleration_used"])
                    for job in jobs
                    if job["acceleration_used"] is not None
                }
            ),
            "backend_observed": sorted(
                {str(job["backend_used"]) for job in jobs if job["backend_used"] is not None}
            ),
        },
        "jobs": jobs,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    """Parse CLI args and run Story 003b benchmark generation."""
    parser = argparse.ArgumentParser(description="Run Story 003b GPU governance benchmark.")
    parser.add_argument("--fixtures-dir", type=Path, default=DEFAULT_FIXTURES_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--stage", default="local")
    parser.add_argument("--acceleration-policy", default="gpu_required")
    parser.add_argument("--api-key", default="benchmark-key")
    parser.add_argument("--gpu-available", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-cpu-only", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--allow-cpu-fallback", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument("--processing-delay-seconds", type=float, default=0.05)
    parser.add_argument("--max-poll-seconds", type=float, default=10.0)
    args = parser.parse_args()

    payload = run_benchmark(
        fixtures_dir=args.fixtures_dir,
        output_json=args.output_json,
        stage=args.stage,
        acceleration_policy=args.acceleration_policy,
        api_key=args.api_key,
        gpu_available=args.gpu_available,
        allow_cpu_only=args.allow_cpu_only,
        allow_cpu_fallback=args.allow_cpu_fallback,
        processing_delay_seconds=args.processing_delay_seconds,
        max_poll_seconds=args.max_poll_seconds,
        data_root=args.data_root,
    )
    print(
        "benchmark-written",
        args.output_json,
        f"jobs={payload['summary']['total_jobs']}",
        f"success_rate={payload['summary']['success_rate']}",
    )


if __name__ == "__main__":
    main()
