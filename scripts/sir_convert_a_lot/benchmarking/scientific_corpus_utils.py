"""Utility functions for the Task 12 scientific-corpus harness.

Purpose:
    Provide deterministic helpers for corpus discovery, job spec generation,
    artifact naming, and summary-stat computation.

Relationships:
    - Used by `scientific_corpus_execution.py` for runtime profile execution.
    - Used by `scripts.sir_convert_a_lot.benchmark_scientific_corpus` orchestration.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus

from .scientific_corpus_types import (
    BackendProfile,
    BenchmarkLatencySummary,
    CorpusFileInfo,
    CorpusSummary,
    LaneJobRecord,
    LaneSummary,
)


def utc_now_iso() -> str:
    """Return current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_sha_or_unknown() -> str:
    """Resolve current repository HEAD SHA or return `'unknown'` on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def slug_for_pdf(pdf_path: Path) -> str:
    """Return deterministic collision-safe document slug for one PDF path."""
    normalized_stem = "".join(
        character.lower() if character.isalnum() else "-" for character in pdf_path.stem.strip()
    )
    collapsed = "-".join(part for part in normalized_stem.split("-") if part)
    stem = collapsed[:60] if collapsed else "doc"
    digest = hashlib.sha256(pdf_path.name.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}"


def discover_corpus(corpus_dir: Path) -> tuple[list[Path], CorpusSummary]:
    """Discover and return sorted PDF corpus and deterministic summary metadata."""
    pdf_paths = sorted(path for path in corpus_dir.glob("*.pdf") if path.is_file())
    if not pdf_paths:
        raise ValueError(f"No PDF files found in corpus path: {corpus_dir}")
    files: list[CorpusFileInfo] = [
        {
            "source_file": path.name,
            "source_size_bytes": path.stat().st_size,
            "document_slug": slug_for_pdf(path),
        }
        for path in pdf_paths
    ]
    return pdf_paths, {
        "path": str(corpus_dir.resolve()),
        "count": len(pdf_paths),
        "files": files,
    }


def percentile(values: list[float], quantile: float) -> float:
    """Compute quantile with linear interpolation on sorted values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return round(sorted_values[0], 6)
    rank = (len(sorted_values) - 1) * quantile
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    interpolated = lower_value + (upper_value - lower_value) * (rank - lower_index)
    return round(interpolated, 6)


def latency_summary(latencies: list[float]) -> BenchmarkLatencySummary:
    """Return deterministic latency summary payload."""
    if not latencies:
        return {"min": 0.0, "mean": 0.0, "p50": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "min": round(min(latencies), 6),
        "mean": round(statistics.mean(latencies), 6),
        "p50": percentile(latencies, 0.50),
        "p90": percentile(latencies, 0.90),
        "p99": percentile(latencies, 0.99),
        "max": round(max(latencies), 6),
    }


def summarize_records(records: list[LaneJobRecord], *, duration_seconds: float) -> LaneSummary:
    """Aggregate per-job records into deterministic lane/profile summary metrics."""
    total = len(records)
    succeeded = sum(1 for record in records if record["status"] == JobStatus.SUCCEEDED.value)
    failed = sum(1 for record in records if record["status"] == JobStatus.FAILED.value)
    canceled = sum(1 for record in records if record["status"] == JobStatus.CANCELED.value)
    running = sum(1 for record in records if record["status"] == JobStatus.RUNNING.value)
    latencies = [record["latency_seconds"] for record in records]
    warnings_total = sum(len(record["warnings"]) for record in records)
    retry_warnings_total = sum(record["retry_warnings_count"] for record in records)

    backend_usage: dict[str, int] = {}
    acceleration_usage: dict[str, int] = {}
    for record in records:
        backend = record["backend_used"]
        acceleration = record["acceleration_used"]
        if backend is not None:
            backend_usage[backend] = backend_usage.get(backend, 0) + 1
        if acceleration is not None:
            acceleration_usage[acceleration] = acceleration_usage.get(acceleration, 0) + 1

    normalized_duration = max(duration_seconds, 1e-9)
    return {
        "total_jobs": total,
        "succeeded_jobs": succeeded,
        "failed_jobs": failed,
        "canceled_jobs": canceled,
        "running_jobs": running,
        "success_rate": round((succeeded / total), 6) if total else 0.0,
        "throughput_jobs_per_minute": round((total / normalized_duration) * 60.0, 6),
        "latency_seconds": latency_summary(latencies),
        "warnings_total": warnings_total,
        "retry_warnings_total": retry_warnings_total,
        "backend_usage": dict(sorted(backend_usage.items())),
        "acceleration_usage": dict(sorted(acceleration_usage.items())),
    }


def build_job_spec(filename: str, profile: BackendProfile) -> dict[str, object]:
    """Build deterministic v1 job spec payload for one source file + profile."""
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": profile.backend_strategy,
            "ocr_mode": profile.ocr_mode,
            "table_mode": profile.table_mode,
            "normalize": profile.normalize,
        },
        "execution": {
            "acceleration_policy": profile.acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def idempotency_key(pdf_path: Path, job_spec: dict[str, object], *, scope: str) -> str:
    """Return deterministic idempotency key scoped to lane/profile/document."""
    file_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    spec_sha = hashlib.sha256(
        json.dumps(job_spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    digest = hashlib.sha256(
        f"{scope}:{pdf_path.name}:{file_sha}:{spec_sha}".encode("utf-8")
    ).hexdigest()
    return f"task12_{digest[:48]}"


def artifact_paths(
    *,
    artifacts_root: Path,
    lane: str,
    profile_name: str,
    document_slug: str,
) -> tuple[Path, Path]:
    """Return deterministic markdown + sidecar metadata artifact paths."""
    if lane == "acceptance":
        markdown_path = artifacts_root / "acceptance" / f"{document_slug}.md"
    else:
        markdown_path = artifacts_root / "evaluation" / profile_name / f"{document_slug}.md"
    metadata_path = markdown_path.with_suffix(".meta.json")
    return markdown_path, metadata_path


def parse_success_result(
    payload: dict[str, object],
) -> tuple[str, str | None, str | None, list[str]]:
    """Extract markdown and metadata from a successful result payload."""
    result_obj = payload.get("result")
    if not isinstance(result_obj, dict):
        raise ValueError("Result payload missing 'result' object.")
    markdown_obj = result_obj.get("markdown_content")
    if not isinstance(markdown_obj, str):
        raise ValueError("Result payload missing inline markdown content.")
    conversion_metadata = result_obj.get("conversion_metadata")
    if not isinstance(conversion_metadata, dict):
        raise ValueError("Result payload missing conversion metadata.")
    backend_used_obj = conversion_metadata.get("backend_used")
    acceleration_used_obj = conversion_metadata.get("acceleration_used")
    backend_used = backend_used_obj if isinstance(backend_used_obj, str) else None
    acceleration_used = acceleration_used_obj if isinstance(acceleration_used_obj, str) else None
    warnings_obj = result_obj.get("warnings")
    warnings: list[str] = []
    if isinstance(warnings_obj, list):
        warnings = [str(item) for item in warnings_obj]
    return markdown_obj, backend_used, acceleration_used, warnings
