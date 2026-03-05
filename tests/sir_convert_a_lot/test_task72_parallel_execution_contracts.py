"""Task-72 parallel PDF execution contract and regression tests.

Purpose:
    Lock bounded parallel PDF chunk execution semantics, including determinism,
    checkpoint safety, cancel/resume behavior, and bounded-cardinality metrics.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpointed_executor`.
    - Exercises `scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2`.
    - Exercises v2 HTTP contracts via `scripts.sir_convert_a_lot.interfaces.http_api`.
"""

from __future__ import annotations

import re
import threading
import time
from _thread import LockType
from dataclasses import replace
from pathlib import Path
from typing import TypedDict, cast

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import JobStatus, TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_pdf_checkpointed_executor
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
)
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.test_api_contract_v2 import (
    _job_spec_v2,
    _post_create,
    _wait_for_terminal,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


class _ActiveCounterState(TypedDict):
    """Thread-safe active conversion counter used by concurrency tests."""

    lock: LockType
    active: int
    max_active: int


def _build_pdf_bytes(*, pages: int) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    try:
        for index in range(pages):
            page = doc.new_page()
            if page is None:
                raise RuntimeError("PyMuPDF returned no page for new_page().")
            page.insert_text((72, 72), f"page {index + 1}", fontsize=12)
        return bytes(doc.tobytes())
    finally:
        doc.close()


def _page_numbers_from_chunk(source_bytes: bytes) -> list[int]:
    import pymupdf

    doc = pymupdf.open(stream=source_bytes, filetype="pdf")
    try:
        page_numbers: list[int] = []
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            if page is None:
                raise RuntimeError("PyMuPDF returned no page for load_page().")
            text = page.get_text("text")
            match = re.search(r"page\s+(\d+)", text.lower())
            if match is None:
                raise AssertionError(f"Could not parse page number from chunk text: {text!r}")
            page_numbers.append(int(match.group(1)))
        return page_numbers
    finally:
        doc.close()


def _make_stub_conversion(
    *,
    delays_by_page: dict[int, float] | None = None,
    active_state: _ActiveCounterState | None = None,
):
    delays = delays_by_page or {}

    def _stub_execute_job_conversion(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del (
            spec,
            source_filename,
            gpu_available,
            gpu_runtime_probe,
            docling_backend,
            pymupdf_backend,
        )
        page_numbers = _page_numbers_from_chunk(source_bytes)
        delay_seconds = max(delays.get(page_number, 0.01) for page_number in page_numbers)

        if active_state is not None:
            lock = active_state["lock"]
            with lock:
                current_active = active_state["active"] + 1
                active_state["active"] = current_active
                active_state["max_active"] = max(active_state["max_active"], current_active)

        try:
            time.sleep(delay_seconds)
            markdown = "".join(f"# page {page_number}\n" for page_number in page_numbers)
            return (
                markdown,
                ConversionMetadata(
                    backend_used="stubbed",
                    acceleration_used="cpu",
                    ocr_enabled=False,
                    table_mode=TableMode.FAST,
                    options_fingerprint="sha256:task72-stubbed",
                ),
                [],
                {"ocr_layout_extract_ms": 8, "markdown_normalize_ms": 2},
            )
        finally:
            if active_state is not None:
                lock = active_state["lock"]
                with lock:
                    active_state["active"] = max(0, active_state["active"] - 1)

    return _stub_execute_job_conversion


def _pdf_md_spec(*, filename: str, pin: bool = False) -> dict[str, object]:
    spec = cast(
        dict[str, object],
        _job_spec_v2(
            filename=filename,
            source_format=SourceFormatV2.PDF,
            output_format=OutputFormatV2.MD,
        ),
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
    spec["retention"] = {"pin": pin}
    return spec


def _parallel_service_config(
    tmp_path: Path, *, data_dir: str, max_workers: int = 2
) -> ServiceConfig:
    return ServiceConfig(
        api_key="secret-key",
        data_root=tmp_path / data_dir,
        gpu_available=False,
        allow_cpu_only=True,
        allow_cpu_fallback=False,
        enable_supervisor=False,
        processing_delay_seconds=0.0,
        max_workers=max_workers,
        enable_parallel_pdf_chunks=True,
        max_chunk_workers=2,
        pdf_chunk_size_pages=1,
        gpu_stage_max_concurrency=1,
    )


def _wait_for_progress_pages(
    client: TestClient,
    *,
    job_id: str,
    minimum_pages: int,
    timeout_seconds: float = 8.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": "secret-key"})
        assert response.status_code == 200
        payload = response.json()
        progress = cast(dict[str, object], payload["job"]["progress"])
        processed_pages_raw = progress.get("processed_pages")
        processed_pages = int(processed_pages_raw) if isinstance(processed_pages_raw, int) else 0
        if processed_pages >= minimum_pages:
            return progress
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for expected processed pages.")


def test_parallel_out_of_order_chunk_completion_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.09, 2: 0.01, 3: 0.01}),
    )

    pdf_bytes = _build_pdf_bytes(pages=3)

    serial_job: StoredJobV2 = _build_job(
        tmp_path / "serial",
        source_filename="serial.pdf",
        source_bytes=pdf_bytes,
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    serial_config = replace(
        _service_config(tmp_path / "serial"),
        enable_parallel_pdf_chunks=False,
        max_chunk_workers=4,
        pdf_chunk_size_pages=1,
        gpu_stage_max_concurrency=4,
    )
    serial_result = execute_v2_job_conversion(
        job=serial_job,
        config=serial_config,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    parallel_job: StoredJobV2 = _build_job(
        tmp_path / "parallel",
        source_filename="parallel.pdf",
        source_bytes=pdf_bytes,
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    parallel_config = replace(
        _service_config(tmp_path / "parallel"),
        enable_parallel_pdf_chunks=True,
        max_chunk_workers=3,
        pdf_chunk_size_pages=1,
        gpu_stage_max_concurrency=3,
    )
    parallel_result = execute_v2_job_conversion(
        job=parallel_job,
        config=parallel_config,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert serial_result.artifact_bytes == parallel_result.artifact_bytes
    assert parallel_result.parallel_enabled is True
    assert parallel_result.max_chunk_workers == 3
    assert parallel_result.chunk_size_pages == 1
    assert parallel_result.scheduling_mode == "parallel_ordered_commit"


def test_parallel_progress_fields_monotonic_under_out_of_order_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.08, 2: 0.01, 3: 0.01, 4: 0.01}),
    )

    job: StoredJobV2 = _build_job(
        tmp_path,
        source_filename="progress.pdf",
        source_bytes=_build_pdf_bytes(pages=4),
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    config = replace(
        _service_config(tmp_path),
        enable_parallel_pdf_chunks=True,
        max_chunk_workers=2,
        pdf_chunk_size_pages=1,
        gpu_stage_max_concurrency=2,
    )

    progress_updates: list[tuple[int, int, float]] = []

    def _progress(update) -> None:
        progress_updates.append(
            (int(update.total_pages), int(update.processed_pages), float(update.percent_complete))
        )

    execute_v2_job_conversion(
        job=job,
        config=config,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
        progress_callback=_progress,
    )

    assert progress_updates
    previous_processed = -1
    for total_pages, processed_pages, percent_complete in progress_updates:
        assert total_pages == 4
        assert processed_pages >= previous_processed
        assert 0 <= processed_pages <= total_pages
        assert 0.0 <= percent_complete <= 100.0
        previous_processed = processed_pages
    assert progress_updates[-1][1] == 4


def test_parallel_multi_job_global_caps_apply_backpressure_without_oom(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    active_state: _ActiveCounterState = {
        "lock": threading.Lock(),
        "active": 0,
        "max_active": 0,
    }
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(
            delays_by_page={1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05},
            active_state=active_state,
        ),
    )

    app = create_app(
        _parallel_service_config(tmp_path, data_dir="service_data_global_cap", max_workers=2)
    )
    client = TestClient(app)

    pdf_a = _build_pdf_bytes(pages=4)
    pdf_b = _build_pdf_bytes(pages=4)

    create_a = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-global-a",
        file_name="a.pdf",
        file_bytes=pdf_a,
        spec=_pdf_md_spec(filename="a.pdf"),
    )
    create_b = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-global-b",
        file_name="b.pdf",
        file_bytes=pdf_b,
        spec=_pdf_md_spec(filename="b.pdf"),
    )

    job_a = create_a.json()["job"]["job_id"]
    job_b = create_b.json()["job"]["job_id"]

    assert _wait_for_terminal(client, "secret-key", job_a) == JobStatus.SUCCEEDED
    assert _wait_for_terminal(client, "secret-key", job_b) == JobStatus.SUCCEEDED

    assert active_state["max_active"] <= 1


def test_parallel_checkpoint_single_writer_prevents_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.04, 2: 0.04, 3: 0.04, 4: 0.04, 5: 0.04}),
    )

    app = create_app(_parallel_service_config(tmp_path, data_dir="service_data_checkpoint"))
    client = TestClient(app)

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-checkpoint-safety",
        file_name="checkpoint.pdf",
        file_bytes=_build_pdf_bytes(pages=5),
        spec=_pdf_md_spec(filename="checkpoint.pdf"),
    )
    job_id = create.json()["job"]["job_id"]

    checkpoint_invalid_seen = False
    for _ in range(220):
        response = client.get(
            f"/v2/convert/jobs/{job_id}/checkpoint",
            headers={"X-API-Key": "secret-key"},
        )
        if response.status_code == 500:
            body = response.json()
            if body.get("error", {}).get("code") == "checkpoint_invalid":
                checkpoint_invalid_seen = True
                break
        status_response = client.get(
            f"/v2/convert/jobs/{job_id}", headers={"X-API-Key": "secret-key"}
        )
        status = status_response.json()["job"]["status"]
        if status in {JobStatus.SUCCEEDED.value, JobStatus.FAILED.value, JobStatus.CANCELED.value}:
            break
        time.sleep(0.01)

    assert checkpoint_invalid_seen is False
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED


