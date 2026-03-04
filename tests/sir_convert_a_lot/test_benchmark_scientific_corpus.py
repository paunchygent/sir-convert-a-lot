"""Task 12 scientific corpus harness tests.

Purpose:
    Validate deterministic schema/ordering, lane behavior, manual-review
    decision flow, and report composition for the scientific corpus benchmark harness.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.benchmark_scientific_corpus`.
    - Uses checked-in PDF fixtures via `tests.sir_convert_a_lot.pdf_fixtures`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.benchmark_scientific_corpus import (
    DEFAULT_ACCEPTANCE_URL,
    DEFAULT_ARTIFACTS_ROOT,
    DEFAULT_EVALUATION_URL,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_REPORT,
    DEFAULT_RUBRIC_PATH,
    run_benchmark,
)
from tests.sir_convert_a_lot.scientific_corpus_harness_fakes import (
    FakeScientificClient,
    build_corpus,
    default_scenario,
    write_rubric,
)


def test_deterministic_ordering_and_output_keys(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    FakeScientificClient.scenario = default_scenario(filenames)
    output_json = tmp_path / "task12.json"
    output_report = tmp_path / "task12.md"
    artifacts_root = tmp_path / "artifacts"
    rubric_path = tmp_path / "rubric.json"

    payload = run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=output_json,
        output_report=output_report,
        artifacts_root=artifacts_root,
        rubric_path=rubric_path,
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    assert list(payload.keys()) == [
        "benchmark_id",
        "generated_at",
        "service_revision",
        "corpus",
        "acceptance_lane",
        "evaluation_lane",
        "quality_rubric",
        "decision",
        "governance_compatibility",
        "artifacts_root",
    ]
    corpus_files = payload["corpus"]["files"]
    assert [entry["source_file"] for entry in corpus_files] == sorted(filenames)
    assert payload["decision"]["mode"] == "manual_review_only"
    assert payload["decision"]["manual_review_completed"] is False
    assert payload["decision"]["quality_winner"] is None
    assert payload["decision"]["recommended_production_backend"] is None
    assert output_json.exists()


def test_default_output_paths_are_outside_docs_reference() -> None:
    assert DEFAULT_OUTPUT_JSON.as_posix().startswith("build/")
    assert DEFAULT_OUTPUT_REPORT.as_posix().startswith("build/")
    assert DEFAULT_ARTIFACTS_ROOT.as_posix().startswith("build/")
    assert DEFAULT_RUBRIC_PATH.as_posix().startswith("build/")
    assert "docs/reference" not in DEFAULT_OUTPUT_JSON.as_posix()
    assert "docs/reference" not in DEFAULT_OUTPUT_REPORT.as_posix()


def test_rejects_docs_reference_output_paths() -> None:
    with pytest.raises(ValueError, match="must not target docs/reference"):
        run_benchmark(
            corpus_dir=Path("."),
            acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
            evaluation_service_url=DEFAULT_EVALUATION_URL,
            api_key="task12-key",
            output_json=Path("docs/reference/forbidden.json"),
            output_report=Path("build/task12.md"),
            artifacts_root=Path("build/task12-artifacts"),
            rubric_path=Path("build/task12-rubric.json"),
            local_sha="local-sha",
            hemma_sha="hemma-sha",
            max_poll_seconds=20.0,
            client_factory=FakeScientificClient,
        )


def test_summary_metrics_shape_and_counts(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    FakeScientificClient.scenario = default_scenario(filenames)
    output_json = tmp_path / "task12.json"
    output_report = tmp_path / "task12.md"

    payload = run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=output_json,
        output_report=output_report,
        artifacts_root=tmp_path / "artifacts",
        rubric_path=tmp_path / "rubric.json",
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    summary = payload["evaluation_lane"]["summary"]
    assert summary["total_jobs"] == 6
    assert summary["succeeded_jobs"] == 6
    assert summary["failed_jobs"] == 0
    latency = summary["latency_seconds"]
    assert set(latency.keys()) == {"min", "mean", "p50", "p90", "p99", "max"}
    assert latency["min"] <= latency["p50"] <= latency["p90"] <= latency["p99"] <= latency["max"]


def test_harness_records_gpu_runtime_unavailable_failures_deterministically(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    scenario = default_scenario(filenames)
    for filename in filenames:
        scenario[(DEFAULT_ACCEPTANCE_URL, "auto", filename)] = {
            "status": "failed",
            "backend_used": "docling",
            "acceleration_used": "cuda",
            "warnings": [],
            "markdown_content": "",
            "error_code": "gpu_not_available",
        }
    FakeScientificClient.scenario = scenario

    payload = run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=tmp_path / "task12.json",
        output_report=tmp_path / "task12.md",
        artifacts_root=tmp_path / "artifacts",
        rubric_path=tmp_path / "rubric.json",
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    acceptance = payload["acceptance_lane"]
    assert acceptance["gate_passed"] is False
    assert acceptance["summary"]["failed_jobs"] == len(filenames)
    for profile in acceptance["profiles"]:
        for record in profile["jobs"]:
            assert record["error_code"] == "gpu_not_available"
            assert record["output_markdown_path"] is None


def test_acceptance_lane_records_warnings_retries_backend_and_acceleration(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    scenario = default_scenario(filenames)
    scenario[(DEFAULT_ACCEPTANCE_URL, "auto", "paper_b.pdf")]["warnings"] = [
        "docling_auto_ocr_retry_applied",
        "minor_quality_warning",
    ]
    FakeScientificClient.scenario = scenario

    payload = run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=tmp_path / "task12.json",
        output_report=tmp_path / "task12.md",
        artifacts_root=tmp_path / "artifacts",
        rubric_path=tmp_path / "rubric.json",
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    summary = payload["acceptance_lane"]["summary"]
    assert summary["warnings_total"] >= 2
    assert summary["retry_warnings_total"] >= 1
    assert summary["backend_usage"] == {"docling": 3}
    assert summary["acceleration_usage"] == {"cuda": 3}


def test_evaluation_lane_emits_backend_profiles_and_artifacts(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    FakeScientificClient.scenario = default_scenario(filenames)
    artifacts_root = tmp_path / "artifacts"

    payload = run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=tmp_path / "task12.json",
        output_report=tmp_path / "task12.md",
        artifacts_root=artifacts_root,
        rubric_path=tmp_path / "rubric.json",
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    profiles = payload["evaluation_lane"]["profiles"]
    assert [profile["profile_name"] for profile in profiles] == ["docling", "pymupdf"]
    for profile in profiles:
        for record in profile["jobs"]:
            markdown_path = record["output_markdown_path"]
            metadata_path = record["output_metadata_path"]
            assert markdown_path is not None
            assert metadata_path is not None
            assert Path(markdown_path).exists()
            assert Path(metadata_path).exists()


def test_manual_verdict_is_governance_checked_without_auto_ranking(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    FakeScientificClient.scenario = default_scenario(filenames)
    rubric_path = tmp_path / "rubric.json"
    write_rubric(
        rubric_path=rubric_path,
        corpus_dir=corpus_dir,
        score_docling=(4, 4, 4),
        score_pymupdf=(4, 4, 4),
        manual_review_completed=True,
        quality_winner="pymupdf",
        recommended_backend="pymupdf",
        follow_up_required=False,
        follow_up_note=None,
    )

    payload = run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=tmp_path / "task12.json",
        output_report=tmp_path / "task12.md",
        artifacts_root=tmp_path / "artifacts",
        rubric_path=rubric_path,
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    decision = payload["decision"]
    governance = payload["governance_compatibility"]
    assert decision["mode"] == "manual_review_only"
    assert decision["manual_review_completed"] is True
    assert decision["quality_winner"] == "pymupdf"
    assert governance["quality_winner_compatible_for_production"] is False
    assert decision["recommended_production_backend"] == "docling"
    assert decision["follow_up_required"] is True
    assert decision["follow_up_note"] is not None


def test_document_slug_is_deterministic_and_collision_safe() -> None:
    from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_utils import slug_for_pdf

    first = slug_for_pdf(Path("Document A.pdf"))
    second = slug_for_pdf(Path("Document-A.pdf"))
    repeat = slug_for_pdf(Path("Document A.pdf"))

    assert first == repeat
    assert first != second


def test_report_contains_required_sections_and_recommendation(tmp_path: Path) -> None:
    corpus_dir, filenames = build_corpus(tmp_path)
    FakeScientificClient.scenario = default_scenario(filenames)
    report_path = tmp_path / "task12-report.md"
    output_json = tmp_path / "task12.json"

    run_benchmark(
        corpus_dir=corpus_dir,
        acceptance_service_url=DEFAULT_ACCEPTANCE_URL,
        evaluation_service_url=DEFAULT_EVALUATION_URL,
        api_key="task12-key",
        output_json=output_json,
        output_report=report_path,
        artifacts_root=tmp_path / "artifacts",
        rubric_path=tmp_path / "rubric.json",
        local_sha="local-sha",
        hemma_sha="hemma-sha",
        max_poll_seconds=20.0,
        client_factory=FakeScientificClient,
    )

    report = report_path.read_text(encoding="utf-8")
    assert "## Corpus and Run Context" in report
    assert "## Lane Methodology" in report
    assert "## Acceptance 10/10 Gate" in report
    assert "## A/B Execution Results" in report
    assert "## Manual Quality Verdict" in report
    assert "## Governance Compatibility" in report
    assert "## Final Recommendation" in report
    assert "## Follow-up Actions" in report
    assert output_json.as_posix() in report
