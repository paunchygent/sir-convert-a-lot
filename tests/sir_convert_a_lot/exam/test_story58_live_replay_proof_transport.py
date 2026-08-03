"""Transport tests for Story 58 live replay proof requests.

Purpose:
    Prove the Story 58 proof runner sends multipart Service API requests in
    the same shape accepted by the live create-job route.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.story58_live_replay_proof_transport`.
    - Complements proof-summary tests by guarding the real multipart boundary
      used for Dev/Prod Service API evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_transport import (
    execute_manifest_request,
)


def test_multipart_create_job_sends_job_spec_as_text_form_part(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Story 58\n", encoding="utf-8")
    job_spec_path = tmp_path / "job-spec.json"
    job_spec_path.write_text(
        json.dumps(
            {
                "api_version": "v2",
                "source": {"kind": "upload", "filename": "note.md", "format": "md"},
                "conversion": {"output_format": "pdf"},
                "retention": {"pin": False},
            }
        ),
        encoding="utf-8",
    )
    seen_path: str | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_path
        seen_path = request.url.path
        body = request.content.decode("utf-8", errors="replace")
        file_marker = 'name="file"; filename="note.md"'
        job_spec_marker = 'name="job_spec"'
        job_spec_part = body[body.find(job_spec_marker) : body.find(job_spec_marker) + 160]
        if (
            request.headers.get("X-API-Key") != "secret-key"
            or file_marker not in body
            or job_spec_marker not in body
            or body.find(file_marker) > body.find(job_spec_marker)
            or "filename=" in job_spec_part
            or "Content-Type:" in job_spec_part
        ):
            return httpx.Response(422, json={"error": {"code": "validation_error"}})
        return httpx.Response(200, json={"accepted_job_spec": True})

    client = httpx.Client(
        base_url="http://proof-service.test",
        transport=httpx.MockTransport(handler),
        timeout=30.0,
    )

    status_code, payload = execute_manifest_request(
        client=client,
        request_spec={
            "method": "POST",
            "path": "/v2/convert/jobs",
            "multipart": {
                "file_path": "note.md",
                "job_spec_file": "job-spec.json",
                "content_type": "text/markdown",
            },
        },
        manifest_root=tmp_path,
        api_key="secret-key",
        correlation_id="corr_story58_transport",
    )

    assert status_code == 200
    assert payload["accepted_job_spec"] is True
    assert seen_path == "/v2/convert/jobs"
