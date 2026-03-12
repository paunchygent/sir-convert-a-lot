"""CLI surface for Task 101 batched Qwen pilot-bundle materialization.

Purpose:
    Own argument parsing, typed CLI normalization, and command dispatch for the
    canonical Task 101 pilot-bundle operator surface.

Relationships:
    - Delegates orchestration to `task101_qwen_pilot_bundle.py`.
    - Reuses batch-plan and batch-execution helpers for direct operator stages.
    - Preserves the canonical `pdm run task-101-pilot-bundle ...` surface while
      keeping CLI concerns out of the orchestration module.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle import (
    DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_FROZEN_PILOT_ROOT,
    DEFAULT_PILOT_BUNDLE_ROOT,
    DEFAULT_TOKENIZER_MODEL,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    assemble_task101_pilot_bundle,
    build_task101_pilot_bundle,
    copy_task101_pilot_bundle_inputs,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    DEFAULT_FINALIZATION_BATCH_ROW_COUNT,
    load_task101_pilot_bundle_batch_plan,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_execution import (
    finalize_task101_pilot_bundle_batch,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import ManifestFamily
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    encode_audio_codes,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    CANONICAL_MANIFEST_FAMILIES,
)


def _manifest_family_from_cli_value(value: object, *, argument_name: str) -> ManifestFamily:
    """Normalize one CLI-provided manifest-family value into the typed literal."""
    if value == "swedish_smoke_train":
        return "swedish_smoke_train"
    if value == "swedish_pilot_train":
        return "swedish_pilot_train"
    if value == "swedish_scaleup_train":
        return "swedish_scaleup_train"
    if value == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    if value == "swedish_final_test":
        return "swedish_final_test"
    if value == "swedish_waxholm_control":
        return "swedish_waxholm_control"
    raise ValueError(f"Malformed `{argument_name}` manifest-family value: {value!r}.")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for deterministic Task 101 pilot-bundle creation."""
    parser = argparse.ArgumentParser(
        description="Materialize one deterministic Task 101 pilot bundle from a frozen root."
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
            default=DEFAULT_FINALIZATION_BATCH_ROW_COUNT,
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the committed Task 101 pilot-bundle CLI surface."""
    args = _parse_args(argv)
    if args.command == "copy":
        plan = copy_task101_pilot_bundle_inputs(
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
        plan = load_task101_pilot_bundle_batch_plan(Path(args.output_root))
        batch = finalize_task101_pilot_bundle_batch(
            output_root=Path(args.output_root),
            plan=plan,
            manifest_family=_manifest_family_from_cli_value(
                args.manifest_family,
                argument_name="manifest_family",
            ),
            batch_index=int(args.batch_index),
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            encode_audio_codes_fn=encode_audio_codes,
        )
        print(json.dumps(asdict(batch), indent=2, ensure_ascii=False))
        return 0
    if args.command == "assemble":
        plan = load_task101_pilot_bundle_batch_plan(Path(args.output_root))
        summary = assemble_task101_pilot_bundle(
            output_root=Path(args.output_root),
            plan=plan,
        )
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        return 0
    if args.command == "build":
        summary = build_task101_pilot_bundle(
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
            encode_audio_codes_fn=encode_audio_codes,
            repo_root=Path.cwd(),
        )
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
