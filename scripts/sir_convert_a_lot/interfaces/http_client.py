"""Sir Convert-a-Lot HTTP client compatibility interface.

Purpose:
    Provide a stable client import path that executes conversions only against
    the active v2 service API endpoints.

Relationships:
    - Used by compatibility facades and benchmark/devops helpers.
    - Delegates transport to `/v2/convert/jobs*` endpoint semantics.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus


@dataclass
class ClientError(Exception):
    """HTTP/service-level error returned by Sir Convert-a-Lot endpoints."""

    code: str
    message: str
    retryable: bool
    status_code: int
    job_id: str | None = None
    details: dict[str, object] | None = None


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
    """Compatibility client backed by Sir Convert-a-Lot v2 job endpoints."""

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

    def get_job_payload(
        self, job_id: str, *, correlation_id: str | None = None
    ) -> dict[str, object]:
        """Fetch raw job payload for a submitted conversion job."""
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

    def _normalize_pdf_job_spec(
        self, *, pdf_path: Path, job_spec: dict[str, object]
    ) -> dict[str, object]:
        """Normalize compatibility job specs to the canonical v2 `pdf -> md` shape."""
        source_obj = job_spec.get("source")
        conversion_obj = job_spec.get("conversion")
        pdf_options_obj = job_spec.get("pdf_options")
        execution_obj = job_spec.get("execution")
        retention_obj = job_spec.get("retention")

        if (
            isinstance(source_obj, dict)
            and source_obj.get("kind") == "upload"
            and source_obj.get("format") == "pdf"
            and isinstance(conversion_obj, dict)
            and isinstance(pdf_options_obj, dict)
        ):
            converted_source = {
                "kind": "upload",
                "filename": pdf_path.name,
                "format": "pdf",
            }
            converted_conversion: dict[str, object] = {
                "output_format": conversion_obj.get("output_format", "md"),
                "css_filenames": conversion_obj.get("css_filenames", []),
                "reference_docx_filename": conversion_obj.get("reference_docx_filename"),
            }
            template_obj = conversion_obj.get("template")
            if isinstance(template_obj, dict):
                converted_conversion["template"] = template_obj

            normalized: dict[str, object] = {
                "api_version": "v2",
                "source": converted_source,
                "conversion": converted_conversion,
                "pdf_options": dict(pdf_options_obj),
                "execution": dict(execution_obj) if isinstance(execution_obj, dict) else None,
                "retention": dict(retention_obj)
                if isinstance(retention_obj, dict)
                else {"pin": False},
            }
            return normalized

        backend_strategy = "auto"
        ocr_mode = "auto"
        table_mode = "accurate"
        normalize = "strict"
        output_format = "md"

        if isinstance(conversion_obj, dict):
            output_obj = conversion_obj.get("output_format")
            backend_obj = conversion_obj.get("backend_strategy")
            ocr_obj = conversion_obj.get("ocr_mode")
            table_obj = conversion_obj.get("table_mode")
            normalize_obj = conversion_obj.get("normalize")
            if isinstance(output_obj, str) and output_obj.strip() != "":
                output_format = output_obj
            if isinstance(backend_obj, str) and backend_obj.strip() != "":
                backend_strategy = backend_obj
            if isinstance(ocr_obj, str) and ocr_obj.strip() != "":
                ocr_mode = ocr_obj
            if isinstance(table_obj, str) and table_obj.strip() != "":
                table_mode = table_obj
            if isinstance(normalize_obj, str) and normalize_obj.strip() != "":
                normalize = normalize_obj

        normalized_spec: dict[str, object] = {
            "api_version": "v2",
            "source": {
                "kind": "upload",
                "filename": pdf_path.name,
                "format": "pdf",
            },
            "conversion": {
                "output_format": output_format,
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "pdf_options": {
                "backend_strategy": backend_strategy,
                "ocr_mode": ocr_mode,
                "table_mode": table_mode,
                "normalize": normalize,
            },
            "execution": dict(execution_obj) if isinstance(execution_obj, dict) else None,
            "retention": dict(retention_obj) if isinstance(retention_obj, dict) else {"pin": False},
        }
        return normalized_spec

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
        normalized_job_spec = self._normalize_pdf_job_spec(pdf_path=pdf_path, job_spec=job_spec)
        with pdf_path.open("rb") as handle:
            response = self._client.post(
                "/v2/convert/jobs",
                params={"wait_seconds": wait_seconds},
                headers=self._headers(
                    idempotency_key=idempotency_key, correlation_id=correlation_id
                ),
                data={
                    "job_spec": json.dumps(
                        normalized_job_spec,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                },
                files={"file": (pdf_path.name, handle, "application/pdf")},
            )

        if response.status_code not in {200, 202}:
            raise self._extract_error(response)

        payload: object = response.json()
        return self._read_job_status(payload)

    def get_job_status(self, job_id: str, *, correlation_id: str | None = None) -> JobStatus:
        """Fetch current job status for a submitted conversion job."""
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

    def fetch_result_payload(
        self,
        job_id: str,
        *,
        correlation_id: str | None = None,
        inline: bool = True,
    ) -> dict[str, object]:
        """Fetch raw successful result payload for a job.

        When `inline=True` and the output artifact is Markdown, the payload
        includes compatibility field `result.markdown_content` decoded from
        `/v2/convert/jobs/{job_id}/artifact`.
        """
        response = self._client.get(
            f"/v2/convert/jobs/{job_id}/result",
            headers=self._headers(correlation_id=correlation_id),
        )

        if response.status_code != 200:
            raise self._extract_error(response, job_id=job_id)

        payload: object = response.json()
        if not isinstance(payload, dict):
            raise ClientError(
                code="invalid_response",
                message="Result response is not a JSON object.",
                retryable=False,
                status_code=500,
                job_id=job_id,
            )

        if not inline:
            return payload

        result_obj = payload.get("result")
        if not isinstance(result_obj, dict):
            return payload

        artifact_obj = result_obj.get("artifact")
        if not isinstance(artifact_obj, dict):
            return payload

        format_obj = artifact_obj.get("format")
        if format_obj != "md":
            return payload

        artifact_response = self._client.get(
            f"/v2/convert/jobs/{job_id}/artifact",
            headers=self._headers(correlation_id=correlation_id),
        )
        if artifact_response.status_code != 200:
            raise self._extract_error(artifact_response, job_id=job_id)
        try:
            markdown_content = artifact_response.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ClientError(
                code="invalid_response",
                message="Markdown artifact is not valid UTF-8.",
                retryable=False,
                status_code=502,
                job_id=job_id,
            ) from exc

        result_with_markdown = dict(result_obj)
        result_with_markdown["markdown_content"] = markdown_content
        payload_with_markdown = dict(payload)
        payload_with_markdown["result"] = result_with_markdown
        return payload_with_markdown

    def fetch_markdown_result(self, job_id: str, *, correlation_id: str | None = None) -> str:
        """Fetch successful markdown artifact content for a job."""
        payload = self.fetch_result_payload(job_id, correlation_id=correlation_id, inline=True)

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