def test_parallel_chunk_commit_updates_heartbeat_and_phase_timings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.05, 2: 0.05, 3: 0.05}),
    )

    app = create_app(_parallel_service_config(tmp_path, data_dir="service_data_progress"))
    client = TestClient(app)

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-progress-heartbeat",
        file_name="progress-heartbeat.pdf",
        file_bytes=_build_pdf_bytes(pages=3),
        spec=_pdf_md_spec(filename="progress-heartbeat.pdf"),
    )
    job_id = create.json()["job"]["job_id"]

    progress_payload = _wait_for_progress_pages(client, job_id=job_id, minimum_pages=1)
    assert progress_payload["last_heartbeat_at"] is not None
    phase_timings = cast(dict[str, object], progress_payload["phase_timings_ms"])
    assert "checkpoint_persist_ms" in phase_timings
    assert "chunk_total_ms" in phase_timings


def test_parallel_resume_after_partial_is_byte_identical_to_serial(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.08, 2: 0.04, 3: 0.04, 4: 0.04, 5: 0.04}),
    )

    app = create_app(_parallel_service_config(tmp_path, data_dir="service_data_resume"))
    client = TestClient(app)

    pdf_bytes = _build_pdf_bytes(pages=5)
    spec = _pdf_md_spec(filename="resume.pdf")

    baseline = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-resume-baseline",
        file_name="resume.pdf",
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

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-resume-cancel",
        file_name="resume.pdf",
        file_bytes=pdf_bytes,
        spec=spec,
    )
    job_id = create.json()["job"]["job_id"]

    _wait_for_progress_pages(client, job_id=job_id, minimum_pages=1)
    cancel = client.post(f"/v2/convert/jobs/{job_id}/cancel", headers={"X-API-Key": "secret-key"})
    assert cancel.status_code in {200, 202}

    resume = client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem-resume-valid"},
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
    assert resumed_artifact.content == baseline_artifact.content


