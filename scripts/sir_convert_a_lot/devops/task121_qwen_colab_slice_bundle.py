"""Portable Colab slice planning for Qwen preprocessing.

Purpose:
    Create deterministic portable selected-source bundles from one Hemma-issued
    Task 103 source-selection run root so notebook-backed Colab preprocessing
    can process a unique, preallocated slice without inventing its own row
    selection logic or output schema.

Relationships:
    - Consumes `selected_source_records.jsonl` from
      `task103_qwen_source_selection.py`.
    - Produces slice bundles that
      `run_task103_qwen_swedish_preprocessing.py` can consume through the
      `selected-source-records` source mode.
    - Stages only the required Hugging Face dataset files for the chosen slice
      before row-processing starts in a notebook or CPU runtime.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal, Sequence

from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_jsonl_objects,
    write_json,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    SourceRecord,
    source_record_from_payload,
    source_record_to_payload,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox import RIXVOX_DATASET_ID
from scripts.sir_convert_a_lot.devops.task103_qwen_source_selection import (
    load_selected_source_records,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_staged_public_corpus import RAW_CORPUS_SUBDIR
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    default_data_root,
)

PortableSliceCommand = Literal["plan", "stage-required-files"]
RIXVOX_STAGING_PREFIX = Path("kblab_rixvox")


@dataclass(frozen=True)
class PortableSliceRequiredFile:
    """Describe one dataset file that must be staged before row-processing."""

    repo_id: str
    repo_type: str
    filename: str
    local_relative_path: str
    revision: str | None


@dataclass(frozen=True)
class PortableSliceSummary:
    """Stable summary for one portable preprocessing slice."""

    source_run_root: str
    slice_count: int
    slice_index: int
    selected_row_count: int
    datasets: list[str]
    source_splits: list[str]
    required_files_count: int


def portable_slice_dir(output_root: Path) -> Path:
    """Return the canonical portable-slice bundle directory."""
    return output_root


def portable_selected_source_records_path(output_root: Path) -> Path:
    """Return the portable selected-source JSONL path."""
    return portable_slice_dir(output_root) / "selected_source_records.jsonl"


def portable_required_files_path(output_root: Path) -> Path:
    """Return the required-Hub-files JSON path."""
    return portable_slice_dir(output_root) / "required_hub_files.json"


def portable_slice_summary_path(output_root: Path) -> Path:
    """Return the portable slice summary JSON path."""
    return portable_slice_dir(output_root) / "slice_summary.json"


def build_portable_slice_bundle(
    *,
    source_run_root: Path,
    output_root: Path,
    slice_count: int,
    slice_index: int,
    rixvox_revision: str | None,
) -> PortableSliceSummary:
    """Create one deterministic portable slice bundle from a source-selection run root."""
    if slice_count <= 0:
        raise ValueError("slice_count must be positive.")
    if slice_index < 0 or slice_index >= slice_count:
        raise ValueError("slice_index must satisfy 0 <= slice_index < slice_count.")

    selected_source_records = load_selected_source_records(source_run_root)
    if selected_source_records is None:
        raise FileNotFoundError(
            "The source run root does not contain selected_source_records.jsonl."
        )

    train_source_records = [
        source_record
        for source_record in selected_source_records
        if source_record.dataset == "rixvox" and source_record.source_split == "train"
    ]
    sorted_train_source_records = sorted(
        train_source_records,
        key=lambda row: (row.dataset, row.source_split, row.speaker_id, row.dataset_row_id),
    )
    slice_source_records = [
        source_record
        for row_index, source_record in enumerate(sorted_train_source_records)
        if row_index % slice_count == slice_index
    ]
    portable_source_records = [
        replace(source_record, source_audio_locator=None, reference_audio_locator=None)
        for source_record in slice_source_records
    ]
    required_files = _required_files_for_portable_slice(
        source_records=slice_source_records,
        rixvox_revision=rixvox_revision,
    )
    write_jsonl(
        portable_selected_source_records_path(output_root),
        [source_record_to_payload(source_record) for source_record in portable_source_records],
    )
    write_json(
        portable_required_files_path(output_root),
        [asdict(required_file) for required_file in required_files],
    )
    summary = PortableSliceSummary(
        source_run_root=source_run_root.as_posix(),
        slice_count=slice_count,
        slice_index=slice_index,
        selected_row_count=len(portable_source_records),
        datasets=sorted({row.dataset for row in portable_source_records}),
        source_splits=sorted({row.source_split for row in portable_source_records}),
        required_files_count=len(required_files),
    )
    write_json(portable_slice_summary_path(output_root), summary)
    return summary


def stage_required_files_for_portable_slice(
    *,
    slice_root: Path,
    data_root: Path,
    cache_dir: Path | None = None,
) -> list[Path]:
    """Stage the exact Hub files required by one portable slice into local raw storage."""
    required_files_payload = json.loads(portable_required_files_path(slice_root).read_text())
    if not isinstance(required_files_payload, list):
        raise ValueError("Portable slice required-files payload must be a list.")
    staged_paths: list[Path] = []
    for payload in required_files_payload:
        required_file = _required_file_from_payload(payload)
        cached_path = Path(
            hf_hub_download(
                repo_id=required_file.repo_id,
                repo_type=required_file.repo_type,
                filename=required_file.filename,
                revision=required_file.revision,
                cache_dir=None if cache_dir is None else cache_dir.as_posix(),
            )
        )
        target_path = data_root / RAW_CORPUS_SUBDIR / required_file.local_relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cached_path, target_path)
        staged_paths.append(target_path)
    return staged_paths


def load_portable_selected_source_records(slice_root: Path) -> list[SourceRecord]:
    """Load the portable selected-source bundle for a notebook/remote worker."""
    return [
        source_record_from_payload(payload)
        for payload in iter_jsonl_objects(portable_selected_source_records_path(slice_root))
    ]


def _required_files_for_portable_slice(
    *,
    source_records: Sequence[SourceRecord],
    rixvox_revision: str | None,
) -> list[PortableSliceRequiredFile]:
    """Render one deduplicated required-file set for a portable RixVox slice."""
    required_files_by_filename: dict[str, PortableSliceRequiredFile] = {}
    for source_record in source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None:
            raise ValueError(
                "Portable slice planning requires resolved source_audio_locator values "
                "in the source-selection run root."
            )
        archive_path_name = source_audio_locator.path.name
        if not archive_path_name.endswith(".tar.gz"):
            raise ValueError(
                "Portable slice planning currently supports only archive-backed "
                "RixVox rows."
            )
        filename = f"data/{source_record.source_split}/{archive_path_name}"
        required_files_by_filename.setdefault(
            filename,
            PortableSliceRequiredFile(
                repo_id=RIXVOX_DATASET_ID,
                repo_type="dataset",
                filename=filename,
                local_relative_path=(
                    RIXVOX_STAGING_PREFIX / filename
                ).as_posix(),
                revision=rixvox_revision,
            ),
        )
    return [required_files_by_filename[key] for key in sorted(required_files_by_filename)]


def _required_file_from_payload(payload: object) -> PortableSliceRequiredFile:
    """Parse one required-file payload from JSON."""
    if not isinstance(payload, dict):
        raise ValueError("Portable slice required-file payload must be a mapping.")
    repo_id = payload.get("repo_id")
    repo_type = payload.get("repo_type")
    filename = payload.get("filename")
    local_relative_path = payload.get("local_relative_path")
    revision = payload.get("revision")
    if not isinstance(repo_id, str):
        raise ValueError("Portable slice required-file payload is missing `repo_id`.")
    if not isinstance(repo_type, str):
        raise ValueError("Portable slice required-file payload is missing `repo_type`.")
    if not isinstance(filename, str):
        raise ValueError("Portable slice required-file payload is missing `filename`.")
    if not isinstance(local_relative_path, str):
        raise ValueError(
            "Portable slice required-file payload is missing `local_relative_path`."
        )
    if revision is not None and not isinstance(revision, str):
        raise ValueError("Portable slice required-file `revision` must be a string or null.")
    return PortableSliceRequiredFile(
        repo_id=repo_id,
        repo_type=repo_type,
        filename=filename,
        local_relative_path=local_relative_path,
        revision=revision,
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for portable Colab slice planning."""
    parser = argparse.ArgumentParser(
        description="Build or stage one portable Colab preprocessing slice."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--source-run-root", type=Path, required=True)
    plan_parser.add_argument("--output-root", type=Path, required=True)
    plan_parser.add_argument("--slice-count", type=int, required=True)
    plan_parser.add_argument("--slice-index", type=int, required=True)
    plan_parser.add_argument("--rixvox-revision", default=None)

    stage_parser = subparsers.add_parser("stage-required-files")
    stage_parser.add_argument("--slice-root", type=Path, required=True)
    stage_parser.add_argument("--data-root", type=Path, default=default_data_root())
    stage_parser.add_argument("--cache-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the portable Colab slice planner or required-file staging surface."""
    args = _parse_args(argv)
    if args.command == "plan":
        summary = build_portable_slice_bundle(
            source_run_root=Path(args.source_run_root),
            output_root=Path(args.output_root),
            slice_count=int(args.slice_count),
            slice_index=int(args.slice_index),
            rixvox_revision=None if args.rixvox_revision is None else str(args.rixvox_revision),
        )
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    staged_paths = stage_required_files_for_portable_slice(
        slice_root=Path(args.slice_root),
        data_root=Path(args.data_root),
        cache_dir=None if args.cache_dir is None else Path(args.cache_dir),
    )
    print(
        json.dumps(
            {
                "slice_root": Path(args.slice_root).as_posix(),
                "staged_paths": [path.as_posix() for path in staged_paths],
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
