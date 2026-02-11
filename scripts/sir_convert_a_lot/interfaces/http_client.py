"""Sir Convert-a-Lot HTTP client interface.

Purpose:
    Provide a typed client for the v1 Sir Convert-a-Lot service endpoints
    with standardized error parsing and polling behavior.

Relationships:
    - Used by `interfaces.cli_app` for local batch conversion workflows.
    - Targets `interfaces.http_api` endpoint semantics.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus


@dataclass(frozen=True)
class ClientError(Exception):
    """HTTP/service-level error returned by Sir Convert-a-Lot endpoints."""

    code: str
    message: str
    retryable: bool
    status_code: int
    job_id: str | None = None


@dataclass(frozen=True)
class ConversionOutcome:
    """Successful conversion outcome returned by client operations."""

    job_id: str
    status: Literal[JobStatus.SUCCEEDED]
    markdown_content: str


@dataclass(frozen=True)
class SubmittedJob:
    """Job state returned immediately after job creation."""

    job_id: str
    status: JobStatus


class SirConvertALotClient:
    """Client for Sir Convert-a-Lot v1 conversion job endpoints."""

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

    def __enter__(self) -> "SirConvertALotClient":
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

    def _extract_error(self, response: httpx.Response) -> ClientError:
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
                code = code_obj if isinstance(code_obj, str) else "unknown_error"
                message = (
                    message_obj
                    if isinstance(message_obj, str)
                    else f"HTTP {response.status_code} request failed"
                )
                retryable = retryable_obj if isinstance(retryable_obj, bool) else False
                return ClientError(
                    code=code,
                    message=message,
                    retryable=retryable,
                    status_code=response.status_code,
                )

        return ClientError(
            code="http_error",
            message=f"HTTP {response.status_code} request failed with non-standard error payload.",
            retryable=False,
            status_code=response.status_code,
        )

    def _read_job_status(self, payload: object) -> SubmittedJob:
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

        return SubmittedJob(job_id=job_id_obj, status=status)

    def submit_pdf_job(
        self,
        *,
        pdf_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        correlation_id: str | None = None,
    ) -> SubmittedJob:
        """Create a conversion job for a single PDF file."""
        with pdf_path.open("rb") as handle:
            response = self._client.post(
                "/v1/convert/jobs",
                params={"wait_seconds": wait_seconds},
                headers=self._headers(
                    idempotency_key=idempotency_key, correlation_id=correlation_id
                ),
                data={"job_spec": json.dumps(job_spec, separators=(",", ":"), sort_keys=True)},
                files={"file": (pdf_path.name, handle, "application/pdf")},
            )

        if response.status_code not in {200, 202}:
            raise self._extract_error(response)

        payload: object = response.json()
        return self._read_job_status(payload)

    def get_job_status(self, job_id: str, *, correlation_id: str | None = None) -> JobStatus:
        """Fetch current job status for a submitted conversion job."""
        response = self._client.get(
            f"/v1/convert/jobs/{job_id}",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 200:
            raise self._extract_error(response)

        payload: object = response.json()
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
        """Poll the status endpoint until terminal status or timeout."""
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

    def fetch_markdown_result(self, job_id: str, *, correlation_id: str | None = None) -> str:
        """Fetch successful markdown artifact content for a job."""
        response = self._client.get(
            f"/v1/convert/jobs/{job_id}/result",
            params={"inline": "true"},
            headers=self._headers(correlation_id=correlation_id),
        )

        if response.status_code != 200:
            raise self._extract_error(response)

        payload: object = response.json()
        if not isinstance(payload, dict):
            raise ClientError(
                code="invalid_response",
                message="Result response is not a JSON object.",
                retryable=False,
                status_code=500,
                job_id=job_id,
            )

        result_obj = payload.get("result")
        if not isinstance(result_obj, dict):
            raise ClientError(
                code="invalid_response",
                message="Result response missing 'result' object.",
                retryable=False,
                status_code=500,
                job_id=job_id,
            )

        markdown_obj = result_obj.get("markdown_content")
        if not isinstance(markdown_obj, str):
            raise ClientError(
                code="invalid_response",
                message="Result response missing inline 'markdown_content'.",
                retryable=False,
                status_code=500,
                job_id=job_id,
            )

        return markdown_obj

    def convert_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        max_poll_seconds: float,
        correlation_id: str | None = None,
    ) -> ConversionOutcome:
        """Submit a job, wait for completion, and fetch inline markdown result."""
        submitted = self.submit_pdf_job(
            pdf_path=pdf_path,
            job_spec=job_spec,
            idempotency_key=idempotency_key,
            wait_seconds=wait_seconds,
            correlation_id=correlation_id,
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

        markdown_content = self.fetch_markdown_result(
            submitted.job_id, correlation_id=correlation_id
        )
        return ConversionOutcome(
            job_id=submitted.job_id,
            status=JobStatus.SUCCEEDED,
            markdown_content=markdown_content,
        )
