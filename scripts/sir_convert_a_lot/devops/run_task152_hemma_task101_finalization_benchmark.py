"""Benchmark Task 101 pilot-bundle finalization throughput on Hemma.

Purpose:
    Materialize a small synthetic Task 101 benchmark root from an existing
    bundle root so we can compare governed finalization variants against the
    same selected rows without mutating the live operator bundle.

Relationships:
    - Reuses Task 101 batch-plan, bundle-build, and container-runtime helpers.
    - Depends on an existing Task 101 bundle root as the source of copied spool
      rows and `audio_24k` files.
    - Writes deterministic benchmark evidence under `build/verification/`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle import (
    DEFAULT_CONTAINER_BATCH_SPAN,
    DEFAULT_PILOT_BUNDLE_ROOT,
    build_task101_pilot_bundle,
    task101_pilot_bundle_report_path,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    Task101PilotBundleBatchPlan,
    build_task101_pilot_bundle_batch_plan,
    load_task101_pilot_bundle_batch_plan,
    render_task101_spool_row_key,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_execution import (
    task101_pilot_bundle_batch_is_complete,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    default_container_settings,
    prepare_task101_pilot_bundle_batch_runtime,
    run_containerized_task101_pilot_bundle_batch,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    encode_audio_codes,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_spool_rows,
    write_json,
    write_spool_row,
)
from scripts.sir_convert_a_lot.devops.task112_hemma_storage_runtime import (
    DEFAULT_SCRATCH_BUILD_ROOT,
)

DEFAULT_OUTPUT_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "verification/task-152-task101-finalization-benchmark"
)
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 64
DEFAULT_SOURCE_BATCH_COUNT = 4
DEFAULT_VARIANT_LABEL = "optimized"


@dataclass(frozen=True)
class Task152BenchmarkReport:
    """Machine-readable summary for one Task 152 Task 101 benchmark variant."""

    variant_label: str
    source_bundle_root: str
    benchmark_root: str
    manifest_family: ManifestFamily
    source_start_batch_index: int
    source_batch_count: int
    benchmark_batch_row_count: int
    container_batch_span: int
    audio_codes_chunk_size: int
    build_image: bool
    selected_row_count: int
    planned_batch_count: int
    started_at: str
    completed_at: str
    duration_seconds: float
    rows_per_minute: float
    task101_bundle_report_path: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _report_path(benchmark_root: Path) -> Path:
    """Return the canonical Task 152 benchmark report path."""
    return benchmark_root / "reports" / "task152_task101_finalization_benchmark.json"


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for Task 152 benchmark runs."""
    parser = argparse.ArgumentParser(
        description="Benchmark Task 101 governed finalization variants on Hemma."
    )
    parser.add_argument("--source-bundle-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--variant-label", default=DEFAULT_VARIANT_LABEL)
    parser.add_argument(
        "--manifest-family",
        choices=("swedish_pilot_train", "swedish_checkpoint_dev"),
        default="swedish_pilot_train",
    )
    parser.add_argument("--source-start-batch-index", type=int, required=True)
    parser.add_argument("--source-batch-count", type=int, default=DEFAULT_SOURCE_BATCH_COUNT)
    parser.add_argument("--benchmark-batch-row-count", type=int, required=True)
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
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Reuse the existing governed Task 100/101 image without `buildx build`.",
    )
    return parser


def _selected_family_rows(
    source_bundle_root: Path,
    *,
    manifest_family: ManifestFamily,
    source_start_batch_index: int,
    source_batch_count: int,
) -> tuple[Task101PilotBundleBatchPlan, list[SpoolRow]]:
    """Return one contiguous selected-row window from the source bundle root."""
    if source_batch_count <= 0:
        raise ValueError("`source_batch_count` must be positive.")
    source_plan = load_task101_pilot_bundle_batch_plan(source_bundle_root)
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
            f"Source bundle root does not contain `{manifest_family}` batches starting at "
            f"`{source_start_batch_index}`."
        )
    family_rows = [
        spool_row
        for spool_row in iter_spool_rows(source_bundle_root)
        if manifest_family in spool_row.manifest_targets
    ]
    selected_row_start = selected_batches[0].row_start_index
    selected_row_end = selected_batches[-1].row_end_exclusive
    selected_rows = family_rows[selected_row_start:selected_row_end]
    expected_row_count = sum(batch.row_count for batch in selected_batches)
    if len(selected_rows) != expected_row_count:
        raise ValueError(
            "Selected Task 152 benchmark rows did not match the expected source batch row count."
        )
    if (
        selected_rows
        and render_task101_spool_row_key(selected_rows[0]) != selected_batches[0].first_row_key
    ):
        raise ValueError("Selected Task 152 benchmark rows did not preserve the first source row.")
    if (
        selected_rows
        and render_task101_spool_row_key(selected_rows[-1]) != selected_batches[-1].last_row_key
    ):
        raise ValueError("Selected Task 152 benchmark rows did not preserve the last source row.")
    return source_plan, selected_rows


