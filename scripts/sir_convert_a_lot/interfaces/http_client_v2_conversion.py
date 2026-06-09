"""HTTP client conversion orchestration for service API v2.

Purpose:
    Keep submit/wait/retry/download conversion orchestration outside the main
    HTTP client class while preserving idempotency replay and progress callback
    behavior for CLI and adapter callers.

Relationships:
    - Called by `interfaces.http_client_v2.SirConvertALotClientV2`.
    - Uses polling helpers in `interfaces.http_client_v2_polling`.
    - Returns public client models from `interfaces.http_client_v2_models`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ArtifactOutcomeV2,
    ClientErrorV2,
    RetryModeV2,
    SubmittedJobV2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_polling import (
    wait_for_terminal_status_v2,
)


class ArtifactConversionClientV2(Protocol):
    """Client operations required for one v2 upload-to-artifact conversion."""

    def submit_job(
        self,
        *,
        source_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        correlation_id: str | None = None,
        resources_zip_bytes: bytes | None = None,
        reference_docx_bytes: bytes | None = None,
    ) -> SubmittedJobV2:
        """Submit one job and return initial service state."""

    def get_job_payload(
        self, job_id: str, *, correlation_id: str | None = None
    ) -> dict[str, object]:
        """Fetch one job status payload."""

    def _read_job_status(self, payload: object) -> SubmittedJobV2:
        """Parse status from a service payload."""

    def download_artifact(self, job_id: str, *, correlation_id: str | None = None) -> bytes:
        """Download terminal artifact bytes."""


def convert_upload_to_artifact_v2(
    *,
    client: ArtifactConversionClientV2,
    source_path: Path,
    job_spec: dict[str, object],
    idempotency_key: str,
    wait_seconds: int,
    max_poll_seconds: float,
    stall_timeout_seconds: float,
    retry_mode: RetryModeV2,
    correlation_id: str | None,
    resources_zip_bytes: bytes | None,
    reference_docx_bytes: bytes | None,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> ArtifactOutcomeV2:
    """Submit a v2 job, wait for success, and download artifact bytes."""
    if retry_mode not in {"auto", "replay_only", "new_job"}:
        raise ClientErrorV2(
            code="invalid_request",
            message=f"Unknown retry_mode '{retry_mode}'.",
            retryable=False,
            status_code=400,
        )

    effective_key = idempotency_key
    if retry_mode == "new_job":
        effective_key = f"{idempotency_key}_new_{uuid4().hex}"

    submitted = client.submit_job(
        source_path=source_path,
        job_spec=job_spec,
        idempotency_key=effective_key,
        wait_seconds=wait_seconds,
        correlation_id=correlation_id,
        resources_zip_bytes=resources_zip_bytes,
        reference_docx_bytes=reference_docx_bytes,
    )

    rerun_of_job_id: str | None = None
    if (
        retry_mode == "auto"
        and submitted.idempotent_replay
        and submitted.status in {JobStatus.FAILED, JobStatus.CANCELED}
    ):
        rerun_of_job_id = submitted.job_id
        submitted = client.submit_job(
            source_path=source_path,
            job_spec=job_spec,
            idempotency_key=f"{idempotency_key}_rerun_{uuid4().hex}",
            wait_seconds=wait_seconds,
            correlation_id=correlation_id,
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=reference_docx_bytes,
        )

    final_status = submitted.status
    if final_status not in TERMINAL_JOB_STATUSES:
        final_status = wait_for_terminal_status_v2(
            poller=client,
            job_id=submitted.job_id,
            timeout_seconds=max_poll_seconds,
            stall_timeout_seconds=stall_timeout_seconds,
            poll_interval_seconds=0.2,
            correlation_id=correlation_id,
            progress_callback=progress_callback,
        )

    if final_status != JobStatus.SUCCEEDED:
        raise ClientErrorV2(
            code="job_not_succeeded",
            message=f"Job {submitted.job_id} ended with status '{final_status.value}'.",
            retryable=False,
            status_code=409,
            job_id=submitted.job_id,
        )

    artifact_bytes = client.download_artifact(submitted.job_id, correlation_id=correlation_id)
    if len(artifact_bytes) == 0:
        raise ClientErrorV2(
            code="invalid_response",
            message="Downloaded artifact is empty.",
            retryable=True,
            status_code=502,
            job_id=submitted.job_id,
        )

    return ArtifactOutcomeV2(
        job_id=submitted.job_id,
        status=JobStatus.SUCCEEDED,
        artifact_bytes=artifact_bytes,
        rerun_of_job_id=rerun_of_job_id,
    )
