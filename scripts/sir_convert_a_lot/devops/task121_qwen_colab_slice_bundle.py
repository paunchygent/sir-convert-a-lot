"""Canonical Task 121 CLI for portable Qwen slice and shard allocation work.

Purpose:
    Expose the repo-owned command surface for portable slice planning,
    localization, shard registry creation, and shard-backed processing-unit
    issuance without embedding domain logic in the CLI module itself.

Relationships:
    - Delegates portable slice planning to
      `task121_qwen_portable_slice_planning.py`.
    - Delegates staging and localization to
      `task121_qwen_portable_slice_localization.py`.
    - Delegates immutable shard registry and assignment behavior to
      `task121_qwen_shard_registry.py` and `task121_qwen_assignment_ledger.py`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    default_data_root,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_assignment_ledger import (
    QwenProcessingUnitSummary,
    QwenShardAssignmentEvent,
    complete_processing_unit,
    issue_processing_unit_from_shards,
    release_processing_unit,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_localization import (
    localize_portable_slice,
    stage_required_files_for_portable_slice,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_models import (
    DedupedSelectedSourceSummary,
    LocalizedSliceSummary,
    PortableSliceSummary,
    UniqueAllocationSummary,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_planning import (
    build_portable_slice_bundle,
    build_remaining_unique_portable_slice_bundle,
    dedupe_selected_source_records,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_shard_registry import (
    QwenShardRegistrySummary,
    build_shard_registry,
)

PortableSliceCommand = Literal[
    "plan",
    "plan-remaining-unique",
    "dedupe-selected-source-records",
    "build-shard-registry",
    "issue-processing-unit-from-shards",
    "release-processing-unit",
    "complete-processing-unit",
    "stage-required-files",
    "localize-slice",
]
Task121JsonPayload = (
    PortableSliceSummary
    | UniqueAllocationSummary
    | DedupedSelectedSourceSummary
    | QwenShardRegistrySummary
    | QwenProcessingUnitSummary
    | QwenShardAssignmentEvent
    | LocalizedSliceSummary
    | dict[str, object]
)


def main(argv: list[str] | None = None) -> int:
    """Run the canonical Task 121 portable slice and shard allocation CLI."""
    args = _parse_args(argv)
    command = args.command
    if command == "plan":
        return _print_json(
            build_portable_slice_bundle(
                source_run_root=args.source_run_root,
                output_root=args.output_root,
                slice_count=args.slice_count,
                slice_index=args.slice_index,
                rixvox_revision=args.rixvox_revision,
            )
        )
    if command == "plan-remaining-unique":
        return _print_json(
            build_remaining_unique_portable_slice_bundle(
                source_run_root=args.source_run_root,
                output_root=args.output_root,
                slice_count=args.slice_count,
                slice_index=args.slice_index,
                rixvox_revision=args.rixvox_revision,
                exclude_completed_run_roots=args.exclude_completed_run_roots,
                exclude_selected_source_records_paths=args.exclude_selected_source_records_paths,
                exclude_row_keys_paths=args.exclude_row_keys_paths,
            )
        )
    if command == "dedupe-selected-source-records":
        return _print_json(
            dedupe_selected_source_records(
                selected_source_records_path=args.selected_source_records_path,
                output_path=args.output_path,
                exclude_completed_run_roots=args.exclude_completed_run_roots,
                exclude_selected_source_records_paths=args.exclude_selected_source_records_paths,
                exclude_row_keys_paths=args.exclude_row_keys_paths,
            )
        )
    if command == "build-shard-registry":
        return _print_json(
            build_shard_registry(
                source_run_root=args.source_run_root,
                registry_root=args.registry_root,
                target_rows_per_shard=args.target_rows_per_shard,
                exclude_completed_run_roots=args.exclude_completed_run_roots,
                exclude_selected_source_records_paths=args.exclude_selected_source_records_paths,
                exclude_row_keys_paths=args.exclude_row_keys_paths,
            )
        )
    if command == "issue-processing-unit-from-shards":
        return _print_json(
            issue_processing_unit_from_shards(
                registry_root=args.registry_root,
                processing_unit_root=args.processing_unit_root,
                processing_unit_id=args.processing_unit_id,
                executor=args.executor,
                shard_ids=args.shard_ids,
            )
        )
    if command == "release-processing-unit":
        return _print_json(
            release_processing_unit(
                registry_root=args.registry_root,
                processing_unit_root=args.processing_unit_root,
                executor=args.executor,
            )
        )
    if command == "complete-processing-unit":
        return _print_json(
            complete_processing_unit(
                registry_root=args.registry_root,
                processing_unit_root=args.processing_unit_root,
                executor=args.executor,
            )
        )
    if command == "stage-required-files":
        staged_paths = stage_required_files_for_portable_slice(
            slice_root=args.slice_root,
            data_root=args.data_root,
            cache_dir=args.cache_dir,
        )
        return _print_json(
            {
                "slice_root": args.slice_root.as_posix(),
                "staged_paths": [path.as_posix() for path in staged_paths],
            }
        )
    return _print_json(
        localize_portable_slice(
            slice_root=args.slice_root,
            data_root=args.data_root,
        )
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for the canonical Task 121 surface."""
    parser = argparse.ArgumentParser(
        description="Plan, dedupe, or materialize portable Qwen preprocessing work."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan")
    _add_planning_arguments(plan_parser)

    unique_plan_parser = subparsers.add_parser("plan-remaining-unique")
    _add_planning_arguments(unique_plan_parser)
    _add_exclusion_arguments(unique_plan_parser)

    dedupe_parser = subparsers.add_parser("dedupe-selected-source-records")
    dedupe_parser.add_argument("--selected-source-records-path", type=Path, required=True)
    dedupe_parser.add_argument("--output-path", type=Path, required=True)
    _add_exclusion_arguments(dedupe_parser)

    shard_registry_parser = subparsers.add_parser("build-shard-registry")
    shard_registry_parser.add_argument("--source-run-root", type=Path, required=True)
    shard_registry_parser.add_argument("--registry-root", type=Path, required=True)
    shard_registry_parser.add_argument("--target-rows-per-shard", type=int, default=5000)
    _add_exclusion_arguments(shard_registry_parser)

    issue_processing_unit_parser = subparsers.add_parser("issue-processing-unit-from-shards")
    issue_processing_unit_parser.add_argument("--registry-root", type=Path, required=True)
    issue_processing_unit_parser.add_argument("--processing-unit-root", type=Path, required=True)
    issue_processing_unit_parser.add_argument("--processing-unit-id", required=True)
    issue_processing_unit_parser.add_argument("--executor", required=True)
    issue_processing_unit_parser.add_argument(
        "--shard-id",
        dest="shard_ids",
        action="append",
        required=True,
    )

    release_processing_unit_parser = subparsers.add_parser("release-processing-unit")
    release_processing_unit_parser.add_argument("--registry-root", type=Path, required=True)
    release_processing_unit_parser.add_argument("--processing-unit-root", type=Path, required=True)
    release_processing_unit_parser.add_argument("--executor", required=True)

    complete_processing_unit_parser = subparsers.add_parser("complete-processing-unit")
    complete_processing_unit_parser.add_argument("--registry-root", type=Path, required=True)
    complete_processing_unit_parser.add_argument(
        "--processing-unit-root",
        type=Path,
        required=True,
    )
    complete_processing_unit_parser.add_argument("--executor", required=True)

    stage_parser = subparsers.add_parser("stage-required-files")
    stage_parser.add_argument("--slice-root", type=Path, required=True)
    stage_parser.add_argument("--data-root", type=Path, default=default_data_root())
    stage_parser.add_argument("--cache-dir", type=Path, default=None)

    localize_parser = subparsers.add_parser("localize-slice")
    localize_parser.add_argument("--slice-root", type=Path, required=True)
    localize_parser.add_argument("--data-root", type=Path, default=default_data_root())
    return parser.parse_args(argv)


def _add_planning_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common portable-slice planning arguments."""
    parser.add_argument("--source-run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--slice-count", type=int, required=True)
    parser.add_argument("--slice-index", type=int, required=True)
    parser.add_argument("--rixvox-revision", default=None)


def _add_exclusion_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common exclusion arguments for unique allocation and dedupe flows."""
    parser.add_argument(
        "--exclude-completed-run-root",
        dest="exclude_completed_run_roots",
        action="append",
        type=Path,
        default=[],
    )
    parser.add_argument(
        "--exclude-selected-source-records-path",
        dest="exclude_selected_source_records_paths",
        action="append",
        type=Path,
        default=[],
    )
    parser.add_argument(
        "--exclude-row-keys-path",
        dest="exclude_row_keys_paths",
        action="append",
        type=Path,
        default=[],
    )


def _print_json(payload: Task121JsonPayload) -> int:
    """Print one JSON payload for operator-facing CLI use."""
    serializable_payload = asdict(payload) if not isinstance(payload, dict) else payload
    print(
        json.dumps(
            serializable_payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
