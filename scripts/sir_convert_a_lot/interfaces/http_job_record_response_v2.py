"""Job-record response mapping for service API v2 routes.

Purpose:
    Build public v2 job status payloads from stored runtime jobs, including
    progress links and safe formula-authority metadata.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2`.
    - Consumes `infrastructure.runtime_models_v2.StoredJobV2`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    JobLinksV2,
    JobProgressV2,
    JobRecordDataV2,
    JobRecordResponseV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def job_record_response_v2(job: StoredJobV2) -> JobRecordResponseV2:
    """Build one public v2 job record response from runtime state."""
    return JobRecordResponseV2(
        job=JobRecordDataV2(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
            source_filename=job.source_filename,
            source_format=job.source_format,
            output_format=job.output_format,
            progress=JobProgressV2(
                stage=job.progress_stage,
                last_heartbeat_at=job.last_heartbeat_at,
                current_phase_started_at=job.current_phase_started_at,
                phase_timings_ms=job.phase_timings_ms,
                total_pages=job.total_pages,
                processed_pages=job.processed_pages,
                failed_pages=job.failed_pages,
                percent_complete=job.percent_complete,
                pages_per_minute=job.pages_per_minute,
                eta_seconds=job.eta_seconds,
            ),
            links=JobLinksV2(
                self=f"/v2/convert/jobs/{job.job_id}",
                result=f"/v2/convert/jobs/{job.job_id}/result",
                artifact=f"/v2/convert/jobs/{job.job_id}/artifact",
                cancel=f"/v2/convert/jobs/{job.job_id}/cancel",
            ),
            formula_authority=dict(job.formula_authority),
        )
    )
