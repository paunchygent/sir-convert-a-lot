"""Bounded source-selection artifacts for staged Qwen preprocessing.

Purpose:
    Persist one deterministic selected-source-record artifact for the staged
    public-corpus pipeline so expensive preflight work can be resumed or reused
    without reparsing the full staged corpus on every row-processing launch.

Relationships:
    - Used by `run_task103_qwen_swedish_preprocessing.py` to materialize or
      reload the bounded source-selection result before row-processing starts.
    - Consumed by Task 114 orchestration to reason about whether source
      selection has already completed for a run root.
    - Serializes `SourceRecord` contracts from `task103_qwen_source_models.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

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

SourceSelectionPhase = Literal[
    "resolving-source-records",
    "resolving-audio-locators",
    "writing-selection-artifacts",
]


@dataclass(frozen=True)
class Task103SourceSelectionHeartbeat:
    """Heartbeat payload for bounded staged-public source selection."""

    phase: SourceSelectionPhase
    current_split: str | None
    selected_row_count: int
    target_row_cap: int | None
    current_parquet_batch_index: int | None
    resolved_audio_locator_count: int | None
    required_audio_locator_count: int | None


@dataclass(frozen=True)
class Task103SourceSelectionSummary:
    """Stable summary for one persisted selected-source artifact set."""

    source_mode: str
    total_selected_rows: int
    datasets: list[str]
    fleurs_splits: list[str]
    rixvox_splits: list[str]
    rixvox_max_rows_per_split: int | None


Task103SourceSelectionHeartbeatCallback = Callable[[Task103SourceSelectionHeartbeat], None]


def source_selection_dir(output_root: Path) -> Path:
    """Return the canonical source-selection artifact directory."""
    return output_root / "source_selection"


def selected_source_records_path(output_root: Path) -> Path:
    """Return the path for the persisted bounded selected-source JSONL."""
    return source_selection_dir(output_root) / "selected_source_records.jsonl"


def source_selection_summary_path(output_root: Path) -> Path:
    """Return the path for the deterministic source-selection summary JSON."""
    return source_selection_dir(output_root) / "selection_summary.json"


def has_selected_source_records(output_root: Path) -> bool:
    """Return whether the run root already contains selected-source artifacts."""
    return selected_source_records_path(output_root).is_file()


def write_selected_source_records(
    output_root: Path,
    *,
    source_records: list[SourceRecord],
    summary: Task103SourceSelectionSummary,
) -> None:
    """Persist one bounded selected-source artifact set deterministically."""
    write_jsonl(
        selected_source_records_path(output_root),
        [source_record_to_payload(row) for row in source_records],
    )
    write_json(source_selection_summary_path(output_root), summary)


def load_selected_source_records(output_root: Path) -> list[SourceRecord] | None:
    """Load one previously persisted bounded selected-source artifact set."""
    path = selected_source_records_path(output_root)
    if not path.exists():
        return None
    return [source_record_from_payload(payload) for payload in iter_jsonl_objects(path)]
