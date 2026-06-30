"""V2 create-job route helper and edge-case tests.

Purpose:
    Cover targeted branch-level behavior for v2 creation routes where error
    handling and replay semantics are easy to miss in broader contract tests.

Relationships:
    - Tests `scripts.sir_convert_a_lot.interfaces.http_routes_jobs_v2`.
    - Reuses typed request helpers from
      `http_routes_jobs_v2_edge_cases_test_support`.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces import http_routes_job_artifacts_v2, http_routes_jobs_v2
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    infer_source_format_from_filename_v2,
)
from tests.sir_convert_a_lot.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    disable_run_job_async,
    job_spec_v2,
    md_to_pdf_spec,
    post_create,
)


def _pdf_to_md_spec(filename: str) -> dict[str, object]:
    spec = job_spec_v2(
        filename=filename,
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    spec["pdf_options"] = {
        "backend_strategy": "auto",
        "ocr_mode": "auto",
        "table_mode": "accurate",
        "normalize": "strict",
    }
    spec["execution"] = {
        "acceleration_policy": "gpu_required",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }
    return spec


def _html_to_md_spec(filename: str) -> dict[str, object]:
    return job_spec_v2(
        filename=filename,
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.MD,
    )


def _html_to_pdf_spec(filename: str) -> dict[str, object]:
    return job_spec_v2(
        filename=filename,
        source_format=SourceFormatV2.HTML,
        output_format=OutputFormatV2.PDF,
    )


def test_create_job_can_defer_execution_to_supervisor_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected_run_job_async(self: ServiceRuntimeV2, job_id: str) -> None:
        del self, job_id
        raise AssertionError("API admission container must not execute submitted jobs")

    monkeypatch.setattr(ServiceRuntimeV2, "run_job_async", _unexpected_run_job_async)
    client, _app = build_client(tmp_path, run_jobs_on_submit=False)

    response = post_create(client, idempotency_key="idem-defer-to-worker")

    assert response.status_code == 202
    assert response.json()["job"]["status"] == JobStatus.QUEUED.value


def test_infer_format_from_filename_returns_none_for_unsupported_suffix() -> None:
    assert infer_source_format_from_filename_v2("archive.txt") is None
    assert infer_source_format_from_filename_v2("README") is None


def test_infer_format_from_filename_returns_expected_supported_formats() -> None:
    assert infer_source_format_from_filename_v2("paper.pdf") == SourceFormatV2.PDF
    assert infer_source_format_from_filename_v2("note.md") == SourceFormatV2.MD
    assert infer_source_format_from_filename_v2("index.htm") == SourceFormatV2.HTML
    assert infer_source_format_from_filename_v2("template.docx") == SourceFormatV2.DOCX


def test_content_type_for_output_raises_for_unsupported_enum_simulation() -> None:
    helper = getattr(http_routes_job_artifacts_v2, "_content_type_for_output")
    with pytest.raises(AssertionError, match="Unsupported output_format"):
        helper("unsupported")


def test_content_type_for_output_returns_expected_supported_values() -> None:
    helper = getattr(http_routes_job_artifacts_v2, "_content_type_for_output")
    assert helper(OutputFormatV2.MD) == "text/markdown"
    assert helper(OutputFormatV2.PDF) == "application/pdf"
    assert (
        helper(OutputFormatV2.DOCX)
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_create_job_rejects_missing_idempotency_key(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(client, idempotency_key=None)

    assert response.status_code == 400
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "idempotency_key_missing"


def test_create_job_rejects_blank_upload_filename(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(client, file_name="   ", spec=md_to_pdf_spec("note.md"))

    assert response.status_code == 400
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {"field": "file.filename"}


def test_create_job_rejects_unsupported_upload_extension(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="note.txt",
        spec=md_to_pdf_spec("note.txt"),
    )

    assert response.status_code == 415
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "unsupported_media_type"
    assert payload["error"]["details"] == {"filename": "note.txt"}


def test_create_job_rejects_empty_upload_bytes(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(client, file_bytes=b"")

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "input_unreadable"


def test_create_job_rejects_payload_too_large(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path, max_upload_bytes=4)
    response = post_create(client, file_bytes=b"12345")

    assert response.status_code == 413
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "payload_too_large"


def test_create_job_rejects_resources_zip_too_large(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path, max_upload_bytes=4)
    response = post_create(
        client,
        file_bytes=b"1234",
        resources_file=("resources.zip", b"12345", "application/zip"),
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "payload_too_large"


def test_create_job_rejects_reference_docx_missing_filename(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        reference_docx_file=(
            "   ",
            b"PK\x03\x04fake-docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {"field": "reference_docx.filename"}


def test_create_job_rejects_reference_docx_wrong_extension(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        reference_docx_file=("reference.txt", b"not-docx", "text/plain"),
    )

    assert response.status_code == 415
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "unsupported_media_type"


def test_create_job_rejects_reference_docx_too_large(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path, max_upload_bytes=4)
    response = post_create(
        client,
        reference_docx_file=(
            "reference.docx",
            b"12345",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "payload_too_large"


def test_create_job_rejects_resources_upload_for_md_output(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="paper.pdf",
        file_bytes=b"%PDF-1.4\n% fake\n%%EOF\n",
        spec=_pdf_to_md_spec("paper.pdf"),
        resources_file=("resources.zip", b"PK\x03\x04small-zip", "application/zip"),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {"field": "resources", "output_format": "md"}


def test_create_job_allows_resources_upload_for_html_to_md(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="index.html",
        file_bytes=b"<html><body><img src='assets/a.png'></body></html>",
        spec=_html_to_md_spec("index.html"),
        resources_file=("resources.zip", b"PK\x03\x04small-zip", "application/zip"),
    )

    assert response.status_code in {200, 202}
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["job"]["source_format"] == "html"
    assert payload["job"]["output_format"] == "md"


def test_create_job_accepts_author_owned_page_css_mode_for_html_to_pdf(
    tmp_path: Path,
) -> None:
    client, _ = build_client(tmp_path)
    spec = _html_to_pdf_spec("index.html")
    conversion = spec["conversion"]
    assert isinstance(conversion, dict)
    conversion["css_filenames"] = ["print.css"]
    conversion["page_css_mode"] = "author_owned"

    response = post_create(
        client,
        file_name="index.html",
        file_bytes=b"<html><body>Hello</body></html>",
        spec=spec,
        resources_file=("resources.zip", b"PK\x03\x04small-zip", "application/zip"),
    )

    assert response.status_code in {200, 202}
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["job"]["source_format"] == "html"
    assert payload["job"]["output_format"] == "pdf"


def test_create_job_idempotency_replay_survives_public_key_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    first_response = post_create(
        client,
        idempotency_key="idem-rotation-replay",
    )
    assert first_response.status_code in {200, 202}
    first_job_id = first_response.json()["job"]["job_id"]

    rotated_app = create_app(
        ServiceConfig(
            api_key="rotated-public-key",
            data_root=app.state.runtime_v2.config.data_root,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    rotated_client = TestClient(rotated_app)
    replay_response = post_create(
        rotated_client,
        idempotency_key="idem-rotation-replay",
        api_key="rotated-public-key",
    )

    assert replay_response.status_code in {200, 202}
    assert replay_response.headers["X-Idempotent-Replay"] == "true"
    assert replay_response.json()["job"]["job_id"] == first_job_id


def test_create_job_rejects_author_owned_page_css_mode_with_pdf_layout(
    tmp_path: Path,
) -> None:
    client, _ = build_client(tmp_path)
    spec = _html_to_pdf_spec("index.html")
    conversion = spec["conversion"]
    assert isinstance(conversion, dict)
    conversion["page_css_mode"] = "author_owned"
    conversion["pdf_layout"] = {
        "paper_size": "a4",
        "orientation": "portrait",
        "margins_mm": 12,
    }

    response = post_create(
        client,
        file_name="index.html",
        file_bytes=b"<html><body>Hello</body></html>",
        spec=spec,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    errors = payload["error"]["details"]["errors"]
    assert isinstance(errors, list)
    assert any(
        error.get("msg")
        == "Value error, page_css_mode='author_owned' cannot be combined with pdf_layout"
        for error in errors
    )


def test_create_job_rejects_reference_docx_upload_for_md_output(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="paper.pdf",
        file_bytes=b"%PDF-1.4\n% fake\n%%EOF\n",
        spec=_pdf_to_md_spec("paper.pdf"),
        reference_docx_file=(
            "reference.docx",
            b"PK\x03\x04small-docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {"field": "reference_docx", "output_format": "md"}


def test_create_job_accepts_small_resources_and_reference_docx(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)

    spec = job_spec_v2(
        filename="note.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.DOCX,
    )
    response = post_create(
        client,
        file_name="note.md",
        file_bytes=b"# Hello\n",
        spec=spec,
        resources_file=("resources.zip", b"PK\x03\x04small-zip", "application/zip"),
        reference_docx_file=(
            "reference.docx",
            b"PK\x03\x04small-docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    assert response.status_code in {200, 202}
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["job"]["source_format"] == "md"
    assert payload["job"]["output_format"] == "docx"


def test_create_job_rejects_invalid_json_job_spec(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(client, spec='{"api_version":"v2",')

    assert response.status_code == 400
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"].startswith("Invalid job_spec JSON:")


def test_create_job_rejects_non_object_job_spec_payload(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(client, spec=json.dumps(["not", "an", "object"]))

    assert response.status_code == 400
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "job_spec must decode into a JSON object."


def test_create_job_rejects_pydantic_validation_error(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    invalid_spec: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": "note.md", "format": "md"},
        "conversion": {
            "output_format": "txt",
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }
    response = post_create(client, spec=invalid_spec)

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"


def test_create_job_returns_404_when_job_missing_after_wait_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _CreatedJob:
        def __init__(self, job_id: str) -> None:
            self.job_id = job_id
            self.status = JobStatus.QUEUED
            self.failure_retryable = False

    class _QueuedJob:
        status = JobStatus.QUEUED

    disable_run_job_async(monkeypatch)
    call_count = {"value": 0}

    def _fake_create_job(self: ServiceRuntimeV2, **kwargs: object) -> _CreatedJob:
        del kwargs
        return _CreatedJob(job_id="jobv2_wait_missing")

    def _fake_get_job(self: ServiceRuntimeV2, job_id: str) -> _QueuedJob | None:
        del self, job_id
        call_count["value"] += 1
        if call_count["value"] == 1:
            return _QueuedJob()
        return None

    async def _fake_sleep(seconds: float) -> None:
        del seconds

    monkeypatch.setattr(ServiceRuntimeV2, "create_job", _fake_create_job)
    monkeypatch.setattr(ServiceRuntimeV2, "get_job", _fake_get_job)
    monkeypatch.setattr(http_routes_jobs_v2.asyncio, "sleep", _fake_sleep)

    client, _ = build_client(tmp_path)
    response = client.post(
        "/v2/convert/jobs?wait_seconds=1",
        headers={
            "X-API-Key": "secret-key",
            "Idempotency-Key": "idem-edge-wait-missing",
            "X-Correlation-ID": "corr_v2_wait_missing",
        },
        files={
            "file": ("note.md", b"# Hello\n", "text/markdown"),
            "job_spec": (None, json.dumps(md_to_pdf_spec("note.md"))),
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def test_create_job_rejects_job_spec_source_filename_mismatch(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="note.md",
        spec=job_spec_v2(
            filename="other.md",
            source_format=SourceFormatV2.MD,
            output_format=OutputFormatV2.PDF,
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "job_spec_filename": "other.md",
        "upload_filename": "note.md",
    }


def test_create_job_rejects_job_spec_source_format_mismatch(tmp_path: Path) -> None:
    client, _ = build_client(tmp_path)
    response = post_create(
        client,
        file_name="note.md",
        spec=job_spec_v2(
            filename="note.md",
            source_format=SourceFormatV2.HTML,
            output_format=OutputFormatV2.PDF,
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {
        "job_spec_format": "html",
        "upload_format": "md",
    }


def test_create_job_idempotency_same_key_different_fingerprint_returns_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, _ = build_client(tmp_path)

    first = post_create(
        client,
        idempotency_key="idem-edge-fingerprint-conflict",
        file_bytes=b"same-path-different-body-1",
    )
    second = post_create(
        client,
        idempotency_key="idem-edge-fingerprint-conflict",
        file_bytes=b"same-path-different-body-2",
    )

    assert first.status_code in {200, 202}
    assert second.status_code == 409
    payload = second.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_retryable_failed_idempotency_replay_admits_new_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    first = post_create(
        client,
        idempotency_key="idem-edge-retryable-failed",
        file_bytes=b"stable-retryable-failed-body",
    )
    assert first.status_code == 202
    failed_job_id = first.json()["job"]["job_id"]
    _mark_job_failed(app.state.runtime_v2, failed_job_id, retryable=True)

    replay = post_create(
        client,
        idempotency_key="idem-edge-retryable-failed",
        file_bytes=b"stable-retryable-failed-body",
    )

    assert replay.status_code == 202
    assert replay.headers["X-Idempotent-Replay"] == "false"
    payload = replay.json()
    new_job_id = payload["job"]["job_id"]
    assert new_job_id != failed_job_id
    assert payload["job"]["status"] == JobStatus.QUEUED.value
    assert payload["idempotency"] == {
        "state": "service_reattempt",
        "idempotent_replay": False,
        "active_job_id": new_job_id,
        "attempt_count": 2,
        "current_attempt": {
            "job_id": new_job_id,
            "status": JobStatus.QUEUED.value,
            "failure_retryable": None,
        },
        "previous_attempts": [
            {
                "job_id": failed_job_id,
                "status": JobStatus.FAILED.value,
                "failure_retryable": True,
            }
        ],
        "replayed_job_id": None,
        "reattempt_of_job_id": failed_job_id,
        "reason": "retryable_failed_terminal",
    }


def test_non_retryable_failed_idempotency_replay_remains_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    first = post_create(
        client,
        idempotency_key="idem-edge-nonretryable-failed",
        file_bytes=b"stable-nonretryable-failed-body",
    )
    assert first.status_code == 202
    failed_job_id = first.json()["job"]["job_id"]
    _mark_job_failed(app.state.runtime_v2, failed_job_id, retryable=False)

    replay = post_create(
        client,
        idempotency_key="idem-edge-nonretryable-failed",
        file_bytes=b"stable-nonretryable-failed-body",
    )

    assert replay.status_code == 200
    assert replay.headers["X-Idempotent-Replay"] == "true"
    payload = replay.json()
    assert payload["job"]["job_id"] == failed_job_id
    assert payload["job"]["status"] == JobStatus.FAILED.value
    assert payload["idempotency"]["state"] == "strict_replay"
    assert payload["idempotency"]["current_attempt"] == {
        "job_id": failed_job_id,
        "status": JobStatus.FAILED.value,
        "failure_retryable": False,
    }


def test_active_succeeded_and_canceled_idempotency_replays_remain_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    active = post_create(
        client,
        idempotency_key="idem-edge-active-strict",
        file_bytes=b"stable-active-body",
    )
    assert active.status_code == 202
    active_job_id = active.json()["job"]["job_id"]
    active_replay = post_create(
        client,
        idempotency_key="idem-edge-active-strict",
        file_bytes=b"stable-active-body",
    )
    assert active_replay.status_code == 202
    assert active_replay.headers["X-Idempotent-Replay"] == "true"
    assert active_replay.json()["job"]["job_id"] == active_job_id
    assert active_replay.json()["idempotency"]["state"] == "strict_replay"

    succeeded = post_create(
        client,
        idempotency_key="idem-edge-succeeded-strict",
        file_bytes=b"stable-succeeded-body",
    )
    assert succeeded.status_code == 202
    succeeded_job_id = succeeded.json()["job"]["job_id"]
    _mark_job_succeeded(app.state.runtime_v2, succeeded_job_id)
    succeeded_replay = post_create(
        client,
        idempotency_key="idem-edge-succeeded-strict",
        file_bytes=b"stable-succeeded-body",
    )
    assert succeeded_replay.status_code == 200
    assert succeeded_replay.headers["X-Idempotent-Replay"] == "true"
    assert succeeded_replay.json()["job"]["job_id"] == succeeded_job_id
    assert succeeded_replay.json()["idempotency"]["state"] == "strict_replay"

    canceled = post_create(
        client,
        idempotency_key="idem-edge-canceled-strict",
        file_bytes=b"stable-canceled-body",
    )
    assert canceled.status_code == 202
    canceled_job_id = canceled.json()["job"]["job_id"]
    assert app.state.runtime_v2.cancel_job(canceled_job_id) == "accepted"
    canceled_replay = post_create(
        client,
        idempotency_key="idem-edge-canceled-strict",
        file_bytes=b"stable-canceled-body",
    )
    assert canceled_replay.status_code == 200
    assert canceled_replay.headers["X-Idempotent-Replay"] == "true"
    assert canceled_replay.json()["job"]["job_id"] == canceled_job_id
    assert canceled_replay.json()["job"]["status"] == JobStatus.CANCELED.value
    assert canceled_replay.json()["idempotency"]["state"] == "strict_replay"


def test_concurrent_retryable_failed_idempotency_replay_converges_to_one_new_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    first = post_create(
        client,
        idempotency_key="idem-edge-concurrent-retryable-failed",
        file_bytes=b"stable-concurrent-retryable-failed-body",
    )
    assert first.status_code == 202
    failed_job_id = first.json()["job"]["job_id"]
    _mark_job_failed(app.state.runtime_v2, failed_job_id, retryable=True)

    def _submit_replay() -> tuple[str, int]:
        response = post_create(
            client,
            idempotency_key="idem-edge-concurrent-retryable-failed",
            file_bytes=b"stable-concurrent-retryable-failed-body",
        )
        assert response.status_code == 202
        payload = response.json()
        assert isinstance(payload, dict)
        job_payload = payload.get("job")
        assert isinstance(job_payload, dict)
        job_id = job_payload.get("job_id")
        assert isinstance(job_id, str)
        idempotency_payload = payload.get("idempotency")
        assert isinstance(idempotency_payload, dict)
        attempt_count = idempotency_payload.get("attempt_count")
        assert isinstance(attempt_count, int)
        return job_id, attempt_count

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_result, second_result = executor.map(lambda _: _submit_replay(), range(2))

    first_job_id, first_attempt_count = first_result
    second_job_id, second_attempt_count = second_result
    assert first_job_id == second_job_id
    assert first_job_id != failed_job_id
    assert first_attempt_count == 2
    assert second_attempt_count == 2
    job_ids = app.state.runtime_v2.job_store.list_job_ids()
    assert sorted(job_ids) == sorted([failed_job_id, first_job_id])


def test_create_job_idempotency_existing_job_missing_returns_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    first = post_create(
        client,
        idempotency_key="idem-edge-missing-existing-job",
        file_bytes=b"stable-fingerprint-body",
    )
    assert first.status_code in {200, 202}
    created_job_id = first.json()["job"]["job_id"]

    runtime = app.state.runtime_v2
    original_get_job = runtime.get_job

    def _missing_created_job(job_id: str) -> object:
        if job_id == created_job_id:
            return None
        return original_get_job(job_id)

    monkeypatch.setattr(runtime, "get_job", _missing_created_job)

    replay = post_create(
        client,
        idempotency_key="idem-edge-missing-existing-job",
        file_bytes=b"stable-fingerprint-body",
    )

    assert replay.status_code == 404
    payload = replay.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "job_not_found"


def _mark_job_failed(runtime: ServiceRuntimeV2, job_id: str, *, retryable: bool) -> None:
    assert runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_failed(
        job_id,
        code="conversion_failed_for_test",
        message="Intentional test failure.",
        retryable=retryable,
        details={"source": "idempotency_test"},
    )


def _mark_job_succeeded(runtime: ServiceRuntimeV2, job_id: str) -> None:
    assert runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"%PDF-1.4\n% fake\n%%EOF\n",
        pipeline_used="md_to_pdf_v2",
        backend_used="test",
        acceleration_used=None,
        options_fingerprint="sha256:idempotency-test",
        warnings=[],
    )
