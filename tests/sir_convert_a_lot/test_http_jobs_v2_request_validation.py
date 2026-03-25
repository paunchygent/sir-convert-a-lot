"""Unit tests for v2 create-job request validation helpers."""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_jobs_v2_request_validation import (
    validate_create_job_route_constraints,
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
            trusted_app_bundle_allowed=False,
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
        trusted_app_bundle_allowed=False,
    )


def test_rejects_trusted_app_bundle_for_public_lane() -> None:
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": "page.html", "format": "html"},
            "conversion": {
                "output_format": "pdf",
                "css_filenames": [],
                "input_trust_mode": "trusted_app_bundle",
            },
            "retention": {"pin": False},
        }
    )

    with pytest.raises(ServiceError) as exc_info:
        validate_create_job_route_constraints(
            spec=spec,
            resources_uploaded=False,
            reference_docx_uploaded=False,
            trusted_app_bundle_allowed=False,
        )

    error = exc_info.value
    assert error.status_code == 403
    assert error.code == "insufficient_scope"
    assert error.details == {
        "required_trust_mode": "trusted_app_bundle",
        "surface": "v2_html_to_pdf",
    }


def test_allows_trusted_app_bundle_for_internal_lane() -> None:
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": "page.html", "format": "html"},
            "conversion": {
                "output_format": "pdf",
                "css_filenames": [],
                "input_trust_mode": "trusted_app_bundle",
            },
            "retention": {"pin": False},
        }
    )

    validate_create_job_route_constraints(
        spec=spec,
        resources_uploaded=False,
        reference_docx_uploaded=False,
        trusted_app_bundle_allowed=True,
    )