def test_parallel_cancel_mid_run_produces_resume_safe_partial(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.08, 2: 0.08, 3: 0.08}),
    )

    app = create_app(_parallel_service_config(tmp_path, data_dir="service_data_cancel_partial"))
    client = TestClient(app)

    spec = _pdf_md_spec(filename="cancel-partial.pdf")
    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-cancel-partial",
        file_name="cancel-partial.pdf",
        file_bytes=_build_pdf_bytes(pages=3),
        spec=spec,
    )
    job_id = create.json()["job"]["job_id"]

    _wait_for_progress_pages(client, job_id=job_id, minimum_pages=1)
    cancel = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key"},
    )
    assert cancel.status_code in {200, 202}

    partial = None
    for _ in range(150):
        response = client.get(
            f"/v2/convert/jobs/{job_id}/artifact/partial",
            headers={"X-API-Key": "secret-key"},
        )
        if response.status_code == 200:
            partial = response.text
            break
        time.sleep(0.01)
    assert partial is not None
    assert "sir-convert-a-lot:partial" in partial

    resume = client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem-cancel-partial-resume"},
    )
    assert resume.status_code in {200, 202}
    resumed_job_id = resume.json()["job"]["job_id"]
    assert resumed_job_id != job_id
    assert _wait_for_terminal(client, "secret-key", resumed_job_id) == JobStatus.SUCCEEDED


