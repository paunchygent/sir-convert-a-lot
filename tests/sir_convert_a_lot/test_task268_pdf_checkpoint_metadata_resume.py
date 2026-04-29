"""Task-268 regression tests for PDF checkpoint terminal metadata truth.

Purpose:
    Prove checkpointed PDF finalization derives terminal backend/OCR metadata
    from committed chunk records when no new chunk conversion runs.

Relationships:
    - Exercises `infrastructure.v2_pdf_checkpointed_executor` through the v2
      conversion executor.
    - Complements the broader Task-72 parallel/cancel/resume contract suite.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import OcrMode, TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OcrEngineV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_pdf_checkpointed_executor
from scripts.sir_convert_a_lot.infrastructure.pdf_checkpoints_v2 import (
    checkpoint_path_for_job_upload,
    load_pdf_checkpoint,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    execute_v2_job_conversion,
)
from tests.sir_convert_a_lot.v2_conversion_executor_test_support import (
    _build_job,
    _service_config,
    _UnusedBackend,
)


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
            if "page 1" in text:
                page_numbers.append(1)
            elif "page 2" in text:
                page_numbers.append(2)
            else:
                raise AssertionError(f"Unexpected chunk text: {text!r}")
        return page_numbers
    finally:
        doc.close()


def _task268_config(tmp_path: Path) -> ServiceConfig:
    return replace(
        _service_config(tmp_path),
        enable_parallel_pdf_chunks=True,
        max_chunk_workers=2,
        pdf_chunk_size_pages=1,
        default_pdf_ocr_engine=OcrEngineV2.EASYOCR,
        default_pdf_ocr_languages=("sv", "en"),
    )


def _build_ocr_job(tmp_path: Path) -> StoredJobV2:
    job = _build_job(
        tmp_path,
        source_filename="task268.pdf",
        source_bytes=_build_pdf_bytes(pages=2),
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )
    pdf_options = job.spec.pdf_options
    if pdf_options is None:
        raise AssertionError("PDF job helper did not create pdf_options.")
    job.spec = job.spec.model_copy(
        update={"pdf_options": pdf_options.model_copy(update={"ocr_mode": OcrMode.AUTO})}
    )
    return job


def test_zero_new_chunk_resume_hydrates_ocr_metadata_from_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    conversion_calls: list[tuple[int, ...]] = []

    def _stub_execute_job_conversion(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
        ocr_engine: OcrEngineV2 | None = None,
        ocr_languages: tuple[str, ...] = (),
        ocr_use_gpu: bool | None = None,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del (
            spec,
            source_filename,
            gpu_available,
            gpu_runtime_probe,
            docling_backend,
            pymupdf_backend,
            ocr_use_gpu,
        )
        page_numbers = _page_numbers_from_chunk(source_bytes)
        conversion_calls.append(tuple(page_numbers))
        ocr_enabled = 1 in page_numbers
        warnings = ["docling_auto_ocr_retry_applied"] if ocr_enabled else []
        markdown = "".join(f"# page {page_number}\n" for page_number in page_numbers)
        if ocr_enabled:
            assert ocr_engine == OcrEngineV2.EASYOCR
            assert ocr_languages == ("sv", "en")
        return (
            markdown,
            ConversionMetadata(
                backend_used="docling",
                acceleration_used="cpu",
                ocr_enabled=ocr_enabled,
                ocr_engine_used="tesseract_cli" if ocr_enabled else None,
                ocr_languages_used=["sv"] if ocr_enabled else [],
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:task268",
            ),
            warnings,
            {"ocr_layout_extract_ms": 8 if ocr_enabled else 0, "markdown_normalize_ms": 2},
        )

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _stub_execute_job_conversion,
    )

    job = _build_ocr_job(tmp_path)
    config = _task268_config(tmp_path)
    first = execute_v2_job_conversion(
        job=job,
        config=config,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )
    first_digest = hashlib.sha256(first.artifact_bytes).hexdigest()
    assert sorted(conversion_calls) == [(1,), (2,)]

    def _unexpected_execute_job_conversion(
        **kwargs,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del kwargs
        raise AssertionError("Checkpointed chunks should not be reprocessed.")

    conversion_calls.clear()
    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _unexpected_execute_job_conversion,
    )

    second = execute_v2_job_conversion(
        job=job,
        config=config,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    assert conversion_calls == []
    assert hashlib.sha256(second.artifact_bytes).hexdigest() == first_digest
    assert second.artifact_bytes == first.artifact_bytes
    assert second.backend_used == "docling"
    assert second.acceleration_used == "cpu"
    assert second.ocr_enabled is True
    assert second.ocr_engine_used == "tesseract_cli"
    assert second.ocr_languages_used == ["sv"]
    assert second.warnings == ["docling_auto_ocr_retry_applied"]
    assert "ocr_layout_extract_ms" in second.phase_timings_ms
    assert "markdown_normalize_ms" in second.phase_timings_ms
    assert "chunk_total_ms" in second.phase_timings_ms
    assert "checkpoint_persist_ms" in second.phase_timings_ms


def test_zero_new_chunk_resume_fails_closed_when_chunk_artifact_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _stub_execute_job_conversion(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
        ocr_engine: OcrEngineV2 | None = None,
        ocr_languages: tuple[str, ...] = (),
        ocr_use_gpu: bool | None = None,
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
        page_numbers = _page_numbers_from_chunk(source_bytes)
        markdown = "".join(f"# page {page_number}\n" for page_number in page_numbers)
        return (
            markdown,
            ConversionMetadata(
                backend_used="docling",
                acceleration_used="cpu",
                ocr_enabled=False,
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:task268",
            ),
            [],
            {"markdown_normalize_ms": 2},
        )

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _stub_execute_job_conversion,
    )

    job = _build_ocr_job(tmp_path)
    config = _task268_config(tmp_path)
    execute_v2_job_conversion(
        job=job,
        config=config,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
    )

    checkpoint = load_pdf_checkpoint(upload_path=job.upload_path)
    assert checkpoint is not None
    chunk_to_remove = checkpoint.chunks[0]
    chunk_path = job.upload_path.parent.parent / chunk_to_remove.artifact_relpath
    chunk_path.unlink()

    def _unexpected_execute_job_conversion(
        **kwargs,
    ) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
        del kwargs
        raise AssertionError("Checkpointed chunks should not be reprocessed.")

    monkeypatch.setattr(
        v2_pdf_checkpointed_executor,
        "execute_job_conversion",
        _unexpected_execute_job_conversion,
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=config,
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    assert exc_info.value.code == "checkpoint_artifact_invalid"
    assert exc_info.value.retryable is False


def test_v1_checkpoint_resume_fails_closed_without_metadata_bridge(
    tmp_path: Path,
) -> None:
    job = _build_ocr_job(tmp_path)
    checkpoint_path = checkpoint_path_for_job_upload(upload_path=job.upload_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(
        json.dumps(
            {
                "schema_version": "v2_pdf_checkpoint_v1",
                "job_id": job.job_id,
                "updated_at": "2026-04-28T12:00:00+00:00",
                "total_pages": 2,
                "chunk_size_pages": 1,
                "processed_pages": 2,
                "failed_pages": 0,
                "chunks": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_v2_job_conversion(
            job=job,
            config=_task268_config(tmp_path),
            docling_backend=_UnusedBackend(),
            pymupdf_backend=_UnusedBackend(),
        )

    assert exc_info.value.code == "checkpoint_invalid"
    assert exc_info.value.retryable is False
