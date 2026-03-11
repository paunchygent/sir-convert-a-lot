"""Contracts and path helpers for Task 121 portable Qwen slices.

Purpose:
    Hold the stable dataclasses, artifact-path helpers, and constants shared by
    portable-slice planning, localization, and shard-backed processing-unit
    issuance.

Relationships:
    - Used by `task121_qwen_portable_slice_planning.py` and
      `task121_qwen_portable_slice_localization.py` for portable slice
      materialization and localization.
    - Used by `task121_qwen_colab_slice_bundle.py` as the thin public CLI
      surface for Task 121.
    - Reused by shard-backed allocation helpers so all Task 121 bundle-shaped
      artifacts share one path contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class LocalizedSliceSummary:
    """Stable summary for one localized portable preprocessing slice."""

    slice_root: str
    localized_row_count: int
    localized_audio_file_count: int
    localized_manifest_path: str
    localized_audio_root: str


@dataclass(frozen=True)
class UniqueAllocationSummary:
    """Stable summary for one guarded unique-allocation planning pass."""

    source_run_root: str
    output_root: str
    slice_count: int
    slice_index: int
    remaining_train_row_count: int
    selected_row_count: int
    excluded_completed_row_count: int
    excluded_reserved_row_count: int
    total_excluded_key_count: int


@dataclass(frozen=True)
class DedupedSelectedSourceSummary:
    """Stable summary for one deduplicated selected-source manifest."""

    input_selected_source_records_path: str
    output_selected_source_records_path: str
    input_row_count: int
    output_row_count: int
    excluded_completed_row_count: int
    excluded_reserved_row_count: int
    total_excluded_key_count: int


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


def unique_allocation_summary_path(output_root: Path) -> Path:
    """Return the guarded-allocation summary JSON path."""
    return portable_slice_dir(output_root) / "unique_allocation_summary.json"


def localized_selected_source_records_path(slice_root: Path) -> Path:
    """Return the localized selected-source JSONL path."""
    return portable_slice_dir(slice_root) / "localized_selected_source_records.jsonl"


def localized_audio_root(slice_root: Path) -> Path:
    """Return the canonical localized-audio directory for one portable slice."""
    return portable_slice_dir(slice_root) / "localized_audio"


def localized_slice_summary_path(slice_root: Path) -> Path:
    """Return the localized-slice summary JSON path."""
    return portable_slice_dir(slice_root) / "localized_slice_summary.json"


def deduped_selected_source_summary_path(output_path: Path) -> Path:
    """Return the summary JSON path for one deduplicated selected-source manifest."""
    return output_path.with_name(f"{output_path.stem}_dedupe_summary.json")
