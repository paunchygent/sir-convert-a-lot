"""Report rendering for Task 12 scientific-corpus benchmarking.

Purpose:
    Convert benchmark payloads into deterministic human-readable markdown
    reference artifacts for Task 12 acceptance/evaluation evidence.

Relationships:
    - Consumes `BenchmarkPayload` from benchmark orchestration.
    - Writes report path referenced by Task 12 backlog documentation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .scientific_corpus_types import BenchmarkPayload, RankingEntry


def render_quality_table(ranking: list[RankingEntry]) -> str:
    """Render deterministic markdown table from ranking entries."""
    lines = [
        "| Backend | Median Score | Severe Failures | Success Rate | p50 Latency |",
        "|---|---:|---:|---:|---:|",
    ]
    for entry in ranking:
        lines.append(
            "| "
            f"{entry['backend']} | "
            f"{entry['median_weighted_score']:.3f} | "
            f"{entry['severe_quality_failures']} | "
            f"{entry['success_rate']:.3f} | "
            f"{entry['latency_p50']:.3f} |"
        )
    return "\n".join(lines)


def write_report(*, report_path: Path, payload: BenchmarkPayload) -> None:
    """Write deterministic markdown report for Task 12 evidence output."""
    acceptance_summary = payload["acceptance_lane"]["summary"]
    evaluation_summary = payload["evaluation_lane"]["summary"]
    decision = payload["decision"]
    governance = payload["governance_compatibility"]
    corpus = payload["corpus"]
    today_iso = datetime.now(UTC).date().isoformat()

    follow_up_lines = ["- None."]
    if decision["follow_up_required"]:
        follow_up_lines = [f"- {decision['follow_up_note']}"]
    task_12_doc_link = (
        "  - docs/backlog/tasks/"
        "task-12-scientific-paper-workload-evidence-harness-hemma-"
        "tunnel-acceptance-report-10-10-corpus.md"
    )
    acceptance_method_line = (
        "- Acceptance lane uses production-lock tunnel service profile (`auto`, `gpu_required`)."
    )
    evaluation_method_line = (
        "- Evaluation lane runs A/B (`docling` vs `pymupdf`) with isolated "
        "eval profile for CPU-only pymupdf."
    )
    succeeded_ratio = f"{acceptance_summary['succeeded_jobs']}/{acceptance_summary['total_jobs']}"
    recommendation_line = (
        f"- Adopt `{decision['recommended_production_backend']}` for production "
        "path based on quality-first ranking and governance constraints."
    )

    report_text = "\n".join(
        [
            "---",
            "type: reference",
            "id: REF-production-pdf-md-scientific-corpus-validation",
            "title: Production PDF->MD Scientific Corpus Validation (Task 12)",
            "status: active",
            f"created: '{today_iso}'",
            f"updated: '{today_iso}'",
            "owners:",
            "  - platform",
            "tags:",
            "  - benchmark",
            "  - task-12",
            "  - scientific-corpus",
            "  - hemma",
            "links:",
            task_12_doc_link,
            "  - docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json",
            "---",
            "",
            "## Corpus and Run Context",
            f"- Corpus path: `{corpus['path']}`",
            f"- Corpus size: `{corpus['count']}` PDFs",
            f"- Local SHA: `{payload['service_revision']['local_sha']}`",
            f"- Hemma SHA: `{payload['service_revision']['hemma_sha']}`",
            f"- Generated at: `{payload['generated_at']}`",
            "",
            "## Lane Methodology",
            acceptance_method_line,
            evaluation_method_line,
            "- Quality ranking uses weighted rubric and deterministic tie-breakers.",
            "",
            "## Acceptance 10/10 Gate",
            f"- Gate passed: `{payload['acceptance_lane']['gate_passed']}`",
            f"- Succeeded jobs: `{succeeded_ratio}`",
            f"- p50 latency: `{acceptance_summary['latency_seconds']['p50']}` seconds",
            f"- Retry warnings: `{acceptance_summary['retry_warnings_total']}`",
            "",
            "## A/B Quality Results",
            render_quality_table(decision["ranking"]),
            "",
            f"- Evaluation lane success rate: `{evaluation_summary['success_rate']}`",
            "",
            "## Governance Compatibility",
            f"- Quality winner: `{governance['quality_winner']}`",
            (
                "- Winner compatible for production profile: "
                f"`{governance['quality_winner_compatible_for_production']}`"
            ),
            f"- Recommended production backend: `{governance['recommended_production_backend']}`",
            "",
            "## Final Recommendation",
            recommendation_line,
            "",
            "## Follow-up Actions",
            *follow_up_lines,
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