def _benchmark_eval_family(manifest_family: ManifestFamily) -> ManifestFamily:
    """Return a distinct family literal for benchmark-plan compatibility."""
    if manifest_family == "swedish_checkpoint_dev":
        return "swedish_pilot_train"
    return "swedish_checkpoint_dev"


def _copy_selected_rows_into_benchmark_root(
    *,
    source_bundle_root: Path,
    benchmark_root: Path,
    selected_rows: list[SpoolRow],
) -> None:
    """Copy only the selected Task 101 spool rows and `audio_24k` files."""
    for spool_row in selected_rows:
        write_spool_row(benchmark_root, spool_row)
        source_audio_path = source_bundle_root / spool_row.audio_24k_path
        target_audio_path = benchmark_root / spool_row.audio_24k_path
        target_audio_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_audio_path, target_audio_path)


def _prepare_benchmark_root(
    *,
    source_bundle_root: Path,
    benchmark_root: Path,
    manifest_family: ManifestFamily,
    source_start_batch_index: int,
    source_batch_count: int,
    benchmark_batch_row_count: int,
) -> Task101PilotBundleBatchPlan:
    """Materialize a deterministic synthetic benchmark root from one source bundle."""
    enforce_generated_output_path(benchmark_root, label=benchmark_root.name)
    if benchmark_root.exists():
        raise ValueError(
            f"Task 152 benchmark root already exists: `{benchmark_root.as_posix()}`. "
            "Choose a new generated output root."
        )
    if benchmark_batch_row_count <= 0:
        raise ValueError("`benchmark_batch_row_count` must be positive.")
    source_plan, selected_rows = _selected_family_rows(
        source_bundle_root,
        manifest_family=manifest_family,
        source_start_batch_index=source_start_batch_index,
        source_batch_count=source_batch_count,
    )
    compatibility_family = _benchmark_eval_family(manifest_family)
    _, compatibility_rows = _selected_family_rows(
        source_bundle_root,
        manifest_family=compatibility_family,
        source_start_batch_index=0,
        source_batch_count=1,
    )
    benchmark_rows = [*selected_rows, *compatibility_rows]
    benchmark_root.mkdir(parents=True, exist_ok=True)
    _copy_selected_rows_into_benchmark_root(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        selected_rows=benchmark_rows,
    )
    return build_task101_pilot_bundle_batch_plan(
        source_root=source_bundle_root,
        output_root=benchmark_root,
        train_manifest_family=manifest_family,
        eval_manifest_family=_benchmark_eval_family(manifest_family),
        tokenizer_model=source_plan.tokenizer_model,
        finalization_batch_row_count=benchmark_batch_row_count,
        retained_row_count=len(benchmark_rows),
        conflict_row_count=0,
        owned_row_keys_path=Path(source_plan.owned_row_keys_path),
        conflict_row_keys_path=Path(source_plan.conflict_row_keys_path),
        repo_head=source_plan.repo_head,
        generated_at=_utc_now_iso(),
    )


def _container_batch_count_for_benchmark(
    *,
    plan: Task101PilotBundleBatchPlan,
    benchmark_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
    requested_span: int,
) -> int:
    """Return the contiguous incomplete Task 101 benchmark batch span."""
    if requested_span <= 1:
        return 1
    selected_batches = [
        batch
        for batch in plan.batches
        if batch.manifest_family == manifest_family and batch.batch_index >= batch_index
    ]
    contiguous_count = 0
    expected_batch_index = batch_index
    for batch in selected_batches:
        if batch.batch_index != expected_batch_index:
            break
        if task101_pilot_bundle_batch_is_complete(benchmark_root, batch):
            break
        contiguous_count += 1
        expected_batch_index += 1
        if contiguous_count >= requested_span:
            break
    return max(contiguous_count, 1)


