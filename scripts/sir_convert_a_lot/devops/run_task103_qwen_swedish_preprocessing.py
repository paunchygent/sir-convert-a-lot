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
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
    run_task103_preprocessing,
)

DEFAULT_OUTPUT_ROOT = Path("build/reference/qwen3-tts-swedish-corpus")
DEFAULT_ASR_MODEL = "KBLab/kb-whisper-large"
DEFAULT_ASR_REVISION = "strict"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"


def _parse_args(argv: list[str] | None) -> Task103PreprocessingSettings:
    """Parse CLI arguments into normalized Task 103 preprocessing settings."""
    parser = argparse.ArgumentParser(
        description="Run the first deterministic Task 103 Swedish preprocessing bundle."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--asr-model", default=DEFAULT_ASR_MODEL)
    parser.add_argument("--asr-revision", default=DEFAULT_ASR_REVISION)
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
    args = parser.parse_args(argv)
    return Task103PreprocessingSettings(
        output_root=Path(args.output_root),
        asr_model=str(args.asr_model),
        asr_revision=str(args.asr_revision),
        tokenizer_model=str(args.tokenizer_model),
    )


def _render_stdout_summary(report: Task103PreprocessingReport) -> str:
    """Render one stable stdout summary for the completed preprocessing run."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Run the Task 103 preprocessing bundle and print one JSON summary."""
    settings = _parse_args(argv)
    enforce_generated_output_path(settings.output_root, label="output_root")
    report = run_task103_preprocessing(settings)
    print(_render_stdout_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
