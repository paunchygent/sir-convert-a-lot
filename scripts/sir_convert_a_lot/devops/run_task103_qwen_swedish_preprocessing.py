"""Run the canonical Task 103 Swedish preprocessing bundle.

Purpose:
    Provide one committed CLI surface for the staged Qwen3-TTS Swedish
    preprocessing pipeline so the repo can materialize deterministic inventory,
    curated, raw, and prepared manifests inside immutable per-run roots and
    optionally promote successful runs into the canonical shared corpus view.

Relationships:
    - Wraps `task103_qwen_preprocessing_core.py`.
    - Emits artifacts under `build/reference/qwen3-tts-swedish-corpus/`.
    - Implements the executable surface promised by
      `task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md`.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Sequence

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    CANONICAL_MANIFEST_FAMILIES,
    ManifestFamily,
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
    run_task103_preprocessing,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_run_roots import (
    Task103RunContext,
    prepare_run_root,
    promote_run_root,
    resolve_run_context,
    write_run_metadata,
    write_run_status,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import SourceRecord
from scripts.sir_convert_a_lot.devops.task103_qwen_staged_public_corpus import (
    staged_public_corpus_source_records,
)
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    default_data_root,
    ensure_bulk_data_storage_path,
)

DEFAULT_OUTPUT_ROOT = Path("build/reference/qwen3-tts-swedish-corpus")
DEFAULT_RUNS_ROOT = Path("build/runs/qwen3-tts-swedish-preprocessing")
DEFAULT_ASR_MODEL = "KBLab/kb-whisper-large"
DEFAULT_ASR_REVISION = "strict"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_SOURCE_MODE = "repo-fixture"
DEFAULT_FLEURS_SPLITS = ("dev", "test")
DEFAULT_RIXVOX_SPLITS = ("dev", "test")
DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT: int | None = None
DEFAULT_RIXVOX_MAX_ROWS_PER_SPLIT: int | None = None
DEFAULT_STAGE = "all"
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 8
DEFAULT_ROW_WORKER_COUNT = 1
DEFAULT_GPU_ASR_WORKER_COUNT = 1
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
    rixvox_max_rows_per_split: int | None
    runs_root: Path
    run_id: str | None
    run_root: Path | None
    promote_on_success: bool


def _parse_csv_list(raw_value: str) -> tuple[str, ...]:
    """Parse one comma-separated CLI list into a normalized tuple."""
    rendered_values = tuple(value.strip() for value in raw_value.split(",") if value.strip() != "")
    if not rendered_values:
        raise SystemExit("Expected at least one split value.")
    return rendered_values


def _parse_manifest_families(raw_value: str) -> tuple[ManifestFamily, ...]:
    """Parse one manifest-family CSV list into typed family literals."""
    rendered_values = _parse_csv_list(raw_value)
    typed_values: list[ManifestFamily] = []
    for value in rendered_values:
        if value == "swedish_smoke_train":
            typed_values.append("swedish_smoke_train")
            continue
        if value == "swedish_pilot_train":
            typed_values.append("swedish_pilot_train")
            continue
        if value == "swedish_scaleup_train":
            typed_values.append("swedish_scaleup_train")
            continue
        if value == "swedish_checkpoint_dev":
            typed_values.append("swedish_checkpoint_dev")
            continue
        if value == "swedish_final_test":
            typed_values.append("swedish_final_test")
            continue
        if value == "swedish_waxholm_control":
            typed_values.append("swedish_waxholm_control")
            continue
        raise SystemExit(f"Unknown manifest family: {value}")
    return tuple(typed_values)


def _parse_args(argv: list[str] | None) -> Task103RunnerSettings:
    """Parse CLI arguments into normalized Task 103 preprocessing settings."""
    parser = argparse.ArgumentParser(
        description="Run the canonical Task 103 Swedish preprocessing bundle."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument(
        "--promote-on-success",
        action="store_true",
        help="Promote the completed run root into the canonical shared corpus path.",
    )
    parser.add_argument("--asr-model", default=DEFAULT_ASR_MODEL)
    parser.add_argument("--asr-revision", default=DEFAULT_ASR_REVISION)
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
    parser.add_argument(
        "--stage",
        choices=("all", "row-processing", "finalization", "reports"),
        default=DEFAULT_STAGE,
    )
    parser.add_argument(
        "--finalization-families",
        default=",".join(CANONICAL_MANIFEST_FAMILIES),
    )
    parser.add_argument(
        "--audio-codes-chunk-size",
        type=int,
        default=DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    )
    parser.add_argument(
        "--row-worker-count",
        type=int,
        default=DEFAULT_ROW_WORKER_COUNT,
    )
    parser.add_argument(
        "--gpu-asr-worker-count",
        type=int,
        default=DEFAULT_GPU_ASR_WORKER_COUNT,
    )
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
    parser.add_argument(
        "--rixvox-max-rows-per-split",
        type=int,
        default=DEFAULT_RIXVOX_MAX_ROWS_PER_SPLIT,
    )
    args = parser.parse_args(argv)
    return Task103RunnerSettings(
        preprocessing=Task103PreprocessingSettings(
            output_root=Path(args.output_root),
            asr_model=str(args.asr_model),
            asr_revision=str(args.asr_revision),
            tokenizer_model=str(args.tokenizer_model),
            stage=args.stage,
            finalization_families=_parse_manifest_families(str(args.finalization_families)),
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            row_worker_count=int(args.row_worker_count),
            gpu_asr_worker_count=int(args.gpu_asr_worker_count),
        ),
        source_mode=args.source_mode,
        data_root=Path(args.data_root),
        fleurs_splits=_parse_csv_list(str(args.fleurs_splits)),
        fleurs_max_rows_per_split=args.fleurs_max_rows_per_split,
        rixvox_splits=_parse_csv_list(str(args.rixvox_splits)),
        rixvox_max_rows_per_split=args.rixvox_max_rows_per_split,
        runs_root=Path(args.runs_root),
        run_id=None if args.run_id is None else str(args.run_id),
        run_root=None if args.run_root is None else Path(args.run_root),
        promote_on_success=bool(args.promote_on_success),
    )


def _resolve_source_records(
    settings: Task103RunnerSettings,
) -> Sequence[SourceRecord] | None:
    """Resolve source records for one requested Task 103 runner mode."""
    if settings.source_mode == "repo-fixture":
        return None
    ensure_bulk_data_storage_path(settings.data_root, label="data_root")
    return list(
        staged_public_corpus_source_records(
            settings.data_root,
            fleurs_splits=settings.fleurs_splits,
            fleurs_max_rows_per_split=settings.fleurs_max_rows_per_split,
            rixvox_splits=settings.rixvox_splits,
            rixvox_max_rows_per_split=settings.rixvox_max_rows_per_split,
        )
    )


def _render_stdout_summary(report: Task103PreprocessingReport) -> str:
    """Render one stable stdout summary for the completed preprocessing run."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)


