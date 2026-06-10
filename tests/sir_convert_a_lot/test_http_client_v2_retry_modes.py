"""HTTP client v2 retry mode tests.

Purpose:
    Validate user-facing retry behavior for v2 idempotency replays without changing
    server-side idempotency semantics.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_client_v2.SirConvertALotClientV2`.
    - Uses `httpx.MockTransport` to simulate API responses deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import SirConvertALotClientV2
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import ClientErrorV2


def _job_payload(*, job_id: str, status: JobStatus) -> dict[str, object]:
    return {
        "api_version": "v2",
        "job": {
            "job_id": job_id,
            "status": status.value,
        },
    }


def test_convert_upload_to_artifact_auto_reruns_terminal_failed_idempotent_replay(
    tmp_path: Path,
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\n% stable\n%%EOF\n")
    job_spec: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "paper.pdf", "format": "pdf"},
        "conversion": {"output_format": "docx"},
        "pdf_options": {},
        "execution": None,
        "retention": {"pin": False},
    }

    calls: list[tuple[str, str]] = []
    post_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal post_calls
        calls.append((request.method, request.url.path))

        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            post_calls += 1
            if post_calls == 2:
                return httpx.Response(
                    200,
                    json=_job_payload(job_id="job_new", status=JobStatus.SUCCEEDED),
                )
            # First call: idempotent replay of a terminal failure.
            return httpx.Response(
                200,
                headers={"X-Idempotent-Replay": "true"},
                json=_job_payload(job_id="job_old", status=JobStatus.FAILED),
            )

        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_new/artifact":
            return httpx.Response(200, content=b"docx-bytes")

        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_new/result":
            return httpx.Response(
                200,
                json={
                    "api_version": "v2",
                    "job_id": "job_new",
                    "status": "succeeded",
                    "result": {
                        "artifact": {
                            "filename": "output.docx",
                            "format": "docx",
                            "size_bytes": 10,
                            "sha256": "abc",
                            "content_type": (
                                "application/vnd.openxmlformats-officedocument"
                                ".wordprocessingml.document"
                            ),
                        },
                        "conversion_metadata": {
                            "pipeline_used": "pdf_to_docx_v2",
                            "options_fingerprint": "sha256:test",
                            "formula_authority": {
                                "action": "fallback",
                                "source_evidence_state": "partial_or_unusable",
                                "reason": "formula_vlm_runtime_unavailable",
                            },
                        },
                        "warnings": [],
                    },
                },
            )

        if request.method == "GET" and request.url.path.startswith("/v2/convert/jobs/"):
            return httpx.Response(
                200, json=_job_payload(job_id="job_new", status=JobStatus.SUCCEEDED)
            )

        return httpx.Response(404, json={"api_version": "v2", "error": {"code": "not_found"}})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test", transport=transport)

    with SirConvertALotClientV2(
        base_url="http://test", api_key="k", http_client=http_client
    ) as client:
        outcome = client.convert_upload_to_artifact(
            source_path=source,
            job_spec=job_spec,
            idempotency_key="idemv2_base",
            wait_seconds=0,
            max_poll_seconds=1.0,
            retry_mode="auto",
        )

    assert outcome.job_id == "job_new"
    assert outcome.rerun_of_job_id == "job_old"
    assert outcome.artifact_bytes == b"docx-bytes"
    assert outcome.formula_authority == {
        "action": "fallback",
        "source_evidence_state": "partial_or_unusable",
        "reason": "formula_vlm_runtime_unavailable",
    }
    assert calls.count(("POST", "/v2/convert/jobs")) == 2


def test_convert_upload_to_artifact_replay_only_does_not_rerun(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\n% stable\n%%EOF\n")
    job_spec: dict[str, object] = json.loads(
        json.dumps(
            {
                "api_version": "v2",
                "source": {"kind": "upload", "filename": "paper.pdf", "format": "pdf"},
                "conversion": {"output_format": "docx"},
                "pdf_options": {},
                "execution": None,
                "retention": {"pin": False},
            }
        )
    )

    post_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal post_count
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            post_count += 1
            return httpx.Response(
                200,
                headers={"X-Idempotent-Replay": "true"},
                json=_job_payload(job_id="job_old", status=JobStatus.FAILED),
            )
        return httpx.Response(404, json={"api_version": "v2", "error": {"code": "not_found"}})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test", transport=transport)
    with SirConvertALotClientV2(
        base_url="http://test", api_key="k", http_client=http_client
    ) as client:
        with pytest.raises(ClientErrorV2) as excinfo:
            client.convert_upload_to_artifact(
                source_path=source,
                job_spec=job_spec,
                idempotency_key="idemv2_base",
                wait_seconds=0,
                max_poll_seconds=1.0,
                retry_mode="replay_only",
            )

    assert post_count == 1
    assert excinfo.value.code == "job_not_succeeded"
    assert excinfo.value.job_id == "job_old"


def test_convert_upload_to_artifact_reports_submitted_replay_to_progress_callback(
    tmp_path: Path,
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\n% stable\n%%EOF\n")
    job_spec: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "paper.pdf", "format": "pdf"},
        "conversion": {"output_format": "docx"},
        "pdf_options": {},
        "execution": None,
        "retention": {"pin": False},
    }
    events: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            return httpx.Response(
                200,
                headers={"X-Idempotent-Replay": "true"},
                json=_job_payload(job_id="job_existing", status=JobStatus.RUNNING),
            )

        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_existing":
            return httpx.Response(
                200,
                json=_job_payload(job_id="job_existing", status=JobStatus.SUCCEEDED),
            )

        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_existing/result":
            return httpx.Response(
                200,
                json={
                    "api_version": "v2",
                    "job_id": "job_existing",
                    "status": "succeeded",
                    "result": {
                        "artifact": {
                            "filename": "output.docx",
                            "format": "docx",
                            "size_bytes": 10,
                            "sha256": "abc",
                            "content_type": (
                                "application/vnd.openxmlformats-officedocument"
                                ".wordprocessingml.document"
                            ),
                        },
                        "conversion_metadata": {
                            "pipeline_used": "pdf_to_docx_v2",
                            "options_fingerprint": "sha256:test",
                            "formula_authority": {},
                        },
                        "warnings": [],
                    },
                },
            )

        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_existing/artifact":
            return httpx.Response(200, content=b"docx-bytes")

        return httpx.Response(404, json={"api_version": "v2", "error": {"code": "not_found"}})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test", transport=transport)

    with SirConvertALotClientV2(
        base_url="http://test", api_key="k", http_client=http_client
    ) as client:
        outcome = client.convert_upload_to_artifact(
            source_path=source,
            job_spec=job_spec,
            idempotency_key="idemv2_base",
            wait_seconds=0,
            max_poll_seconds=1.0,
            retry_mode="auto",
            progress_callback=events.append,
        )

    assert outcome.job_id == "job_existing"
    assert events[0] == {
        "job": {
            "job_id": "job_existing",
            "status": "running",
            "idempotent_replay": True,
        }
    }
