"""Run-root allocation and promotion helpers for staged Qwen preprocessing.

Purpose:
    Provide immutable per-run root allocation, run metadata/status emission,
    and promotion helpers so Task 103/T110 preprocessing no longer executes
    directly inside one shared mutable corpus directory.

Relationships:
    - Used by `run_task103_qwen_swedish_preprocessing.py` to allocate live
      run roots and record run-scoped metadata.
    - Keeps promotion logic separate from row/finalization modules so the core
      stage code can continue to treat one run root as its local output root.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import write_json

RunStatus = Literal["allocated", "running", "failed", "completed", "promoted"]


@dataclass(frozen=True)
class Task103RunContext:
    """Resolved run-root context for one Task 103 execution."""

    run_id: str
    run_root: Path
    promoted_root: Path
    runs_root: Path
    uses_run_root: bool
    promote_on_success: bool


@dataclass(frozen=True)
class Task103RunStatusPayload:
    """Stable status payload written into one run root."""

    run_id: str
    run_root: str
    promoted_root: str
    status: RunStatus
    stage: str
    source_mode: str
    updated_at: str
    error: str | None = None
    current_family: str | None = None
    completed_families: tuple[str, ...] | None = None
    current_chunk_index: int | None = None
    completed_chunk_count: int | None = None
    total_chunk_count: int | None = None
    processed_row_count: int | None = None
    total_row_count: int | None = None
    current_dataset_row_id: str | None = None
    current_split: str | None = None
    selected_row_count: int | None = None
    target_row_cap: int | None = None
    current_parquet_batch_index: int | None = None
    resolved_audio_locator_count: int | None = None
    required_audio_locator_count: int | None = None


def utc_now_iso() -> str:
    """Return the current UTC time in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_run_id() -> str:
    """Return one deterministic timestamp-based run id."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ").lower()


def resolve_run_context(
    *,
    promoted_root: Path,
    runs_root: Path,
    source_mode: str,
    run_id: str | None,
    run_root: Path | None,
    promote_on_success: bool,
) -> Task103RunContext:
    """Resolve the effective run root and promotion target for one execution."""
    promoted_root = promoted_root.resolve()
    runs_root = runs_root.resolve()
    if run_root is not None and run_id is not None:
        raise SystemExit("Use either `--run-root` or `--run-id`, not both.")
    if run_root is not None:
        resolved_run_root = run_root.resolve()
        resolved_run_id = resolved_run_root.name
        uses_run_root = True
    elif source_mode == "staged-public-corpus" or run_id is not None or promote_on_success:
        resolved_run_id = run_id or default_run_id()
        resolved_run_root = (runs_root / resolved_run_id).resolve()
        uses_run_root = True
    else:
        resolved_run_id = "direct-output"
        resolved_run_root = promoted_root
        uses_run_root = False
    return Task103RunContext(
        run_id=resolved_run_id,
        run_root=resolved_run_root,
        promoted_root=promoted_root,
        runs_root=runs_root,
        uses_run_root=uses_run_root,
        promote_on_success=promote_on_success,
    )


def prepare_run_root(context: Task103RunContext) -> None:
    """Create the run root and supporting metadata directories when needed."""
    enforce_generated_output_path(context.run_root, label="run_root")
    context.run_root.mkdir(parents=True, exist_ok=True)
    (context.run_root / "logs").mkdir(parents=True, exist_ok=True)


def write_run_metadata(
    context: Task103RunContext,
    *,
    source_mode: str,
    stage: str,
    runner_payload: dict[str, object],
) -> None:
    """Write one deterministic run.json payload into the run root."""
    write_json(
        context.run_root / "run.json",
        {
            "run_id": context.run_id,
            "run_root": context.run_root.as_posix(),
            "promoted_root": context.promoted_root.as_posix(),
            "runs_root": context.runs_root.as_posix(),
            "uses_run_root": context.uses_run_root,
            "promote_on_success": context.promote_on_success,
            "source_mode": source_mode,
            "stage": stage,
            "generated_at": utc_now_iso(),
            "runner_settings": runner_payload,
        },
    )


def write_run_status(
    context: Task103RunContext,
    *,
    source_mode: str,
    stage: str,
    status: RunStatus,
    error: str | None = None,
    current_family: str | None = None,
    completed_families: tuple[str, ...] | None = None,
    current_chunk_index: int | None = None,
    completed_chunk_count: int | None = None,
    total_chunk_count: int | None = None,
    processed_row_count: int | None = None,
    total_row_count: int | None = None,
    current_dataset_row_id: str | None = None,
    current_split: str | None = None,
    selected_row_count: int | None = None,
    target_row_cap: int | None = None,
    current_parquet_batch_index: int | None = None,
    resolved_audio_locator_count: int | None = None,
    required_audio_locator_count: int | None = None,
) -> None:
    """Write one deterministic status payload into the run root."""
    existing_payload: dict[str, object] = {}
    status_path = context.run_root / "status.json"
    if status_path.exists():
        loaded = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing_payload = loaded
    payload = Task103RunStatusPayload(
        run_id=context.run_id,
        run_root=context.run_root.as_posix(),
        promoted_root=context.promoted_root.as_posix(),
        status=status,
        stage=stage,
        source_mode=source_mode,
        updated_at=utc_now_iso(),
        error=error,
        current_family=_status_string_value(existing_payload, "current_family", current_family),
        completed_families=_status_string_tuple_value(
            existing_payload,
            "completed_families",
            completed_families,
        ),
        current_chunk_index=_status_int_value(
            existing_payload,
            "current_chunk_index",
            current_chunk_index,
        ),
        completed_chunk_count=_status_int_value(
            existing_payload,
            "completed_chunk_count",
            completed_chunk_count,
        ),
        total_chunk_count=_status_int_value(
            existing_payload,
            "total_chunk_count",
            total_chunk_count,
        ),
        processed_row_count=_status_int_value(
            existing_payload,
            "processed_row_count",
            processed_row_count,
        ),
        total_row_count=_status_int_value(
            existing_payload,
            "total_row_count",
            total_row_count,
        ),
        current_dataset_row_id=_status_string_value(
            existing_payload,
            "current_dataset_row_id",
            current_dataset_row_id,
        ),
        current_split=_status_string_value(existing_payload, "current_split", current_split),
        selected_row_count=_status_int_value(
            existing_payload,
            "selected_row_count",
            selected_row_count,
        ),
        target_row_cap=_status_int_value(
            existing_payload,
            "target_row_cap",
            target_row_cap,
        ),
        current_parquet_batch_index=_status_int_value(
            existing_payload,
            "current_parquet_batch_index",
            current_parquet_batch_index,
        ),
        resolved_audio_locator_count=_status_int_value(
            existing_payload,
            "resolved_audio_locator_count",
            resolved_audio_locator_count,
        ),
        required_audio_locator_count=_status_int_value(
            existing_payload,
            "required_audio_locator_count",
            required_audio_locator_count,
        ),
    )
    write_json(status_path, asdict(payload))


def _status_int_value(
    existing_payload: dict[str, object],
    key: str,
    candidate: int | None,
) -> int | None:
    """Return the new status integer when present, else preserve the existing value."""
    if candidate is not None:
        return candidate
    existing = existing_payload.get(key)
    if isinstance(existing, int):
        return existing
    return None


def _status_string_value(
    existing_payload: dict[str, object],
    key: str,
    candidate: str | None,
) -> str | None:
    """Return the new status string when present, else preserve the existing value."""
    if candidate is not None:
        return candidate
    existing = existing_payload.get(key)
    if isinstance(existing, str):
        return existing
    return None


def _status_string_tuple_value(
    existing_payload: dict[str, object],
    key: str,
    candidate: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """Return the new status string tuple when present, else preserve the existing value."""
    if candidate is not None:
        return candidate
    existing = existing_payload.get(key)
    if isinstance(existing, list) and all(isinstance(item, str) for item in existing):
        return tuple(existing)
    return None


def promote_run_root(context: Task103RunContext) -> Path:
    """Promote one successful run root into the canonical shared corpus path."""
    if not context.uses_run_root:
        return context.promoted_root
    promoted_root = context.promoted_root
    enforce_generated_output_path(promoted_root, label="promoted_root")
    promoted_root.parent.mkdir(parents=True, exist_ok=True)
    if promoted_root.is_symlink() or promoted_root.is_file():
        promoted_root.unlink()
    elif promoted_root.exists():
        shutil.rmtree(promoted_root)
    promoted_root.symlink_to(context.run_root, target_is_directory=True)
    return promoted_root
