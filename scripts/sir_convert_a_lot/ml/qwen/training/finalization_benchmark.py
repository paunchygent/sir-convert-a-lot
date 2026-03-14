"""Finalization benchmark helpers for canonical Qwen training bundles.

Purpose:
    Materialize a small synthetic benchmark root from an existing training
    bundle so finalization throughput can be compared without mutating the
    source bundle.

Relationships:
    - Reuses canonical training-bundle helpers from `ml.qwen.training.bundles`.
    - Reuses preprocessing storage contracts for spool rows and copied audio.
    - Used by the public `cli/ml/qwen_finalization_benchmark.py` entrypoint.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import encode_audio_codes
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import SpoolRow
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import row_key_for_source_identity
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    iter_spool_rows,
    write_json,
    write_spool_row,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    DEFAULT_BATCH_ROW_COUNT,
    DEFAULT_CONTAINER_BATCH_SPAN,
    BundleBatchPlan,
    build_training_bundle,
    bundle_batch_is_complete,
    bundle_report_path,
    finalize_training_bundle_batch,
    load_training_bundle_batch_plan,
    prepare_training_bundle_inputs,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-finalization-benchmark")
DEFAULT_SOURCE_BATCH_COUNT = 4
DEFAULT_VARIANT_LABEL = "optimized"


@dataclass(frozen=True)
class FinalizationBenchmarkReport:
    """Machine-readable summary for one finalization benchmark variant."""

    variant_label: str
    source_bundle_root: str
    benchmark_root: str
    manifest_family: ManifestFamily
    source_start_batch_index: int
    source_batch_count: int
    benchmark_batch_row_count: int
    container_batch_span: int
    audio_codes_chunk_size: int
    selected_row_count: int
    planned_batch_count: int
    started_at: str
    completed_at: str
    duration_seconds: float
    rows_per_minute: float
    training_bundle_report_path: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def report_path(benchmark_root: Path) -> Path:
    """Return the canonical benchmark report path."""
    return benchmark_root / "reports" / "finalization_benchmark.json"


def build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for benchmark runs."""
    parser = argparse.ArgumentParser(description="Benchmark canonical Qwen finalization variants.")
    parser.add_argument("--source-bundle-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--variant-label", default=DEFAULT_VARIANT_LABEL)
    parser.add_argument(
        "--manifest-family",
        choices=("swedish_pilot_train", "swedish_checkpoint_dev"),
        default="swedish_pilot_train",
    )
    parser.add_argument("--source-start-batch-index", type=int, required=True)
    parser.add_argument("--source-batch-count", type=int, default=DEFAULT_SOURCE_BATCH_COUNT)
    parser.add_argument("--benchmark-batch-row-count", type=int, default=DEFAULT_BATCH_ROW_COUNT)
    parser.add_argument(
        "--audio-codes-chunk-size",
        type=int,
        default=DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    )
    parser.add_argument(
        "--container-batch-span",
        type=int,
        default=DEFAULT_CONTAINER_BATCH_SPAN,
    )
    return parser


def selected_family_rows(
    source_bundle_root: Path,
    *,
    manifest_family: ManifestFamily,
    source_start_batch_index: int,
    source_batch_count: int,
) -> tuple[BundleBatchPlan, list[SpoolRow]]:
    """Return one contiguous selected-row window from the source bundle root."""
    if source_batch_count <= 0:
        raise ValueError("`source_batch_count` must be positive.")
    source_plan = load_training_bundle_batch_plan(source_bundle_root)
    family_batches = [
        batch for batch in source_plan.batches if batch.manifest_family == manifest_family
    ]
    selected_batches = [
        batch
        for batch in family_batches
        if source_start_batch_index
        <= batch.batch_index
        < source_start_batch_index + source_batch_count
    ]
    if not selected_batches:
        raise ValueError(
            "Source bundle root does not contain "
            f"`{manifest_family}` batches starting at `{source_start_batch_index}`."
        )
    family_rows = [
        row
        for row in iter_spool_rows(source_bundle_root)
        if manifest_family in row.manifest_targets
    ]
    selected_row_start = selected_batches[0].batch_index * source_plan.finalization_batch_row_count
    selected_row_end = selected_row_start + sum(batch.row_count for batch in selected_batches)
    selected_rows = family_rows[selected_row_start:selected_row_end]
    if (
        selected_rows
        and row_key_for_source_identity(selected_rows[0]) != selected_batches[0].first_row_key
    ):
        raise ValueError("Selected benchmark rows did not preserve the first source row.")
    if (
        selected_rows
        and row_key_for_source_identity(selected_rows[-1]) != selected_batches[-1].last_row_key
    ):
        raise ValueError("Selected benchmark rows did not preserve the last source row.")
    return source_plan, selected_rows


