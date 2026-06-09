"""Report rendering for PDF throughput lane throughput benchmarking.

Purpose:
    Convert PDF throughput benchmark payloads into deterministic markdown reports that
    summarize profile comparisons, resource evidence, and rollout guidance.

Relationships:
    - Consumes payloads emitted by
      `scripts.sir_convert_a_lot.pdf_throughput_benchmark_report`.
    - Writes generated report artifacts under `build/benchmarks/governed-artifact/`.
"""

from __future__ import annotations

from pathlib import Path

from .pdf_throughput_types import (
    BenchmarkPayload,
    DirtyCorpusReportExtension,
    ProfilePayload,
)


def _render_profile_rows(profiles: list[ProfilePayload]) -> list[str]:
    lines = [
        (
            "| Profile | Success Rate | p50 | p90 | Peak Queue | "
            "Peak Chunk Saturation | Peak GPU Busy |"
        ),
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


def _render_dirty_corpus_section(dirty_corpus: DirtyCorpusReportExtension | None) -> list[str]:
    if dirty_corpus is None:
        return []
    manifest = dirty_corpus["manifest"]
    ocr_summary = dirty_corpus["ocr_metadata_summary"]
    failure_taxonomy = dirty_corpus["failure_taxonomy"]
    dirty_pdf_ocr_proof = dirty_corpus["dirty_pdf_ocr_proof"]
    lines = [
        "",
        "## Dirty Corpus Manifest",
        f"- Schema: `{manifest['schema_version']}`",
        f"- Corpus id: `{manifest['corpus_id']}`",
        f"- Entries: `{manifest['entry_count']}`",
        f"- Executed entries: `{manifest['executed_entry_count']}`",
        f"- Total pages: `{manifest['total_pages']}`",
        f"- Source hashes verified: `{manifest['source_hashes_verified']}`",
        f"- Real-data gate satisfied: `{manifest['real_data_gate_satisfied']}`",
        (
            "- Missing required dirty classes: "
            f"`{', '.join(manifest['missing_required_dirty_data_classes']) or 'none'}`"
        ),
        f"- Expected OCR languages: `{', '.join(manifest['expected_ocr_languages'])}`",
        f"- Privacy states: `{manifest['privacy_state_counts']}`",
        f"- Synthetic fixture entries: `{manifest['synthetic_fixture_entry_count']}`",
        f"- Safe excerpt entries: `{manifest['safe_excerpt_entry_count']}`",
        "",
        "## Dirty Corpus Safety",
        f"- All profiles inside safe matrix: `{dirty_corpus['all_profiles_safe']}`",
        f"- Hemma deploy verification parity required: `{dirty_corpus['deploy_parity_required']}`",
        f"- Hemma deploy verification parity proven: `{dirty_corpus['deploy_parity_proven']}`",
        "",
        "| Profile | Workers | GPU Stage Cap | Safe | Reason |",
        "|---|---:|---:|---|---|",
    ]
    for profile in dirty_corpus["profile_safety"]:
        lines.append(
            "| "
            f"{profile['profile_name']} | "
            f"{profile['max_chunk_workers']} | "
            f"{profile['gpu_stage_max_concurrency']} | "
            f"{profile['safe_profile']} | "
            f"{profile['unsafe_reason'] or ''} |"
        )
    lines.extend(
        [
            "",
            "## Dirty Corpus OCR Metadata",
            f"- OCR enabled jobs: `{ocr_summary['ocr_enabled_job_count']}`",
            f"- OCR engines used: `{', '.join(ocr_summary['ocr_engine_used_values']) or 'none'}`",
            (
                "- OCR languages used: "
                f"`{', '.join(ocr_summary['ocr_languages_used_values']) or 'none'}`"
            ),
            f"- Backends used: `{', '.join(ocr_summary['backend_used_values']) or 'none'}`",
            (
                "- Acceleration used: "
                f"`{', '.join(ocr_summary['acceleration_used_values']) or 'none'}`"
            ),
            "",
            "## Dirty Corpus Failure Taxonomy",
            f"- Failed jobs: `{failure_taxonomy['failed_job_count']}`",
            f"- Warnings: `{failure_taxonomy['warning_count']}`",
            (f"- Input-quality warnings: `{failure_taxonomy['input_quality_warning_count']}`"),
            (f"- Engine/runtime failures: `{failure_taxonomy['engine_runtime_failure_count']}`"),
            f"- Timeout failures: `{failure_taxonomy['timeout_failure_count']}`",
            f"- GPU/resource failures: `{failure_taxonomy['gpu_resource_failure_count']}`",
            f"- Conversion-bug failures: `{failure_taxonomy['conversion_bug_failure_count']}`",
            "",
            "## dirty PDF OCR final proof Final Proof Target",
            (
                "- Production service runtime: "
                f"`{dirty_pdf_ocr_proof['production_service_runtime']}`"
            ),
            f"- Target executed pages: `{dirty_pdf_ocr_proof['target_executed_pages']}`",
            f"- Target wall-clock seconds: `{dirty_pdf_ocr_proof['target_wall_clock_seconds']}`",
            f"- Tuned profile: `{dirty_pdf_ocr_proof['tuned_profile']}`",
            f"- Tuned total pages: `{dirty_pdf_ocr_proof['tuned_total_pages']}`",
            (f"- Tuned wall-clock seconds: `{dirty_pdf_ocr_proof['tuned_wall_clock_seconds']}`"),
            f"- Tuned success rate: `{dirty_pdf_ocr_proof['tuned_success_rate']}`",
            (f"- Meets 150-page target: `{dirty_pdf_ocr_proof['meets_150_page_target']}`"),
        ]
    )
    return lines


def write_report(
    *, report_path: Path, benchmark_json_path: Path, payload: BenchmarkPayload
) -> None:
    """Write deterministic markdown report for PDF throughput benchmark evidence output."""
    comparison = payload["comparison"]
    corpus = payload["corpus"]
    lines = [
        "---",
        "type: reference",
        "id: REF-pdf-throughput-throughput-report",
        "title: PDF throughput benchmark Throughput Benchmark Report",
        "status: active",
        f"created: '{payload['generated_at'][:10]}'",
        f"updated: '{payload['generated_at'][:10]}'",
        "owners:",
        "  - platform",
        "tags:",
        "  - benchmark",
        "  - performance",
        "  - throughput",
        "  - pdf-throughput",
        "links:",
        (
            "  - docs/backlog/tasks/"
            "pdf-throughput-run-throughput-benchmark-and-publish-performance-tuning-report.md"
        ),
        (
            "  - docs/backlog/stories/"
            "pdf-throughput-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md"
        ),
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
        "## Runtime Surface",
        f"- Benchmark mode: `{payload['runtime_surface']['mode']}`",
        f"- Benchmark host: `{payload['runtime_surface']['host'] or 'unspecified'}`",
        f"- Benchmark service URL: `{payload['runtime_surface']['service_url'] or 'n/a'}`",
        f"- Parity metadata source: `{payload['runtime_surface']['parity_source']}`",
        "",
        "## Runtime Parity",
        f"- Parity proven: `{payload['runtime_parity']['parity_proven']}`",
        f"- Hemma deploy verification status: `{payload['runtime_parity']['status'] or 'missing'}`",
        f"- Lane: `{payload['runtime_parity']['lane'] or 'missing'}`",
        f"- Expected revision: `{payload['runtime_parity']['expected_revision'] or 'missing'}`",
        f"- Remote revision: `{payload['runtime_parity']['remote_revision'] or 'missing'}`",
        f"- Service revision: `{payload['runtime_parity']['service_revision'] or 'missing'}`",
        (
            "- expected_revision_matches_remote: "
            f"`{payload['runtime_parity']['expected_revision_matches_remote']}`"
        ),
        (
            "- service_revision_matches_remote: "
            f"`{payload['runtime_parity']['service_revision_matches_remote']}`"
        ),
        f"- live_smoke_passed: `{payload['runtime_parity']['live_smoke_passed']}`",
        f"- metrics_scan_passed: `{payload['runtime_parity']['metrics_scan_passed']}`",
        "",
        "## Profile Comparison",
        *_render_profile_rows(payload["profiles"]),
        "",
        "## Outcome",
        f"- Baseline profile: `{comparison['baseline_profile']}`",
        f"- Tuned profile: `{comparison['tuned_profile']}`",
        f"- Improvement vs baseline (p50): `{comparison['p50_improvement_percent']}`%",
        f"- Meets PDF throughput benchmark target (`>= 40%`): `{comparison['meets_target']}`",
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
    lines.extend(_render_dirty_corpus_section(payload["dirty_corpus"]))
    if payload["runtime_parity"]["notes"]:
        lines.extend(["", "## Parity Notes"])
        for note in payload["runtime_parity"]["notes"]:
            lines.append(f"- {note}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
