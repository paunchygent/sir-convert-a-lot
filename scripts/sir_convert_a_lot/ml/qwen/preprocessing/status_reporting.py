"""Run-status orchestration helpers for the canonical Qwen preprocessing runner.

Purpose:
    Give the preprocessing pipeline one dedicated module for run-status
    lifecycle writes and heartbeat persistence so the public CLI runner does
    not need to inline status-transition details for source selection, row
    processing, and finalization.

Relationships:
    - Used by `cli/ml/qwen_preprocess.py`.
    - Delegates persistence to `ml.qwen.preprocessing.run_roots`.
    - Mirrors the heartbeat contracts from the preprocessing models and
      source-selection modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    FinalizationHeartbeat,
    RowProcessingHeartbeat,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.run_roots import (
    RunContext,
    write_run_status,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.source_selection import (
    SourceSelectionHeartbeat,
)


@dataclass(frozen=True)
class RunStatusReporter:
    """Write stable preprocessing run-status transitions for one run context."""

    context: RunContext
    source_mode: str
    stage: str

    def write_allocated(self) -> None:
        """Persist the initial allocated status for the current stage."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="allocated",
        )

    def write_stage_running(self) -> None:
        """Persist a generic running status for the current stage."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="running",
        )

    def write_source_selection_running(
        self,
        *,
        selected_row_count: int,
        target_row_cap: int | None,
    ) -> None:
        """Persist source-selection progress once the bounded selection is resolved."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage="source-selection",
            status="running",
            selected_row_count=selected_row_count,
            target_row_cap=target_row_cap,
        )

    def write_failed(self, error: str) -> None:
        """Persist a failed status for the current stage with traceback text."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="failed",
            error=error,
        )

    def write_finished(self, *, promoted: bool) -> None:
        """Persist the terminal completed or promoted status for the current stage."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="promoted" if promoted else "completed",
        )

    def source_selection_heartbeat(self, heartbeat: SourceSelectionHeartbeat) -> None:
        """Persist one source-selection heartbeat into the run status payload."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage="source-selection",
            status="running",
            current_split=heartbeat.current_split,
            selected_row_count=heartbeat.selected_row_count,
            target_row_cap=heartbeat.target_row_cap,
            current_parquet_batch_index=heartbeat.current_parquet_batch_index,
            resolved_audio_locator_count=heartbeat.resolved_audio_locator_count,
            required_audio_locator_count=heartbeat.required_audio_locator_count,
        )

    def row_processing_heartbeat(self, heartbeat: RowProcessingHeartbeat) -> None:
        """Persist one row-processing heartbeat into the run status payload."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="running",
            processed_row_count=heartbeat.processed_row_count,
            total_row_count=heartbeat.total_row_count,
            current_dataset_row_id=heartbeat.current_dataset_row_id,
        )

    def finalization_heartbeat(self, heartbeat: FinalizationHeartbeat) -> None:
        """Persist one finalization heartbeat into the run status payload."""
        write_run_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="running",
            current_family=heartbeat.current_family,
            completed_families=heartbeat.completed_families,
            current_chunk_index=heartbeat.current_chunk_index,
            completed_chunk_count=heartbeat.completed_chunk_count,
            total_chunk_count=heartbeat.total_chunk_count,
        )
