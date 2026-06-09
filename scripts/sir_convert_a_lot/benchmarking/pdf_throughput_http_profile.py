"""HTTP profile execution for PDF throughput benchmark throughput benchmarks.

Purpose:
    Execute one PDF throughput lane/PDF throughput benchmark profile through the in-process v2 HTTP
    app,
    collect job metadata, metrics peaks, latency summaries, and OCR/backend
    result metadata.

Relationships:
    - Used by `pdf_throughput_profile_runner` for per-profile execution.
    - Uses `pdf_throughput_profiles.ProfileSpec` for the governed benchmark profile
      settings.
    - Exercises `interfaces.http_api.create_app` and the v2 runtime stack.
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

from .pdf_throughput_profiles import ProfileSpec
from .pdf_throughput_types import (
    CorpusFileRecord,
    JobRecord,
    ProfilePayload,
    ProfileSummary,
    ResourceEvidence,
)


class _ResultMetadataFields(TypedDict):
    """Conversion metadata fields copied into one benchmark job record."""

    backend_used: str | None
    acceleration_used: str | None
    ocr_enabled: bool | None
    ocr_engine_used: str | None
    ocr_languages_used: list[str] | None
    gpu_busy_percent: int | None
    gpu_memory_used_percent: int | None
    warnings: list[str]


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


def _coerce_optional_str_list(value: object) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


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
    raise RuntimeError(f"PDF throughput benchmark polling timed out for {job_id}.")


def _summarize(
    latencies: list[float],
    pages_per_minute: list[float],
    failed_jobs: int,
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
        "total_latency_seconds": round(sum(latencies), 6),
        "latency_seconds": {
            "min": round(min(latencies), 6) if latencies else 0.0,
            "mean": round(mean_latency, 6),
            "p50": _percentile(latencies, 0.50),
            "p90": _percentile(latencies, 0.90),
            "max": round(max(latencies), 6) if latencies else 0.0,
        },
        "pages_per_minute_p50": _percentile(pages_per_minute, 0.50),
    }


def _failed_create_job_record(
    *,
    source_path: Path,
    corpus_record: CorpusFileRecord,
    warning: str,
) -> JobRecord:
    return {
        "source_file": source_path.name,
        "page_count": corpus_record["page_count"],
        "job_id": None,
        "status": "failed",
        "latency_seconds": 0.0,
        "pages_per_minute": None,
        "backend_used": None,
        "acceleration_used": None,
        "ocr_enabled": None,
        "ocr_engine_used": None,
        "ocr_languages_used": None,
        "gpu_busy_percent": None,
        "gpu_memory_used_percent": None,
        "warnings": [warning],
    }


def run_profile(
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
    """Execute one benchmark profile and return its payload."""
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
                    "Idempotency-Key": f"pdf-throughput-{profile.profile_name}-{index:03d}",
                    "X-Correlation-ID": f"corr_pdf-throughput_{profile.profile_name}_{index:03d}",
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
                    _failed_create_job_record(
                        source_path=source_path,
                        corpus_record=corpus_record,
                        warning=f"http_{create_response.status_code}",
                    )
                )
                continue
            _record_completed_job(
                client=client,
                api_key=api_key,
                create_payload_obj=create_response.json(),
                corpus_record=corpus_record,
                source_path=source_path,
                max_poll_seconds=max_poll_seconds,
                resource_evidence=resource_evidence,
                jobs=jobs,
                latencies=latencies,
                pages_per_minute_values=pages_per_minute_values,
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


def _record_completed_job(
    *,
    client: TestClient,
    api_key: str,
    create_payload_obj: object,
    corpus_record: CorpusFileRecord,
    source_path: Path,
    max_poll_seconds: float,
    resource_evidence: ResourceEvidence,
    jobs: list[JobRecord],
    latencies: list[float],
    pages_per_minute_values: list[float],
) -> None:
    if not isinstance(create_payload_obj, dict):
        raise RuntimeError("PDF throughput benchmark create response is not a JSON object.")
    create_job_obj = create_payload_obj.get("job")
    if not isinstance(create_job_obj, dict):
        raise RuntimeError("PDF throughput benchmark create response is missing job object.")
    job_id_obj = create_job_obj.get("job_id")
    if not isinstance(job_id_obj, str):
        raise RuntimeError("PDF throughput benchmark create response is missing string job_id.")
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
        raise RuntimeError(
            f"PDF throughput benchmark final payload missing job object for {job_id}."
        )
    created_at_obj = job_obj.get("created_at")
    updated_at_obj = job_obj.get("updated_at")
    progress_obj = job_obj.get("progress")
    status_obj = job_obj.get("status")
    if not isinstance(created_at_obj, str) or not isinstance(updated_at_obj, str):
        raise RuntimeError(
            f"PDF throughput benchmark final payload missing timestamps for {job_id}."
        )
    if not isinstance(progress_obj, dict):
        raise RuntimeError(
            f"PDF throughput benchmark final payload missing progress object for {job_id}."
        )
    if not isinstance(status_obj, str):
        raise RuntimeError(
            f"PDF throughput benchmark final payload missing status string for {job_id}."
        )
    created_at = _parse_timestamp(created_at_obj)
    updated_at = _parse_timestamp(updated_at_obj)
    latency_seconds = round((updated_at - created_at).total_seconds(), 6)
    pages_per_minute = progress_obj.get("pages_per_minute")
    metadata = _read_result_metadata(
        client=client, api_key=api_key, job_id=job_id, status=status_obj
    )
    if status_obj == JobStatus.SUCCEEDED.value:
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
                float(pages_per_minute) if isinstance(pages_per_minute, (int, float)) else None
            ),
            "backend_used": metadata["backend_used"],
            "acceleration_used": metadata["acceleration_used"],
            "ocr_enabled": metadata["ocr_enabled"],
            "ocr_engine_used": metadata["ocr_engine_used"],
            "ocr_languages_used": metadata["ocr_languages_used"],
            "gpu_busy_percent": metadata["gpu_busy_percent"],
            "gpu_memory_used_percent": metadata["gpu_memory_used_percent"],
            "warnings": metadata["warnings"],
        }
    )


def _read_result_metadata(
    *,
    client: TestClient,
    api_key: str,
    job_id: str,
    status: str,
) -> _ResultMetadataFields:
    if status != JobStatus.SUCCEEDED.value:
        return {
            "backend_used": None,
            "acceleration_used": None,
            "ocr_enabled": None,
            "ocr_engine_used": None,
            "ocr_languages_used": None,
            "gpu_busy_percent": None,
            "gpu_memory_used_percent": None,
            "warnings": [],
        }
    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": api_key},
    )
    result_payload_obj: object = result_response.json()
    if not isinstance(result_payload_obj, dict):
        raise RuntimeError(
            f"PDF throughput benchmark result payload is not an object for {job_id}."
        )
    result_obj = result_payload_obj.get("result")
    if not isinstance(result_obj, dict):
        raise RuntimeError(
            f"PDF throughput benchmark result payload missing result object for {job_id}."
        )
    metadata_obj = result_obj.get("conversion_metadata")
    if not isinstance(metadata_obj, dict):
        raise RuntimeError(
            f"PDF throughput benchmark result payload missing conversion metadata for {job_id}."
        )
    warnings_obj = result_obj.get("warnings", [])
    warnings = (
        list(warnings_obj)
        if isinstance(warnings_obj, list) and all(isinstance(item, str) for item in warnings_obj)
        else []
    )
    return {
        "backend_used": metadata_obj.get("backend_used")
        if isinstance(metadata_obj.get("backend_used"), str)
        else None,
        "acceleration_used": metadata_obj.get("acceleration_used")
        if isinstance(metadata_obj.get("acceleration_used"), str)
        else None,
        "ocr_enabled": metadata_obj.get("ocr_enabled")
        if isinstance(metadata_obj.get("ocr_enabled"), bool)
        else None,
        "ocr_engine_used": metadata_obj.get("ocr_engine_used")
        if isinstance(metadata_obj.get("ocr_engine_used"), str)
        else None,
        "ocr_languages_used": _coerce_optional_str_list(metadata_obj.get("ocr_languages_used")),
        "gpu_busy_percent": metadata_obj.get("gpu_busy_percent")
        if isinstance(metadata_obj.get("gpu_busy_percent"), int)
        else None,
        "gpu_memory_used_percent": metadata_obj.get("gpu_memory_used_percent")
        if isinstance(metadata_obj.get("gpu_memory_used_percent"), int)
        else None,
        "warnings": warnings,
    }
