"""Test helpers for the scientific-corpus benchmark scientific-corpus benchmark harness.

Purpose:
    Keep scientific-corpus harness tests deterministic and readable by
    centralizing fakes, scenario builders, and rubric helpers.

Relationships:
    - Used by `tests.sir_convert_a_lot.test_benchmark_scientific_corpus`.
    - Exercises `scripts.sir_convert_a_lot.benchmark_scientific_corpus` via the
      same protocol used by the benchmark harness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from scripts.sir_convert_a_lot.benchmark_scientific_corpus import (
    DEFAULT_ACCEPTANCE_URL,
    DEFAULT_EVALUATION_URL,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ClientErrorV2,
    SubmittedJobV2,
)
from tests.sir_convert_a_lot.pdf_fixtures import copy_fixture_pdf


class ScenarioEntry(TypedDict):
    """Fake lane/profile scenario entry for harness client behavior."""

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

    def submit_job(
        self,
        *,
        source_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        correlation_id: str | None = None,
    ) -> SubmittedJobV2:
        del wait_seconds, correlation_id
        pdf_options_obj = job_spec.get("pdf_options")
        assert isinstance(pdf_options_obj, dict)
        backend_obj = pdf_options_obj.get("backend_strategy")
        assert isinstance(backend_obj, str)
        key = (self.base_url, backend_obj, source_path.name)
        entry = self.scenario[key]
        job_id = f"job_{idempotency_key[-12:]}"
        self._jobs[job_id] = entry
        return SubmittedJobV2(job_id=job_id, status=JobStatus.QUEUED)

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

    def get_result_payload(
        self,
        job_id: str,
        *,
        correlation_id: str | None = None,
    ) -> dict[str, object]:
        del correlation_id
        entry = self._jobs[job_id]
        if entry["status"] != JobStatus.SUCCEEDED.value:
            raise ClientErrorV2(
                code=entry["error_code"],
                message="simulated non-success result fetch",
                retryable=False,
                status_code=409,
                job_id=job_id,
            )
        return {
            "api_version": "v2",
            "job_id": job_id,
            "status": "succeeded",
            "result": {
                "conversion_metadata": {
                    "backend_used": entry["backend_used"],
                    "acceleration_used": entry["acceleration_used"],
                },
                "warnings": entry["warnings"],
            },
        }

    def download_artifact(self, job_id: str, *, correlation_id: str | None = None) -> bytes:
        del correlation_id
        entry = self._jobs[job_id]
        if entry["status"] != JobStatus.SUCCEEDED.value:
            raise ClientErrorV2(
                code="job_not_succeeded",
                message="simulated non-success artifact download",
                retryable=False,
                status_code=409,
                job_id=job_id,
            )
        return entry["markdown_content"].encode("utf-8")


def build_corpus(tmp_path: Path) -> tuple[Path, list[str]]:
    """Create a deterministic mini-corpus under tmp_path and return path + filenames."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True)
    filenames = ["paper_c.pdf", "paper_a.pdf", "paper_b.pdf"]
    for index, filename in enumerate(filenames):
        fixture = "paper_alpha.pdf" if index % 2 == 0 else "paper_beta.pdf"
        copy_fixture_pdf(corpus_dir / filename, fixture)
    return corpus_dir, filenames


def default_scenario(filenames: list[str]) -> dict[tuple[str, str, str], ScenarioEntry]:
    """Return deterministic baseline scenario for both lanes and both backends."""
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


def write_rubric(
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
    """Write a deterministic rubric JSON file for scientific-corpus benchmark manual-review logic
    tests.
    """
    from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_utils import slug_for_pdf

    entries: list[dict[str, object]] = []
    for file_path in sorted(path for path in corpus_dir.glob("*.pdf") if path.is_file()):
        slug = slug_for_pdf(file_path)
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
