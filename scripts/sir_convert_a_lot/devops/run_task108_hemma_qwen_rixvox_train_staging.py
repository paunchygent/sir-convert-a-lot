"""Run the bounded Task 108 RixVox train staging surface on Hemma.

Purpose:
    Provide the committed argv-friendly Hemma entrypoint that stages
    revision-pinned `train_metadata.parquet` and a bounded set of
    `data/train/train_<n>.tar.gz` archives for the Qwen Swedish fine-tuning
    lane.

Relationships:
    - Uses `task108_qwen_rixvox_train_staging_runtime.py`.
    - Writes deterministic evidence under
      `build/reference/qwen3-tts-swedish-corpus/rixvox-train-staging/`.
    - Supplies raw train assets for the next Task 108 preprocessing slice.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_PAUSE_SECONDS,
    default_data_root,
    default_hf_cache_dir,
)
from scripts.sir_convert_a_lot.devops.task108_qwen_rixvox_train_staging_runtime import (
    Task108RixvoxTrainStagingReport,
    Task108RixvoxTrainStagingSettings,
    normalize_train_audio_shards,
    run_task108_rixvox_train_staging,
)

DEFAULT_OUTPUT_ROOT = Path("build/reference/qwen3-tts-swedish-corpus/rixvox-train-staging")
DEFAULT_TRAIN_AUDIO_SHARDS = (0,)


def _parse_args(argv: list[str] | None) -> Task108RixvoxTrainStagingSettings:
    """Parse CLI arguments into normalized Task 108 staging settings."""
    parser = argparse.ArgumentParser(
        description="Run the bounded Task 108 RixVox train staging surface on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    parser.add_argument(
        "--train-audio-shard",
        action="append",
        dest="train_audio_shards",
        type=int,
        default=None,
        help="Repeat to stage additional RixVox train_<n>.tar.gz archives.",
    )
    parser.add_argument(
        "--request-pause-seconds",
        type=float,
        default=DEFAULT_REQUEST_PAUSE_SECONDS,
    )
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    args = parser.parse_args(argv)
    parsed_shards = tuple(args.train_audio_shards or DEFAULT_TRAIN_AUDIO_SHARDS)
    return Task108RixvoxTrainStagingSettings(
        output_root=Path(args.output_root),
        data_root=Path(args.data_root),
        hf_cache_dir=Path(args.hf_cache_dir),
        train_audio_shards=normalize_train_audio_shards(parsed_shards),
        request_pause_seconds=float(args.request_pause_seconds),
        max_retries=int(args.max_retries),
    )


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_report_markdown(report: Task108RixvoxTrainStagingReport) -> str:
    """Render one concise markdown summary for Task 108 train staging."""
    staged_lines = "\n".join(
        f"- `{record.filename}` -> `{record.staged_path}`" for record in report.downloaded_files
    )
    return (
        "# Task 108 RixVox Train Staging Report\n\n"
        f"- data_root: `{report.data_root}`\n"
        f"- hf_cache_dir: `{report.hf_cache_dir}`\n"
        f"- dataset_revision: `{report.dataset_revision}`\n"
        f"- train_audio_shards: `{report.train_audio_shards}`\n"
        f"- train_metadata_staged: `{report.train_metadata_staged}`\n"
        f"- train_audio_archive_count: `{report.train_audio_archive_count}`\n\n"
        "## Staged Files\n\n"
        f"{staged_lines}\n"
    )


def _render_stdout_summary(report: Task108RixvoxTrainStagingReport) -> str:
    """Render one stable stdout summary for the completed Task 108 staging run."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Run the bounded Task 108 staging pass and emit deterministic evidence."""
    settings = _parse_args(argv)
    report_json_path = settings.output_root / "report.json"
    report_md_path = settings.output_root / "report.md"
    enforce_generated_output_path(report_json_path, label="task108_report_json")
    enforce_generated_output_path(report_md_path, label="task108_report_md")
    report = run_task108_rixvox_train_staging(settings)
    _write_json(report_json_path, asdict(report))
    report_md_path.write_text(_build_report_markdown(report) + "\n", encoding="utf-8")
    print(_render_stdout_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