def test_parallel_resume_requires_valid_retained_checkpoint_and_returns_new_job_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.06, 2: 0.06}),
    )

    config = _parallel_service_config(tmp_path, data_dir="service_data_resume_missing")
    config = replace(config, processing_delay_seconds=0.2)
    app = create_app(config)
    client = TestClient(app)

    missing_spec = _pdf_md_spec(filename="missing-checkpoint.pdf")
    missing_create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-resume-missing",
        file_name="missing-checkpoint.pdf",
        file_bytes=_build_pdf_bytes(pages=2),
        spec=missing_spec,
    )
    missing_job_id = missing_create.json()["job"]["job_id"]

    cancel = client.post(
        f"/v2/convert/jobs/{missing_job_id}/cancel",
        headers={"X-API-Key": "secret-key"},
    )
    assert cancel.status_code in {200, 202}

    resume_missing = client.post(
        f"/v2/convert/jobs/{missing_job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem-resume-missing-retry"},
    )
    assert resume_missing.status_code == 409
    assert resume_missing.json()["error"]["code"] == "resume_checkpoint_missing"

    valid_create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-resume-valid-create",
        file_name="valid-checkpoint.pdf",
        file_bytes=_build_pdf_bytes(pages=2),
        spec=_pdf_md_spec(filename="valid-checkpoint.pdf"),
    )
    valid_job_id = valid_create.json()["job"]["job_id"]
    _wait_for_progress_pages(client, job_id=valid_job_id, minimum_pages=1)
    cancel_valid = client.post(
        f"/v2/convert/jobs/{valid_job_id}/cancel",
        headers={"X-API-Key": "secret-key"},
    )
    assert cancel_valid.status_code in {200, 202}
    resume_valid = client.post(
        f"/v2/convert/jobs/{valid_job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem-resume-valid-retry"},
    )
    assert resume_valid.status_code in {200, 202}
    resumed_job_id = resume_valid.json()["job"]["job_id"]
    assert resumed_job_id != valid_job_id


def test_parallel_checkpoint_and_partial_retention_respects_job_expiry_and_pin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.05, 2: 0.05}),
    )

    config = _parallel_service_config(tmp_path, data_dir="service_data_retention")
    config = replace(config, result_ttl_seconds=1, upload_ttl_seconds=1)
    app = create_app(config)
    client = TestClient(app)

    unpinned_spec = _pdf_md_spec(filename="unpinned.pdf", pin=False)
    unpinned_create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-retention-unpinned",
        file_name="unpinned.pdf",
        file_bytes=_build_pdf_bytes(pages=2),
        spec=unpinned_spec,
    )
    unpinned_job_id = unpinned_create.json()["job"]["job_id"]
    _wait_for_progress_pages(client, job_id=unpinned_job_id, minimum_pages=1)
    client.post(f"/v2/convert/jobs/{unpinned_job_id}/cancel", headers={"X-API-Key": "secret-key"})
    unpinned_checkpoint = client.get(
        f"/v2/convert/jobs/{unpinned_job_id}/checkpoint",
        headers={"X-API-Key": "secret-key"},
    )
    assert unpinned_checkpoint.status_code == 200

    pinned_spec = _pdf_md_spec(filename="pinned.pdf", pin=True)
    pinned_create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-retention-pinned",
        file_name="pinned.pdf",
        file_bytes=_build_pdf_bytes(pages=2),
        spec=pinned_spec,
    )
    pinned_job_id = pinned_create.json()["job"]["job_id"]
    _wait_for_progress_pages(client, job_id=pinned_job_id, minimum_pages=1)
    client.post(f"/v2/convert/jobs/{pinned_job_id}/cancel", headers={"X-API-Key": "secret-key"})
    pinned_checkpoint = client.get(
        f"/v2/convert/jobs/{pinned_job_id}/checkpoint",
        headers={"X-API-Key": "secret-key"},
    )
    assert pinned_checkpoint.status_code == 200

    time.sleep(1.2)
    runtime = app.state.runtime_v2
    runtime.job_store.sweep_expired()

    unpinned_after = client.get(
        f"/v2/convert/jobs/{unpinned_job_id}/checkpoint",
        headers={"X-API-Key": "secret-key"},
    )
    assert unpinned_after.status_code == 404

    pinned_after = client.get(
        f"/v2/convert/jobs/{pinned_job_id}/checkpoint",
        headers={"X-API-Key": "secret-key"},
    )
    assert pinned_after.status_code == 200


