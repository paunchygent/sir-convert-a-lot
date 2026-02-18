"""Sir Convert-a-Lot HTTP client for service API v2.

Purpose:
    Provide a typed, synchronous client for the Sir Convert-a-Lot **v2** service
    endpoints. v2 extends the service with multi-format conversions executed on
    Hemma (md/html/pdf -> pdf/docx) while preserving the locked v1 PDF->MD
    contract.

Relationships:
    - Used by `scripts.sir_convert_a_lot.interfaces.cli_app` for remote-only
      multi-format conversions (submit/poll/download).
    - Targets `scripts.sir_convert_a_lot.interfaces.http_routes_jobs_v2` endpoint
      semantics (`/v2/convert/jobs/*`).
    - Reuses the shared `ClientError` envelope parsing behavior from
      `scripts.sir_convert_a_lot.interfaces.http_client`.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Literal, TypeAlias

import httpx

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client import ClientError

RequestFileValue: TypeAlias = tuple[str, IO[bytes] | bytes | str, str]


@dataclass(frozen=True)
class SubmittedJobV2:
    """Job state returned immediately after v2 job creation."""

    job_id: str
    status: JobStatus


@dataclass(frozen=True)
class ArtifactOutcomeV2:
    """Successful artifact outcome returned by v2 client operations."""

    job_id: str
    status: Literal[JobStatus.SUCCEEDED]
    artifact_bytes: bytes


def _content_type_for_source_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix in {".html", ".htm"}:
        return "text/html"
    return "application/octet-stream"


class SirConvertALotClientV2:
    """Client for Sir Convert-a-Lot v2 conversion job endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 60.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._owned_client = http_client is None
        self._client = (
            http_client
            if http_client is not None
            else httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)
        )

    def close(self) -> None:
        """Close underlying HTTP client when this instance owns it."""
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> "SirConvertALotClientV2":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _headers(
        self, *, idempotency_key: str | None = None, correlation_id: str | None = None
    ) -> dict[str, str]:
        headers = {"X-API-Key": self.api_key}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if correlation_id is not None:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def _extract_error(self, response: httpx.Response, *, job_id: str | None = None) -> ClientError:
        payload: object
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                code_obj = error_obj.get("code")
                message_obj = error_obj.get("message")
                retryable_obj = error_obj.get("retryable")
                details_obj = error_obj.get("details")
                code = code_obj if isinstance(code_obj, str) else "unknown_error"
                message = (
                    message_obj
                    if isinstance(message_obj, str)
                    else f"HTTP {response.status_code} request failed"
                )
                retryable = retryable_obj if isinstance(retryable_obj, bool) else False
                details = details_obj if isinstance(details_obj, dict) else None
                return ClientError(
                    code=code,
                    message=message,
                    retryable=retryable,
                    status_code=response.status_code,
                    job_id=job_id,
                    details=details,
                )

        return ClientError(
            code="http_error",
            message=f"HTTP {response.status_code} request failed with non-standard error payload.",
            retryable=False,
            status_code=response.status_code,
            job_id=job_id,
            details=None,
        )

    def _read_job_status(self, payload: object) -> SubmittedJobV2:
        if not isinstance(payload, dict):
            raise ClientError(
                code="invalid_response",
                message="Service response is not a JSON object.",
                retryable=False,
                status_code=500,
            )

        job_obj = payload.get("job")
        if not isinstance(job_obj, dict):
            raise ClientError(
                code="invalid_response",
                message="Service response is missing the 'job' object.",
                retryable=False,
                status_code=500,
            )

        job_id_obj = job_obj.get("job_id")
        status_obj = job_obj.get("status")
        if not isinstance(job_id_obj, str) or not isinstance(status_obj, str):
            raise ClientError(
                code="invalid_response",
                message="Service response is missing 'job_id' or 'status'.",
                retryable=False,
                status_code=500,
            )

        try:
            status = JobStatus(status_obj)
        except ValueError as exc:
            raise ClientError(
                code="invalid_response",
                message=f"Unknown job status '{status_obj}' in service response.",
                retryable=False,
                status_code=500,
            ) from exc

        return SubmittedJobV2(job_id=job_id_obj, status=status)

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
        """Create a v2 conversion job for one uploaded input file."""

        files: dict[str, RequestFileValue] = {}

        with source_path.open("rb") as handle:
            files["file"] = (source_path.name, handle, _content_type_for_source_path(source_path))
            if resources_zip_bytes is not None:
                files["resources"] = ("resources.zip", resources_zip_bytes, "application/zip")
            if reference_docx_bytes is not None:
                files["reference_docx"] = (
                    "reference.docx",
                    reference_docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

            response = self._client.post(
                "/v2/convert/jobs",
                params={"wait_seconds": wait_seconds},
                headers=self._headers(
                    idempotency_key=idempotency_key, correlation_id=correlation_id
                ),
                data={"job_spec": json.dumps(job_spec, separators=(",", ":"), sort_keys=True)},
                files=files,
            )

        if response.status_code not in {200, 202}:
            raise self._extract_error(response)

        payload: object = response.json()
        return self._read_job_status(payload)

    def get_job_payload(
        self, job_id: str, *, correlation_id: str | None = None
    ) -> dict[str, object]:
        """Fetch raw job payload for a submitted v2 job."""
        response = self._client.get(
            f"/v2/convert/jobs/{job_id}",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 200:
            raise self._extract_error(response, job_id=job_id)
        payload: object = response.json()
        if not isinstance(payload, dict):
            raise ClientError(
                code="invalid_response",
                message="Job response is not a JSON object.",
                retryable=False,
                status_code=500,
                job_id=job_id,
            )
        return payload

    def get_job_status(self, job_id: str, *, correlation_id: str | None = None) -> JobStatus:
        """Fetch current v2 job status."""
        payload = self.get_job_payload(job_id, correlation_id=correlation_id)
        submitted = self._read_job_status(payload)
        return submitted.status

    def wait_for_terminal_status(
        self,
        job_id: str,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float = 0.2,
        correlation_id: str | None = None,
    ) -> JobStatus:
        """Poll v2 job status until terminal status or timeout."""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status = self.get_job_status(job_id, correlation_id=correlation_id)
            if status in TERMINAL_JOB_STATUSES:
                return status
            time.sleep(poll_interval_seconds)

        raise ClientError(
            code="job_timeout",
            message="Timed out waiting for conversion job to reach a terminal state.",
            retryable=True,
            status_code=408,
            job_id=job_id,
        )

    def download_artifact(self, job_id: str, *, correlation_id: str | None = None) -> bytes:
        """Download output artifact bytes for a successful v2 job."""
        response = self._client.get(
            f"/v2/convert/jobs/{job_id}/artifact",
            headers=self._headers(correlation_id=correlation_id),
        )

        if response.status_code == 200:
            return response.content

        if response.status_code == 202:
            raise ClientError(
                code="job_not_terminal",
                message="Job is not in a terminal state yet.",
                retryable=True,
                status_code=202,
                job_id=job_id,
            )

        raise self._extract_error(response, job_id=job_id)

    def convert_upload_to_artifact(
        self,
        *,
        source_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        max_poll_seconds: float,
        correlation_id: str | None = None,
        resources_zip_bytes: bytes | None = None,
        reference_docx_bytes: bytes | None = None,
    ) -> ArtifactOutcomeV2:
        """Submit a v2 job, wait for success, and download artifact bytes."""
        submitted = self.submit_job(
            source_path=source_path,
            job_spec=job_spec,
            idempotency_key=idempotency_key,
            wait_seconds=wait_seconds,
            correlation_id=correlation_id,
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=reference_docx_bytes,
        )

        final_status = submitted.status
        if final_status not in TERMINAL_JOB_STATUSES:
            final_status = self.wait_for_terminal_status(
                submitted.job_id,
                timeout_seconds=max_poll_seconds,
                correlation_id=correlation_id,
            )

        if final_status != JobStatus.SUCCEEDED:
            raise ClientError(
                code="job_not_succeeded",
                message=f"Job {submitted.job_id} ended with status '{final_status.value}'.",
                retryable=False,
                status_code=409,
                job_id=submitted.job_id,
            )

        artifact_bytes = self.download_artifact(submitted.job_id, correlation_id=correlation_id)
        if len(artifact_bytes) == 0:
            raise ClientError(
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
        )
