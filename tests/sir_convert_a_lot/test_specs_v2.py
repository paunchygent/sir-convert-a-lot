"""V2 domain spec validation branch coverage tests.

Purpose:
    Exercise `JobSpecV2` route and option invariants for invalid v2 request
    combinations to keep branch-level validation behavior deterministic.

Relationships:
    - Tests `scripts.sir_convert_a_lot.domain.specs_v2.JobSpecV2`.
    - Complements API-level contract tests with direct model validation checks.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2


def _base_payload(*, source_format: str = "md", output_format: str = "pdf") -> dict[str, object]:
    payload: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "input.dat", "format": source_format},
        "conversion": {
            "output_format": output_format,
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }
    return payload


def _pdf_options_payload() -> dict[str, object]:
    return {
        "backend_strategy": "auto",
        "ocr_mode": "off",
        "table_mode": "fast",
        "normalize": "standard",
    }


def _execution_payload() -> dict[str, object]:
    return {
        "acceleration_policy": "cpu_only",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }


def test_job_spec_rejects_non_upload_source_kind() -> None:
    payload = _base_payload(source_format="md", output_format="pdf")
    source = payload["source"]
    assert isinstance(source, dict)
    source["kind"] = "remote"

    with pytest.raises(ValidationError, match="upload"):
        JobSpecV2.model_validate(payload)


def test_job_spec_rejects_unsupported_v2_route() -> None:
    payload = _base_payload(source_format="pdf", output_format="pdf")
    payload["pdf_options"] = _pdf_options_payload()
    payload["execution"] = _execution_payload()

    with pytest.raises(ValidationError, match="Unsupported v2 route: pdf -> pdf"):
        JobSpecV2.model_validate(payload)


def test_job_spec_requires_pdf_options_for_pdf_source() -> None:
    payload = _base_payload(source_format="pdf", output_format="docx")
    payload["execution"] = _execution_payload()

    with pytest.raises(ValidationError, match="pdf_options is required"):
        JobSpecV2.model_validate(payload)


def test_job_spec_requires_execution_for_pdf_source() -> None:
    payload = _base_payload(source_format="pdf", output_format="docx")
    payload["pdf_options"] = _pdf_options_payload()

    with pytest.raises(ValidationError, match="execution is required"):
        JobSpecV2.model_validate(payload)


def test_job_spec_rejects_css_filenames_for_docx_output() -> None:
    payload = _base_payload(source_format="md", output_format="docx")
    conversion = payload["conversion"]
    assert isinstance(conversion, dict)
    conversion["css_filenames"] = ["style.css"]

    with pytest.raises(ValidationError, match="css_filenames is only supported for PDF outputs"):
        JobSpecV2.model_validate(payload)


def test_job_spec_rejects_reference_docx_for_non_docx_output() -> None:
    payload = _base_payload(source_format="md", output_format="pdf")
    conversion = payload["conversion"]
    assert isinstance(conversion, dict)
    conversion["reference_docx_filename"] = "reference.docx"

    with pytest.raises(
        ValidationError, match="reference_docx_filename is only supported for DOCX outputs"
    ):
        JobSpecV2.model_validate(payload)


def test_job_spec_rejects_template_for_non_docx_output() -> None:
    payload = _base_payload(source_format="md", output_format="pdf")
    conversion = payload["conversion"]
    assert isinstance(conversion, dict)
    conversion["template"] = {"template_id": "academic-report", "version": "1.0.0"}

    with pytest.raises(ValidationError, match="template is only supported for DOCX outputs"):
        JobSpecV2.model_validate(payload)


def test_job_spec_rejects_template_with_reference_docx_filename_together() -> None:
    payload = _base_payload(source_format="md", output_format="docx")
    conversion = payload["conversion"]
    assert isinstance(conversion, dict)
    conversion["template"] = {"template_id": "academic-report", "version": "1.0.0"}
    conversion["reference_docx_filename"] = "reference.docx"

    with pytest.raises(
        ValidationError,
        match="reference_docx_filename and template cannot both be provided for DOCX outputs",
    ):
        JobSpecV2.model_validate(payload)


def test_job_spec_rejects_css_filenames_for_md_output() -> None:
    payload = _base_payload(source_format="pdf", output_format="md")
    payload["pdf_options"] = _pdf_options_payload()
    payload["execution"] = _execution_payload()
    conversion = payload["conversion"]
    assert isinstance(conversion, dict)
    conversion["css_filenames"] = ["style.css"]

    with pytest.raises(ValidationError, match="css_filenames is only supported for PDF outputs"):
        JobSpecV2.model_validate(payload)


def test_job_spec_accepts_pdf_to_md_route() -> None:
    payload = _base_payload(source_format="pdf", output_format="md")
    payload["pdf_options"] = _pdf_options_payload()
    payload["execution"] = _execution_payload()

    spec = JobSpecV2.model_validate(payload)
    assert spec.source.format.value == "pdf"
    assert spec.conversion.output_format.value == "md"


def test_job_spec_accepts_docx_to_md_route() -> None:
    payload = _base_payload(source_format="docx", output_format="md")

    spec = JobSpecV2.model_validate(payload)
    assert spec.source.format.value == "docx"
    assert spec.conversion.output_format.value == "md"


def test_job_spec_accepts_docx_template_selector_for_docx_output() -> None:
    payload = _base_payload(source_format="md", output_format="docx")
    conversion = payload["conversion"]
    assert isinstance(conversion, dict)
    conversion["template"] = {"template_id": "academic-report", "version": "1.0.0"}

    spec = JobSpecV2.model_validate(payload)
    assert spec.conversion.output_format.value == "docx"
    assert spec.conversion.template is not None
    assert spec.conversion.template.template_id == "academic-report"
    assert spec.conversion.template.version == "1.0.0"