def _resolve_run_context(settings: Task103RunnerSettings) -> Task103RunContext:
    """Resolve the effective run-root context for one Task 103 invocation."""
    return resolve_run_context(
        promoted_root=settings.preprocessing.output_root,
        runs_root=settings.runs_root,
        source_mode=settings.source_mode,
        run_id=settings.run_id,
        run_root=settings.run_root,
        promote_on_success=settings.promote_on_success,
    )


def _runner_payload(
    settings: Task103RunnerSettings,
    context: Task103RunContext,
) -> dict[str, object]:
    """Render a stable run-metadata payload for one Task 103 invocation."""
    return {
        "source_mode": settings.source_mode,
        "data_root": settings.data_root.as_posix(),
        "fleurs_splits": list(settings.fleurs_splits),
        "fleurs_max_rows_per_split": settings.fleurs_max_rows_per_split,
        "rixvox_splits": list(settings.rixvox_splits),
        "rixvox_max_rows_per_split": settings.rixvox_max_rows_per_split,
        "runs_root": settings.runs_root.as_posix(),
        "run_id": context.run_id,
        "run_root": context.run_root.as_posix(),
        "promoted_root": context.promoted_root.as_posix(),
        "promote_on_success": context.promote_on_success,
        "preprocessing": asdict(
            Task103PreprocessingSettings(
                output_root=context.run_root,
                asr_model=settings.preprocessing.asr_model,
                asr_revision=settings.preprocessing.asr_revision,
                tokenizer_model=settings.preprocessing.tokenizer_model,
                stage=settings.preprocessing.stage,
                finalization_families=settings.preprocessing.finalization_families,
                audio_codes_chunk_size=settings.preprocessing.audio_codes_chunk_size,
                row_worker_count=settings.preprocessing.row_worker_count,
                gpu_asr_worker_count=settings.preprocessing.gpu_asr_worker_count,
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the Task 103 preprocessing bundle and print one JSON summary."""
    settings = _parse_args(argv)
    enforce_generated_output_path(settings.preprocessing.output_root, label="output_root")
    context = _resolve_run_context(settings)
    prepare_run_root(context)
    write_run_metadata(
        context,
        source_mode=settings.source_mode,
        stage=settings.preprocessing.stage,
        runner_payload=_runner_payload(settings, context),
    )
    write_run_status(
        context,
        source_mode=settings.source_mode,
        stage=settings.preprocessing.stage,
        status="allocated",
    )
    source_records = _resolve_source_records(settings)
    effective_settings = Task103PreprocessingSettings(
        output_root=context.run_root,
        asr_model=settings.preprocessing.asr_model,
        asr_revision=settings.preprocessing.asr_revision,
        tokenizer_model=settings.preprocessing.tokenizer_model,
        stage=settings.preprocessing.stage,
        finalization_families=settings.preprocessing.finalization_families,
        audio_codes_chunk_size=settings.preprocessing.audio_codes_chunk_size,
        row_worker_count=settings.preprocessing.row_worker_count,
        gpu_asr_worker_count=settings.preprocessing.gpu_asr_worker_count,
    )
    try:
        write_run_status(
            context,
            source_mode=settings.source_mode,
            stage=settings.preprocessing.stage,
            status="running",
        )
        report = run_task103_preprocessing(effective_settings, source_records=source_records)
    except Exception:
        rendered_error = traceback.format_exc().strip()
        write_run_status(
            context,
            source_mode=settings.source_mode,
            stage=settings.preprocessing.stage,
            status="failed",
            error=rendered_error,
        )
        raise
    if context.promote_on_success and effective_settings.stage in {"all", "finalization"}:
        promote_run_root(context)
    write_run_status(
        context,
        source_mode=settings.source_mode,
        stage=settings.preprocessing.stage,
        status="promoted"
        if context.promote_on_success and effective_settings.stage in {"all", "finalization"}
        else "completed",
    )
    print(_render_stdout_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
