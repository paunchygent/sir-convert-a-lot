"""Tests for the PDF throughput benchmark throughput benchmark harness.

Purpose:
    Validate payload shape, report generation, and output-path policy for the
    PDF throughput lane throughput benchmark/report surface.

Relationships:
    - Tests `scripts.sir_convert_a_lot.pdf_throughput_benchmark_report`.
    - Protects the command/report surface intended for PDF throughput benchmark closeout.
"""

from __future__ import annotations

import importlib.machinery
import time
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.benchmarking.pdf_throughput_types import (
    CorpusFileRecord,
    ProfilePayload,
)
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult
from scripts.sir_convert_a_lot.pdf_throughput_benchmark_report import (
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_REPORT,
    ProfileSpec,
    RuntimeParityInputs,
    _build_two_worker_sweep_profiles,
    main,
    run_benchmark,
)


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
        options_fingerprint="sha256:pdf-throughput-stub",
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

    output_json = tmp_path / "pdf-throughput.json"
    output_report = tmp_path / "pdf-throughput.md"
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
    assert payload["benchmark_id"] == "pdf-throughput-throughput-benchmark"
    assert payload["comparison"]["baseline_profile"] == "serial_baseline"
    assert payload["comparison"]["tuned_profile"] == "parallel_conservative"
    assert len(payload["profiles"]) == 2
    assert payload["dirty_corpus"] is None
    assert payload["runtime_surface"]["mode"] == "in_process_app"
    assert payload["runtime_parity"]["parity_proven"] is False
    report_text = output_report.read_text(encoding="utf-8")
    assert "## Runtime Surface" in report_text
    assert "## Runtime Parity" in report_text


def test_smoke_command_stdout_excludes_performance_metrics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2,
        "execute_v2_job_conversion",
        _stub_execute_v2_job_conversion,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "pdf_throughput_benchmark_report",
            "--output-json",
            (tmp_path / "pdf-report.json").as_posix(),
            "--output-report",
            (tmp_path / "pdf-report.md").as_posix(),
            "--corpus-root",
            (tmp_path / "corpus").as_posix(),
            "--data-root",
            (tmp_path / "runtime").as_posix(),
            "--page-counts",
            "2",
            "--acceleration-policy",
            "cpu_only",
            "--ocr-mode",
            "off",
            "--ocr-engine",
            "auto",
            "--ocr-languages",
            "en",
            "--no-gpu-available",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "pdf-benchmark-report-written" in output
    assert "p50" not in output
    assert "p90" not in output
    assert "latency" not in output
    assert "throughput" not in output
    assert "pages_per_minute" not in output
    assert "improvement" not in output


def test_build_two_worker_sweep_profiles_stays_within_safe_bounds() -> None:
    profiles = _build_two_worker_sweep_profiles(
        chunk_sizes=(2, 4, 6),
        gpu_stage_caps=(1, 2),
    )

    assert [profile.profile_name for profile in profiles] == [
        "serial_baseline",
        "parallel_conservative",
        "parallel_2w_chunk2_cap1",
        "parallel_2w_chunk2_cap2",
        "parallel_2w_chunk4_cap1",
        "parallel_2w_chunk6_cap1",
        "parallel_2w_chunk6_cap2",
    ]
    assert all(profile.max_chunk_workers <= 2 for profile in profiles)
    assert all(profile.gpu_stage_max_concurrency <= 2 for profile in profiles)


def test_default_output_paths_are_outside_docs_reference() -> None:
    assert DEFAULT_OUTPUT_JSON.as_posix().startswith("build/")
    assert DEFAULT_OUTPUT_REPORT.as_posix().startswith("build/")
    assert "docs/reference" not in DEFAULT_OUTPUT_JSON.as_posix()
    assert "docs/reference" not in DEFAULT_OUTPUT_REPORT.as_posix()


def test_run_benchmark_rejects_docs_reference_output_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must not target docs/reference"):
        run_benchmark(
            output_json=Path("docs/reference/forbidden-pdf-throughput.json"),
            output_report=tmp_path / "pdf-throughput.md",
            corpus_root=tmp_path / "corpus",
            data_root=tmp_path / "runtime",
            page_counts=(2,),
            api_key="benchmark-key",
            acceleration_policy="cpu_only",
            gpu_available=False,
        )


def test_run_benchmark_supports_two_worker_sweep_profiles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2, "execute_v2_job_conversion", _stub_execute_v2_job_conversion
    )

    payload = run_benchmark(
        output_json=tmp_path / "pdf-throughput-sweep.json",
        output_report=tmp_path / "pdf-throughput-sweep.md",
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
        two_worker_sweep=True,
        two_worker_chunk_sizes=(3, 4),
        two_worker_gpu_stage_caps=(1, 2),
    )

    profile_names = [profile["profile_name"] for profile in payload["profiles"]]
    assert profile_names == [
        "serial_baseline",
        "parallel_conservative",
        "parallel_2w_chunk3_cap1",
        "parallel_2w_chunk3_cap2",
        "parallel_2w_chunk4_cap1",
    ]


