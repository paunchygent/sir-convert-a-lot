"""Unit tests for v2 create-job request validation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_jobs_v2_request_validation import (
    validate_create_job_route_constraints,
)
from tests.sir_convert_a_lot.service.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    md_to_pdf_spec,
    post_create,
)


def test_rejects_reference_docx_upload_for_pdf_output() -> None:
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": "page.html", "format": "html"},
            "conversion": {"output_format": "pdf", "css_filenames": []},
            "retention": {"pin": False},
        }
    )

    with pytest.raises(ServiceError) as exc_info:
        validate_create_job_route_constraints(
            spec=spec,
            resources_uploaded=False,
            reference_docx_uploaded=True,
        )

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "validation_error"
    details = error.details
    assert isinstance(details, dict)
    field = details.get("field")
    output_format = details.get("output_format")
    assert isinstance(field, str)
    assert isinstance(output_format, str)
    assert field == "reference_docx"
    assert output_format == "pdf"


def test_allows_reference_docx_upload_for_docx_output() -> None:
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": "lesson.md", "format": "md"},
            "conversion": {"output_format": "docx", "css_filenames": []},
            "retention": {"pin": False},
        }
    )

    validate_create_job_route_constraints(
        spec=spec,
        resources_uploaded=False,
        reference_docx_uploaded=True,
    )


def test_create_job_rejects_retired_artifact_language(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path, run_jobs_on_submit=False)
    spec = md_to_pdf_spec("note.md")
    conversion = spec["conversion"]
    assert isinstance(conversion, dict)
    conversion["artifact_language"] = "sv"

    response = post_create(client, spec=spec)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
