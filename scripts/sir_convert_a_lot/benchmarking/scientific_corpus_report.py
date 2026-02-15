"""Report rendering for Task 12 scientific-corpus benchmarking.

Purpose:
    Convert benchmark payloads into deterministic human-readable markdown
    artifacts for Task 12 acceptance/evaluation evidence.

Relationships:
    - Consumes `BenchmarkPayload` from benchmark orchestration.
    - Writes report path referenced by Task 12 backlog documentation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .scientific_corpus_types import BenchmarkPayload, LaneProfileResult


def _render_usage(usage: dict[str, int]) -> str:
    return ", ".join(f"{name}:{count}" for name, count in sorted(usage.items()))


def render_profile_metrics_table(profiles: list[LaneProfileResult]) -> str:
    """Render deterministic markdown table from profile execution summaries."""
    lines = [
        "| Backend | Success Rate | Succeeded/Total | "
        "p50 Latency | Backend Usage | Acceleration Usage |",
        "|---|---:|---:|---:|---|---|",
    ]
    for profile in profiles:
        summary = profile["summary"]
        succeeded_ratio = f"{summary['succeeded_jobs']}/{summary['total_jobs']}"
        lines.append(
            "| "
            f"{profile['profile_name']} | "
            f"{summary['success_rate']:.3f} | "
            f"{succeeded_ratio} | "
            f"{summary['latency_seconds']['p50']:.3f} | "
            f"{_render_usage(summary['backend_usage'])} | "
            f"{_render_usage(summary['acceleration_usage'])} |"
        )
    return "\n".join(lines)


def write_report(
    *, report_path: Path, benchmark_json_path: Path, payload: BenchmarkPayload
) -> None:
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
    manual_method_line = (
        "- Backend winner/recommendation is manual-review driven; no weighted "
        "automatic ranking is applied."
    )
    succeeded_ratio = f"{acceptance_summary['succeeded_jobs']}/{acceptance_summary['total_jobs']}"
    recommendation_line = "- Recommendation pending manual quality verdict."
    if decision["recommended_production_backend"] is not None:
        recommendation_line = (
            f"- Adopt `{decision['recommended_production_backend']}` for production "
            "path based on manual quality review and governance constraints."
        )
    manual_review_status_line = (
        f"- Manual review completed: `{decision['manual_review_completed']}`"
    )
    quality_winner_line = f"- Manual quality winner: `{decision['quality_winner'] or 'pending'}`"

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
            f"  - {benchmark_json_path.as_posix()}",
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
            manual_method_line,
            "",
            "## Acceptance 10/10 Gate",
            f"- Gate passed: `{payload['acceptance_lane']['gate_passed']}`",
            f"- Succeeded jobs: `{succeeded_ratio}`",
            f"- p50 latency: `{acceptance_summary['latency_seconds']['p50']}` seconds",
            f"- Retry warnings: `{acceptance_summary['retry_warnings_total']}`",
            "",
            "## A/B Execution Results",
            render_profile_metrics_table(payload["evaluation_lane"]["profiles"]),
            "",
            f"- Evaluation lane success rate: `{evaluation_summary['success_rate']}`",
            "",
            "## Manual Quality Verdict",
            manual_review_status_line,
            quality_winner_line,
            (
                f"- Manual recommended production backend: "
                f"`{decision['recommended_production_backend'] or 'pending'}`"
            ),
            "",
            "## Governance Compatibility",
            f"- Quality winner: `{governance['quality_winner'] or 'pending'}`",
            (
                "- Winner compatible for production profile: "
                f"`{governance['quality_winner_compatible_for_production']}`"
            ),
            (
                f"- Recommended production backend: "
                f"`{governance['recommended_production_backend'] or 'pending'}`"
            ),
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
