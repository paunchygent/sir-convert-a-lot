"""Contract tests for v2 PDF partial artifact and checkpoint endpoints.

Purpose:
    Lock the ADR-0005 contract for:
      - `GET /v2/convert/jobs/{job_id}/artifact/partial`
      - `GET /v2/convert/jobs/{job_id}/checkpoint`
    ensuring the endpoints behave predictably for queued/running/canceled/terminal jobs.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_api.create_app`.
    - Uses runtime monkeypatching to simulate incremental checkpoint persistence.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.test_api_contract_v2 import (
    _job_spec_v2,
    _post_create,
    _wait_for_terminal,
)


def test_pdf_partial_and_checkpoint_endpoints_transition_202_to_200(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
    from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import dt_to_rfc3339, utc_now
    from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
        PdfChunkRecordV2,
        assemble_partial_markdown_artifact,
        build_initial_pdf_checkpoint,
        persist_pdf_checkpoint,
        persist_pdf_chunk_markdown,
    )

    allow_write = threading.Event()
    wrote_partial = threading.Event()
    allow_finish = threading.Event()

    def _executor(**kwargs) -> V2ExecutionResult:
        job = kwargs["job"]
        allow_write.wait(timeout=3)

        checkpoint = build_initial_pdf_checkpoint(
            job_id=job.job_id,
            chunk_size_pages=10,
            total_pages=2,
        )
        relpath, size_bytes, sha_hex = persist_pdf_chunk_markdown(
            upload_path=job.upload_path,
            chunk_index=0,
            start_page=1,
            end_page=1,
            markdown_content="# Page 1\n\nBody\n",
        )
        checkpoint.chunks.append(
            PdfChunkRecordV2(
                chunk_index=0,
                start_page=1,
                end_page=1,
                status="succeeded",
                started_at=dt_to_rfc3339(utc_now()),
                completed_at=dt_to_rfc3339(utc_now()),
                artifact_relpath=relpath,
                sha256=f"sha256:{sha_hex}",
                size_bytes=size_bytes,
                phase_timings_ms={"chunk_elapsed_ms": 5},
            )
        )
        checkpoint.processed_pages = 1
        persist_pdf_checkpoint(upload_path=job.upload_path, checkpoint=checkpoint)
        assemble_partial_markdown_artifact(upload_path=job.upload_path, checkpoint=checkpoint)
        wrote_partial.set()

        allow_finish.wait(timeout=3)
        return V2ExecutionResult(
            artifact_bytes=b"# Final markdown\n",
            pipeline_used="pdf_to_md_v2",
            backend_used="docling",
            acceleration_used="cuda",
            warnings=[],
            phase_timings_ms={"backend_convert_ms": 1},
            options_fingerprint="contract_test_partial_checkpoint",
        )

    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _executor)

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    spec = _job_spec_v2(
        filename="paper.pdf",
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

    create_response = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-pdf-md-partial",
        file_name="paper.pdf",
        file_bytes=b"%PDF-1.4\n% fake\n%%EOF\n",
        spec=spec,
    )
    assert create_response.status_code in {200, 202}
    job_id = create_response.json()["job"]["job_id"]

    # Before partial/checkpoint exists, endpoints return 202.
    for _ in range(50):
        status = client.get(
            f"/v2/convert/jobs/{job_id}",
            headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_status_pre"},
        ).json()["job"]["status"]
        if status == JobStatus.RUNNING.value:
            break
        time.sleep(0.01)

    partial_pre = client.get(
        f"/v2/convert/jobs/{job_id}/artifact/partial",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_partial_pre"},
    )
    assert partial_pre.status_code == 202

    checkpoint_pre = client.get(
        f"/v2/convert/jobs/{job_id}/checkpoint",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_checkpoint_pre"},
    )
    assert checkpoint_pre.status_code == 202

    # Allow the executor to persist checkpoint + partial while the job is still running.
    allow_write.set()
    assert wrote_partial.wait(timeout=3)

    partial_post = client.get(
        f"/v2/convert/jobs/{job_id}/artifact/partial",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_partial_post"},
    )
    assert partial_post.status_code == 200
    assert partial_post.headers.get("content-type", "").startswith("text/markdown")
    assert "sir-convert-a-lot:partial" in partial_post.text

    checkpoint_post = client.get(
        f"/v2/convert/jobs/{job_id}/checkpoint",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_checkpoint_post"},
    )
    assert checkpoint_post.status_code == 200
    payload = checkpoint_post.json()
    assert payload["job_id"] == job_id
    assert payload["processed_pages"] == 1

    allow_finish.set()
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    # After success, partial endpoint is rejected in favor of terminal artifact endpoint.
    partial_after = client.get(
        f"/v2/convert/jobs/{job_id}/artifact/partial",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_partial_after"},
    )
    assert partial_after.status_code == 409
