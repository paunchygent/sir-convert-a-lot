"""Task 12 scientific corpus harness tests.

Purpose:
    Validate deterministic schema/ordering, lane behavior, manual-review
    decision flow, and report composition for the scientific corpus benchmark harness.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.benchmark_scientific_corpus`.
    - Uses checked-in PDF fixtures via `tests.sir_convert_a_lot.pdf_fixtures`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

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
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client import ClientError, SubmittedJob
from tests.sir_convert_a_lot.pdf_fixtures import copy_fixture_pdf


class ScenarioEntry(TypedDict):
    """Fake lane/profile scenario for test harness client."""

    status: str
    backend_used: str
    acceleration_used: str
    warnings: list[str]
    markdown_content: str
    error_code: str


class FakeScientificClient:
    """Deterministic fake client for scientific benchmark harness tests."""

    scenario: dict[tuple[str, str, str], ScenarioEntry] = {}

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self._jobs: dict[str, ScenarioEntry] = {}

    def __enter__(self) -> "FakeScientificClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def submit_pdf_job(
        self,
        *,
        pdf_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        correlation_id: str | None = None,
    ) -> SubmittedJob:
        del wait_seconds, correlation_id
        conversion_obj = job_spec.get("conversion")
        assert isinstance(conversion_obj, dict)
        backend_obj = conversion_obj.get("backend_strategy")
        assert isinstance(backend_obj, str)
        key = (self.base_url, backend_obj, pdf_path.name)
        entry = self.scenario[key]
        job_id = f"job_{idempotency_key[-12:]}"
        self._jobs[job_id] = entry
        return SubmittedJob(job_id=job_id, status=JobStatus.QUEUED)

    def wait_for_terminal_status(
        self,
        job_id: str,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float = 0.2,
        correlation_id: str | None = None,
    ) -> JobStatus:
        del timeout_seconds, poll_interval_seconds, correlation_id
        entry = self._jobs[job_id]
        return JobStatus(entry["status"])

    def fetch_result_payload(
        self,
        job_id: str,
        *,
        correlation_id: str | None = None,
        inline: bool = True,
    ) -> dict[str, object]:
        del correlation_id, inline
        entry = self._jobs[job_id]
        if entry["status"] != JobStatus.SUCCEEDED.value:
            raise ClientError(
                code=entry["error_code"],
                message="simulated non-success result fetch",
                retryable=False,
                status_code=409,
                job_id=job_id,
            )
        return {
            "api_version": "v1",
            "job_id": job_id,
            "status": "succeeded",
            "result": {
                "artifact": {"markdown_filename": "x.md", "size_bytes": 1, "sha256": "abc"},
                "conversion_metadata": {
                    "backend_used": entry["backend_used"],
                    "acceleration_used": entry["acceleration_used"],
                    "ocr_enabled": False,
                    "table_mode": "accurate",
                    "options_fingerprint": "sha256:fixture",
                },
                "warnings": entry["warnings"],
                "markdown_content": entry["markdown_content"],
            },
        }


def _build_corpus(tmp_path: Path) -> tuple[Path, list[str]]:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True)
    filenames = ["paper_c.pdf", "paper_a.pdf", "paper_b.pdf"]
    for index, filename in enumerate(filenames):
        fixture = "paper_alpha.pdf" if index % 2 == 0 else "paper_beta.pdf"
        copy_fixture_pdf(corpus_dir / filename, fixture)
    return corpus_dir, filenames


def _default_scenario(filenames: list[str]) -> dict[tuple[str, str, str], ScenarioEntry]:
    scenario: dict[tuple[str, str, str], ScenarioEntry] = {}
    for filename in filenames:
        scenario[(DEFAULT_ACCEPTANCE_URL, "auto", filename)] = {
            "status": "succeeded",
            "backend_used": "docling",
            "acceleration_used": "cuda",
            "warnings": ["docling_auto_ocr_retry_applied"] if filename.endswith("a.pdf") else [],
            "markdown_content": f"# acceptance {filename}\n",
            "error_code": "job_not_succeeded",
        }
        scenario[(DEFAULT_EVALUATION_URL, "docling", filename)] = {
            "status": "succeeded",
            "backend_used": "docling",
            "acceleration_used": "cuda",
            "warnings": [],
            "markdown_content": f"# docling {filename}\n",
            "error_code": "job_not_succeeded",
        }
        scenario[(DEFAULT_EVALUATION_URL, "pymupdf", filename)] = {
            "status": "succeeded",
            "backend_used": "pymupdf",
            "acceleration_used": "cpu",
            "warnings": [],
            "markdown_content": f"# pymupdf {filename}\n",
            "error_code": "job_not_succeeded",
        }
    return scenario


def _write_rubric(
    *,
    rubric_path: Path,
    corpus_dir: Path,
    score_docling: tuple[int, int, int],
    score_pymupdf: tuple[int, int, int],
    manual_review_completed: bool = False,
    quality_winner: str | None = None,
    recommended_backend: str | None = None,
    follow_up_required: bool = False,
    follow_up_note: str | None = None,
) -> None:
    from scripts.sir_convert_a_lot.benchmark_scientific_corpus import _slug_for_pdf

    entries: list[dict[str, object]] = []
    for file_path in sorted(path for path in corpus_dir.glob("*.pdf") if path.is_file()):
        slug = _slug_for_pdf(file_path)
        entries.append(
            {
                "source_file": file_path.name,
                "document_slug": slug,
                "backend": "docling",
                "layout_fidelity": score_docling[0],
                "information_retention": score_docling[1],
                "legibility": score_docling[2],
                "notes": "docling score",
            }
        )
        p_layout, p_retention, p_legibility = score_pymupdf
        entries.append(
            {
                "source_file": file_path.name,
                "document_slug": slug,
                "backend": "pymupdf",
                "layout_fidelity": p_layout,
                "information_retention": p_retention,
                "legibility": p_legibility,
                "notes": "pymupdf score",
            }
        )
    manual_verdict: dict[str, object] | None = None
    if manual_review_completed and quality_winner is not None and recommended_backend is not None:
        manual_verdict = {
            "quality_winner": quality_winner,
            "recommended_production_backend": recommended_backend,
            "follow_up_required": follow_up_required,
            "follow_up_note": follow_up_note,
        }

    rubric_payload = {
        "generated_at": "2026-02-14T00:00:00Z",
        "auto_generated": False,
        "manual_review_completed": manual_review_completed,
        "manual_verdict": manual_verdict,
        "entries": entries,
    }
    rubric_path.parent.mkdir(parents=True, exist_ok=True)
    rubric_path.write_text(
        json.dumps(rubric_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def test_deterministic_ordering_and_output_keys(tmp_path: Path) -> None:
    corpus_dir, filenames = _build_corpus(tmp_path)
    FakeScientificClient.scenario = _default_scenario(filenames)
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
    corpus_dir, filenames = _build_corpus(tmp_path)
    FakeScientificClient.scenario = _default_scenario(filenames)
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
    corpus_dir, filenames = _build_corpus(tmp_path)
    scenario = _default_scenario(filenames)
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
    corpus_dir, filenames = _build_corpus(tmp_path)
    scenario = _default_scenario(filenames)
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
    corpus_dir, filenames = _build_corpus(tmp_path)
    FakeScientificClient.scenario = _default_scenario(filenames)
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
    corpus_dir, filenames = _build_corpus(tmp_path)
    FakeScientificClient.scenario = _default_scenario(filenames)
    rubric_path = tmp_path / "rubric.json"
    _write_rubric(
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
    from scripts.sir_convert_a_lot.benchmark_scientific_corpus import _slug_for_pdf

    first = _slug_for_pdf(Path("Document A.pdf"))
    second = _slug_for_pdf(Path("Document-A.pdf"))
    repeat = _slug_for_pdf(Path("Document A.pdf"))

    assert first == repeat
    assert first != second


def test_report_contains_required_sections_and_recommendation(tmp_path: Path) -> None:
    corpus_dir, filenames = _build_corpus(tmp_path)
    FakeScientificClient.scenario = _default_scenario(filenames)
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
