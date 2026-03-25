"""Contract tests for v2 cancel-with-save and resume-from-checkpoint (PDF routes).

Purpose:
    Lock ADR-0005 semantics for:
      - cancel-with-save stopping further chunk processing, and
      - resume creating a new job id that continues from persisted checkpoints.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_api.create_app`.
    - Exercises checkpointed PDF execution in `infrastructure.v2_pdf_checkpointed_executor`.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import JobStatus, TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.test_api_contract_v2 import (
    _job_spec_v2,
    _post_create,
    _wait_for_terminal,
)


def _build_pdf_bytes(*, pages: int) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    try:
        for index in range(pages):
            page = doc.new_page()
            if page is None:
                raise RuntimeError("PyMuPDF returned no page for new_page()")
            page.insert_text((72, 72), f"page {index + 1}", fontsize=12)
        return bytes(doc.tobytes())
    finally:
        doc.close()


def test_cancel_with_save_and_resume_from_checkpoint_produces_deterministic_final_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import v2_pdf_checkpointed_executor

    execute_calls: list[str] = []

    def _stub_execute_job_conversion(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
        ocr_engine=None,
        ocr_languages=(),
        ocr_use_gpu=None,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del (
            spec,
            source_filename,
            gpu_available,
            gpu_runtime_probe,
            docling_backend,
            pymupdf_backend,
            ocr_engine,
            ocr_languages,
            ocr_use_gpu,
        )
        import pymupdf

        chunk_doc = pymupdf.open(stream=source_bytes, filetype="pdf")
        try:
            texts: list[str] = []
            for page_index in range(chunk_doc.page_count):
                page = chunk_doc.load_page(page_index)
                if page is None:
                    raise RuntimeError("PyMuPDF returned no page for load_page().")
                texts.append(page.get_text("text"))
            digest = hashlib.sha256("".join(texts).encode("utf-8")).hexdigest()
        finally:
            chunk_doc.close()
        execute_calls.append(digest)
        time.sleep(0.2)
        return (
            f"# chunk {digest}\n",
            ConversionMetadata(
                backend_used="stubbed",
                acceleration_used="cpu",
                ocr_enabled=False,
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:stubbed",
            ),
            [],
            {},
        )

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor, "execute_job_conversion", _stub_execute_job_conversion
    )

    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            gpu_available=False,
            allow_cpu_only=True,
            allow_cpu_fallback=False,
            enable_supervisor=False,
            processing_delay_seconds=0.0,
        )
    )
    client = TestClient(app)

    pdf_bytes = _build_pdf_bytes(pages=11)
    spec = _job_spec_v2(
        filename="paper.pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    spec["pdf_options"] = {
        "backend_strategy": "auto",
        "ocr_mode": "off",
        "table_mode": "fast",
        "normalize": "standard",
    }
    spec["execution"] = {
        "acceleration_policy": "cpu_only",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }

    baseline = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem_baseline",
        file_name="paper.pdf",
        file_bytes=pdf_bytes,
        spec=spec,
    )
    baseline_job_id = baseline.json()["job"]["job_id"]
    assert _wait_for_terminal(client, "secret-key", baseline_job_id) == JobStatus.SUCCEEDED
    baseline_artifact = client.get(
        f"/v2/convert/jobs/{baseline_job_id}/artifact",
        headers={"X-API-Key": "secret-key"},
    )
    assert baseline_artifact.status_code == 200
    baseline_bytes = baseline_artifact.content

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem_cancel_resume",
        file_name="paper.pdf",
        file_bytes=pdf_bytes,
        spec=spec,
    )
    job_id = create.json()["job"]["job_id"]

    for _ in range(100):
        status = client.get(
            f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": "secret-key"}
        ).json()["job"]["status"]
        if status == JobStatus.RUNNING.value:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Job never reached running status.")

    checkpoint = None
    for _ in range(200):
        response = client.get(
            f"/v2/convert/jobs/{job_id}/checkpoint", headers={"X-API-Key": "secret-key"}
        )
        if response.status_code == 200:
            candidate = response.json()
            if isinstance(candidate, dict) and int(candidate.get("processed_pages", 0)) > 0:
                checkpoint = candidate
                break
        time.sleep(0.01)
    assert checkpoint is not None
    assert checkpoint["processed_pages"] > 0

    cancel = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key"},
    )
    assert cancel.status_code in {200, 202}

    partial = None
    for _ in range(200):
        response = client.get(
            f"/v2/convert/jobs/{job_id}/artifact/partial", headers={"X-API-Key": "secret-key"}
        )
        if response.status_code == 200:
            partial = response.text
            break
        time.sleep(0.01)
    assert partial is not None
    assert "sir-convert-a-lot:partial" in partial

    resume = client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem_resume_1"},
    )
    assert resume.status_code in {200, 202}
    resumed_job_id = resume.json()["job"]["job_id"]
    assert resumed_job_id != job_id

    assert _wait_for_terminal(client, "secret-key", resumed_job_id) == JobStatus.SUCCEEDED
    resumed_artifact = client.get(
        f"/v2/convert/jobs/{resumed_job_id}/artifact",
        headers={"X-API-Key": "secret-key"},
    )
    assert resumed_artifact.status_code == 200
    assert resumed_artifact.content == baseline_bytes


def test_resume_idempotency_replay_survives_public_key_rotation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import v2_pdf_checkpointed_executor

    def _stub_execute_job_conversion(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
        ocr_engine=None,
        ocr_languages=(),
        ocr_use_gpu=None,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del (
            spec,
            source_filename,
            gpu_available,
            gpu_runtime_probe,
            docling_backend,
            pymupdf_backend,
            ocr_engine,
            ocr_languages,
            ocr_use_gpu,
        )
        time.sleep(0.2)
        return (
            "# chunk\n",
            ConversionMetadata(
                backend_used="stubbed",
                acceleration_used="cpu",
                ocr_enabled=False,
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:stubbed",
            ),
            [],
            {},
        )

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor, "execute_job_conversion", _stub_execute_job_conversion
    )

    base_config = ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / "service_data_rotation_resume",
        gpu_available=False,
        allow_cpu_only=True,
        allow_cpu_fallback=False,
        enable_supervisor=False,
        processing_delay_seconds=0.0,
    )
    client = TestClient(create_app(base_config))

    pdf_bytes = _build_pdf_bytes(pages=11)
    spec = _job_spec_v2(
        filename="paper.pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    spec["pdf_options"] = {
        "backend_strategy": "auto",
        "ocr_mode": "off",
        "table_mode": "fast",
        "normalize": "standard",
    }
    spec["execution"] = {
        "acceleration_policy": "cpu_only",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem_resume_rotation_source",
        file_name="paper.pdf",
        file_bytes=pdf_bytes,
        spec=spec,
    )
    job_id = create.json()["job"]["job_id"]

    for _ in range(100):
        status = client.get(
            f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": "secret-key"}
        ).json()["job"]["status"]
        if status == JobStatus.RUNNING.value:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Job never reached running status.")

    for _ in range(200):
        response = client.get(
            f"/v2/convert/jobs/{job_id}/checkpoint", headers={"X-API-Key": "secret-key"}
        )
        if response.status_code == 200 and int(response.json().get("processed_pages", 0)) > 0:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Checkpoint never became available before cancel.")

    cancel = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key"},
    )
    assert cancel.status_code in {200, 202}

    first_resume = client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem_resume_rotation"},
    )
    assert first_resume.status_code in {200, 202}
    resumed_job_id = first_resume.json()["job"]["job_id"]

    rotated_client = TestClient(
        create_app(
            ServiceConfig(
                api_key="rotated-public-key",
                data_root=base_config.data_root,
                gpu_available=False,
                allow_cpu_only=True,
                allow_cpu_fallback=False,
                enable_supervisor=False,
                processing_delay_seconds=0.0,
            )
        )
    )
    replay_resume = rotated_client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={
            "X-API-Key": "rotated-public-key",
            "Idempotency-Key": "idem_resume_rotation",
        },
    )

    assert replay_resume.status_code in {200, 202}
    assert replay_resume.headers["X-Idempotent-Replay"] == "true"
    assert replay_resume.json()["job"]["job_id"] == resumed_job_id


def test_resume_idempotency_replay_survives_internal_key_rotation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.sir_convert_a_lot.infrastructure import v2_pdf_checkpointed_executor

    def _stub_execute_job_conversion(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
        ocr_engine=None,
        ocr_languages=(),
        ocr_use_gpu=None,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del (
            spec,
            source_filename,
            source_bytes,
            gpu_available,
            gpu_runtime_probe,
            docling_backend,
            pymupdf_backend,
            ocr_engine,
            ocr_languages,
            ocr_use_gpu,
        )
        time.sleep(0.2)
        return (
            "# chunk\n",
            ConversionMetadata(
                backend_used="stubbed",
                acceleration_used="cpu",
                ocr_enabled=False,
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:stubbed",
            ),
            [],
            {},
        )

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor, "execute_job_conversion", _stub_execute_job_conversion
    )

    base_config = ServiceConfig(
        api_key="secret-key",
        internal_api_key="internal-secret-key",
        data_root=tmp_path / "service_data_internal_rotation_resume",
        gpu_available=False,
        allow_cpu_only=True,
        allow_cpu_fallback=False,
        enable_supervisor=False,
        processing_delay_seconds=0.0,
    )
    client = TestClient(create_app(base_config))

    pdf_bytes = _build_pdf_bytes(pages=11)
    spec = _job_spec_v2(
        filename="paper.pdf",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    spec["pdf_options"] = {
        "backend_strategy": "auto",
        "ocr_mode": "off",
        "table_mode": "fast",
        "normalize": "standard",
    }
    spec["execution"] = {
        "acceleration_policy": "cpu_only",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }

    create = _post_create(
        client,
        api_key="internal-secret-key",
        idempotency_key="idem_internal_resume_rotation_source",
        file_name="paper.pdf",
        file_bytes=pdf_bytes,
        spec=spec,
    )
    job_id = create.json()["job"]["job_id"]

    for _ in range(100):
        status = client.get(
            f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": "internal-secret-key"}
        ).json()["job"]["status"]
        if status == JobStatus.RUNNING.value:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Job never reached running status.")

    for _ in range(200):
        response = client.get(
            f"/v2/convert/jobs/{job_id}/checkpoint",
            headers={"X-API-Key": "internal-secret-key"},
        )
        if response.status_code == 200 and int(response.json().get("processed_pages", 0)) > 0:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Checkpoint never became available before cancel.")

    cancel = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "internal-secret-key"},
    )
    assert cancel.status_code in {200, 202}

    first_resume = client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={
            "X-API-Key": "internal-secret-key",
            "Idempotency-Key": "idem_internal_resume_rotation",
        },
    )
    assert first_resume.status_code in {200, 202}
    resumed_job_id = first_resume.json()["job"]["job_id"]

    rotated_client = TestClient(
        create_app(
            ServiceConfig(
                api_key="secret-key",
                internal_api_key="rotated-internal-key",
                data_root=base_config.data_root,
                gpu_available=False,
                allow_cpu_only=True,
                allow_cpu_fallback=False,
                enable_supervisor=False,
                processing_delay_seconds=0.0,
            )
        )
    )
    replay_resume = rotated_client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={
            "X-API-Key": "rotated-internal-key",
            "Idempotency-Key": "idem_internal_resume_rotation",
        },
    )

    assert replay_resume.status_code in {200, 202}
    assert replay_resume.headers["X-Idempotent-Replay"] == "true"
    assert replay_resume.json()["job"]["job_id"] == resumed_job_id