def test_production_service_runtime_does_not_dispatch_testclient_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def forbidden_in_process_profile(**_kwargs: object) -> ProfilePayload:
        raise AssertionError("production_service runtime must not use TestClient profile runner")

    def service_profile_stub(
        *,
        profile: ProfileSpec,
        service_url: str,
        corpus_root: Path,
        corpus_records: list[CorpusFileRecord],
        api_key: str,
        acceleration_policy: str,
        ocr_mode: str,
        ocr_engine: str,
        ocr_languages: list[str],
        max_poll_seconds: float,
    ) -> ProfilePayload:
        del service_url, corpus_root, api_key, acceleration_policy
        del ocr_mode, ocr_engine, ocr_languages, max_poll_seconds
        return {
            "profile_name": profile.profile_name,
            "config": {
                "parallel_enabled": profile.parallel_enabled,
                "max_chunk_workers": profile.max_chunk_workers,
                "chunk_size_pages": profile.chunk_size_pages,
                "gpu_stage_max_concurrency": profile.gpu_stage_max_concurrency,
                "acceleration_policy": "gpu_required",
            },
            "summary": {
                "total_jobs": len(corpus_records),
                "succeeded_jobs": len(corpus_records),
                "failed_jobs": 0,
                "success_rate": 1.0,
                "error_rate": 0.0,
                "total_latency_seconds": 5.0,
                "latency_seconds": {"min": 5.0, "mean": 5.0, "p50": 5.0, "p90": 5.0, "max": 5.0},
                "pages_per_minute_p50": 24.0,
            },
            "resource_evidence": {
                "peak_jobs_queued": 0.0,
                "peak_jobs_active": 1.0,
                "peak_worker_saturation_ratio": 0.0,
                "peak_chunk_worker_saturation_ratio": 0.0,
                "peak_gpu_busy_percent": 25.0,
                "peak_gpu_memory_used_percent": 10.0,
                "contains_job_id_label": False,
            },
            "jobs": [
                {
                    "source_file": record["filename"],
                    "page_count": record["page_count"],
                    "job_id": f"job_{index:03d}",
                    "status": "succeeded",
                    "latency_seconds": 5.0,
                    "pages_per_minute": 24.0,
                    "backend_used": "docling",
                    "acceleration_used": "cuda",
                    "ocr_enabled": True,
                    "ocr_engine_used": "easyocr",
                    "ocr_languages_used": ["sv", "en"],
                    "gpu_busy_percent": 25,
                    "gpu_memory_used_percent": 10,
                    "warnings": [],
                }
                for index, record in enumerate(corpus_records, start=1)
            ],
        }

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.benchmarking.pdf_throughput_profile_runner.run_in_process_profile",
        forbidden_in_process_profile,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.benchmarking.pdf_throughput_profile_runner.run_service_profile",
        service_profile_stub,
    )

    payload = run_benchmark(
        output_json=tmp_path / "pdf-throughput-service.json",
        output_report=tmp_path / "pdf-throughput-service.md",
        corpus_root=tmp_path / "corpus",
        data_root=tmp_path / "runtime",
        page_counts=(2,),
        api_key="benchmark-key",
        runtime_mode="production_service",
        runtime_host="hemma",
        runtime_service_url="http://127.0.0.1:28085",
        profiles=[
            ProfileSpec(
                profile_name="production_service_current",
                parallel_enabled=True,
                max_chunk_workers=2,
                chunk_size_pages=4,
                gpu_stage_max_concurrency=2,
            )
        ],
    )

    assert payload["runtime_surface"]["mode"] == "production_service"
    assert [profile["profile_name"] for profile in payload["profiles"]] == [
        "production_service_current"
    ]


def test_run_benchmark_embeds_runtime_parity_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runtime_engine_v2, "execute_v2_job_conversion", _stub_execute_v2_job_conversion
    )
    parity_report = tmp_path / "deploy-parity-report.json"
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
        output_json=tmp_path / "pdf-throughput.json",
        output_report=tmp_path / "pdf-throughput.md",
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
    assert payload["runtime_surface"]["parity_source"].startswith("deploy_parity_report_json:")
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
        output_json=tmp_path / "pdf-throughput.json",
        output_report=tmp_path / "pdf-throughput.md",
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
    assert (
        "Hemma deploy verification live smoke proof is missing or failed."
        in payload["runtime_parity"]["notes"]
    )


def test_run_benchmark_fails_fast_when_easyocr_missing_for_in_process_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.benchmarking.pdf_ocr_runtime_preflight.importlib.util.find_spec",
        lambda _module_name: None,
    )

    with pytest.raises(RuntimeError, match="missing EasyOCR"):
        run_benchmark(
            output_json=tmp_path / "pdf-throughput.json",
            output_report=tmp_path / "pdf-throughput.md",
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
        "scripts.sir_convert_a_lot.benchmarking.pdf_ocr_runtime_preflight.importlib.util.find_spec",
        lambda _module_name: importlib.machinery.ModuleSpec("easyocr", loader=None),
    )

    with pytest.raises(RuntimeError, match="missing the EasyOCR model directory"):
        run_benchmark(
            output_json=tmp_path / "pdf-throughput.json",
            output_report=tmp_path / "pdf-throughput.md",
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
