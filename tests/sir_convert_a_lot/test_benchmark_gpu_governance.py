"""Benchmark runner tests for Story 003b evidence generation.

Purpose:
    Validate schema shape and deterministic ordering for benchmark JSON output
    produced by the GPU governance benchmark runner.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.benchmark_gpu_governance.run_benchmark`.
    - Protects benchmark evidence pipeline used in Story 003b docs.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.benchmark_gpu_governance import run_benchmark
from tests.sir_convert_a_lot.pdf_fixtures import copy_fixture_pdf


def _write_fixture(path: Path, label: str) -> None:
    fixture_name = "paper_alpha.pdf" if label.endswith("a") else "paper_beta.pdf"
    copy_fixture_pdf(path, fixture_name)


def test_run_benchmark_writes_expected_json_payload(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True)
    _write_fixture(fixtures_dir / "b.pdf", "bench-b")
    _write_fixture(fixtures_dir / "a.pdf", "bench-a")
    _write_fixture(fixtures_dir / "c.pdf", "bench-c")

    output_json = tmp_path / "benchmark.json"
    payload = run_benchmark(
        fixtures_dir=fixtures_dir,
        output_json=output_json,
        stage="local-test",
        acceleration_policy="gpu_required",
        api_key="benchmark-key",
        gpu_available=False,
        allow_cpu_only=False,
        allow_cpu_fallback=True,
        processing_delay_seconds=0.01,
        max_poll_seconds=20.0,
        data_root=tmp_path / "runtime_data",
    )

    assert output_json.exists()
    assert payload["benchmark_id"] == "story-003b-gpu-governance"
    assert payload["stage"] == "local-test"

    summary = payload["summary"]
    assert summary["total_jobs"] == 3
    assert summary["succeeded_jobs"] == 0
    assert summary["failed_jobs"] == 3
    assert summary["success_rate"] == 0.0

    jobs = payload["jobs"]
    assert [job["source_file"] for job in jobs] == ["a.pdf", "b.pdf", "c.pdf"]
    assert all(job["acceleration_used"] is None for job in jobs)
    assert all(job["error_code"] is not None for job in jobs)

    latency = summary["latency_seconds"]
    assert set(latency.keys()) == {"min", "mean", "p50", "p95", "max"}
