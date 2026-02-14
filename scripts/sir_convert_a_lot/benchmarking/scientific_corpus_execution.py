"""Execution engine for Task 12 scientific-corpus lanes and profiles.

Purpose:
    Execute deterministic submit/poll/result flows for acceptance/evaluation
    lanes and persist benchmark artifacts per document/profile.

Relationships:
    - Uses `interfaces.http_client` compatible clients via typed protocol.
    - Uses `scientific_corpus_utils.py` for job spec, idempotency, and summaries.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client import ClientError

from .scientific_corpus_types import (
    BackendProfile,
    BenchmarkClient,
    BenchmarkClientFactory,
    LaneJobRecord,
    LaneProfileResult,
    LaneResult,
)
from .scientific_corpus_utils import (
    artifact_paths,
    build_job_spec,
    idempotency_key,
    parse_success_result,
    slug_for_pdf,
    summarize_records,
)


def run_profile(
    *,
    client: BenchmarkClient,
    lane: str,
    profile: BackendProfile,
    pdf_paths: list[Path],
    artifacts_root: Path,
    max_poll_seconds: float,
) -> LaneProfileResult:
    """Execute one profile over all documents and return per-job evidence."""
    records: list[LaneJobRecord] = []
    profile_start = time.monotonic()

    for index, pdf_path in enumerate(pdf_paths, start=1):
        source_file = pdf_path.name
        source_size = pdf_path.stat().st_size
        document_slug = slug_for_pdf(pdf_path)
        job_spec = build_job_spec(source_file, profile)
        request_idempotency_key = idempotency_key(
            pdf_path,
            job_spec,
            scope=f"{lane}:{profile.profile_name}:{index:03d}",
        )
        correlation_id = f"corr_task12_{lane}_{profile.profile_name}_{index:03d}"
        markdown_path, metadata_path = artifact_paths(
            artifacts_root=artifacts_root,
            lane=lane,
            profile_name=profile.profile_name,
            document_slug=document_slug,
        )

        start_time = time.monotonic()
        status = JobStatus.FAILED
        job_id: str | None = None
        backend_used: str | None = None
        acceleration_used: str | None = None
        warnings: list[str] = []
        error_code: str | None = None
        markdown_output_path: str | None = None

        try:
            submitted = client.submit_pdf_job(
                pdf_path=pdf_path,
                job_spec=job_spec,
                idempotency_key=request_idempotency_key,
                wait_seconds=0,
                correlation_id=correlation_id,
            )
            job_id = submitted.job_id
            status = submitted.status
            if status not in TERMINAL_JOB_STATUSES:
                status = client.wait_for_terminal_status(
                    submitted.job_id,
                    timeout_seconds=max_poll_seconds,
                    correlation_id=correlation_id,
                )

            if status == JobStatus.SUCCEEDED:
                result_payload = client.fetch_result_payload(
                    submitted.job_id,
                    correlation_id=correlation_id,
                    inline=True,
                )
                markdown_content, backend_used, acceleration_used, warnings = parse_success_result(
                    result_payload
                )
                markdown_path.parent.mkdir(parents=True, exist_ok=True)
                markdown_path.write_text(markdown_content, encoding="utf-8")
                markdown_output_path = markdown_path.as_posix()
            else:
                try:
                    client.fetch_result_payload(
                        submitted.job_id,
                        correlation_id=correlation_id,
                        inline=False,
                    )
                except ClientError as result_error:
                    error_code = result_error.code
        except ClientError as request_error:
            error_code = request_error.code
            if request_error.job_id is not None:
                job_id = request_error.job_id
            status = JobStatus.FAILED
        except Exception:
            error_code = "harness_runtime_error"
            status = JobStatus.FAILED

        latency_seconds = round(time.monotonic() - start_time, 6)
        retry_warnings_count = sum(1 for warning in warnings if "retry" in warning.lower())
        metadata_output_path = metadata_path.as_posix()
        record: LaneJobRecord = {
            "source_file": source_file,
            "source_size_bytes": source_size,
            "document_slug": document_slug,
            "backend_profile": profile.profile_name,
            "job_id": job_id,
            "status": status.value,
            "error_code": error_code,
            "latency_seconds": latency_seconds,
            "backend_used": backend_used,
            "acceleration_used": acceleration_used,
            "warnings": warnings,
            "retry_warnings_count": retry_warnings_count,
            "output_markdown_path": markdown_output_path,
            "output_metadata_path": metadata_output_path,
        }

        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        records.append(record)

    profile_summary = summarize_records(records, duration_seconds=time.monotonic() - profile_start)
    return {
        "profile_name": profile.profile_name,
        "job_spec_profile": profile.to_job_spec_profile(),
        "summary": profile_summary,
        "jobs": records,
    }


def run_lane(
    *,
    lane: str,
    service_url: str,
    api_key: str,
    profiles: list[BackendProfile],
    pdf_paths: list[Path],
    artifacts_root: Path,
    max_poll_seconds: float,
    client_factory: BenchmarkClientFactory,
) -> LaneResult:
    """Execute one lane over its backend profiles and aggregate summary metrics."""
    lane_profiles: list[LaneProfileResult] = []
    lane_start = time.monotonic()
    with client_factory(base_url=service_url, api_key=api_key) as client:
        for profile in profiles:
            lane_profiles.append(
                run_profile(
                    client=client,
                    lane=lane,
                    profile=profile,
                    pdf_paths=pdf_paths,
                    artifacts_root=artifacts_root,
                    max_poll_seconds=max_poll_seconds,
                )
            )

    all_records = [record for profile in lane_profiles for record in profile["jobs"]]
    lane_summary = summarize_records(all_records, duration_seconds=time.monotonic() - lane_start)
    gate_passed = lane_summary["succeeded_jobs"] == lane_summary["total_jobs"]
    return {
        "lane": lane,
        "service_url": service_url,
        "profiles": lane_profiles,
        "summary": lane_summary,
        "gate_passed": gate_passed,
    }
