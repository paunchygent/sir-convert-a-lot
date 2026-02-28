"""Template selector edge-case tests for v2 create-job routes.

Purpose:
    Verify deterministic validation behavior for template selection in v2 job
    creation requests.

Relationships:
    - Exercises template validation through `http_routes_jobs_v2` create-job.
    - Reuses shared typed helpers from
      `http_routes_jobs_v2_edge_cases_test_support`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from tests.sir_convert_a_lot.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    job_spec_v2,
    post_create,
)


def _md_to_docx_template_spec(
    *,
    filename: str,
    template_id: str,
    version: str | None,
) -> dict[str, object]:
    spec = job_spec_v2(
        filename=filename,
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
    )
    conversion = spec["conversion"]
    assert isinstance(conversion, dict)
    conversion["template"] = {
        "template_id": template_id,
        "version": version,
    }
    return spec


def test_create_job_rejects_unknown_template_id_for_docx_output(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="note.md",
        file_bytes=b"# Hello\n",
        spec=_md_to_docx_template_spec(
            filename="note.md",
            template_id="unknown-template",
            version="1.0.0",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.template.template_id",
        "template_id": "unknown-template",
    }


def test_create_job_rejects_unknown_template_version_for_docx_output(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="note.md",
        file_bytes=b"# Hello\n",
        spec=_md_to_docx_template_spec(
            filename="note.md",
            template_id="academic-report",
            version="9.9.9",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "field": "conversion.template.version",
        "template_id": "academic-report",
        "version": "9.9.9",
    }
