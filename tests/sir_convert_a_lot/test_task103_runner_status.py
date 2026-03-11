"""Task 103 runner-status helper tests.

Purpose:
    Cover the extracted run-status lifecycle helper directly so Task 103 runner
    refactors can validate status persistence behavior without relying only on
    end-to-end runner tests.

Relationships:
    - Tests `task103_qwen_runner_status.py`.
    - Complements the higher-level runner tests in
      `test_task103_runner.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    Task103FinalizationHeartbeat,
    Task103RowProcessingHeartbeat,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_run_roots import (
    Task103RunContext,
    prepare_run_root,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_runner_status import (
    Task103RunStatusReporter,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_selection import (
    Task103SourceSelectionHeartbeat,
)


def _build_run_context(tmp_path: Path) -> Task103RunContext:
    """Build one deterministic Task 103 run context for status-helper tests."""
    context = Task103RunContext(
        run_id="proof-run",
        run_root=tmp_path / "runs" / "proof-run",
        promoted_root=tmp_path / "reference" / "qwen3-tts-swedish-corpus",
        runs_root=tmp_path / "runs",
        uses_run_root=True,
        promote_on_success=False,
    )
    prepare_run_root(context)
    return context


def _load_status_payload(run_root: Path) -> dict[str, object]:
    """Load the persisted status payload for one run root."""
    return json.loads((run_root / "status.json").read_text(encoding="utf-8"))


def test_task103_run_status_reporter_writes_allocation_failure_and_completion(
    tmp_path: Path,
) -> None:
    """The reporter should own the basic stage lifecycle transitions."""
    context = _build_run_context(tmp_path)
    reporter = Task103RunStatusReporter(
        context=context,
        source_mode="staged-public-corpus",
        stage="row-processing",
    )

    reporter.write_allocated()
    assert _load_status_payload(context.run_root)["status"] == "allocated"

    reporter.write_stage_running()
    assert _load_status_payload(context.run_root)["status"] == "running"

    reporter.write_failed("boom")
    failed_payload = _load_status_payload(context.run_root)
    assert failed_payload["status"] == "failed"
    assert failed_payload["error"] == "boom"

    reporter.write_finished(promoted=False)
    completed_payload = _load_status_payload(context.run_root)
    assert completed_payload["status"] == "completed"
    assert completed_payload["stage"] == "row-processing"

    reporter.write_finished(promoted=True)
    promoted_payload = _load_status_payload(context.run_root)
    assert promoted_payload["status"] == "promoted"


def test_task103_run_status_reporter_persists_source_selection_heartbeat(
    tmp_path: Path,
) -> None:
    """The reporter should persist source-selection heartbeat fields directly."""
    context = _build_run_context(tmp_path)
    reporter = Task103RunStatusReporter(
        context=context,
        source_mode="staged-public-corpus",
        stage="source-selection",
    )

    reporter.source_selection_heartbeat(
        Task103SourceSelectionHeartbeat(
            phase="resolving-source-records",
            current_split="train",
            selected_row_count=42,
            target_row_cap=128,
            current_parquet_batch_index=3,
            resolved_audio_locator_count=21,
            required_audio_locator_count=25,
        )
    )

    payload = _load_status_payload(context.run_root)
    assert payload["stage"] == "source-selection"
    assert payload["status"] == "running"
    assert payload["current_split"] == "train"
    assert payload["selected_row_count"] == 42
    assert payload["current_parquet_batch_index"] == 3
    assert payload["resolved_audio_locator_count"] == 21
    assert payload["required_audio_locator_count"] == 25


def test_task103_run_status_reporter_persists_row_and_finalization_heartbeats(
    tmp_path: Path,
) -> None:
    """The reporter should preserve row and finalization heartbeat fields."""
    context = _build_run_context(tmp_path)
    reporter = Task103RunStatusReporter(
        context=context,
        source_mode="staged-public-corpus",
        stage="finalization",
    )

    reporter.row_processing_heartbeat(
        Task103RowProcessingHeartbeat(
            processed_row_count=7,
            total_row_count=12,
            current_dataset_row_id="GR01KRU1-1-0",
        )
    )
    row_payload = _load_status_payload(context.run_root)
    assert row_payload["processed_row_count"] == 7
    assert row_payload["total_row_count"] == 12
    assert row_payload["current_dataset_row_id"] == "GR01KRU1-1-0"

    reporter.finalization_heartbeat(
        Task103FinalizationHeartbeat(
            current_family="swedish_smoke_train",
            completed_families=("swedish_checkpoint_dev",),
            current_chunk_index=2,
            completed_chunk_count=1,
            total_chunk_count=3,
        )
    )
    finalization_payload = _load_status_payload(context.run_root)
    assert finalization_payload["stage"] == "finalization"
    assert finalization_payload["processed_row_count"] == 7
    assert finalization_payload["total_row_count"] == 12
    assert finalization_payload["current_dataset_row_id"] == "GR01KRU1-1-0"
    assert finalization_payload["current_family"] == "swedish_smoke_train"
    assert finalization_payload["completed_families"] == ["swedish_checkpoint_dev"]
    assert finalization_payload["current_chunk_index"] == 2
    assert finalization_payload["completed_chunk_count"] == 1
    assert finalization_payload["total_chunk_count"] == 3