def benchmark_eval_family(manifest_family: ManifestFamily) -> ManifestFamily:
    """Return a distinct family literal for benchmark-plan compatibility."""
    if manifest_family == "swedish_checkpoint_dev":
        return "swedish_pilot_train"
    return "swedish_checkpoint_dev"


def copy_selected_rows_into_benchmark_root(
    *,
    source_bundle_root: Path,
    benchmark_root: Path,
    selected_rows: list[SpoolRow],
) -> None:
    """Copy only the selected spool rows and local audio files."""
    for spool_row in selected_rows:
        write_spool_row(benchmark_root, spool_row)
        source_audio_path = source_bundle_root / spool_row.audio_24k_path
        target_audio_path = benchmark_root / spool_row.audio_24k_path
        target_audio_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_audio_path, target_audio_path)


def prepare_benchmark_root(
    *,
    source_bundle_root: Path,
    benchmark_root: Path,
    manifest_family: ManifestFamily,
    source_start_batch_index: int,
    source_batch_count: int,
    benchmark_batch_row_count: int,
) -> BundleBatchPlan:
    """Materialize a deterministic synthetic benchmark root from one source bundle."""
    enforce_generated_output_path(benchmark_root, label=benchmark_root.name)
    if benchmark_root.exists():
        raise ValueError(
            "Benchmark root already exists: "
            f"`{benchmark_root.as_posix()}`. Choose a new generated output root."
        )
    source_plan, selected_rows = selected_family_rows(
        source_bundle_root,
        manifest_family=manifest_family,
        source_start_batch_index=source_start_batch_index,
        source_batch_count=source_batch_count,
    )
    compatibility_family = benchmark_eval_family(manifest_family)
    _, compatibility_rows = selected_family_rows(
        source_bundle_root,
        manifest_family=compatibility_family,
        source_start_batch_index=0,
        source_batch_count=1,
    )
    benchmark_rows = [*selected_rows, *compatibility_rows]
    benchmark_root.mkdir(parents=True, exist_ok=True)
    copy_selected_rows_into_benchmark_root(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        selected_rows=benchmark_rows,
    )
    reports_root = benchmark_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    owned_row_keys_path = reports_root / "canonical_processed_root_owned_row_keys.jsonl"
    owned_row_keys_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "dataset": row.dataset,
                    "source_split": row.source_split,
                    "dataset_row_id": row.dataset_row_id,
                }
            )
            for row in benchmark_rows
        )
        + "\n",
        encoding="utf-8",
    )
    conflict_row_keys_path = reports_root / "canonical_processed_root_conflict_row_keys.jsonl"
    conflict_row_keys_path.write_text("", encoding="utf-8")
    write_json(
        reports_root / "canonical_processed_root_freeze.json",
        {
            "output_root": benchmark_root.as_posix(),
            "retained_row_count": len(benchmark_rows),
            "conflict_row_count": 0,
            "owned_row_keys_path": owned_row_keys_path.as_posix(),
            "conflict_row_keys_path": conflict_row_keys_path.as_posix(),
        },
    )
    return prepare_training_bundle_inputs(
        source_root=benchmark_root,
        output_root=benchmark_root,
        train_manifest_family=manifest_family,
        eval_manifest_family=benchmark_eval_family(manifest_family),
        tokenizer_model=source_plan.tokenizer_model,
        finalization_batch_row_count=benchmark_batch_row_count,
        repo_root=Path.cwd(),
    )


