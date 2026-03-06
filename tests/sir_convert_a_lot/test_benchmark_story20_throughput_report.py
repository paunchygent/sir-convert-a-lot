"""Tests for the Task 74 throughput benchmark harness.

Purpose:
    Validate payload shape, report generation, and output-path policy for the
    Story 20 throughput benchmark/report surface.

Relationships:
    - Tests `scripts.sir_convert_a_lot.benchmark_story20_throughput_report`.
    - Protects the command/report surface intended for Task 74 closeout.
"""

from __future__ import annotations

import importlib.machinery
import time
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.benchmark_story20_throughput_report import (
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_REPORT,
    RuntimeParityInputs,
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
    assert payload["runtime_surface"]["mode"] == "in_process_app"
    assert payload["runtime_parity"]["parity_proven"] is False
    report_text = output_report.read_text(encoding="utf-8")
    assert "## Runtime Surface" in report_text
    assert "## Runtime Parity" in report_text


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


def test_run_benchmark_embeds_task76_runtime_parity_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2, "execute_v2_job_conversion", _stub_execute_v2_job_conversion
    )
    parity_report = tmp_path / "task76-report.json"
    parity_report.write_text(
        (
            "{"
            '"status":"passed",'
            '"lane":"host",'
            '"expected_revision":"abc",'
            '"remote_revision":"abc",'
            '"service_revision":"abc",'
            '"service_url":"http://127.0.0.1:28085",'
            '"checks":{'
            '"expected_revision_matches_remote":true,'
            '"service_revision_matches_remote":true,'
            '"live_smoke_passed":true,'
            '"metrics_scan_passed":true'
            "}"
            "}"
        ),
        encoding="utf-8",
    )

    payload = run_benchmark(
        output_json=tmp_path / "task74.json",
        output_report=tmp_path / "task74.md",
        corpus_root=tmp_path / "corpus",
        data_root=tmp_path / "runtime",
        page_counts=(2,),
        api_key="benchmark-key",
        acceleration_policy="cpu_only",
        ocr_mode="off",
        ocr_engine="auto",
        ocr_languages=[],
        max_poll_seconds=30.0,
        gpu_available=False,
        runtime_mode="in_process_app",
        runtime_host="hemma",
        runtime_parity_inputs=RuntimeParityInputs(
            report_json_path=parity_report,
            status=None,
            lane=None,
            expected_revision=None,
            remote_revision=None,
            service_revision=None,
            expected_revision_matches_remote=None,
            service_revision_matches_remote=None,
            live_smoke_passed=None,
            metrics_scan_passed=None,
        ),
    )

    assert payload["runtime_surface"]["host"] == "hemma"
    assert payload["runtime_surface"]["parity_source"].startswith("task76_report_json:")
    assert payload["runtime_parity"]["parity_proven"] is True
    assert payload["runtime_parity"]["service_revision"] == "abc"
    assert payload["runtime_parity"]["live_smoke_passed"] is True


def test_run_benchmark_marks_runtime_parity_unproven_when_checks_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2, "execute_v2_job_conversion", _stub_execute_v2_job_conversion
    )

    payload = run_benchmark(
        output_json=tmp_path / "task74.json",
        output_report=tmp_path / "task74.md",
        corpus_root=tmp_path / "corpus",
        data_root=tmp_path / "runtime",
        page_counts=(2,),
        api_key="benchmark-key",
        acceleration_policy="cpu_only",
        ocr_mode="off",
        ocr_engine="auto",
        ocr_languages=[],
        gpu_available=False,
        runtime_parity_inputs=RuntimeParityInputs(
            report_json_path=None,
            status="passed",
            lane="host",
            expected_revision="abc",
            remote_revision="abc",
            service_revision="abc",
            expected_revision_matches_remote=True,
            service_revision_matches_remote=True,
            live_smoke_passed=False,
            metrics_scan_passed=True,
        ),
    )

    assert payload["runtime_parity"]["parity_proven"] is False
    assert "Task 76 live smoke proof is missing or failed." in payload["runtime_parity"]["notes"]


def test_run_benchmark_fails_fast_when_easyocr_missing_for_in_process_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.benchmark_story20_throughput_report.importlib.util.find_spec",
        lambda _module_name: None,
    )

    with pytest.raises(RuntimeError, match="missing EasyOCR"):
        run_benchmark(
            output_json=tmp_path / "task74.json",
            output_report=tmp_path / "task74.md",
            corpus_root=tmp_path / "corpus",
            data_root=tmp_path / "runtime",
            page_counts=(2,),
            api_key="benchmark-key",
            acceleration_policy="gpu_required",
            ocr_mode="force",
            ocr_engine="easyocr",
            ocr_languages=["sv", "en"],
            gpu_available=True,
        )


def test_run_benchmark_fails_fast_when_easyocr_model_dir_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.benchmark_story20_throughput_report.importlib.util.find_spec",
        lambda _module_name: importlib.machinery.ModuleSpec("easyocr", loader=None),
    )

    with pytest.raises(RuntimeError, match="missing the EasyOCR model directory"):
        run_benchmark(
            output_json=tmp_path / "task74.json",
            output_report=tmp_path / "task74.md",
            corpus_root=tmp_path / "corpus",
            data_root=tmp_path / "runtime",
            page_counts=(2,),
            api_key="benchmark-key",
            acceleration_policy="gpu_required",
            ocr_mode="force",
            ocr_engine="easyocr",
            ocr_languages=["sv", "en"],
            gpu_available=True,
            easyocr_model_storage_directory=(tmp_path / "missing-model-dir").as_posix(),
        )
