"""Benchmark Story 20 throughput and tuning guidance for Task 74.

Purpose:
    Generate a representative scanned-PDF corpus, run baseline/tuned profile
    comparisons through the v2 API/runtime path, and emit machine-readable plus
    human-readable evidence for Task 74.

Relationships:
    - Uses `scripts.sir_convert_a_lot.interfaces.http_api.create_app` to
      exercise the real v2 HTTP/runtime stack with per-profile configs when
      running in-process harness benchmarks.
    - Uses `scripts.sir_convert_a_lot.benchmarking.story20_throughput_report`
      to render the markdown report artifact.
    - Is orchestrated on Hemma by
      `scripts.sir_convert_a_lot.devops.run_task74_hemma_benchmark`.
    - Writes generated artifacts under `build/benchmarks/story-20/`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.benchmarking.story20_throughput_report import write_report
from scripts.sir_convert_a_lot.benchmarking.story20_throughput_types import (
    BenchmarkPayload,
    CorpusFileRecord,
    JobRecord,
    ProfilePayload,
    ProfileSummary,
    ResourceEvidence,
    RuntimeParitySummary,
    RuntimeSurface,
    Task76ReportChecks,
    Task76ReportPayload,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

DEFAULT_OUTPUT_ROOT = Path("build/benchmarks/story-20/task-74-throughput")
DEFAULT_OUTPUT_JSON = DEFAULT_OUTPUT_ROOT / "task-74-throughput-benchmark-local.json"
DEFAULT_OUTPUT_REPORT = DEFAULT_OUTPUT_ROOT / "task-74-throughput-report.md"
DEFAULT_CORPUS_ROOT = DEFAULT_OUTPUT_ROOT / "corpus"
DEFAULT_DATA_ROOT = DEFAULT_OUTPUT_ROOT / "runtime"
DEFAULT_PAGE_COUNTS = (120, 180, 240)


@dataclass(frozen=True)
class ProfileSpec:
    """One benchmark runtime profile."""

    profile_name: str
    parallel_enabled: bool
    max_chunk_workers: int
    chunk_size_pages: int
    gpu_stage_max_concurrency: int


@dataclass(frozen=True)
class RuntimeParityInputs:
    """Optional Task 76 parity metadata provided to the benchmark harness."""

    report_json_path: Path | None
    status: str | None
    lane: str | None
    expected_revision: str | None
    remote_revision: str | None
    service_revision: str | None
    expected_revision_matches_remote: bool | None
    service_revision_matches_remote: bool | None
    live_smoke_passed: bool | None
    metrics_scan_passed: bool | None


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 6)
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * percentile
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    interpolated = lower_value + (upper_value - lower_value) * (rank - lower_index)
    return round(interpolated, 6)


def _metric_max(metrics_text: str, metric_name: str) -> float:
    values: list[float] = []
    for line in metrics_text.splitlines():
        if line.startswith(metric_name):
            values.append(float(line.rsplit(" ", 1)[-1]))
    return max(values) if values else 0.0


def _coerce_optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _coerce_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _assert_in_process_runtime_supports_requested_ocr(
    *,
    ocr_mode: str,
    ocr_engine: str,
    easyocr_model_storage_directory: str | None,
) -> None:
    if ocr_mode == "off":
        return
    if ocr_engine != "easyocr":
        return
    if importlib.util.find_spec("easyocr") is None:
        raise RuntimeError(
            "Task 74 in-process benchmark runtime is missing EasyOCR. "
            "Run `pdm sync` in the benchmark environment or use the canonical "
            "`benchmark:task-74-hemma` workflow before benchmarking."
        )
    if easyocr_model_storage_directory is None:
        return
    model_dir = Path(easyocr_model_storage_directory).expanduser()
    if not model_dir.exists():
        raise RuntimeError(
            "Task 74 in-process benchmark runtime is missing the EasyOCR model directory "
            f"`{model_dir}`. Warm the host EasyOCR cache first or pass "
            "`--easyocr-model-storage-dir` to a prepared path."
        )


def _read_runtime_parity_report(report_json_path: Path) -> Task76ReportPayload:
    payload_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError("Task 76 parity report must contain a JSON object at the root.")
    raw_checks = payload_obj.get("checks")
    checks_obj: object = raw_checks if isinstance(raw_checks, dict) else {}
    checks: Task76ReportChecks = {
        "expected_revision_matches_remote": _coerce_optional_bool(
            checks_obj.get("expected_revision_matches_remote")
            if isinstance(checks_obj, dict)
            else None
        ),
        "service_revision_matches_remote": _coerce_optional_bool(
            checks_obj.get("service_revision_matches_remote")
            if isinstance(checks_obj, dict)
            else None
        ),
        "live_smoke_passed": _coerce_optional_bool(
            checks_obj.get("live_smoke_passed") if isinstance(checks_obj, dict) else None
        ),
        "metrics_scan_passed": _coerce_optional_bool(
            checks_obj.get("metrics_scan_passed") if isinstance(checks_obj, dict) else None
        ),
    }
    return {
        "status": _coerce_optional_str(payload_obj.get("status")),
        "lane": _coerce_optional_str(payload_obj.get("lane")),
        "expected_revision": _coerce_optional_str(payload_obj.get("expected_revision")),
        "remote_revision": _coerce_optional_str(payload_obj.get("remote_revision")),
        "service_revision": _coerce_optional_str(payload_obj.get("service_revision")),
        "checks": checks,
    }


def _build_runtime_parity_summary(
    *,
    inputs: RuntimeParityInputs,
) -> tuple[RuntimeSurface, RuntimeParitySummary]:
    parity_source = "none"
    status = inputs.status
    lane = inputs.lane
    expected_revision = inputs.expected_revision
    remote_revision = inputs.remote_revision
    service_revision = inputs.service_revision
    expected_revision_matches_remote = inputs.expected_revision_matches_remote
    service_revision_matches_remote = inputs.service_revision_matches_remote
    live_smoke_passed = inputs.live_smoke_passed
    metrics_scan_passed = inputs.metrics_scan_passed

    if inputs.report_json_path is not None:
        report_payload = _read_runtime_parity_report(inputs.report_json_path)
        checks_obj = report_payload["checks"]
        parity_source = f"task76_report_json:{inputs.report_json_path.as_posix()}"
        status = report_payload["status"] or status
        lane = report_payload["lane"] or lane
        expected_revision = report_payload["expected_revision"] or expected_revision
        remote_revision = report_payload["remote_revision"] or remote_revision
        service_revision = report_payload["service_revision"] or service_revision
        expected_revision_matches_remote = checks_obj["expected_revision_matches_remote"]
        if expected_revision_matches_remote is None:
            expected_revision_matches_remote = inputs.expected_revision_matches_remote
        service_revision_matches_remote = checks_obj["service_revision_matches_remote"]
        if service_revision_matches_remote is None:
            service_revision_matches_remote = inputs.service_revision_matches_remote
        live_smoke_passed = checks_obj["live_smoke_passed"]
        if live_smoke_passed is None:
            live_smoke_passed = inputs.live_smoke_passed
        metrics_scan_passed = checks_obj["metrics_scan_passed"]
        if metrics_scan_passed is None:
            metrics_scan_passed = inputs.metrics_scan_passed
    elif any(
        value is not None
        for value in [
            status,
            lane,
            expected_revision,
            remote_revision,
            service_revision,
            expected_revision_matches_remote,
            service_revision_matches_remote,
            live_smoke_passed,
            metrics_scan_passed,
        ]
    ):
        parity_source = "cli_flags"

    notes: list[str] = []
    parity_proven = True
    if status != "passed":
        parity_proven = False
        notes.append("Task 76 parity status is not `passed`.")
    if expected_revision is None or remote_revision is None or service_revision is None:
        parity_proven = False
        notes.append("Missing expected/remote/service revision metadata.")
    if expected_revision_matches_remote is not True:
        parity_proven = False
        notes.append("`expected_revision_matches_remote` is not true.")
    if service_revision_matches_remote is not True:
        parity_proven = False
        notes.append("`service_revision_matches_remote` is not true.")
    if live_smoke_passed is not True:
        parity_proven = False
        notes.append("Task 76 live smoke proof is missing or failed.")
    if metrics_scan_passed is not True:
        parity_proven = False
        notes.append("Task 76 metrics safety proof is missing or failed.")

    runtime_surface: RuntimeSurface = {
        "mode": "in_process_app",
        "host": None,
        "service_url": None,
        "parity_source": parity_source,
    }
    runtime_parity: RuntimeParitySummary = {
        "status": status,
        "lane": lane,
        "expected_revision": expected_revision,
        "remote_revision": remote_revision,
        "service_revision": service_revision,
        "expected_revision_matches_remote": expected_revision_matches_remote,
        "service_revision_matches_remote": service_revision_matches_remote,
        "live_smoke_passed": live_smoke_passed,
        "metrics_scan_passed": metrics_scan_passed,
        "parity_proven": parity_proven,
        "notes": notes,
    }
    return runtime_surface, runtime_parity


def _build_scan_template_image(text: str) -> bytes:
    import pymupdf

    template_doc = pymupdf.open()
    try:
        page = template_doc.new_page(width=595, height=842)
        if page is None:
            raise RuntimeError("PyMuPDF returned no page for template generation.")
        page.insert_textbox(
            pymupdf.Rect(48, 48, 547, 794),
            text,
            fontsize=14,
            fontname="helv",
            align=0,
        )
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0), alpha=False)
        return bytes(pixmap.tobytes("png"))
    finally:
        template_doc.close()


def generate_corpus(*, corpus_root: Path, page_counts: tuple[int, ...]) -> list[CorpusFileRecord]:
    """Generate representative scanned PDFs for throughput benchmarking."""
    import pymupdf

    corpus_root.mkdir(parents=True, exist_ok=True)
    records: list[CorpusFileRecord] = []
    for document_index, page_count in enumerate(page_counts, start=1):
        templates = [
            _build_scan_template_image(
                "\n".join(
                    [
                        f"Story 20 benchmark document {document_index}",
                        f"Template {template_index + 1}",
                        "OCR target text with Swedish characters: å ä ö.",
                        "Synthetic scanned textbook content for throughput profiling.",
                    ]
                )
            )
            for template_index in range(4)
        ]
        output_path = corpus_root / f"story20-benchmark-{document_index:02d}-{page_count}p.pdf"
        document = pymupdf.open()
        try:
            for page_index in range(page_count):
                page = document.new_page(width=595, height=842)
                if page is None:
                    raise RuntimeError("PyMuPDF returned no page for corpus generation.")
                page.insert_image(page.rect, stream=templates[page_index % len(templates)])
            document.save(output_path.as_posix())
        finally:
            document.close()
        file_bytes = output_path.read_bytes()
        records.append(
            {
                "filename": output_path.name,
                "page_count": page_count,
                "size_bytes": len(file_bytes),
                "sha256": _sha256_bytes(file_bytes),
            }
        )
    return records


def _job_spec(
    *,
    filename: str,
    acceleration_policy: str,
    ocr_mode: str,
    ocr_engine: str,
    ocr_languages: list[str],
) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": "pdf"},
        "conversion": {
            "output_format": "md",
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "pdf_options": {
            "backend_strategy": "auto",
            "ocr_mode": ocr_mode,
            "ocr_engine": ocr_engine,
            "ocr_languages": ocr_languages,
            "table_mode": "fast",
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 7200,
        },
        "retention": {"pin": False},
    }


def _poll_job_and_metrics(
    client: TestClient,
    *,
    api_key: str,
    job_id: str,
    max_poll_seconds: float,
    resource_evidence: ResourceEvidence,
) -> dict[str, object]:
    deadline = time.monotonic() + max_poll_seconds
    while time.monotonic() < deadline:
        metrics_text = client.get("/metrics").text
        resource_evidence["peak_jobs_queued"] = max(
            resource_evidence["peak_jobs_queued"],
            _metric_max(metrics_text, "sir_convert_a_lot_v2_jobs_queued"),
        )
        resource_evidence["peak_jobs_active"] = max(
            resource_evidence["peak_jobs_active"],
            _metric_max(metrics_text, "sir_convert_a_lot_v2_jobs_active"),
        )
        resource_evidence["peak_worker_saturation_ratio"] = max(
            resource_evidence["peak_worker_saturation_ratio"],
            _metric_max(metrics_text, "sir_convert_a_lot_v2_worker_saturation_ratio"),
        )
        resource_evidence["peak_chunk_worker_saturation_ratio"] = max(
            resource_evidence["peak_chunk_worker_saturation_ratio"],
            _metric_max(metrics_text, "sir_convert_a_lot_v2_chunk_worker_saturation_ratio"),
        )
        resource_evidence["peak_gpu_busy_percent"] = max(
            resource_evidence["peak_gpu_busy_percent"],
            _metric_max(metrics_text, "sir_convert_a_lot_v2_gpu_busy_percent"),
        )
        resource_evidence["peak_gpu_memory_used_percent"] = max(
            resource_evidence["peak_gpu_memory_used_percent"],
            _metric_max(metrics_text, "sir_convert_a_lot_v2_gpu_memory_used_percent"),
        )
        resource_evidence["contains_job_id_label"] = resource_evidence["contains_job_id_label"] or (
            "job_id=" in metrics_text or "jobv2_" in metrics_text
        )

        response = client.get(f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": api_key})
        if response.status_code != 200:
            raise RuntimeError(f"Job polling failed for {job_id}: {response.status_code}")
        payload_obj: object = response.json()
        if not isinstance(payload_obj, dict):
            raise RuntimeError(f"Job polling returned non-object payload for {job_id}.")
        payload = payload_obj
        job_obj = payload["job"]
        if not isinstance(job_obj, dict):
            raise RuntimeError(f"Job polling payload missing job object for {job_id}.")
        status = JobStatus(job_obj["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return payload
        time.sleep(0.2)
    raise RuntimeError(f"Task 74 benchmark polling timed out for {job_id}.")


def _summarize(
    latencies: list[float], pages_per_minute: list[float], failed_jobs: int
) -> ProfileSummary:
    total_jobs = len(latencies) + failed_jobs
    succeeded_jobs = len(latencies)
    success_rate = float(succeeded_jobs) / float(total_jobs) if total_jobs else 0.0
    error_rate = float(failed_jobs) / float(total_jobs) if total_jobs else 0.0
    mean_latency = statistics.fmean(latencies) if latencies else 0.0
    return {
        "total_jobs": total_jobs,
        "succeeded_jobs": succeeded_jobs,
        "failed_jobs": failed_jobs,
        "success_rate": round(success_rate, 6),
        "error_rate": round(error_rate, 6),
        "latency_seconds": {
            "min": round(min(latencies), 6) if latencies else 0.0,
            "mean": round(mean_latency, 6),
            "p50": _percentile(latencies, 0.50),
            "p90": _percentile(latencies, 0.90),
            "max": round(max(latencies), 6) if latencies else 0.0,
        },
        "pages_per_minute_p50": _percentile(pages_per_minute, 0.50),
    }


def _run_profile(
    *,
    profile: ProfileSpec,
    corpus_root: Path,
    corpus_records: list[CorpusFileRecord],
    data_root: Path,
    api_key: str,
    acceleration_policy: str,
    ocr_mode: str,
    ocr_engine: str,
    ocr_languages: list[str],
    max_poll_seconds: float,
    gpu_available: bool,
    easyocr_model_storage_directory: str | None,
) -> ProfilePayload:
    config = ServiceConfig(
        api_key=api_key,
        data_root=data_root / profile.profile_name,
        gpu_available=gpu_available,
        allow_cpu_only=(acceleration_policy == "cpu_only"),
        allow_cpu_fallback=False,
        processing_delay_seconds=0.0,
        enable_parallel_pdf_chunks=profile.parallel_enabled,
        max_chunk_workers=profile.max_chunk_workers,
        pdf_chunk_size_pages=profile.chunk_size_pages,
        gpu_stage_max_concurrency=profile.gpu_stage_max_concurrency,
        easyocr_model_storage_directory=easyocr_model_storage_directory,
    )
    app = create_app(config)
    jobs: list[JobRecord] = []
    latencies: list[float] = []
    pages_per_minute_values: list[float] = []
    resource_evidence: ResourceEvidence = {
        "peak_jobs_queued": 0.0,
        "peak_jobs_active": 0.0,
        "peak_worker_saturation_ratio": 0.0,
        "peak_chunk_worker_saturation_ratio": 0.0,
        "peak_gpu_busy_percent": 0.0,
        "peak_gpu_memory_used_percent": 0.0,
        "contains_job_id_label": False,
    }
    with TestClient(app) as client:
        for index, corpus_record in enumerate(corpus_records, start=1):
            source_path = corpus_root / corpus_record["filename"]
            create_response = client.post(
                "/v2/convert/jobs?wait_seconds=0",
                headers={
                    "X-API-Key": api_key,
                    "Idempotency-Key": f"task74-{profile.profile_name}-{index:03d}",
                    "X-Correlation-ID": f"corr_task74_{profile.profile_name}_{index:03d}",
                },
                files={
                    "file": (source_path.name, source_path.read_bytes(), "application/pdf"),
                    "job_spec": (
                        None,
                        json.dumps(
                            _job_spec(
                                filename=source_path.name,
                                acceleration_policy=acceleration_policy,
                                ocr_mode=ocr_mode,
                                ocr_engine=ocr_engine,
                                ocr_languages=ocr_languages,
                            ),
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ),
                },
            )
            if create_response.status_code not in {200, 202}:
                jobs.append(
                    {
                        "source_file": source_path.name,
                        "page_count": corpus_record["page_count"],
                        "job_id": None,
                        "status": "failed",
                        "latency_seconds": 0.0,
                        "pages_per_minute": None,
                        "backend_used": None,
                        "acceleration_used": None,
                        "gpu_busy_percent": None,
                        "gpu_memory_used_percent": None,
                        "warnings": [f"http_{create_response.status_code}"],
                    }
                )
                continue

            create_payload_obj: object = create_response.json()
            if not isinstance(create_payload_obj, dict):
                raise RuntimeError("Task 74 create response is not a JSON object.")
            create_job_obj = create_payload_obj.get("job")
            if not isinstance(create_job_obj, dict):
                raise RuntimeError("Task 74 create response is missing job object.")
            job_id_obj = create_job_obj.get("job_id")
            if not isinstance(job_id_obj, str):
                raise RuntimeError("Task 74 create response is missing string job_id.")
            job_id = job_id_obj
            final_payload = _poll_job_and_metrics(
                client,
                api_key=api_key,
                job_id=job_id,
                max_poll_seconds=max_poll_seconds,
                resource_evidence=resource_evidence,
            )
            job_obj = final_payload["job"]
            if not isinstance(job_obj, dict):
                raise RuntimeError(f"Task 74 final payload missing job object for {job_id}.")
            created_at_obj = job_obj.get("created_at")
            updated_at_obj = job_obj.get("updated_at")
            progress_obj = job_obj.get("progress")
            status_obj = job_obj.get("status")
            if not isinstance(created_at_obj, str) or not isinstance(updated_at_obj, str):
                raise RuntimeError(f"Task 74 final payload missing timestamps for {job_id}.")
            if not isinstance(progress_obj, dict):
                raise RuntimeError(f"Task 74 final payload missing progress object for {job_id}.")
            if not isinstance(status_obj, str):
                raise RuntimeError(f"Task 74 final payload missing status string for {job_id}.")
            created_at = _parse_timestamp(created_at_obj)
            updated_at = _parse_timestamp(updated_at_obj)
            latency_seconds = round((updated_at - created_at).total_seconds(), 6)
            pages_per_minute = progress_obj.get("pages_per_minute")
            warnings: list[str] = []
            backend_used = None
            acceleration_used = None
            gpu_busy_percent = None
            gpu_memory_used_percent = None
            if status_obj == JobStatus.SUCCEEDED.value:
                result_response = client.get(
                    f"/v2/convert/jobs/{job_id}/result",
                    headers={"X-API-Key": api_key},
                )
                result_payload_obj: object = result_response.json()
                if not isinstance(result_payload_obj, dict):
                    raise RuntimeError(f"Task 74 result payload is not an object for {job_id}.")
                result_obj = result_payload_obj.get("result")
                if not isinstance(result_obj, dict):
                    raise RuntimeError(
                        f"Task 74 result payload missing result object for {job_id}."
                    )
                metadata_obj = result_obj.get("conversion_metadata")
                if not isinstance(metadata_obj, dict):
                    raise RuntimeError(
                        f"Task 74 result payload missing conversion metadata for {job_id}."
                    )
                warnings_obj = result_obj.get("warnings", [])
                warnings = (
                    list(warnings_obj)
                    if isinstance(warnings_obj, list)
                    and all(isinstance(item, str) for item in warnings_obj)
                    else []
                )
                backend_used_obj = metadata_obj.get("backend_used")
                acceleration_used_obj = metadata_obj.get("acceleration_used")
                gpu_busy_obj = metadata_obj.get("gpu_busy_percent")
                gpu_memory_obj = metadata_obj.get("gpu_memory_used_percent")
                backend_used = backend_used_obj if isinstance(backend_used_obj, str) else None
                acceleration_used = (
                    acceleration_used_obj if isinstance(acceleration_used_obj, str) else None
                )
                gpu_busy_percent = gpu_busy_obj if isinstance(gpu_busy_obj, int) else None
                gpu_memory_used_percent = (
                    gpu_memory_obj if isinstance(gpu_memory_obj, int) else None
                )
                latencies.append(latency_seconds)
                if isinstance(pages_per_minute, (int, float)):
                    pages_per_minute_values.append(float(pages_per_minute))
            jobs.append(
                {
                    "source_file": source_path.name,
                    "page_count": corpus_record["page_count"],
                    "job_id": job_id,
                    "status": status_obj,
                    "latency_seconds": latency_seconds,
                    "pages_per_minute": (
                        float(pages_per_minute)
                        if isinstance(pages_per_minute, (int, float))
                        else None
                    ),
                    "backend_used": backend_used,
                    "acceleration_used": acceleration_used,
                    "gpu_busy_percent": gpu_busy_percent,
                    "gpu_memory_used_percent": gpu_memory_used_percent,
                    "warnings": warnings,
                }
            )
    failed_jobs = sum(1 for job in jobs if job["status"] != JobStatus.SUCCEEDED.value)
    return {
        "profile_name": profile.profile_name,
        "config": {
            "parallel_enabled": profile.parallel_enabled,
            "max_chunk_workers": profile.max_chunk_workers,
            "chunk_size_pages": profile.chunk_size_pages,
            "gpu_stage_max_concurrency": profile.gpu_stage_max_concurrency,
            "acceleration_policy": acceleration_policy,
        },
        "summary": _summarize(latencies, pages_per_minute_values, failed_jobs),
        "resource_evidence": resource_evidence,
        "jobs": jobs,
    }


def _default_profiles() -> list[ProfileSpec]:
    return [
        ProfileSpec(
            profile_name="serial_baseline",
            parallel_enabled=False,
            max_chunk_workers=1,
            chunk_size_pages=8,
            gpu_stage_max_concurrency=1,
        ),
        ProfileSpec(
            profile_name="parallel_conservative",
            parallel_enabled=True,
            max_chunk_workers=2,
            chunk_size_pages=4,
            gpu_stage_max_concurrency=2,
        ),
    ]


def run_benchmark(
    *,
    output_json: Path,
    output_report: Path,
    corpus_root: Path,
    data_root: Path,
    page_counts: tuple[int, ...] = DEFAULT_PAGE_COUNTS,
    api_key: str = "benchmark-key",
    acceleration_policy: str = "gpu_required",
    ocr_mode: str = "force",
    ocr_engine: str = "easyocr",
    ocr_languages: list[str] | None = None,
    max_poll_seconds: float = 7200.0,
    gpu_available: bool = True,
    profiles: list[ProfileSpec] | None = None,
    runtime_mode: str = "in_process_app",
    runtime_host: str | None = None,
    runtime_service_url: str | None = None,
    easyocr_model_storage_directory: str | None = "/opt/easyocr-models",
    runtime_parity_inputs: RuntimeParityInputs | None = None,
) -> BenchmarkPayload:
    """Run the Task 74 throughput benchmark and return the payload."""
    resolved_languages = list(ocr_languages or ["sv", "en"])
    for path_value, label in [
        (output_json, "output_json"),
        (output_report, "output_report"),
        (corpus_root, "corpus_root"),
        (data_root, "data_root"),
    ]:
        enforce_generated_output_path(path_value, label=label)

    if runtime_mode == "in_process_app":
        _assert_in_process_runtime_supports_requested_ocr(
            ocr_mode=ocr_mode,
            ocr_engine=ocr_engine,
            easyocr_model_storage_directory=easyocr_model_storage_directory,
        )

    corpus_records = generate_corpus(corpus_root=corpus_root, page_counts=page_counts)
    resolved_profiles = profiles or _default_profiles()
    runtime_surface, runtime_parity = _build_runtime_parity_summary(
        inputs=runtime_parity_inputs
        or RuntimeParityInputs(
            report_json_path=None,
            status=None,
            lane=None,
            expected_revision=None,
            remote_revision=None,
            service_revision=None,
            expected_revision_matches_remote=None,
            service_revision_matches_remote=None,
            live_smoke_passed=None,
            metrics_scan_passed=None,
        )
    )
    runtime_surface["mode"] = runtime_mode
    runtime_surface["host"] = runtime_host
    runtime_surface["service_url"] = runtime_service_url
    profile_payloads = [
        _run_profile(
            profile=profile,
            corpus_root=corpus_root,
            corpus_records=corpus_records,
            data_root=data_root,
            api_key=api_key,
            acceleration_policy=acceleration_policy,
            ocr_mode=ocr_mode,
            ocr_engine=ocr_engine,
            ocr_languages=resolved_languages,
            max_poll_seconds=max_poll_seconds,
            gpu_available=gpu_available,
            easyocr_model_storage_directory=easyocr_model_storage_directory,
        )
        for profile in resolved_profiles
    ]

    baseline = profile_payloads[0]
    tuned_candidates = [
        profile for profile in profile_payloads[1:] if profile["summary"]["failed_jobs"] == 0
    ]
    tuned = min(
        tuned_candidates or profile_payloads[1:],
        key=lambda profile: profile["summary"]["latency_seconds"]["p50"],
    )
    baseline_p50 = baseline["summary"]["latency_seconds"]["p50"]
    tuned_p50 = tuned["summary"]["latency_seconds"]["p50"]
    improvement_percent = (
        round(((baseline_p50 - tuned_p50) / baseline_p50) * 100.0, 4) if baseline_p50 > 0 else 0.0
    )
    payload: BenchmarkPayload = {
        "benchmark_id": "task-74-throughput-benchmark",
        "generated_at": _utc_now_iso(),
        "mode": runtime_mode,
        "corpus": {
            "corpus_root": str(corpus_root.resolve()),
            "count": len(corpus_records),
            "page_counts": list(page_counts),
            "files": corpus_records,
        },
        "job_defaults": {
            "acceleration_policy": acceleration_policy,
            "ocr_mode": ocr_mode,
            "ocr_engine": ocr_engine,
            "ocr_languages": resolved_languages,
        },
        "runtime_surface": runtime_surface,
        "runtime_parity": runtime_parity,
        "profiles": profile_payloads,
        "comparison": {
            "baseline_profile": baseline["profile_name"],
            "tuned_profile": tuned["profile_name"],
            "p50_improvement_percent": improvement_percent,
            "meets_target": improvement_percent >= 40.0,
            "recommended_profile": tuned["profile_name"],
            "recommended_defaults": tuned["config"],
            "rollback_conditions": [
                "success_rate drops below 1.0 on the benchmark corpus",
                "peak chunk worker saturation remains >= 0.95 while queue depth stays elevated",
                (
                    "observed gpu_busy_percent stays near 0 or "
                    "gpu_memory_used_percent exceeds safe headroom"
                ),
            ],
        },
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path=output_report, benchmark_json_path=output_json, payload=payload)
    return payload


def main() -> None:
    """Parse CLI args and run the Task 74 benchmark harness."""
    parser = argparse.ArgumentParser(description="Run Story 20 Task 74 throughput benchmark.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--page-counts", default="120,180,240")
    parser.add_argument("--api-key", default="benchmark-key")
    parser.add_argument("--acceleration-policy", default="gpu_required")
    parser.add_argument("--ocr-mode", default="force")
    parser.add_argument("--ocr-engine", default="easyocr")
    parser.add_argument("--ocr-languages", default="sv,en")
    parser.add_argument("--max-poll-seconds", type=float, default=7200.0)
    parser.add_argument("--runtime-mode", default="in_process_app")
    parser.add_argument("--runtime-host")
    parser.add_argument("--runtime-service-url")
    parser.add_argument("--easyocr-model-storage-dir")
    parser.add_argument("--task76-report-json", type=Path)
    parser.add_argument("--parity-status")
    parser.add_argument("--parity-lane")
    parser.add_argument("--parity-expected-revision")
    parser.add_argument("--parity-remote-revision")
    parser.add_argument("--parity-service-revision")
    parser.add_argument(
        "--parity-expected-remote-ok",
        dest="parity_expected_remote_ok",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-expected-remote-ok",
        dest="parity_expected_remote_ok",
        action="store_false",
    )
    parser.add_argument(
        "--parity-service-remote-ok",
        dest="parity_service_remote_ok",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-service-remote-ok",
        dest="parity_service_remote_ok",
        action="store_false",
    )
    parser.add_argument(
        "--parity-live-smoke-passed",
        dest="parity_live_smoke_passed",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-live-smoke-passed",
        dest="parity_live_smoke_passed",
        action="store_false",
    )
    parser.add_argument(
        "--parity-metrics-scan-passed",
        dest="parity_metrics_scan_passed",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-metrics-scan-passed",
        dest="parity_metrics_scan_passed",
        action="store_false",
    )
    parser.add_argument("--gpu-available", dest="gpu_available", action="store_true")
    parser.add_argument("--no-gpu-available", dest="gpu_available", action="store_false")
    parser.set_defaults(
        gpu_available=True,
        parity_expected_remote_ok=None,
        parity_service_remote_ok=None,
        parity_live_smoke_passed=None,
        parity_metrics_scan_passed=None,
    )
    args = parser.parse_args()

    page_counts = tuple(
        int(value.strip()) for value in args.page_counts.split(",") if value.strip()
    )
    payload = run_benchmark(
        output_json=args.output_json,
        output_report=args.output_report,
        corpus_root=args.corpus_root,
        data_root=args.data_root,
        page_counts=page_counts,
        api_key=args.api_key,
        acceleration_policy=args.acceleration_policy,
        ocr_mode=args.ocr_mode,
        ocr_engine=args.ocr_engine,
        ocr_languages=[value.strip() for value in args.ocr_languages.split(",") if value.strip()],
        max_poll_seconds=args.max_poll_seconds,
        gpu_available=args.gpu_available,
        runtime_mode=str(args.runtime_mode),
        runtime_host=_coerce_optional_str(args.runtime_host),
        runtime_service_url=_coerce_optional_str(args.runtime_service_url),
        easyocr_model_storage_directory=_coerce_optional_str(args.easyocr_model_storage_dir)
        or "/opt/easyocr-models",
        runtime_parity_inputs=RuntimeParityInputs(
            report_json_path=args.task76_report_json,
            status=_coerce_optional_str(args.parity_status),
            lane=_coerce_optional_str(args.parity_lane),
            expected_revision=_coerce_optional_str(args.parity_expected_revision),
            remote_revision=_coerce_optional_str(args.parity_remote_revision),
            service_revision=_coerce_optional_str(args.parity_service_revision),
            expected_revision_matches_remote=args.parity_expected_remote_ok,
            service_revision_matches_remote=args.parity_service_remote_ok,
            live_smoke_passed=args.parity_live_smoke_passed,
            metrics_scan_passed=args.parity_metrics_scan_passed,
        ),
    )
    print(
        "task74-benchmark-written",
        json.dumps(
            {
                "output_json": args.output_json.as_posix(),
                "recommended_profile": payload["comparison"]["recommended_profile"],
                "p50_improvement_percent": payload["comparison"]["p50_improvement_percent"],
                "runtime_parity_proven": payload["runtime_parity"]["parity_proven"],
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
