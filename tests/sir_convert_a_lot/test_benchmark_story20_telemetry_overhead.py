"""Tests for Task 73 telemetry overhead benchmark runner.

Purpose:
    Validate payload shape and output-policy behavior for deterministic
    telemetry-overhead evidence generation.

Relationships:
    - Tests `scripts.sir_convert_a_lot.benchmark_story20_telemetry_overhead`.
    - Protects Task 73 benchmark evidence workflow under Story 20.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.benchmark_story20_telemetry_overhead import (
    DEFAULT_OUTPUT_JSON,
    run_benchmark,
)


def test_run_benchmark_writes_expected_payload(tmp_path: Path) -> None:
    output_json = tmp_path / "story20-telemetry.json"
    payload = run_benchmark(
        output_json=output_json,
        data_root=tmp_path / "runtime_data",
        total_jobs=8,
        max_workers=3,
        stub_work_seconds=0.002,
    )

    assert output_json.exists()
    assert payload["benchmark_id"] == "task-73-telemetry-overhead"
    assert len(payload["variants"]) == 3
    variants = {entry["variant"]: entry for entry in payload["variants"]}
    assert set(variants.keys()) == {
        "telemetry_full",
        "telemetry_sink_disabled",
        "telemetry_calls_bypassed",
    }

    telemetry_full = variants["telemetry_full"]
    assert telemetry_full["total_jobs"] == 8
    assert telemetry_full["succeeded_jobs"] == 8
    assert telemetry_full["failed_jobs"] == 0
    assert telemetry_full["metrics_summary"]["contains_job_id_label"] is False
    assert telemetry_full["metrics_summary"]["stage_duration_samples"] > 0
    sink_disabled = variants["telemetry_sink_disabled"]
    bypassed = variants["telemetry_calls_bypassed"]
    assert sink_disabled["metrics_summary"] == {}
    assert bypassed["metrics_summary"] == {}
    assert "overhead_percent" in payload
    assert "full_vs_sink_disabled" in payload["overhead_percent"]
    assert "full_vs_bypassed" in payload["overhead_percent"]


def test_default_output_json_path_is_outside_docs_reference() -> None:
    output_path = DEFAULT_OUTPUT_JSON.as_posix()
    assert output_path.startswith("build/")
    assert "docs/reference" not in output_path


def test_run_benchmark_rejects_docs_reference_output_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must not target docs/reference"):
        run_benchmark(
            output_json=Path("docs/reference/forbidden-story20-telemetry.json"),
            data_root=tmp_path / "runtime_data",
            total_jobs=3,
            max_workers=2,
            stub_work_seconds=0.0,
        )
