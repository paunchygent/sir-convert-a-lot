"""Live status reporter for the detached Task 101 Qwen pilot probe.

Purpose:
    Keep the detached in-container probe focused on orchestration while this
    module owns truthful live heartbeat persistence, phase-history tracking,
    and launch-metadata tracker updates for Task 101.

Relationships:
    - Used by `task101_qwen_pilot_probe.py`.
    - Consumes progress heartbeats emitted by `sft_12hz.py`.
    - Delegates JSON payload assembly to `task101_qwen_pilot_probe_reporting.py`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import TrainingProgressHeartbeat
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe_reporting import (
    _completed_status_payload,
    _failed_status_payload,
    _merge_launch_tracking_metadata,
    _running_status_payload,
    _write_json,
)

if TYPE_CHECKING:
    from scripts.devops.qwen_finetuning_patches.sft_12hz import TrainingSummary


@dataclass(frozen=True)
class Task101PilotStatusReporterConfig:
    """Static run metadata required to write one Task 101 status artifact."""

    status_path: Path
    launch_metadata_path: Path | None
    train_jsonl: Path
    eval_jsonl: Path
    output_dir: Path
    train_row_count: int
    eval_row_count: int
    checkpoint_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    resume_from_checkpoint: Path | None
    tracking_plan: Mapping[str, object] | None
    gradient_accumulation_steps: int = 4
    dataloader_tuning: Mapping[str, object] | None = None
    ref_mel_cache_config: Mapping[str, object] | None = None
    profiling_plan: Mapping[str, object] | None = None


@dataclass
class Task101PilotStatusReporter:
    """Persist truthful live Task 101 heartbeat and terminal status payloads."""

    config: Task101PilotStatusReporterConfig
    tracking: dict[str, object] | None = None
    latest_heartbeat: TrainingProgressHeartbeat | None = None
    phase_history: list[dict[str, object]] = field(default_factory=list)

    def write_startup(self) -> None:
        """Persist the initial startup heartbeat before training begins."""
        startup_heartbeat = TrainingProgressHeartbeat(
            phase="startup",
            updated_at=self._status_timestamp(),
            current_epoch=0,
            current_step=0,
            current_optimizer_step=0,
            current_train_iteration=0,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            latest_loss=None,
            smoothed_loss=None,
            latest_durable_checkpoint_path=(
                None
                if self.config.resume_from_checkpoint is None
                else self.config.resume_from_checkpoint.as_posix()
            ),
            latest_durable_checkpoint_step=None,
            latest_durable_checkpoint_saved_at=None,
        )
        self._record_heartbeat(startup_heartbeat)
        self._write_running_status()

    def tracking_ready(self, tracking: dict[str, object]) -> None:
        """Persist live tracker metadata once Accelerate finishes initialization."""
        self.tracking = tracking
        self._write_running_status()
        if self.config.launch_metadata_path is not None:
            _merge_launch_tracking_metadata(self.config.launch_metadata_path, tracking=tracking)

    def heartbeat(self, heartbeat: TrainingProgressHeartbeat) -> None:
        """Persist one live heartbeat emitted by the patched trainer."""
        self._record_heartbeat(heartbeat)
        self._write_running_status()

    def write_completed(self, training_summary: "TrainingSummary") -> None:
        """Persist the terminal completed or signal-stop status payload."""
        terminal_phase = "signal-stop" if training_summary.stopped_early else "completed"
        self._ensure_terminal_phase(terminal_phase)
        _write_json(
            self.config.status_path,
            _completed_status_payload(
                train_jsonl=self.config.train_jsonl,
                eval_jsonl=self.config.eval_jsonl,
                output_dir=self.config.output_dir,
                train_row_count=self.config.train_row_count,
                eval_row_count=self.config.eval_row_count,
                training_summary=training_summary,
                live_progress=self._live_progress_payload(),
                phase_history=self.phase_history,
            ),
        )

    def write_failed(self, exc: Exception) -> None:
        """Persist the terminal failed status payload with the last live heartbeat."""
        self._ensure_terminal_phase("failed")
        _write_json(
            self.config.status_path,
            _failed_status_payload(
                train_jsonl=self.config.train_jsonl,
                eval_jsonl=self.config.eval_jsonl,
                output_dir=self.config.output_dir,
                train_row_count=self.config.train_row_count,
                eval_row_count=self.config.eval_row_count,
                exc=exc,
                live_progress=self._live_progress_payload(),
                phase_history=self.phase_history,
                tracking=self.tracking,
            ),
        )

    def _record_heartbeat(self, heartbeat: TrainingProgressHeartbeat) -> None:
        """Store one live heartbeat and append a phase event when the phase changes."""
        previous_phase = None if self.latest_heartbeat is None else self.latest_heartbeat.phase
        self.latest_heartbeat = heartbeat
        if heartbeat.phase != previous_phase:
            self.phase_history.append(
                {
                    "phase": heartbeat.phase,
                    "updated_at": heartbeat.updated_at,
                    "current_epoch": heartbeat.current_epoch,
                    "current_step": heartbeat.current_step,
                    "current_optimizer_step": heartbeat.current_optimizer_step,
                    "current_train_iteration": heartbeat.current_train_iteration,
                }
            )

    def _write_running_status(self) -> None:
        """Persist the current running status payload with live heartbeat fields."""
        _write_json(
            self.config.status_path,
            _running_status_payload(
                train_jsonl=self.config.train_jsonl,
                eval_jsonl=self.config.eval_jsonl,
                output_dir=self.config.output_dir,
                train_row_count=self.config.train_row_count,
                eval_row_count=self.config.eval_row_count,
                checkpoint_interval_steps=self.config.checkpoint_interval_steps,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                durable_checkpoint_retention=self.config.durable_checkpoint_retention,
                durable_checkpoint_min_free_bytes=(self.config.durable_checkpoint_min_free_bytes),
                dataloader_tuning=(
                    None
                    if self.config.dataloader_tuning is None
                    else dict(self.config.dataloader_tuning)
                ),
                ref_mel_cache_config=(
                    None
                    if self.config.ref_mel_cache_config is None
                    else dict(self.config.ref_mel_cache_config)
                ),
                profiling_plan=(
                    None if self.config.profiling_plan is None else dict(self.config.profiling_plan)
                ),
                resume_from_checkpoint=self.config.resume_from_checkpoint,
                tracking_plan=(
                    None if self.config.tracking_plan is None else dict(self.config.tracking_plan)
                ),
                tracking=self.tracking,
                live_progress=self._live_progress_payload(),
                phase_history=self.phase_history,
            ),
        )

    def _live_progress_payload(self) -> dict[str, object] | None:
        """Return the current live heartbeat as a JSON-serializable mapping."""
        if self.latest_heartbeat is None:
            return None
        return asdict(self.latest_heartbeat)

    def _ensure_terminal_phase(self, phase: str) -> None:
        """Append one terminal phase event if it has not been recorded already."""
        live_progress = self._live_progress_payload()
        updated_at = self._status_timestamp()
        if live_progress is None:
            current_epoch = 0
            current_step = 0
        else:
            existing_phase = live_progress["phase"]
            if existing_phase == phase:
                return
            current_epoch = self._required_progress_int(live_progress, "current_epoch")
            current_step = self._required_progress_int(live_progress, "current_step")
        self.phase_history.append(
            {
                "phase": phase,
                "updated_at": updated_at,
                "current_epoch": current_epoch,
                "current_step": current_step,
                "current_optimizer_step": current_step,
                "current_train_iteration": (
                    0
                    if self.latest_heartbeat is None
                    else (
                        0
                        if self.latest_heartbeat.current_train_iteration is None
                        else self.latest_heartbeat.current_train_iteration
                    )
                ),
            }
        )

    def _status_timestamp(self) -> str:
        """Return the timestamp used for the initial startup heartbeat."""
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _required_progress_int(self, payload: dict[str, object], key: str) -> int:
        """Return one required integer field from the current live heartbeat payload."""
        value = payload.get(key)
        if not isinstance(value, int):
            raise SystemExit(f"Task 101 reporter encountered malformed live progress `{key}`.")
        return value
