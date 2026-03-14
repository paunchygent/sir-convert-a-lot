"""Public CLI entrypoint for Task 101 Qwen training-bundle materialization.

Purpose:
    Provide the operator command surface for copying, finalizing, assembling,
    and building deterministic Task 101 training bundles from the frozen Qwen
    pilot root.

Relationships:
    - Delegates orchestration to `ml.qwen.training.bundles`.
    - Reuses the governed Qwen container runtime from
      `ml.qwen.training.bundle_runtime`.
    - Exposes the public `pdm run task-101-pilot-bundle ...` contract.
"""

from __future__ import annotations

import argparse
import json
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    CANONICAL_MANIFEST_FAMILIES,
    ManifestFamily,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_contracts import BundleSummary
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime import (
    load_training_bundle_runtime_fingerprint,
    prepare_training_bundle_batch_runtime,
    run_containerized_training_bundle_batch,
    training_bundle_runtime_fingerprint_path,
    validate_runtime_fingerprint_matches,
    write_training_bundle_runtime_fingerprint,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_state import (
    bundle_batch_log_path,
    bundle_build_exit_path,
    utc_now_iso,
    write_progress_state,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    DEFAULT_BATCH_ROW_COUNT,
    DEFAULT_TOKENIZER_MODEL,
    assemble_training_bundle,
    bundle_batch_is_complete,
    bundle_progress_state_path,
    bundle_report_path,
    load_training_bundle_batch_plan,
    prepare_training_bundle_inputs,
)

DEFAULT_FROZEN_PILOT_ROOT = Path(
    "/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/"
    "task140-qwen-pilot-frozen-20260311a"
)
DEFAULT_PILOT_BUNDLE_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle"
)
DEFAULT_TRAIN_MANIFEST_FAMILY: ManifestFamily = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY: ManifestFamily = "swedish_checkpoint_dev"


def _manifest_family_from_cli_value(value: object, *, argument_name: str) -> ManifestFamily:
    """Normalize one manifest-family CLI value into the typed literal contract."""
    match value:
        case "swedish_smoke_train":
            return "swedish_smoke_train"
        case "swedish_pilot_train":
            return "swedish_pilot_train"
        case "swedish_scaleup_train":
            return "swedish_scaleup_train"
        case "swedish_checkpoint_dev":
            return "swedish_checkpoint_dev"
        case "swedish_final_test":
            return "swedish_final_test"
        case "swedish_waxholm_control":
            return "swedish_waxholm_control"
        case _:
            raise ValueError(f"Malformed `{argument_name}` manifest-family value: {value!r}.")


