"""Sir Convert-a-Lot HTTP client for service API v2.

Purpose:
    Provide a typed, synchronous client for the Sir Convert-a-Lot **v2** service
    endpoints for multi-format conversions executed on Hemma
    (pdf/md/html -> md/pdf/docx).

Relationships:
    - Used by `scripts.sir_convert_a_lot.interfaces.cli_app` for remote-only
      multi-format conversions (submit/poll/download).
    - Targets `scripts.sir_convert_a_lot.interfaces.http_routes_jobs_v2` endpoint
      semantics (`/v2/convert/jobs/*`).
    - Owns the v2 client error envelope parsing behavior (`ClientErrorV2`).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client_v2_conversion import (
    convert_upload_to_artifact_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ArtifactOutcomeV2,
    ClientErrorV2,
    RequestFileValue,
    RetryModeV2,
    SubmittedJobV2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_polling import (
    wait_for_terminal_status_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_upload_helpers import (
    content_type_for_source_path,
)

DEFAULT_STALL_TIMEOUT_SECONDS: float = 120.0


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

    def _extract_error(
        self, response: httpx.Response, *, job_id: str | None = None
    ) -> ClientErrorV2:
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
                return ClientErrorV2(
                    code=code,
                    message=message,
                    retryable=retryable,
                    status_code=response.status_code,
                    job_id=job_id,
                    details=details,
                )

        return ClientErrorV2(
            code="http_error",
            message=f"HTTP {response.status_code} request failed with non-standard error payload.",
            retryable=False,
            status_code=response.status_code,
            job_id=job_id,
            details=None,
        )

    def _read_job_status(self, payload: object) -> SubmittedJobV2:
        if not isinstance(payload, dict):
            raise ClientErrorV2(
                code="invalid_response",
                message="Service response is not a JSON object.",
                retryable=False,
                status_code=500,
            )

        job_obj = payload.get("job")
        if not isinstance(job_obj, dict):
            raise ClientErrorV2(
                code="invalid_response",
                message="Service response is missing the 'job' object.",
                retryable=False,
                status_code=500,
            )

        job_id_obj = job_obj.get("job_id")
        status_obj = job_obj.get("status")
        if not isinstance(job_id_obj, str) or not isinstance(status_obj, str):
            raise ClientErrorV2(
                code="invalid_response",
                message="Service response is missing 'job_id' or 'status'.",
                retryable=False,
                status_code=500,
            )

        try:
            status = JobStatus(status_obj)
        except ValueError as exc:
            raise ClientErrorV2(
                code="invalid_response",
                message=f"Unknown job status '{status_obj}' in service response.",
                retryable=False,
                status_code=500,
            ) from exc

        idempotency = _idempotency_metadata_from_payload(payload)

        return SubmittedJobV2(job_id=job_id_obj, status=status, idempotency=idempotency)

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
            files["file"] = (source_path.name, handle, content_type_for_source_path(source_path))
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

        idempotent_replay = response.headers.get("X-Idempotent-Replay", "").lower() == "true"
        payload: object = response.json()
        submitted = self._read_job_status(payload)
        return SubmittedJobV2(
            job_id=submitted.job_id,
            status=submitted.status,
            idempotent_replay=idempotent_replay,
            idempotency=dict(submitted.idempotency),
        )

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
            raise ClientErrorV2(
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

    def get_result_payload(
        self, job_id: str, *, correlation_id: str | None = None
    ) -> dict[str, object]:
        """Fetch raw v2 job result payload."""
        response = self._client.get(
            f"/v2/convert/jobs/{job_id}/result",
            headers=self._headers(correlation_id=correlation_id),
        )

        if response.status_code == 200:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise ClientErrorV2(
                    code="invalid_response",
                    message="Job result payload is not a JSON object.",
                    retryable=False,
                    status_code=500,
                    job_id=job_id,
                )
            return payload

        if response.status_code == 202:
            raise ClientErrorV2(
                code="job_not_terminal",
                message="Job is not in a terminal state yet.",
                retryable=True,
                status_code=202,
                job_id=job_id,
            )

        raise self._extract_error(response, job_id=job_id)

    def cancel_job(self, job_id: str, *, correlation_id: str | None = None) -> SubmittedJobV2:
        """Request cancellation for one v2 job."""
        response = self._client.post(
            f"/v2/convert/jobs/{job_id}/cancel",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code not in {200, 202}:
            raise self._extract_error(response, job_id=job_id)
        payload: object = response.json()
        status = self._read_job_status(payload)
        return SubmittedJobV2(job_id=status.job_id, status=status.status)

    def resume_job(
        self,
        *,
        source_job_id: str,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> SubmittedJobV2:
        """Resume a PDF job from its latest checkpoint by creating a new v2 job."""
        response = self._client.post(
            f"/v2/convert/jobs/{source_job_id}/resume",
            headers=self._headers(idempotency_key=idempotency_key, correlation_id=correlation_id),
        )
        if response.status_code not in {200, 202}:
            raise self._extract_error(response, job_id=source_job_id)
        idempotent_replay = response.headers.get("X-Idempotent-Replay", "").lower() == "true"
        payload: object = response.json()
        status = self._read_job_status(payload)
        return SubmittedJobV2(
            job_id=status.job_id,
            status=status.status,
            idempotent_replay=idempotent_replay,
            idempotency=dict(status.idempotency),
        )

    def download_partial_artifact(self, job_id: str, *, correlation_id: str | None = None) -> bytes:
        """Download partial markdown bytes for a long-running PDF job when available."""
        response = self._client.get(
            f"/v2/convert/jobs/{job_id}/artifact/partial",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code == 200:
            return response.content
        if response.status_code == 202:
            payload: object = response.json()
            status = self._read_job_status(payload)
            raise ClientErrorV2(
                code="partial_artifact_not_ready",
                message="Partial artifact is not available yet.",
                retryable=True,
                status_code=202,
                job_id=status.job_id,
                details={"status": status.status.value},
            )
        raise self._extract_error(response, job_id=job_id)

    def get_checkpoint_payload(
        self, job_id: str, *, correlation_id: str | None = None
    ) -> dict[str, object]:
        """Fetch the latest checkpoint JSON payload for a long-running PDF job."""
        response = self._client.get(
            f"/v2/convert/jobs/{job_id}/checkpoint",
            headers=self._headers(correlation_id=correlation_id),
        )
        payload_obj: object
        if response.status_code == 200:
            payload_obj = response.json()
            if not isinstance(payload_obj, dict):
                raise ClientErrorV2(
                    code="invalid_response",
                    message="Checkpoint payload is not a JSON object.",
                    retryable=False,
                    status_code=500,
                    job_id=job_id,
                )
            return payload_obj
        if response.status_code == 202:
            payload_obj = response.json()
            status = self._read_job_status(payload_obj)
            raise ClientErrorV2(
                code="checkpoint_not_ready",
                message="Checkpoint is not available yet.",
                retryable=True,
                status_code=202,
                job_id=status.job_id,
                details={"status": status.status.value},
            )
        raise self._extract_error(response, job_id=job_id)

    def wait_for_terminal_status(
        self,
        job_id: str,
        *,
        timeout_seconds: float,
        stall_timeout_seconds: float = DEFAULT_STALL_TIMEOUT_SECONDS,
        poll_interval_seconds: float = 0.2,
        correlation_id: str | None = None,
    ) -> JobStatus:
        """Poll v2 job status until terminal status or classified timeout."""
        return wait_for_terminal_status_v2(
            poller=self,
            job_id=job_id,
            timeout_seconds=timeout_seconds,
            stall_timeout_seconds=stall_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            correlation_id=correlation_id,
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
            raise ClientErrorV2(
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
        stall_timeout_seconds: float = DEFAULT_STALL_TIMEOUT_SECONDS,
        retry_mode: RetryModeV2 = "auto",
        correlation_id: str | None = None,
        resources_zip_bytes: bytes | None = None,
        reference_docx_bytes: bytes | None = None,
        progress_callback: Callable[[dict[str, object]], None] | None = None,
    ) -> ArtifactOutcomeV2:
        """Submit a v2 job, wait for success, and download artifact bytes."""
        return convert_upload_to_artifact_v2(
            client=self,
            source_path=source_path,
            job_spec=job_spec,
            idempotency_key=idempotency_key,
            wait_seconds=wait_seconds,
            max_poll_seconds=max_poll_seconds,
            stall_timeout_seconds=stall_timeout_seconds,
            retry_mode=retry_mode,
            correlation_id=correlation_id,
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=reference_docx_bytes,
            progress_callback=progress_callback,
        )


def _idempotency_metadata_from_payload(payload: dict[str, object]) -> dict[str, object]:
    idempotency_obj = payload.get("idempotency")
    if not isinstance(idempotency_obj, dict):
        return {}
    return {str(key): value for key, value in idempotency_obj.items()}