def run_finalization_benchmark(
    *,
    source_bundle_root: Path,
    benchmark_root: Path,
    variant_label: str,
    manifest_family: ManifestFamily,
    source_start_batch_index: int,
    source_batch_count: int,
    benchmark_batch_row_count: int,
    audio_codes_chunk_size: int,
    container_batch_span: int,
) -> FinalizationBenchmarkReport:
    """Run one deterministic finalization benchmark variant end to end."""
    plan = prepare_benchmark_root(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        manifest_family=manifest_family,
        source_start_batch_index=source_start_batch_index,
        source_batch_count=source_batch_count,
        benchmark_batch_row_count=benchmark_batch_row_count,
    )
    started_at = utc_now_iso()
    started_monotonic = time.monotonic()
    family_batches = [batch for batch in plan.batches if batch.manifest_family == manifest_family]
    for batch in family_batches:
        if bundle_batch_is_complete(benchmark_root, batch):
            continue
        finalize_training_bundle_batch(
            output_root=benchmark_root,
            plan=plan,
            manifest_family=batch.manifest_family,
            batch_index=batch.batch_index,
            audio_codes_chunk_size=audio_codes_chunk_size,
            encode_audio_codes_fn=encode_audio_codes,
        )
    build_training_bundle(
        source_root=benchmark_root,
        output_root=benchmark_root,
        train_manifest_family=manifest_family,
        eval_manifest_family=benchmark_eval_family(manifest_family),
        tokenizer_model=plan.tokenizer_model,
        finalization_batch_row_count=benchmark_batch_row_count,
        audio_codes_chunk_size=audio_codes_chunk_size,
        encode_audio_codes_fn=encode_audio_codes,
        repo_root=Path.cwd(),
    )
    duration_seconds = time.monotonic() - started_monotonic
    completed_at = utc_now_iso()
    training_bundle_report = json.loads(
        bundle_report_path(benchmark_root).read_text(encoding="utf-8")
    )
    report = FinalizationBenchmarkReport(
        variant_label=variant_label,
        source_bundle_root=source_bundle_root.as_posix(),
        benchmark_root=benchmark_root.as_posix(),
        manifest_family=manifest_family,
        source_start_batch_index=source_start_batch_index,
        source_batch_count=source_batch_count,
        benchmark_batch_row_count=benchmark_batch_row_count,
        container_batch_span=container_batch_span,
        audio_codes_chunk_size=audio_codes_chunk_size,
        selected_row_count=plan.family_row_counts[manifest_family],
        planned_batch_count=len(family_batches),
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        rows_per_minute=(plan.family_row_counts[manifest_family] / duration_seconds) * 60.0
        if duration_seconds > 0
        else 0.0,
        training_bundle_report_path=bundle_report_path(benchmark_root).as_posix(),
    )
    write_json(report_path(benchmark_root), report)
    write_json(
        benchmark_root / "reports" / "training_bundle_report_copy.json", training_bundle_report
    )
    return report


def main(argv: list[str] | None = None) -> int:
    """Run one finalization benchmark variant."""
    args = build_parser().parse_args(argv)
    benchmark_root = Path(args.output_root) / str(args.variant_label)
    report = run_finalization_benchmark(
        source_bundle_root=Path(args.source_bundle_root),
        benchmark_root=benchmark_root,
        variant_label=str(args.variant_label),
        manifest_family=args.manifest_family,
        source_start_batch_index=int(args.source_start_batch_index),
        source_batch_count=int(args.source_batch_count),
        benchmark_batch_row_count=int(args.benchmark_batch_row_count),
        audio_codes_chunk_size=int(args.audio_codes_chunk_size),
        container_batch_span=int(args.container_batch_span),
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0
