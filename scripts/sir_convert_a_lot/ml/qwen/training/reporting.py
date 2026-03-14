"""Report and status helpers for the Qwen training pipeline.

Purpose:
    Provide truthful live heartbeat persistence, phase-history tracking,
    and machine-readable terminal reports for Qwen training.

Relationships:
    - Consumes data contracts from `ml.qwen.training.models`.
    - Consumes progress heartbeats emitted by the patched Qwen trainer.
    - Used by the in-container trainer probe to maintain status artifacts.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import NonFiniteLossError
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import TrainingProgressHeartbeat
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingReport

if TYPE_CHECKING:
    from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary


@dataclass(frozen=True)
class StatusReporterConfig:
    """Static run metadata required to write one training status artifact."""

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
    tracking_plan: Mapping[str, object] | None = None
    gradient_accumulation_steps: int = 4
    dataloader_tuning: Mapping[str, object] | None = None
    heartbeat_policy: Mapping[str, object] | None = None
    finite_loss_guard_config: Mapping[str, object] | None = None
    ref_mel_cache_config: Mapping[str, object] | None = None
    bundle_precomputed_reference_input: Mapping[str, object] | None = None
    profiling_plan: Mapping[str, object] | None = None


@dataclass
class StatusReporter:
    """Persist truthful live training heartbeat and terminal status payloads."""

    config: StatusReporterConfig
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
            merge_launch_tracking_metadata(self.config.launch_metadata_path, tracking=tracking)

    def heartbeat(self, heartbeat: TrainingProgressHeartbeat) -> None:
        """Persist one live heartbeat emitted by the patched trainer."""
        self._record_heartbeat(heartbeat)
        self._write_running_status()

    def write_completed(self, training_summary: TrainingSummary) -> None:
        """Persist the terminal completed or signal-stop status payload."""
        terminal_phase = "signal-stop" if training_summary.stopped_early else "completed"
        self._ensure_terminal_phase(terminal_phase)
        write_json(
            self.config.status_path,
            _completed_status_payload(
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
                training_summary=training_summary,
                live_progress=self._live_progress_payload(),
                phase_history=self.phase_history,
            ),
        )

    def write_failed(self, exc: Exception) -> None:
        """Persist the terminal failed status payload with the last live heartbeat."""
        self._ensure_terminal_phase("failed")
        write_json(
            self.config.status_path,
            _failed_status_payload(
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
        write_json(
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
            raise SystemExit(f"Reporter encountered malformed live progress `{key}`.")
        return value


# --- Payload Builders ---


def build_training_report(
    *,
    model_id: str,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    bundle_precomputed_reference_input: Mapping[str, object] | None,
    training_summary: TrainingSummary,
) -> TrainingReport:
    """Build the machine-readable report from one completed training run."""
    return TrainingReport(
        generated_at=_utc_now_iso(),
        model_id=model_id,
        train_jsonl=train_jsonl.as_posix(),
        eval_jsonl=eval_jsonl.as_posix(),
        output_dir=output_dir.as_posix(),
        train_row_count=train_row_count,
        eval_row_count=eval_row_count,
        upstream_trainer_uses_eval_manifest=False,
        torch_version=str(torch.__version__),
        torchaudio_version=_package_version("torchaudio"),
        torch_cuda_available=True,
        torch_cuda_device_count=int(torch.cuda.device_count()),
        torch_hip_version=str(torch.version.hip),
        flash_attn_importable=importlib.util.find_spec("flash_attn") is not None,
        flash_attn_version=_package_version("flash-attn"),
        bundle_precomputed_reference_input=(
            None
            if bundle_precomputed_reference_input is None
            else dict(bundle_precomputed_reference_input)
        ),
        tracking=None if training_summary.tracking is None else asdict(training_summary.tracking),
        training_summary=asdict(training_summary),
    )


def _running_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    checkpoint_interval_steps: int,
    gradient_accumulation_steps: int,
    durable_checkpoint_retention: int,
    durable_checkpoint_min_free_bytes: int,
    dataloader_tuning: dict[str, object] | None,
    heartbeat_policy: dict[str, object] | None,
    finite_loss_guard_config: dict[str, object] | None,
    ref_mel_cache_config: dict[str, object] | None,
    bundle_precomputed_reference_input: dict[str, object] | None,
    profiling_plan: dict[str, object] | None,
    resume_from_checkpoint: Path | None,
    tracking_plan: dict[str, object] | None = None,
    tracking: dict[str, object] | None = None,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build the running-status payload written before training starts."""
    current_phase = None if live_progress is None else live_progress.get("phase")
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    raw_current_optimizer_step = (
        None if live_progress is None else live_progress.get("current_optimizer_step")
    )
    current_optimizer_step = (
        current_step if raw_current_optimizer_step is None else raw_current_optimizer_step
    )
    raw_current_train_iteration = (
        None if live_progress is None else live_progress.get("current_train_iteration")
    )
    current_train_iteration = (
        current_optimizer_step
        if raw_current_train_iteration is None
        else raw_current_train_iteration
    )
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_path = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_path")
    )
    latest_durable_checkpoint_step = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_step")
    )
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    return {
        "status": "running",
        "stage": "training",
        "updated_at": _utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "upstream_trainer_uses_eval_manifest": False,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "step_semantics": _step_semantics_payload(gradient_accumulation_steps),
        "checkpoint_interval_steps": checkpoint_interval_steps,
        "durable_checkpoint_retention": durable_checkpoint_retention,
        "durable_checkpoint_min_free_bytes": durable_checkpoint_min_free_bytes,
        "dataloader_tuning": dataloader_tuning,
        "heartbeat_policy": heartbeat_policy,
        "finite_loss_guard": finite_loss_guard_config,
        "ref_mel_cache": ref_mel_cache_config,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "profiling": profiling_plan,
        "resumed_from_checkpoint_path": (
            None if resume_from_checkpoint is None else resume_from_checkpoint.as_posix()
        ),
        "current_phase": current_phase,
        "current_epoch": current_epoch,
        "current_step": current_step,
        "current_optimizer_step": current_optimizer_step,
        "current_train_iteration": current_train_iteration,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "latest_durable_checkpoint_path": latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "tracking_plan": tracking_plan,
        "tracking": tracking,
        "phase_history": [] if phase_history is None else phase_history,
    }


