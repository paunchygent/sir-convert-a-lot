"""Scientific-corpus evidence harness for Task 12.

Purpose:
    Execute the dual-lane Task 12 benchmark over the scientific-paper corpus
    and generate deterministic machine-readable and human-readable artifacts.

Relationships:
    - Orchestrates lane execution via `benchmarking/scientific_corpus_execution.py`.
    - Applies rubric + decision logic via `benchmarking/scientific_corpus_quality.py`.
    - Writes report artifact via `benchmarking/scientific_corpus_report.py`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_execution import run_lane
from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_quality import (
    compute_decision,
    load_or_initialize_rubric,
)
from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_report import write_report
from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_types import (
    BackendProfile,
    BenchmarkClientFactory,
    BenchmarkPayload,
)
from scripts.sir_convert_a_lot.benchmarking.scientific_corpus_utils import (
    discover_corpus,
    git_sha_or_unknown,
    slug_for_pdf,
    utc_now_iso,
)
from scripts.sir_convert_a_lot.interfaces.http_client import SirConvertALotClient

DEFAULT_CORPUS_DIR = Path(
    "/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater"
)
DEFAULT_OUTPUT_JSON = Path("docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json")
DEFAULT_OUTPUT_REPORT = Path("docs/reference/ref-production-pdf-md-scientific-corpus-validation.md")
DEFAULT_ARTIFACTS_ROOT = Path("docs/reference/artifacts/task-12-scientific-corpus")
DEFAULT_RUBRIC_PATH = DEFAULT_ARTIFACTS_ROOT / "manual-quality-rubric.json"
DEFAULT_ACCEPTANCE_URL = "http://127.0.0.1:28085"
DEFAULT_EVALUATION_URL = "http://127.0.0.1:28086"

# Backward-compatible alias used by tests and existing imports.
_slug_for_pdf = slug_for_pdf


def _acceptance_profiles() -> list[BackendProfile]:
    return [
        BackendProfile(
            profile_name="auto",
            backend_strategy="auto",
            ocr_mode="auto",
            table_mode="accurate",
            normalize="standard",
            acceleration_policy="gpu_required",
        )
    ]


def _evaluation_profiles() -> list[BackendProfile]:
    return [
        BackendProfile(
            profile_name="docling",
            backend_strategy="docling",
            ocr_mode="auto",
            table_mode="accurate",
            normalize="standard",
            acceleration_policy="gpu_required",
        ),
        BackendProfile(
            profile_name="pymupdf",
            backend_strategy="pymupdf",
            ocr_mode="off",
            table_mode="accurate",
            normalize="standard",
            acceleration_policy="cpu_only",
        ),
    ]


def run_benchmark(
    *,
    corpus_dir: Path,
    acceptance_service_url: str,
    evaluation_service_url: str,
    api_key: str,
    output_json: Path,
    output_report: Path,
    artifacts_root: Path,
    rubric_path: Path,
    local_sha: str | None,
    hemma_sha: str | None,
    max_poll_seconds: float,
    client_factory: BenchmarkClientFactory = SirConvertALotClient,
) -> BenchmarkPayload:
    """Run Task 12 dual-lane evidence benchmark and return payload."""
    pdf_paths, corpus_summary = discover_corpus(corpus_dir)
    acceptance_profiles = _acceptance_profiles()
    evaluation_profiles = _evaluation_profiles()

    acceptance_lane = run_lane(
        lane="acceptance",
        service_url=acceptance_service_url,
        api_key=api_key,
        profiles=acceptance_profiles,
        pdf_paths=pdf_paths,
        artifacts_root=artifacts_root,
        max_poll_seconds=max_poll_seconds,
        client_factory=client_factory,
    )
    evaluation_lane = run_lane(
        lane="evaluation",
        service_url=evaluation_service_url,
        api_key=api_key,
        profiles=evaluation_profiles,
        pdf_paths=pdf_paths,
        artifacts_root=artifacts_root,
        max_poll_seconds=max_poll_seconds,
        client_factory=client_factory,
    )

    rubric_payload = load_or_initialize_rubric(
        rubric_path=rubric_path,
        corpus_files=corpus_summary["files"],
        backends=[profile.profile_name for profile in evaluation_profiles],
    )
    decision, governance = compute_decision(
        evaluation_lane=evaluation_lane,
        rubric_payload=rubric_payload,
        corpus_files=corpus_summary["files"],
        production_profile=acceptance_profiles[0].to_job_spec_profile(),
    )

    resolved_local_sha = (
        local_sha if local_sha is not None and local_sha != "" else git_sha_or_unknown()
    )
    resolved_hemma_sha = (
        hemma_sha if hemma_sha is not None and hemma_sha != "" else resolved_local_sha
    )
    payload: BenchmarkPayload = {
        "benchmark_id": "task-12-scientific-corpus",
        "generated_at": utc_now_iso(),
        "service_revision": {"local_sha": resolved_local_sha, "hemma_sha": resolved_hemma_sha},
        "corpus": corpus_summary,
        "acceptance_lane": acceptance_lane,
        "evaluation_lane": evaluation_lane,
        "quality_rubric": rubric_payload,
        "decision": decision,
        "governance_compatibility": governance,
        "artifacts_root": str(artifacts_root.resolve()),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path=output_report, payload=payload)
    return payload


def main() -> None:
    """Parse CLI arguments and run Task 12 evidence harness."""
    parser = argparse.ArgumentParser(
        description="Run Task 12 scientific-corpus evidence benchmark."
    )
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--acceptance-service-url", default=DEFAULT_ACCEPTANCE_URL)
    parser.add_argument("--evaluation-service-url", default=DEFAULT_EVALUATION_URL)
    parser.add_argument("--api-key", required=False)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    parser.add_argument("--artifacts-root", type=Path, default=DEFAULT_ARTIFACTS_ROOT)
    parser.add_argument("--rubric-path", type=Path, default=DEFAULT_RUBRIC_PATH)
    parser.add_argument("--local-sha", default="")
    parser.add_argument("--hemma-sha", default="")
    parser.add_argument("--max-poll-seconds", type=float, default=1200.0)
    args = parser.parse_args()

    api_key = args.api_key
    if api_key is None or api_key.strip() == "":
        raise ValueError("Missing API key: provide --api-key.")

    payload = run_benchmark(
        corpus_dir=args.corpus_dir,
        acceptance_service_url=args.acceptance_service_url,
        evaluation_service_url=args.evaluation_service_url,
        api_key=api_key,
        output_json=args.output_json,
        output_report=args.output_report,
        artifacts_root=args.artifacts_root,
        rubric_path=args.rubric_path,
        local_sha=args.local_sha,
        hemma_sha=args.hemma_sha,
        max_poll_seconds=args.max_poll_seconds,
    )
    acceptance = payload["acceptance_lane"]["summary"]
    decision = payload["decision"]
    print(
        "task12-benchmark-written",
        args.output_json,
        f"acceptance_success={acceptance['succeeded_jobs']}/{acceptance['total_jobs']}",
        f"quality_winner={decision['quality_winner']}",
        f"recommended={decision['recommended_production_backend']}",
    )


if __name__ == "__main__":
    main()
