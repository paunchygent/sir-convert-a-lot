"""Tests for the Task 74 throughput benchmark harness.

Purpose:
    Validate payload shape, report generation, and output-path policy for the
    Story 20 throughput benchmark/report surface.

Relationships:
    - Tests `scripts.sir_convert_a_lot.benchmark_story20_throughput_report`.
    - Protects the command/report surface intended for Task 74 closeout.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.benchmark_story20_throughput_report import (
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_REPORT,
    run_benchmark,
)
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult


def _stub_execute_v2_job_conversion(*, config, **_kwargs):
    if not config.enable_parallel_pdf_chunks:
        time.sleep(0.08)
    elif config.max_chunk_workers <= 2:
        time.sleep(0.03)
    else:
        time.sleep(0.01)
    return V2ExecutionResult(
        artifact_bytes=b"# benchmark\n",
        pipeline_used="pdf_to_md_v2",
        backend_used="docling",
        acceleration_used="cpu",
        warnings=[],
        phase_timings_ms={"conversion_total_ms": 10},
        options_fingerprint="sha256:task74-stub",
        ocr_enabled=True,
        ocr_engine_used="easyocr",
        ocr_languages_used=["sv", "en"],
    )


def test_run_benchmark_writes_expected_payload_and_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2, "execute_v2_job_conversion", _stub_execute_v2_job_conversion
    )

    output_json = tmp_path / "task74.json"
    output_report = tmp_path / "task74.md"
    payload = run_benchmark(
        output_json=output_json,
        output_report=output_report,
        corpus_root=tmp_path / "corpus",
        data_root=tmp_path / "runtime",
        page_counts=(2, 3),
        api_key="benchmark-key",
        acceleration_policy="cpu_only",
        ocr_mode="off",
        ocr_engine="auto",
        ocr_languages=[],
        max_poll_seconds=30.0,
        gpu_available=False,
    )

    assert output_json.exists()
    assert output_report.exists()
    assert payload["benchmark_id"] == "task-74-throughput-benchmark"
    assert payload["comparison"]["baseline_profile"] == "serial_baseline"
    assert payload["comparison"]["recommended_profile"] in {
        "parallel_conservative",
        "parallel_tuned",
    }
    assert payload["comparison"]["recommended_profile"] != "serial_baseline"
    assert payload["comparison"]["p50_improvement_percent"] >= 0.0
    assert len(payload["profiles"]) == 3


def test_default_output_paths_are_outside_docs_reference() -> None:
    assert DEFAULT_OUTPUT_JSON.as_posix().startswith("build/")
    assert DEFAULT_OUTPUT_REPORT.as_posix().startswith("build/")
    assert "docs/reference" not in DEFAULT_OUTPUT_JSON.as_posix()
    assert "docs/reference" not in DEFAULT_OUTPUT_REPORT.as_posix()


def test_run_benchmark_rejects_docs_reference_output_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must not target docs/reference"):
        run_benchmark(
            output_json=Path("docs/reference/forbidden-task74.json"),
            output_report=tmp_path / "task74.md",
            corpus_root=tmp_path / "corpus",
            data_root=tmp_path / "runtime",
            page_counts=(2,),
            api_key="benchmark-key",
            acceleration_policy="cpu_only",
            gpu_available=False,
        )
