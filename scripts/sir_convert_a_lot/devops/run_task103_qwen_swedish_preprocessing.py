"""Run the first deterministic Task 103 Swedish preprocessing bundle.

Purpose:
    Provide one committed CLI surface for the initial Qwen3-TTS Swedish
    preprocessing pass so the repo can materialize deterministic inventory,
    curated, raw, and prepared manifests without ad hoc notebooks.

Relationships:
    - Wraps `task103_qwen_preprocessing_core.py`.
    - Emits artifacts under `build/reference/qwen3-tts-swedish-corpus/`.
    - Implements the executable surface promised by
      `task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Sequence

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
    run_task103_preprocessing,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import SourceRecord
from scripts.sir_convert_a_lot.devops.task103_qwen_staged_public_corpus import (
    staged_public_corpus_source_records,
)
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    default_data_root,
    ensure_data_disk_path,
)

DEFAULT_OUTPUT_ROOT = Path("build/reference/qwen3-tts-swedish-corpus")
DEFAULT_ASR_MODEL = "KBLab/kb-whisper-large"
DEFAULT_ASR_REVISION = "strict"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_SOURCE_MODE = "repo-fixture"
DEFAULT_FLEURS_SPLITS = ("dev", "test")
DEFAULT_RIXVOX_SPLITS = ("dev", "test")
DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT: int | None = None
SourceMode = Literal["repo-fixture", "staged-public-corpus"]


@dataclass(frozen=True)
class Task103RunnerSettings:
    """Normalized CLI settings for Task 103 preprocessing entrypoints."""

    preprocessing: Task103PreprocessingSettings
    source_mode: SourceMode
    data_root: Path
    fleurs_splits: tuple[str, ...]
    fleurs_max_rows_per_split: int | None
    rixvox_splits: tuple[str, ...]


def _parse_csv_list(raw_value: str) -> tuple[str, ...]:
    """Parse one comma-separated CLI list into a normalized tuple."""
    rendered_values = tuple(
        value.strip() for value in raw_value.split(",") if value.strip() != ""
    )
    if not rendered_values:
        raise SystemExit("Expected at least one split value.")
    return rendered_values


def _parse_args(argv: list[str] | None) -> Task103RunnerSettings:
    """Parse CLI arguments into normalized Task 103 preprocessing settings."""
    parser = argparse.ArgumentParser(
        description="Run the first deterministic Task 103 Swedish preprocessing bundle."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--asr-model", default=DEFAULT_ASR_MODEL)
    parser.add_argument("--asr-revision", default=DEFAULT_ASR_REVISION)
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
    parser.add_argument(
        "--source-mode",
        choices=("repo-fixture", "staged-public-corpus"),
        default=DEFAULT_SOURCE_MODE,
    )
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--fleurs-splits", default=",".join(DEFAULT_FLEURS_SPLITS))
    parser.add_argument(
        "--fleurs-max-rows-per-split",
        type=int,
        default=DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    )
    parser.add_argument("--rixvox-splits", default=",".join(DEFAULT_RIXVOX_SPLITS))
    args = parser.parse_args(argv)
    return Task103RunnerSettings(
        preprocessing=Task103PreprocessingSettings(
            output_root=Path(args.output_root),
            asr_model=str(args.asr_model),
            asr_revision=str(args.asr_revision),
            tokenizer_model=str(args.tokenizer_model),
        ),
        source_mode=args.source_mode,
        data_root=Path(args.data_root),
        fleurs_splits=_parse_csv_list(str(args.fleurs_splits)),
        fleurs_max_rows_per_split=args.fleurs_max_rows_per_split,
        rixvox_splits=_parse_csv_list(str(args.rixvox_splits)),
    )


def _resolve_source_records(
    settings: Task103RunnerSettings,
) -> Sequence[SourceRecord] | None:
    """Resolve source records for one requested Task 103 runner mode."""
    if settings.source_mode == "repo-fixture":
        return None
    ensure_data_disk_path(settings.data_root, label="data_root")
    return staged_public_corpus_source_records(
        settings.data_root,
        fleurs_splits=settings.fleurs_splits,
        fleurs_max_rows_per_split=settings.fleurs_max_rows_per_split,
        rixvox_splits=settings.rixvox_splits,
    )


def _render_stdout_summary(report: Task103PreprocessingReport) -> str:
    """Render one stable stdout summary for the completed preprocessing run."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Run the Task 103 preprocessing bundle and print one JSON summary."""
    settings = _parse_args(argv)
    enforce_generated_output_path(settings.preprocessing.output_root, label="output_root")
    source_records = _resolve_source_records(settings)
    report = run_task103_preprocessing(settings.preprocessing, source_records=source_records)
    print(_render_stdout_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