def test_parallel_defaults_remain_serial_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS", raising=False)
    monkeypatch.delenv("SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS", raising=False)
    monkeypatch.delenv("SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES", raising=False)
    monkeypatch.delenv("SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY", raising=False)
    from scripts.sir_convert_a_lot.infrastructure.runtime_config import service_config_from_env

    config = service_config_from_env()
    assert config.enable_parallel_pdf_chunks is False
    assert config.max_chunk_workers == 1
    assert config.pdf_chunk_size_pages == 10


def test_parallel_env_bounds_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS", "0")
    from scripts.sir_convert_a_lot.infrastructure.runtime_config import service_config_from_env

    with pytest.raises(ValueError, match="SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS"):
        service_config_from_env()


def test_parallel_metrics_emit_bounded_labels_without_job_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.02, 2: 0.02}),
    )

    app = create_app(_parallel_service_config(tmp_path, data_dir="service_data_metrics_parallel"))
    client = TestClient(app)

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-metrics-parallel",
        file_name="metrics-parallel.pdf",
        file_bytes=_build_pdf_bytes(pages=2),
        spec=_pdf_md_spec(filename="metrics-parallel.pdf"),
    )
    job_id = create.json()["job"]["job_id"]
    assert _wait_for_terminal(client, "secret-key", job_id) == JobStatus.SUCCEEDED

    result_payload = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers={"X-API-Key": "secret-key"},
    ).json()
    conversion_metadata = result_payload["result"]["conversion_metadata"]
    assert conversion_metadata["parallel_enabled"] is True
    assert conversion_metadata["max_chunk_workers"] == 2
    assert conversion_metadata["chunk_size_pages"] == 1
    assert conversion_metadata["effective_gpu_stage_limit"] == 1
    assert conversion_metadata["scheduling_mode"] == "parallel_ordered_commit"

    metrics_text = client.get("/metrics").text
    assert "sir_convert_a_lot_v2_chunk_workers_active" in metrics_text
    assert "sir_convert_a_lot_v2_chunk_workers_per_job_max" in metrics_text
    assert "sir_convert_a_lot_v2_chunk_workers_global_cap" in metrics_text
    assert "sir_convert_a_lot_v2_chunk_worker_saturation_ratio" in metrics_text
    assert "job_id=" not in metrics_text
    assert job_id not in metrics_text


def test_parallel_api_contract_parity_for_artifact_checkpoint_resume(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _make_stub_conversion(delays_by_page={1: 0.06, 2: 0.06, 3: 0.06}),
    )

    app = create_app(_parallel_service_config(tmp_path, data_dir="service_data_parity"))
    client = TestClient(app)

    create = _post_create(
        client,
        api_key="secret-key",
        idempotency_key="idem-parity",
        file_name="parity.pdf",
        file_bytes=_build_pdf_bytes(pages=3),
        spec=_pdf_md_spec(filename="parity.pdf"),
    )
    job_id = create.json()["job"]["job_id"]

    artifact_pre = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key"},
    )
    assert artifact_pre.status_code == 202

    checkpoint_pre = client.get(
        f"/v2/convert/jobs/{job_id}/checkpoint",
        headers={"X-API-Key": "secret-key"},
    )
    assert checkpoint_pre.status_code in {200, 202}

    _wait_for_progress_pages(client, job_id=job_id, minimum_pages=1)
    cancel = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers={"X-API-Key": "secret-key"},
    )
    assert cancel.status_code in {200, 202}

    resume = client.post(
        f"/v2/convert/jobs/{job_id}/resume",
        headers={"X-API-Key": "secret-key", "Idempotency-Key": "idem-parity-resume"},
    )
    assert resume.status_code in {200, 202}
    resumed_job_id = resume.json()["job"]["job_id"]
    assert resumed_job_id != job_id
