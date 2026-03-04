"""Shared helpers for v2 jobs-route edge-case tests.

Purpose:
    Provide typed app/client and multipart request helpers reused by
    edge-case test modules for v2 job creation and retrieval paths.

Relationships:
    - Uses `scripts.sir_convert_a_lot.interfaces.http_api.create_app` to build the app.
    - Reused by `test_http_routes_jobs_v2_edge_cases_create` and
      `test_http_routes_jobs_v2_edge_cases_read_cancel`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import IO, Mapping, TypeAlias

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_MultipartFieldValue: TypeAlias = (
    IO[bytes]
    | bytes
    | str
    | tuple[str | None, IO[bytes] | bytes | str]
    | tuple[str | None, IO[bytes] | bytes | str, str | None]
    | tuple[str | None, IO[bytes] | bytes | str, str | None, Mapping[str, str]]
)
_MultipartFiles: TypeAlias = list[tuple[str, _MultipartFieldValue]]


def build_client(
    tmp_path: Path,
    *,
    max_upload_bytes: int = 50 * 1024 * 1024,
) -> tuple[TestClient, FastAPI]:
    """Build a test client and FastAPI app for v2 route edge-case tests."""

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            max_upload_bytes=max_upload_bytes,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    return TestClient(app), app


def job_spec_v2(
    *,
    filename: str,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
) -> dict[str, object]:
    """Build a canonical v2 job-spec payload used by route tests."""

    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": source_format.value},
        "conversion": {
            "output_format": output_format.value,
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }


def md_to_pdf_spec(filename: str) -> dict[str, object]:
    """Build the common markdown-to-pdf job spec for input filename."""

    return job_spec_v2(
        filename=filename,
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )


def post_create(
    client: TestClient,
    *,
    file_name: str = "note.md",
    file_bytes: bytes = b"# Hello\n",
    spec: dict[str, object] | str | None = None,
    idempotency_key: str | None = "idem-edge-default",
    resources_file: tuple[str, bytes, str] | None = None,
    reference_docx_file: tuple[str, bytes, str] | None = None,
) -> httpx.Response:
    """Submit a typed multipart request to `POST /v2/convert/jobs`."""

    headers = {
        "X-API-Key": "secret-key",
        "X-Correlation-ID": "corr_v2_edge_cases",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    job_spec_payload = spec
    if job_spec_payload is None:
        job_spec_payload = md_to_pdf_spec(file_name)
    serialized_spec = (
        json.dumps(job_spec_payload) if isinstance(job_spec_payload, dict) else job_spec_payload
    )

    files: _MultipartFiles = [
        ("file", (file_name, file_bytes, "application/octet-stream")),
        ("job_spec", (None, serialized_spec)),
    ]
    if resources_file is not None:
        files.append(("resources", resources_file))
    if reference_docx_file is not None:
        files.append(("reference_docx", reference_docx_file))

    return client.post("/v2/convert/jobs", headers=headers, files=files)


def disable_run_job_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable asynchronous runtime job execution in route tests."""

    def _noop_run_job_async(self: ServiceRuntimeV2, job_id: str) -> None:
        del self, job_id

    monkeypatch.setattr(ServiceRuntimeV2, "run_job_async", _noop_run_job_async)
