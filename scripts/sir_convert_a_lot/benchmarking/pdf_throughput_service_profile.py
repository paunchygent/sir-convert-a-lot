"""Production-service profile execution for Hemma PDF throughput benchmarks.

Purpose:
    Execute one PDF throughput benchmark profile through the deployed Sir Convert-a-Lot
    v2 HTTP service instead of an in-process FastAPI `TestClient`.

Relationships:
    - Used by `pdf_throughput_profile_runner` when `runtime_mode=production_service`.
    - Shares payload helpers with `pdf_throughput_http_profile` so service-backed and
      in-process smoke evidence keep the same report schema.
    - Keeps dirty PDF OCR final proof final proof tied to the production service lane on Hemma.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TypedDict

import httpx

from scripts.sir_convert_a_lot.domain.specs import JobStatus

from .pdf_throughput_http_profile import (
    _coerce_optional_str_list,
    _failed_create_job_record,
    _job_spec,
    _metric_max,
    _parse_timestamp,
    _summarize,
)
from .pdf_throughput_profiles import ProfileSpec
from .pdf_throughput_types import (
    CorpusFileRecord,
    JobRecord,
    ProfilePayload,
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


def _empty_resource_evidence() -> ResourceEvidence:
    return {
        "peak_jobs_queued": 0.0,
        "peak_jobs_active": 0.0,
        "peak_worker_saturation_ratio": 0.0,
        "peak_chunk_worker_saturation_ratio": 0.0,
        "peak_gpu_busy_percent": 0.0,
        "peak_gpu_memory_used_percent": 0.0,
        "contains_job_id_label": False,
    }


def _sample_metrics(client: httpx.Client, resource_evidence: ResourceEvidence) -> None:
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


def _poll_job_and_metrics(
    client: httpx.Client,
    *,
    api_key: str,
    job_id: str,
    max_poll_seconds: float,
    resource_evidence: ResourceEvidence,
) -> dict[str, object]:
    deadline = time.monotonic() + max_poll_seconds
    while time.monotonic() < deadline:
        _sample_metrics(client, resource_evidence)
        response = client.get(f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": api_key})
        response.raise_for_status()
        payload_obj: object = response.json()
        if not isinstance(payload_obj, dict):
            raise RuntimeError(f"Job polling returned non-object payload for {job_id}.")
        payload = payload_obj
        job_obj = payload.get("job")
        if not isinstance(job_obj, dict):
            raise RuntimeError(f"Job polling payload missing job object for {job_id}.")
        status = JobStatus(job_obj["status"])
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return payload
        time.sleep(0.2)
    raise RuntimeError(
        f"PDF throughput benchmark service benchmark polling timed out for {job_id}."
    )


def _read_result_metadata(
    *,
    client: httpx.Client,
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
    result_response.raise_for_status()
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


def _record_completed_job(
    *,
    client: httpx.Client,
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
    latency_seconds = round(
        (_parse_timestamp(updated_at_obj) - _parse_timestamp(created_at_obj)).total_seconds(),
        6,
    )
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


def run_profile(
    *,
    profile: ProfileSpec,
    service_url: str,
    corpus_root: Path,
    corpus_records: list[CorpusFileRecord],
    api_key: str,
    acceleration_policy: str,
    ocr_mode: str,
    ocr_engine: str,
    ocr_languages: list[str],
    max_poll_seconds: float,
) -> ProfilePayload:
    """Execute one benchmark profile through a deployed HTTP service."""
    jobs: list[JobRecord] = []
    latencies: list[float] = []
    pages_per_minute_values: list[float] = []
    resource_evidence = _empty_resource_evidence()
    timeout = httpx.Timeout(timeout=max_poll_seconds + 60.0, connect=10.0)
    with httpx.Client(base_url=service_url, timeout=timeout) as client:
        for index, corpus_record in enumerate(corpus_records, start=1):
            source_path = corpus_root / corpus_record["filename"]
            create_response = client.post(
                "/v2/convert/jobs",
                params={"wait_seconds": 0},
                headers={
                    "X-API-Key": api_key,
                    "Idempotency-Key": f"pdf-throughput-service-{profile.profile_name}-{index:03d}",
                    "X-Correlation-ID": (
                        f"corr_pdf-throughput_service_{profile.profile_name}_{index:03d}"
                    ),
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