def run_task152_benchmark(
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
    build_image: bool,
) -> Task152BenchmarkReport:
    """Run one deterministic Task 152 benchmark variant end to end."""
    plan = _prepare_benchmark_root(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        manifest_family=manifest_family,
        source_start_batch_index=source_start_batch_index,
        source_batch_count=source_batch_count,
        benchmark_batch_row_count=benchmark_batch_row_count,
    )
    runtime_settings = replace(default_container_settings(), build_image=build_image)
    hf_mount, runtime_fingerprint = prepare_task101_pilot_bundle_batch_runtime(
        settings=runtime_settings
    )

    def _run_containerized_batch(
        output_root: Path,
        plan: Task101PilotBundleBatchPlan,
        batch_manifest_family: ManifestFamily,
        batch_index: int,
        batch_audio_codes_chunk_size: int,
        batch_encode_audio_codes_fn: object,
        repo_root: Path,
    ) -> None:
        del batch_encode_audio_codes_fn
        batch_count = _container_batch_count_for_benchmark(
            plan=plan,
            benchmark_root=output_root,
            manifest_family=batch_manifest_family,
            batch_index=batch_index,
            requested_span=container_batch_span,
        )
        run_containerized_task101_pilot_bundle_batch(
            repo_root=repo_root,
            output_root=output_root,
            manifest_family=batch_manifest_family,
            batch_index=batch_index,
            batch_count=batch_count,
            audio_codes_chunk_size=batch_audio_codes_chunk_size,
            settings=runtime_settings,
            hf_mount=hf_mount,
            fingerprint=runtime_fingerprint,
        )

    started_at = _utc_now_iso()
    started_monotonic = time.monotonic()
    summary = build_task101_pilot_bundle(
        source_root=source_bundle_root,
        output_root=benchmark_root,
        train_manifest_family=manifest_family,
        eval_manifest_family=_benchmark_eval_family(manifest_family),
        tokenizer_model=plan.tokenizer_model,
        finalization_batch_row_count=benchmark_batch_row_count,
        audio_codes_chunk_size=audio_codes_chunk_size,
        container_batch_span=container_batch_span,
        encode_audio_codes_fn=encode_audio_codes,
        repo_root=Path.cwd(),
        run_batch_fn=_run_containerized_batch,
        expected_runtime_fingerprint=runtime_fingerprint,
    )
    duration_seconds = time.monotonic() - started_monotonic
    completed_at = _utc_now_iso()
    report = Task152BenchmarkReport(
        variant_label=variant_label,
        source_bundle_root=source_bundle_root.as_posix(),
        benchmark_root=benchmark_root.as_posix(),
        manifest_family=manifest_family,
        source_start_batch_index=source_start_batch_index,
        source_batch_count=source_batch_count,
        benchmark_batch_row_count=benchmark_batch_row_count,
        container_batch_span=container_batch_span,
        audio_codes_chunk_size=audio_codes_chunk_size,
        build_image=build_image,
        selected_row_count=plan.family_row_counts[manifest_family],
        planned_batch_count=len(
            [batch for batch in plan.batches if batch.manifest_family == manifest_family]
        ),
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        rows_per_minute=(plan.family_row_counts[manifest_family] / duration_seconds) * 60.0,
        task101_bundle_report_path=task101_pilot_bundle_report_path(
            Path(summary.output_root)
        ).as_posix(),
    )
    write_json(_report_path(benchmark_root), report)
    return report


def main(argv: list[str] | None = None) -> int:
    """Run one Task 152 Task 101 benchmark variant."""
    args = _build_parser().parse_args(argv)
    benchmark_root = Path(args.output_root) / str(args.variant_label)
    report = run_task152_benchmark(
        source_bundle_root=Path(args.source_bundle_root),
        benchmark_root=benchmark_root,
        variant_label=str(args.variant_label),
        manifest_family=args.manifest_family,
        source_start_batch_index=int(args.source_start_batch_index),
        source_batch_count=int(args.source_batch_count),
        benchmark_batch_row_count=int(args.benchmark_batch_row_count),
        audio_codes_chunk_size=int(args.audio_codes_chunk_size),
        container_batch_span=int(args.container_batch_span),
        build_image=not bool(args.skip_build),
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
