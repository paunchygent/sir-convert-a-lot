"""Tests for v2 PDF chunk conversion worker outcomes.

Purpose:
    Prove chunk worker outcomes preserve execution-boundary metadata before
    ordered checkpoint commit writes records for progress and resume surfaces.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.v2_pdf_chunk_conversion`.
    - Complements checkpoint runner tests that verify ordered persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_pdf_chunk_conversion
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_chunk_conversion import (
    convert_pending_pdf_chunk_v2,
)
from tests.sir_convert_a_lot.conversion.v2_conversion_executor_test_support import (
    _build_job,
    _build_v1_job_spec,
    _service_config,
    _UnusedBackend,
)


def test_chunk_conversion_outcome_records_worker_start_and_completion_times(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    observed_times = [
        datetime(2026, 6, 4, 12, 0, 0, tzinfo=UTC),
        datetime(2026, 6, 4, 12, 0, 7, tzinfo=UTC),
    ]

    def _fake_utc_now() -> datetime:
        return observed_times.pop(0)

    def _stub_execute_chunk_conversion(**kwargs):
        del kwargs
        return (
            "# chunk\n",
            ConversionMetadata(
                backend_used="docling",
                acceleration_used="cuda",
                ocr_enabled=False,
                table_mode=TableMode.ACCURATE,
                options_fingerprint="sha256:chunk-timing",
                formula_authority={
                    "action": "rejected",
                    "source_evidence_state": "usable",
                    "reason": "source_layer_authoritative_and_generated_formula_quality_defect",
                },
            ),
            [],
            {"ocr_layout_extract_ms": 7},
        )

    monkeypatch.setattr(v2_pdf_chunk_conversion, "utc_now", _fake_utc_now, raising=False)
    job = _build_job(
        tmp_path,
        source_filename="chunk.pdf",
        source_bytes=b"%PDF-1.4 fixture",
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
    )

    outcome = convert_pending_pdf_chunk_v2(
        chunk_index=0,
        start_page=1,
        end_page=4,
        chunk_pdf_bytes=b"%PDF-1.4 chunk",
        job=job,
        config=_service_config(tmp_path),
        v1_spec=_build_v1_job_spec(),
        probe=None,
        docling_backend=_UnusedBackend(),
        pymupdf_backend=_UnusedBackend(),
        resolved_ocr=None,
        execute_chunk_conversion=_stub_execute_chunk_conversion,
        on_chunk_worker_start=None,
        on_chunk_worker_finish=None,
    )

    assert outcome.started_at == "2026-06-04T12:00:00Z"
    assert outcome.completed_at == "2026-06-04T12:00:07Z"
    assert outcome.formula_authority == {
        "action": "rejected",
        "source_evidence_state": "usable",
        "reason": "source_layer_authoritative_and_generated_formula_quality_defect",
    }