def _completed_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    bundle_precomputed_reference_input: dict[str, object] | None,
    training_summary: TrainingSummary,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build the terminal success payload for the training status artifact."""
    current_phase = "signal-stop" if training_summary.stopped_early else "completed"
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    raw_current_optimizer_step = (
        None if live_progress is None else live_progress.get("current_optimizer_step")
    )
    current_optimizer_step = (
        current_step if raw_current_optimizer_step is None else raw_current_optimizer_step
    )
    raw_current_train_iteration = (
        None if live_progress is None else live_progress.get("current_train_iteration")
    )
    current_train_iteration = (
        current_optimizer_step
        if raw_current_train_iteration is None
        else raw_current_train_iteration
    )
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    return {
        "status": "stopped" if training_summary.stopped_early else "completed",
        "stage": "training",
        "updated_at": _utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "upstream_trainer_uses_eval_manifest": False,
        "gradient_accumulation_steps": training_summary.gradient_accumulation_steps,
        "step_semantics": _step_semantics_payload(training_summary.gradient_accumulation_steps),
        "current_phase": current_phase,
        "current_epoch": current_epoch,
        "current_step": current_step,
        "current_optimizer_step": current_optimizer_step,
        "current_train_iteration": current_train_iteration,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "optimizer_steps_completed": training_summary.optimizer_steps_completed,
        "train_iterations_completed": training_summary.train_iterations_completed,
        "checkpoint_interval_steps": training_summary.checkpoint_interval_steps,
        "durable_checkpoint_retention": training_summary.durable_checkpoint_retention,
        "durable_checkpoint_min_free_bytes": training_summary.durable_checkpoint_min_free_bytes,
        "dataloader_tuning": training_summary.dataloader_tuning,
        "heartbeat_policy": training_summary.heartbeat_policy,
        "finite_loss_guard": training_summary.finite_loss_guard,
        "ref_mel_cache": training_summary.ref_mel_cache,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "acceptance_measurement_valid": training_summary.acceptance_measurement_valid,
        "resumed_from_checkpoint_path": training_summary.resumed_from_checkpoint_path,
        "latest_durable_checkpoint_path": training_summary.latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": training_summary.latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "stop_requested": training_summary.stop_requested,
        "stop_signal": training_summary.stop_signal,
        "stopped_early": training_summary.stopped_early,
        "tracking": None
        if training_summary.tracking is None
        else asdict(training_summary.tracking),
        "phase_history": [] if phase_history is None else phase_history,
    }


def _failed_status_payload(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    bundle_precomputed_reference_input: dict[str, object] | None = None,
    exc: Exception,
    live_progress: dict[str, object] | None = None,
    phase_history: list[dict[str, object]] | None = None,
    tracking: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the terminal failure payload for the training status artifact."""
    current_epoch = None if live_progress is None else live_progress.get("current_epoch")
    current_step = None if live_progress is None else live_progress.get("current_step")
    raw_current_optimizer_step = (
        None if live_progress is None else live_progress.get("current_optimizer_step")
    )
    current_optimizer_step = (
        current_step if raw_current_optimizer_step is None else raw_current_optimizer_step
    )
    raw_current_train_iteration = (
        None if live_progress is None else live_progress.get("current_train_iteration")
    )
    current_train_iteration = (
        current_optimizer_step
        if raw_current_train_iteration is None
        else raw_current_train_iteration
    )
    latest_loss = None if live_progress is None else live_progress.get("latest_loss")
    smoothed_loss = None if live_progress is None else live_progress.get("smoothed_loss")
    latest_durable_checkpoint_path = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_path")
    )
    latest_durable_checkpoint_step = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_step")
    )
    latest_durable_checkpoint_saved_at = (
        None if live_progress is None else live_progress.get("latest_durable_checkpoint_saved_at")
    )
    finite_loss_guard_payload = None
    acceptance_measurement_valid = None
    if isinstance(exc, NonFiniteLossError):
        finite_loss_guard_payload = exc.payload()
        acceptance_measurement_valid = False
    return {
        "status": "failed",
        "stage": "training",
        "updated_at": _utc_now_iso(),
        "train_jsonl": train_jsonl.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "train_row_count": train_row_count,
        "eval_row_count": eval_row_count,
        "upstream_trainer_uses_eval_manifest": False,
        "gradient_accumulation_steps": (
            None if live_progress is None else live_progress.get("gradient_accumulation_steps")
        ),
        "step_semantics": _step_semantics_payload(
            None
            if live_progress is None
            else _optional_int(live_progress, "gradient_accumulation_steps")
        ),
        "current_phase": "failed",
        "current_epoch": current_epoch,
        "current_step": current_step,
        "current_optimizer_step": current_optimizer_step,
        "current_train_iteration": current_train_iteration,
        "latest_loss": latest_loss,
        "smoothed_loss": smoothed_loss,
        "latest_durable_checkpoint_path": latest_durable_checkpoint_path,
        "latest_durable_checkpoint_step": latest_durable_checkpoint_step,
        "latest_durable_checkpoint_saved_at": latest_durable_checkpoint_saved_at,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "finite_loss_guard": finite_loss_guard_payload,
        "acceptance_measurement_valid": acceptance_measurement_valid,
        "tracking": tracking,
        "phase_history": [] if phase_history is None else phase_history,
        "error": f"{type(exc).__name__}: {exc}",
    }


# --- Helpers ---


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_launch_tracking_metadata(
    launch_metadata_path: Path,
    *,
    tracking: dict[str, object],
) -> None:
    """Merge live tracker metadata into the detached launch artifact."""
    if not launch_metadata_path.exists():
        return
    payload = json.loads(launch_metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Launch metadata was malformed while merging tracking data.")
    payload["tracking"] = tracking
    write_json(launch_metadata_path, payload)


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_version(distribution_name: str) -> str | None:
    """Return one installed package version, or `None` when it is absent."""
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return one optional integer payload field."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        return None
    return value


def _step_semantics_payload(gradient_accumulation_steps: int | None) -> dict[str, object] | None:
    """Return a machine-readable step-semantics payload for status artifacts."""
    if gradient_accumulation_steps is None:
        return None
    return {
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "optimizer_step_definition": (
            "increments only on iterations where accelerate.sync_gradients is true"
        ),
        "train_iteration_definition": "increments on every dataloader iteration",
    }
