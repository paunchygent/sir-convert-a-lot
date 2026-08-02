"""Tests for the parallel PDF throughput benchmark runner.

Purpose:
    Validate payload shape and output-path policy for deterministic parallel PDF throughput
    benchmark evidence generation.

Relationships:
    - Tests `scripts.sir_convert_a_lot.pdf_parallel_throughput_benchmark`.
    - Protects the evidence workflow used to terminalize parallel PDF throughput under PDF
    throughput lane.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.pdf_parallel_throughput_benchmark import (
    DEFAULT_OUTPUT_JSON,
    run_benchmark,
)


def test_run_benchmark_writes_expected_payload(tmp_path: Path) -> None:
    output_json = tmp_path / "pdf-parallel-throughput.json"
    payload = run_benchmark(
        output_json=output_json,
        data_root=tmp_path / "runtime_data",
        total_pages=8,
        repeats=3,
        chunk_size_pages=1,
        max_chunk_workers=4,
        stub_work_seconds=0.05,
    )

    assert output_json.exists()
    assert payload["benchmark_id"] == "pdf-parallel-throughput"
    assert len(payload["profiles"]) == 2
    profiles = {entry["profile"]: entry for entry in payload["profiles"]}
    assert set(profiles.keys()) == {"serial", "parallel"}

    serial = profiles["serial"]
    parallel = profiles["parallel"]
    assert serial["result_metadata"]["parallel_enabled"] is False
    assert serial["result_metadata"]["scheduling_mode"] == "serial"
    assert parallel["result_metadata"]["parallel_enabled"] is True
    assert parallel["result_metadata"]["scheduling_mode"] == "parallel_ordered_commit"
    assert payload["comparison"]["byte_identical_to_serial"] is True
    assert payload["comparison"]["p50_wall_clock_improvement_percent"] > 10.0


def test_default_output_json_path_is_outside_docs_reference() -> None:
    output_path = DEFAULT_OUTPUT_JSON.as_posix()
    assert output_path.startswith("build/")
    assert "docs/reference" not in output_path


def test_run_benchmark_rejects_docs_reference_output_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must not target docs/reference"):
        run_benchmark(
            output_json=Path("docs/reference/forbidden-pdf-parallel-throughput.json"),
            data_root=tmp_path / "runtime_data",
        )