def build_parser() -> argparse.ArgumentParser:
    """Build the committed Task 101 training-bundle CLI parser."""
    parser = argparse.ArgumentParser(
        description="Materialize one deterministic Task 101 Qwen training bundle."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common_copy_arguments(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument("--source-root", type=Path, default=DEFAULT_FROZEN_PILOT_ROOT)
        target_parser.add_argument("--output-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
        target_parser.add_argument(
            "--train-manifest-family",
            default=DEFAULT_TRAIN_MANIFEST_FAMILY,
            choices=CANONICAL_MANIFEST_FAMILIES,
        )
        target_parser.add_argument(
            "--eval-manifest-family",
            default=DEFAULT_EVAL_MANIFEST_FAMILY,
            choices=CANONICAL_MANIFEST_FAMILIES,
        )
        target_parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
        target_parser.add_argument(
            "--finalization-batch-row-count",
            type=int,
            default=DEFAULT_BATCH_ROW_COUNT,
        )

    copy_parser = subparsers.add_parser("copy")
    _add_common_copy_arguments(copy_parser)

    finalize_batch_parser = subparsers.add_parser("finalize-batch")
    finalize_batch_parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_PILOT_BUNDLE_ROOT,
    )
    finalize_batch_parser.add_argument(
        "--manifest-family",
        required=True,
        choices=CANONICAL_MANIFEST_FAMILIES,
    )
    finalize_batch_parser.add_argument("--batch-index", type=int, required=True)
    finalize_batch_parser.add_argument(
        "--audio-codes-chunk-size",
        type=int,
        default=DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    )

    assemble_parser = subparsers.add_parser("assemble")
    assemble_parser.add_argument("--output-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)

    build_parser = subparsers.add_parser("build")
    _add_common_copy_arguments(build_parser)
    build_parser.add_argument(
        "--audio-codes-chunk-size",
        type=int,
        default=DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    )
    return parser


def _build_bundle_in_governed_runtime(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    finalization_batch_row_count: int,
    audio_codes_chunk_size: int,
    repo_root: Path,
) -> BundleSummary:
    """Materialize one bundle with host orchestration and governed batch containers."""
    with suppress(FileNotFoundError):
        bundle_build_exit_path(output_root).unlink()
    if bundle_report_path(output_root).exists():
        runtime_path = training_bundle_runtime_fingerprint_path(output_root)
        if not runtime_path.exists():
            raise SystemExit(
                "Existing training bundle report was found, but the governed runtime "
                "fingerprint is missing. Rebuild the bundle under the container runtime."
            )
        _, fingerprint = prepare_training_bundle_batch_runtime()
        observed_fingerprint = load_training_bundle_runtime_fingerprint(runtime_path)
        validate_runtime_fingerprint_matches(observed_fingerprint, fingerprint)
        return assemble_training_bundle(output_root)

    plan = prepare_training_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        repo_root=repo_root,
    )
    hf_mount, fingerprint = prepare_training_bundle_batch_runtime()
    write_training_bundle_runtime_fingerprint(output_root, fingerprint)
    completed_batch_count = sum(
        1
        for batch in plan.batches
        if bundle_batch_is_complete(
            output_root,
            batch,
            expected_runtime_fingerprint=fingerprint,
        )
    )
    write_progress_state(
        output_root,
        status_path=bundle_progress_state_path(output_root),
        status="running" if completed_batch_count < len(plan.batches) else "completed",
        completed_batch_count=completed_batch_count,
        total_batch_count=len(plan.batches),
        current_phase=None,
        current_manifest_family=None,
        current_batch_index=None,
        current_batch_log_path=None,
        current_batch_started_at=None,
        last_completed_manifest_family=None,
        last_completed_batch_index=None,
        last_completed_at=None,
    )
    for batch in plan.batches:
        if bundle_batch_is_complete(
            output_root,
            batch,
            expected_runtime_fingerprint=fingerprint,
        ):
            continue
        batch_started_at = utc_now_iso()
        write_progress_state(
            output_root,
            status_path=bundle_progress_state_path(output_root),
            status="running",
            completed_batch_count=completed_batch_count,
            total_batch_count=len(plan.batches),
            current_phase="batch-finalization",
            current_manifest_family=batch.manifest_family,
            current_batch_index=batch.batch_index,
            current_batch_log_path=bundle_batch_log_path(
                output_root,
                batch.manifest_family,
                batch.batch_index,
            ).as_posix(),
            current_batch_started_at=batch_started_at,
        )
        run_containerized_training_bundle_batch(
            repo_root=repo_root,
            output_root=output_root,
            manifest_family=batch.manifest_family,
            batch_index=batch.batch_index,
            batch_count=1,
            audio_codes_chunk_size=audio_codes_chunk_size,
            hf_mount=hf_mount,
            fingerprint=fingerprint,
        )
        completed_batch_count = sum(
            1
            for candidate in plan.batches
            if bundle_batch_is_complete(
                output_root,
                candidate,
                expected_runtime_fingerprint=fingerprint,
            )
        )
        write_progress_state(
            output_root,
            status_path=bundle_progress_state_path(output_root),
            status="running" if completed_batch_count < len(plan.batches) else "completed",
            completed_batch_count=completed_batch_count,
            total_batch_count=len(plan.batches),
            current_phase=None,
            current_manifest_family=None,
            current_batch_index=None,
            current_batch_log_path=None,
            current_batch_started_at=None,
            last_completed_manifest_family=batch.manifest_family,
            last_completed_batch_index=batch.batch_index,
            last_completed_at=utc_now_iso(),
        )
    return assemble_training_bundle(output_root)


def main(argv: list[str] | None = None) -> int:
    """Run the restored Task 101 training-bundle CLI surface."""
    args = build_parser().parse_args(argv)
    if args.command == "copy":
        plan = prepare_training_bundle_inputs(
            source_root=Path(args.source_root),
            output_root=Path(args.output_root),
            train_manifest_family=_manifest_family_from_cli_value(
                args.train_manifest_family,
                argument_name="train_manifest_family",
            ),
            eval_manifest_family=_manifest_family_from_cli_value(
                args.eval_manifest_family,
                argument_name="eval_manifest_family",
            ),
            tokenizer_model=str(args.tokenizer_model),
            finalization_batch_row_count=int(args.finalization_batch_row_count),
            repo_root=Path.cwd(),
        )
        print(json.dumps(asdict(plan), indent=2, ensure_ascii=False))
        return 0
    if args.command == "finalize-batch":
        output_root = Path(args.output_root)
        plan = load_training_bundle_batch_plan(output_root)
        manifest_family = _manifest_family_from_cli_value(
            args.manifest_family,
            argument_name="manifest_family",
        )
        hf_mount, fingerprint = prepare_training_bundle_batch_runtime()
        write_training_bundle_runtime_fingerprint(output_root, fingerprint)
        run_containerized_training_bundle_batch(
            repo_root=Path.cwd(),
            output_root=output_root,
            manifest_family=manifest_family,
            batch_index=int(args.batch_index),
            batch_count=1,
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            hf_mount=hf_mount,
            fingerprint=fingerprint,
        )
        batch = next(
            candidate
            for candidate in plan.batches
            if candidate.manifest_family == manifest_family
            and candidate.batch_index == int(args.batch_index)
        )
        print(json.dumps(asdict(batch), indent=2, ensure_ascii=False))
        return 0
    if args.command == "assemble":
        summary = assemble_training_bundle(Path(args.output_root))
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        return 0
    if args.command == "build":
        summary = _build_bundle_in_governed_runtime(
            source_root=Path(args.source_root),
            output_root=Path(args.output_root),
            train_manifest_family=_manifest_family_from_cli_value(
                args.train_manifest_family,
                argument_name="train_manifest_family",
            ),
            eval_manifest_family=_manifest_family_from_cli_value(
                args.eval_manifest_family,
                argument_name="eval_manifest_family",
            ),
            tokenizer_model=str(args.tokenizer_model),
            finalization_batch_row_count=int(args.finalization_batch_row_count),
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            repo_root=Path.cwd(),
        )
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
