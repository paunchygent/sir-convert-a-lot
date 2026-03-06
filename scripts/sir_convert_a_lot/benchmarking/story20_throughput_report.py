"""Report rendering for Story 20 throughput benchmarking.

Purpose:
    Convert Task 74 benchmark payloads into deterministic markdown reports that
    summarize profile comparisons, resource evidence, and rollout guidance.

Relationships:
    - Consumes payloads emitted by
      `scripts.sir_convert_a_lot.benchmark_story20_throughput_report`.
    - Writes generated report artifacts under `build/benchmarks/story-20/`.
"""

from __future__ import annotations

from pathlib import Path

from .story20_throughput_types import BenchmarkPayload, ProfilePayload


def _render_profile_rows(profiles: list[ProfilePayload]) -> list[str]:
    lines = [
        "| Profile | Success Rate | p50 | p90 | Peak Queue | Peak Chunk Saturation | Peak GPU Busy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for profile in profiles:
        summary = profile["summary"]
        resource = profile["resource_evidence"]
        lines.append(
            "| "
            f"{profile['profile_name']} | "
            f"{summary['success_rate']:.3f} | "
            f"{summary['latency_seconds']['p50']:.3f} | "
            f"{summary['latency_seconds']['p90']:.3f} | "
            f"{resource['peak_jobs_queued']:.0f} | "
            f"{resource['peak_chunk_worker_saturation_ratio']:.3f} | "
            f"{resource['peak_gpu_busy_percent']:.1f} |"
        )
    return lines


def write_report(
    *, report_path: Path, benchmark_json_path: Path, payload: BenchmarkPayload
) -> None:
    """Write deterministic markdown report for Task 74 evidence output."""
    comparison = payload["comparison"]
    corpus = payload["corpus"]
    lines = [
        "---",
        "type: reference",
        "id: REF-task-74-throughput-report",
        "title: Task 74 Throughput Benchmark Report",
        "status: active",
        f"created: '{payload['generated_at'][:10]}'",
        f"updated: '{payload['generated_at'][:10]}'",
        "owners:",
        "  - platform",
        "tags:",
        "  - benchmark",
        "  - performance",
        "  - throughput",
        "  - story-20",
        "links:",
        "  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md",
        "  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md",
        "  - docs/runbooks/runbook-hemma-devops-and-gpu.md",
        f"  - {benchmark_json_path.as_posix()}",
        "---",
        "",
        "## Corpus",
        f"- Mode: `{payload['mode']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Corpus root: `{corpus['corpus_root']}`",
        f"- Files: `{corpus['count']}`",
        f"- Page counts: `{', '.join(str(value) for value in corpus['page_counts'])}`",
        f"- OCR mode: `{payload['job_defaults']['ocr_mode']}`",
        f"- OCR engine: `{payload['job_defaults']['ocr_engine']}`",
        f"- OCR languages: `{', '.join(payload['job_defaults']['ocr_languages'])}`",
        "",
        "## Profile Comparison",
        *_render_profile_rows(payload["profiles"]),
        "",
        "## Outcome",
        f"- Baseline profile: `{comparison['baseline_profile']}`",
        f"- Tuned profile: `{comparison['tuned_profile']}`",
        f"- Improvement vs baseline (p50): `{comparison['p50_improvement_percent']}`%",
        f"- Meets Task 74 target (`>= 40%`): `{comparison['meets_target']}`",
        f"- Recommended profile: `{comparison['recommended_profile']}`",
        "",
        "## Recommended Defaults",
    ]
    recommended_defaults = comparison["recommended_defaults"]
    for key, value in recommended_defaults.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Rollback Conditions",
        ]
    )
    rollback_conditions = comparison["rollback_conditions"]
    for item in rollback_conditions:
        lines.append(f"- {item}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
