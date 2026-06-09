"""Evaluate formula/OCR candidates on established Task 344 incident inputs.

Purpose:
    Build a bounded evidence bundle for specialist formula/document OCR
    candidates before any production formula-lane infrastructure is designed.

Relationships:
    - Consumes Task 344 page-window replay reports and rendered source pages.
    - Delegates input preparation, candidate execution, and report writing to
      Task 346 helper modules.
    - Produces local evidence only; it does not change conversion runtime.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.devops.task346_formula_candidate_eval_candidates import (
    BAD_MARKERS,
    CandidateSpec,
    candidate_sources,
    collect_marker_counts,
    default_external_candidates,
    run_external_candidate,
    run_granite_baseline,
    run_source_layer_baseline,
)
from scripts.sir_convert_a_lot.devops.task346_formula_candidate_eval_inputs import (
    SourceInput,
    build_source_inputs,
    harvest_formula_regions,
    limit_regions,
    load_source_inputs_from_report,
    parse_page_range,
    read_json_object,
    sha256_file,
    source_input_payload,
)
from scripts.sir_convert_a_lot.devops.task346_formula_candidate_eval_reporting import (
    candidate_dicts,
    render_visual_review_index,
    write_json,
    write_markdown_report,
)

__all__ = [
    "BAD_MARKERS",
    "CandidateSpec",
    "SourceInput",
    "collect_marker_counts",
    "harvest_formula_regions",
    "render_visual_review_index",
    "run_external_candidate",
]

DEFAULT_INPUT_ROOT = Path("build/verification/task-344-md-review-20260605T112725Z")
DEFAULT_OUTPUT_ROOT = Path("build/verification/task-346-formula-candidate-eval")
DEFAULT_PAGES = "13-16"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Task 346 candidate evaluation CLI."""
    args = build_parser().parse_args(argv)
    run_dir = Path(str(args.output_dir)) / utc_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    report = run_evaluation(args=args, run_dir=run_dir)
    write_json(run_dir / "report.json", report)
    write_markdown_report(path=run_dir / "report.md", payload=report)
    render_visual_review_index(
        path=run_dir / "visual-review.html",
        source_inputs=tuple(load_source_inputs_from_report(report)),
        candidate_results=tuple(candidate_dicts(report)),
    )
    print((run_dir / "report.json").as_posix())
    return 0


def run_evaluation(*, args: argparse.Namespace, run_dir: Path) -> dict[str, object]:
    """Build source evidence, execute candidates, and return the report payload."""
    input_root = Path(str(args.input_root))
    report_path = Path(str(args.incident_report))
    source_pdf = Path(str(args.source_pdf))
    baseline_markdown = Path(str(args.baseline_markdown))
    incident_report = read_json_object(report_path)
    pages = parse_page_range(str(args.pages))
    regions = harvest_formula_regions(incident_report, fallback_first_page=pages[0])
    limited_regions = limit_regions(regions, int(args.max_formula_crops))
    source_inputs = build_source_inputs(
        source_pdf=source_pdf,
        rendered_root=input_root / "rendered",
        regions=limited_regions,
        pages=pages,
        output_root=run_dir / "sources",
    )
    candidate_results = run_candidates(
        args=args,
        source_pdf=source_pdf,
        baseline_markdown=baseline_markdown,
        incident_report=incident_report,
        source_inputs=source_inputs,
        run_dir=run_dir,
    )
    return {
        "schema_version": "task346_formula_candidate_eval_v1",
        "run_id": run_dir.name,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_pdf": source_pdf.as_posix(),
        "source_sha256": sha256_file(source_pdf) if source_pdf.exists() else None,
        "incident_report": report_path.as_posix(),
        "baseline_markdown": baseline_markdown.as_posix(),
        "pages": list(pages),
        "formula_region_count": len(regions),
        "evaluated_formula_region_count": len(limited_regions),
        "source_inputs": [source_input_payload(source_input) for source_input in source_inputs],
        "candidate_results": candidate_results,
        "candidate_sources": candidate_sources(),
    }


def run_candidates(
    *,
    args: argparse.Namespace,
    source_pdf: Path,
    baseline_markdown: Path,
    incident_report: dict[str, object],
    source_inputs: Sequence[SourceInput],
    run_dir: Path,
) -> list[dict[str, object]]:
    """Run baseline and configured external candidate adapters."""
    results = [
        run_granite_baseline(
            baseline_markdown=baseline_markdown,
            incident_report=incident_report,
            output_root=run_dir / "candidates" / "granite_docling_baseline",
        ),
        run_source_layer_baseline(
            source_pdf=source_pdf,
            source_inputs=source_inputs,
            output_root=run_dir / "candidates" / "source_layer_pymupdf",
        ),
    ]
    for candidate in default_external_candidates():
        candidate_inputs = tuple(
            source_input
            for source_input in source_inputs
            if source_input.kind == candidate.input_kind
        )
        results.append(
            run_external_candidate(
                candidate=candidate,
                source_inputs=candidate_inputs,
                output_root=run_dir / "candidates" / candidate.candidate_id,
                executable=str(args.paddleocr_executable),
                device=str(args.paddle_device),
                paddle_template=args.paddle_formula_command,
                timeout_seconds=float(args.candidate_timeout_seconds),
                deepseek_template=args.deepseek_ocr2_command,
                deepseek_batch_template=args.deepseek_ocr2_batch_command,
            )
        )
    return results


def utc_run_id() -> str:
    """Return a stable timestamped run id."""
    return datetime.now(UTC).strftime("task346-formula-candidate-eval-%Y%m%dT%H%M%SZ")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--incident-report", type=Path, default=DEFAULT_INPUT_ROOT / "report.json")
    parser.add_argument("--source-pdf", type=Path, default=DEFAULT_INPUT_ROOT / "input.pdf")
    parser.add_argument(
        "--baseline-markdown",
        type=Path,
        default=DEFAULT_INPUT_ROOT / "p000013-000016.child.md",
    )
    parser.add_argument("--pages", default=DEFAULT_PAGES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-formula-crops", type=int, default=0)
    parser.add_argument("--candidate-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--paddleocr-executable", default=os.environ.get("PADDLEOCR", "paddleocr"))
    parser.add_argument("--paddle-device", default=os.environ.get("PADDLEOCR_DEVICE", "gpu"))
    parser.add_argument(
        "--paddle-formula-command",
        default=os.environ.get("SIR_CONVERT_A_LOT_TASK346_PADDLE_FORMULA_COMMAND"),
        help=(
            "Optional argv template with {input}, {output_dir}, {model}, and {device}; "
            "used when PaddleOCR's installed CLI does not expose formula recognition."
        ),
    )
    parser.add_argument(
        "--deepseek-ocr2-command",
        default=os.environ.get("SIR_CONVERT_A_LOT_TASK346_DEEPSEEK_OCR2_COMMAND"),
        help=(
            "Optional argv template with {input}, {output}, {output_dir}, and {model}; "
            "preferred for DeepSeek-OCR-2 HF eager page-image replay."
        ),
    )
    parser.add_argument(
        "--deepseek-ocr2-batch-command",
        default=os.environ.get("SIR_CONVERT_A_LOT_TASK346_DEEPSEEK_OCR2_BATCH_COMMAND"),
        help=(
            "Optional argv template with {input_dir}, {output_dir}, and {model}; "
            "kept for explicit DeepSeek-OCR-2/vLLM diagnostics only."
        ),
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
