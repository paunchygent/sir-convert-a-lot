"""Run the Task 106 Hemma-only Qwen corpus acquisition surface.

Purpose:
    Provide one committed argv-friendly runner for staging the first real
    Swedish corpus assets on Hemma's HDD bulk-data tier without broad local
    snapshot downloads or deprecated dataset-script loading.

Relationships:
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run task-106-acquire`.
    - Uses `task106_qwen_corpus_acquisition_runtime.py`.
    - Writes deterministic evidence under
      `build/reference/qwen3-tts-swedish-corpus/acquisition/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    DEFAULT_FLEURS_SPLITS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_REQUEST_PAUSE_SECONDS,
    DEFAULT_RIXVOX_SPLITS,
    DEFAULT_WAXHOLM_MAX_FILES,
    Task106AcquisitionReport,
    Task106AcquisitionSettings,
    default_data_root,
    default_hf_cache_dir,
    run_task106_acquisition,
)


def _parse_args(argv: list[str] | None) -> Task106AcquisitionSettings:
    """Parse CLI arguments into normalized Task 106 acquisition settings."""
    parser = argparse.ArgumentParser(
        description="Run the Task 106 Hemma-only Qwen corpus acquisition surface."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    parser.add_argument("--waxholm-max-files", type=int, default=DEFAULT_WAXHOLM_MAX_FILES)
    parser.add_argument(
        "--request-pause-seconds",
        type=float,
        default=DEFAULT_REQUEST_PAUSE_SECONDS,
    )
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument(
        "--fleurs-split",
        action="append",
        dest="fleurs_splits",
        default=None,
        choices=["dev", "test"],
    )
    parser.add_argument(
        "--rixvox-split",
        action="append",
        dest="rixvox_splits",
        default=None,
        choices=["dev", "test"],
    )
    args = parser.parse_args(argv)
    fleurs_splits = tuple(args.fleurs_splits or DEFAULT_FLEURS_SPLITS)
    rixvox_splits = tuple(args.rixvox_splits or DEFAULT_RIXVOX_SPLITS)
    return Task106AcquisitionSettings(
        output_root=Path(args.output_root),
        data_root=Path(args.data_root),
        hf_cache_dir=Path(args.hf_cache_dir),
        fleurs_splits=fleurs_splits,
        rixvox_splits=rixvox_splits,
        waxholm_max_files=int(args.waxholm_max_files),
        request_pause_seconds=float(args.request_pause_seconds),
        max_retries=int(args.max_retries),
    )


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_report_markdown(report: Task106AcquisitionReport) -> str:
    """Render one concise markdown summary for Task 106 acquisition."""
    dataset_lines = "\n".join(
        f"- `{dataset}`: `{count}` files @ `{report.dataset_revisions[dataset]}`"
        for dataset, count in sorted(report.counts_by_dataset.items())
    )
    return (
        "# Task 106 Qwen Corpus Acquisition Report\n\n"
        f"- data_root: `{report.data_root}`\n"
        f"- hf_cache_dir: `{report.hf_cache_dir}`\n\n"
        "## Counts\n\n"
        f"{dataset_lines}\n"
    )


def _render_stdout_summary(report: Task106AcquisitionReport) -> str:
    """Render one stable stdout summary for the completed acquisition run."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Run the Task 106 acquisition pass and emit deterministic evidence."""
    settings = _parse_args(argv)
    report_json_path = settings.output_root / "report.json"
    report_md_path = settings.output_root / "report.md"
    enforce_generated_output_path(report_json_path, label="task106_report_json")
    enforce_generated_output_path(report_md_path, label="task106_report_md")
    report = run_task106_acquisition(settings)
    _write_json(report_json_path, asdict(report))
    report_md_path.write_text(_build_report_markdown(report) + "\n", encoding="utf-8")
    print(_render_stdout_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
