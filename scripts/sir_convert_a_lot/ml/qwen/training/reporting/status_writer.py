"""Stateful status writer for Qwen training progress artifacts.

Purpose:
    Persist truthful startup, heartbeat, completed, and failed status payloads
    while keeping payload assembly and artifact I/O separate.

Relationships:
    - Used by the in-container Qwen trainer entrypoint.
    - Consumes `config`, `status_payloads`, `artifact_io`, and
      `failure_projection`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import (
    TrainingProgressHeartbeat,
)

from .artifact_io import merge_launch_tracking_metadata, write_json
from .config import StatusReporterConfig
from .failure_projection import (
    required_progress_int,
    resolve_failed_progress,
    resolve_terminal_progress,
)
from .status_payloads import (
    completed_status_payload,
    failed_status_payload,
    running_status_payload,
)

if False:  # pragma: no cover
    from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary


@dataclass
class StatusReporter:
    """Persist truthful live training heartbeat and terminal status payloads."""

    config: StatusReporterConfig
    tracking: dict[str, object] | None = None
    talker_runtime: dict[str, object] | None = None
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
            dataloader_length=self.config.dataloader_length,
            eval_dataloader_length=self.config.eval_dataloader_length,
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
            merge_launch_tracking_metadata(self.config.launch_metadata_path, tracking=tracking)

    def runtime_ready(self, talker_runtime: dict[str, object]) -> None:
        """Persist the resolved talker-runtime fingerprint once the model is loaded."""
        self.talker_runtime = talker_runtime
        if self.config.talker_runtime_path is not None:
            write_json(self.config.talker_runtime_path, talker_runtime)
        self._write_running_status()

    def heartbeat(self, heartbeat: TrainingProgressHeartbeat) -> None:
        """Persist one live heartbeat emitted by the patched trainer."""
        self._record_heartbeat(heartbeat)
        self._write_running_status()

    def write_completed(self, training_summary: "TrainingSummary") -> None:
        """Persist the terminal completed or signal-stop status payload."""
        terminal_phase = "signal-stop" if training_summary.stopped_early else "completed"
        self._ensure_terminal_phase(terminal_phase)
        write_json(
            self.config.status_path,
            completed_status_payload(
                train_jsonl=self.config.train_jsonl,
                eval_jsonl=self.config.eval_jsonl,
                output_dir=self.config.output_dir,
                train_row_count=self.config.train_row_count,
                eval_row_count=self.config.eval_row_count,
                bundle_precomputed_reference_input=(
                    None
                    if self.config.bundle_precomputed_reference_input is None
                    else dict(self.config.bundle_precomputed_reference_input)
                ),
                throughput_profile=(
                    None
                    if self.config.throughput_profile is None
                    else dict(self.config.throughput_profile)
                ),
                training_summary=training_summary,
                live_progress=self._live_progress_payload(),
                phase_history=self.phase_history,
            ),
        )

    def write_failed(self, exc: BaseException) -> dict[str, object]:
        """Persist the terminal failed status payload with the last live heartbeat."""
        terminal_progress = resolve_failed_progress(
            live_progress=self._live_progress_payload(),
            exc=exc,
        )
        self._ensure_terminal_phase("failed", terminal_progress=terminal_progress)
        payload = failed_status_payload(
            train_jsonl=self.config.train_jsonl,
            eval_jsonl=self.config.eval_jsonl,
            output_dir=self.config.output_dir,
            train_row_count=self.config.train_row_count,
            eval_row_count=self.config.eval_row_count,
            dataloader_length=self.config.dataloader_length,
            eval_dataloader_length=self.config.eval_dataloader_length,
            bundle_precomputed_reference_input=(
                None
                if self.config.bundle_precomputed_reference_input is None
                else dict(self.config.bundle_precomputed_reference_input)
            ),
            throughput_profile=(
                None
                if self.config.throughput_profile is None
                else dict(self.config.throughput_profile)
            ),
            diagnostic=(None if self.config.diagnostic is None else dict(self.config.diagnostic)),
            exc=exc,
            live_progress=self._live_progress_payload(),
            phase_history=self.phase_history,
            tracking=self.tracking,
            talker_runtime=self.talker_runtime,
        )
        write_json(self.config.status_path, payload)
        return payload

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
        write_json(
            self.config.status_path,
            running_status_payload(
                train_jsonl=self.config.train_jsonl,
                eval_jsonl=self.config.eval_jsonl,
                output_dir=self.config.output_dir,
                train_row_count=self.config.train_row_count,
                eval_row_count=self.config.eval_row_count,
                dataloader_length=self.config.dataloader_length,
                eval_dataloader_length=self.config.eval_dataloader_length,
                checkpoint_interval_steps=self.config.checkpoint_interval_steps,
                eval_interval_steps=self.config.eval_interval_steps,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                durable_checkpoint_retention=self.config.durable_checkpoint_retention,
                durable_checkpoint_min_free_bytes=self.config.durable_checkpoint_min_free_bytes,
                dataloader_tuning=(
                    None
                    if self.config.dataloader_tuning is None
                    else dict(self.config.dataloader_tuning)
                ),
                heartbeat_policy=(
                    None
                    if self.config.heartbeat_policy is None
                    else dict(self.config.heartbeat_policy)
                ),
                finite_loss_guard_config=(
                    None
                    if self.config.finite_loss_guard_config is None
                    else dict(self.config.finite_loss_guard_config)
                ),
                ref_mel_cache_config=(
                    None
                    if self.config.ref_mel_cache_config is None
                    else dict(self.config.ref_mel_cache_config)
                ),
                bundle_precomputed_reference_input=(
                    None
                    if self.config.bundle_precomputed_reference_input is None
                    else dict(self.config.bundle_precomputed_reference_input)
                ),
                throughput_profile=(
                    None
                    if self.config.throughput_profile is None
                    else dict(self.config.throughput_profile)
                ),
                profiling_plan=(
                    None if self.config.profiling_plan is None else dict(self.config.profiling_plan)
                ),
                diagnostic=(
                    None if self.config.diagnostic is None else dict(self.config.diagnostic)
                ),
                talker_runtime=(None if self.talker_runtime is None else dict(self.talker_runtime)),
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

    def _ensure_terminal_phase(
        self,
        phase: str,
        *,
        terminal_progress: dict[str, object | None] | None = None,
    ) -> None:
        """Append one terminal phase event if it has not been recorded already."""
        live_progress = self._live_progress_payload()
        updated_at = self._status_timestamp()
        if terminal_progress is None:
            terminal_progress = resolve_terminal_progress(live_progress=live_progress)
        if live_progress is None and terminal_progress is None:
            current_epoch = 0
            current_step = 0
            current_optimizer_step = 0
            current_train_iteration = 0
        else:
            existing_phase = None if live_progress is None else live_progress["phase"]
            if existing_phase == phase:
                return
            if terminal_progress is None:
                raise SystemExit("Reporter encountered missing terminal progress.")
            current_epoch = required_progress_int(terminal_progress, "current_epoch")
            current_step = required_progress_int(terminal_progress, "current_step")
            current_optimizer_step = required_progress_int(
                terminal_progress,
                "current_optimizer_step",
            )
            current_train_iteration = required_progress_int(
                terminal_progress,
                "current_train_iteration",
            )
        self.phase_history.append(
            {
                "phase": phase,
                "updated_at": updated_at,
                "current_epoch": current_epoch,
                "current_step": current_step,
                "current_optimizer_step": current_optimizer_step,
                "current_train_iteration": current_train_iteration,
            }
        )

    def _status_timestamp(self) -> str:
        """Return the timestamp used for the initial startup heartbeat."""
        from datetime import UTC, datetime

        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
