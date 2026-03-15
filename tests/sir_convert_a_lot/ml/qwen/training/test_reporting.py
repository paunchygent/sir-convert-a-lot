"""Focused tests for canonical Qwen live status reporting."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.metadata import render_status_markdown
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedStatus
from scripts.sir_convert_a_lot.ml.qwen.training.reporting import (
    StatusReporter,
    StatusReporterConfig,
)

NonFiniteLossError = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls"
).NonFiniteLossError
TrainingProgressHeartbeat = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.sft_12hz_progress"
).TrainingProgressHeartbeat


def _required_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return one nested mapping from a reporter payload."""
    resolved = payload[key]
    assert isinstance(resolved, dict)
    return resolved


def test_status_reporter_persists_live_phase_history_and_tracking(tmp_path: Path) -> None:
    """The reporter should preserve live progress, phase history, and tracker ids."""
    output_dir = tmp_path / "run"
    status_path = output_dir / "status.json"
    launch_metadata_path = tmp_path / "launch.json"
    launch_metadata_path.write_text(
        json.dumps({"launch_id": "qwen-run"}) + "\n",
        encoding="utf-8",
    )
    reporter = StatusReporter(
        StatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=launch_metadata_path,
            talker_runtime_path=output_dir / "talker_runtime.json",
            train_jsonl=tmp_path / "train.jsonl",
            eval_jsonl=tmp_path / "eval.jsonl",
            output_dir=output_dir,
            train_row_count=10,
            eval_row_count=2,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            resume_from_checkpoint=None,
            tracking_plan={
                "project_name": "qwen-training",
                "run_name": "qwen-run",
            },
            heartbeat_policy={"interval_optimizer_steps": 20},
            finite_loss_guard_config={
                "enabled": True,
                "max_consecutive_non_finite_steps": 3,
            },
            bundle_precomputed_reference_input={
                "kind": "ref_mel",
                "version": "task101_ref_mel_v1",
                "artifact_count": 2,
            },
            throughput_profile={
                "profile_label": "hemma-throughput-aggressive-v1",
                "policy_kind": "bucketed-frame-token-budget-v1",
                "max_batch_size": 8,
                "minimum_required_max_batch_size": 8,
            },
        )
    )

    reporter.write_startup()
    reporter.tracking_ready(
        {
            "project_name": "qwen-training",
            "run_name": "qwen-run",
            "mlflow_run_id": "mlflow-run-id",
        }
    )
    reporter.runtime_ready(
        {
            "text_projection": {
                "available": True,
                "resolved_path": "model.talker.text_projection",
                "probeable_as_module": True,
            }
        }
    )
    reporter.heartbeat(
        TrainingProgressHeartbeat(
            phase="train",
            updated_at="2026-03-13T12:00:01Z",
            current_epoch=0,
            current_step=1,
            latest_loss=1.5,
            smoothed_loss=1.5,
            latest_durable_checkpoint_path=None,
            latest_durable_checkpoint_step=None,
            latest_durable_checkpoint_saved_at=None,
        )
    )
    reporter.heartbeat(
        TrainingProgressHeartbeat(
            phase="durable-checkpoint-save",
            updated_at="2026-03-13T12:00:03Z",
            current_epoch=0,
            current_step=2,
            latest_loss=1.2,
            smoothed_loss=1.47,
            latest_durable_checkpoint_path=(
                output_dir / "checkpoints" / "state-step-00000002"
            ).as_posix(),
            latest_durable_checkpoint_step=2,
            latest_durable_checkpoint_saved_at="2026-03-13T12:00:03Z",
        )
    )
    reporter.heartbeat(
        TrainingProgressHeartbeat(
            phase="eval",
            updated_at="2026-03-13T12:00:04Z",
            current_epoch=0,
            current_step=2,
            current_optimizer_step=2,
            current_train_iteration=2,
            gradient_accumulation_steps=4,
            latest_loss=1.2,
            smoothed_loss=1.47,
            latest_eval_loss=0.9,
            best_eval_loss=0.9,
            best_eval_step=2,
            eval_runs_completed=1,
            latest_durable_checkpoint_path=(
                output_dir / "checkpoints" / "state-step-00000002"
            ).as_posix(),
            latest_durable_checkpoint_step=2,
            latest_durable_checkpoint_saved_at="2026-03-13T12:00:03Z",
        )
    )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    launch_payload = json.loads(launch_metadata_path.read_text(encoding="utf-8"))

    assert payload["status"] == "running"
    assert payload["current_phase"] == "eval"
    assert payload["current_epoch"] == 0
    assert payload["current_step"] == 2
    assert payload["current_optimizer_step"] == 2
    assert payload["current_train_iteration"] == 2
    assert payload["gradient_accumulation_steps"] == 4
    assert payload["step_semantics"]["gradient_accumulation_steps"] == 4
    assert payload["step_semantics"]["epoch_index_base"] == 0
    assert payload["smoothed_loss"] == 1.47
    assert payload["latest_eval_loss"] == 0.9
    assert payload["best_eval_loss"] == 0.9
    assert payload["best_eval_step"] == 2
    assert payload["eval_runs_completed"] == 1
    assert payload["heartbeat_policy"] == {"interval_optimizer_steps": 20}
    assert payload["finite_loss_guard"] == {
        "enabled": True,
        "max_consecutive_non_finite_steps": 3,
    }
    assert payload["bundle_precomputed_reference_input"] == {
        "kind": "ref_mel",
        "version": "task101_ref_mel_v1",
        "artifact_count": 2,
    }
    assert payload["throughput_profile"] == {
        "profile_label": "hemma-throughput-aggressive-v1",
        "policy_kind": "bucketed-frame-token-budget-v1",
        "max_batch_size": 8,
        "minimum_required_max_batch_size": 8,
    }
    talker_runtime = _required_mapping(payload, "talker_runtime")
    text_projection = _required_mapping(talker_runtime, "text_projection")
    assert text_projection["resolved_path"] == (
        "model.talker.text_projection"
    )
    assert payload["tracking"]["mlflow_run_id"] == "mlflow-run-id"
    assert [event["phase"] for event in payload["phase_history"]] == [
        "startup",
        "train",
        "durable-checkpoint-save",
        "eval",
    ]
    assert launch_payload["tracking"]["mlflow_run_id"] == "mlflow-run-id"


def test_status_markdown_surfaces_live_training_fields() -> None:
    """The markdown renderer should surface live phase and tracker summary fields."""
    markdown = render_status_markdown(
        DetachedStatus(
            checked_at="2026-03-13T12:00:10Z",
            launch_kind="training",
            launch_id="qwen-run",
            container_name="qwen-run-container",
            container_id="container-id",
            status="running",
            running=True,
            exit_code=0,
            oom_killed=False,
            started_at="2026-03-13T12:00:00Z",
            finished_at="",
            pilot_status_found=True,
            pilot_status={
                "updated_at": "2026-03-13T12:00:08Z",
                "current_phase": "train",
                "current_epoch": 0,
                "current_step": 3,
                "latest_loss": 1.1,
                "smoothed_loss": 1.3,
                "latest_eval_loss": 0.7,
                "best_eval_loss": 0.7,
                "best_eval_step": 2,
                "eval_runs_completed": 1,
                "latest_durable_checkpoint_step": 2,
                "latest_durable_checkpoint_saved_at": "2026-03-13T12:00:03Z",
                "tracking": {"mlflow_run_id": "mlflow-run-id"},
                "bundle_precomputed_reference_input": {
                    "kind": "ref_mel",
                    "version": "task101_ref_mel_v1",
                    "artifact_count": 2,
                },
                "throughput_profile": {
                    "profile_label": "hemma-throughput-aggressive-v1",
                    "policy_kind": "bucketed-frame-token-budget-v1",
                    "max_batch_size": 8,
                    "minimum_required_max_batch_size": 8,
                    "batch_occupancy": {
                        "total_batches": 1,
                        "realized_max_batch_size": 1,
                        "batch_size_histogram": {"1": 1},
                    },
                },
                "data_path_attribution": {
                    "proof_mode_enabled": True,
                    "authoritative": True,
                    "runtime_ref_mel_extraction_count": 0,
                    "persisted_ref_mel_load_count": 3,
                },
                "diagnostic": {
                    "kind": "diagnose-non-finite",
                },
            },
            pilot_report_found=False,
            pilot_report=None,
            latest_checkpoint_found=False,
            latest_checkpoint=None,
            logs_tail="still running",
        )
    )

    assert "- launch_kind: `training`" in markdown
    assert "- pilot_current_phase: `train`" in markdown
    assert "- pilot_current_step: `3`" in markdown
    assert "- pilot_smoothed_loss: `1.3`" in markdown
    assert "- pilot_latest_eval_loss: `0.7`" in markdown
    assert "- pilot_best_eval_loss: `0.7`" in markdown
    assert "- pilot_best_eval_step: `2`" in markdown
    assert "- pilot_eval_runs_completed: `1`" in markdown
    assert "- pilot_mlflow_run_id: `mlflow-run-id`" in markdown
    assert "- pilot_diagnostic_kind: `diagnose-non-finite`" in markdown
    assert "- pilot_bundle_precomputed_reference_input_kind: `ref_mel`" in markdown
    assert "- pilot_bundle_precomputed_reference_input_version: `task101_ref_mel_v1`" in markdown
    assert "- pilot_bundle_precomputed_reference_input_count: `2`" in markdown
    assert "- pilot_throughput_profile_label: `hemma-throughput-aggressive-v1`" in markdown
    assert "- pilot_throughput_policy_kind: `bucketed-frame-token-budget-v1`" in markdown
    assert "- pilot_throughput_max_batch_size: `8`" in markdown
    assert "- pilot_throughput_minimum_required_max_batch_size: `8`" in markdown
    assert "- pilot_throughput_total_batches: `1`" in markdown
    assert "- pilot_throughput_realized_max_batch_size: `1`" in markdown
    assert "- pilot_data_path_proof_mode_enabled: `True`" in markdown
    assert "- pilot_data_path_authoritative: `True`" in markdown
    assert "- pilot_runtime_ref_mel_extraction_count: `0`" in markdown
    assert "- pilot_persisted_ref_mel_load_count: `3`" in markdown


def test_status_reporter_marks_non_finite_loss_failures_invalid_for_acceptance(
    tmp_path: Path,
) -> None:
    """Failed status should surface the finite-loss guard blocker explicitly."""
    output_dir = tmp_path / "run"
    status_path = output_dir / "status.json"
    reporter = StatusReporter(
        StatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=None,
            talker_runtime_path=output_dir / "talker_runtime.json",
            train_jsonl=tmp_path / "train.jsonl",
            eval_jsonl=tmp_path / "eval.jsonl",
            output_dir=output_dir,
            train_row_count=10,
            eval_row_count=2,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            resume_from_checkpoint=None,
        )
    )

    reporter.write_startup()
    reporter.runtime_ready(
        {
            "text_projection": {
                "available": True,
                "resolved_path": "model.talker.text_projection",
                "probeable_as_module": True,
            }
        }
    )
    reporter.write_failed(
        NonFiniteLossError(
            optimizer_step=8,
            current_epoch=1,
            current_train_iteration=32,
            consecutive_non_finite_steps=3,
            max_consecutive_non_finite_steps=3,
            loss_value=float("nan"),
            main_loss_value=float("nan"),
            sub_talker_loss_value=0.1,
            grad_norm_value=float("nan"),
        )
    )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["current_epoch"] == 1
    assert payload["current_step"] == 8
    assert payload["current_optimizer_step"] == 8
    assert payload["current_train_iteration"] == 32
    assert payload["acceptance_measurement_valid"] is False
    talker_runtime = _required_mapping(payload, "talker_runtime")
    text_projection = _required_mapping(talker_runtime, "text_projection")
    assert text_projection["resolved_path"] == (
        "model.talker.text_projection"
    )
    assert payload["finite_loss_guard"]["trigger_reason"] == "non-finite-loss"
    assert payload["finite_loss_guard"]["optimizer_step"] == 8
    assert payload["finite_loss_guard"]["current_train_iteration"] == 32
    assert payload["finite_loss_guard"]["main_loss_is_finite"] is False
    assert payload["finite_loss_guard"]["sub_talker_loss_is_finite"] is True
    assert payload["finite_loss_guard"]["grad_norm_is_finite"] is False
    assert payload["finite_loss_guard"]["step_forensics"] is None
    assert payload["finite_loss_guard"]["recent_observations"] is None


def test_status_reporter_failure_overrides_stale_live_step_counters(tmp_path: Path) -> None:
    """Failed status should report the exception step even when the last heartbeat is older."""
    output_dir = tmp_path / "run"
    status_path = output_dir / "status.json"
    reporter = StatusReporter(
        StatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=None,
            talker_runtime_path=output_dir / "talker_runtime.json",
            train_jsonl=tmp_path / "train.jsonl",
            eval_jsonl=tmp_path / "eval.jsonl",
            output_dir=output_dir,
            train_row_count=10,
            eval_row_count=2,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            resume_from_checkpoint=None,
        )
    )

    reporter.write_startup()
    reporter.heartbeat(
        TrainingProgressHeartbeat(
            phase="train",
            updated_at="2026-03-14T18:19:00Z",
            current_epoch=0,
            current_step=1,
            current_optimizer_step=1,
            current_train_iteration=4,
            gradient_accumulation_steps=4,
            latest_loss=14.1,
            smoothed_loss=14.1,
            latest_eval_loss=0.8,
            best_eval_loss=0.8,
            best_eval_step=1,
            eval_runs_completed=1,
            latest_durable_checkpoint_path=None,
            latest_durable_checkpoint_step=None,
            latest_durable_checkpoint_saved_at=None,
        )
    )

    reporter.write_failed(
        NonFiniteLossError(
            optimizer_step=17,
            current_epoch=0,
            current_train_iteration=68,
            consecutive_non_finite_steps=3,
            max_consecutive_non_finite_steps=3,
            loss_value=float("nan"),
            main_loss_value=float("nan"),
            sub_talker_loss_value=0.1,
            grad_norm_value=float("nan"),
        )
    )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["current_optimizer_step"] == 17
    assert payload["current_step"] == 17
    assert payload["current_train_iteration"] == 68
    assert payload["latest_eval_loss"] == 0.8
    assert payload["best_eval_loss"] == 0.8
    assert payload["best_eval_step"] == 1
    assert payload["eval_runs_completed"] == 1
    assert payload["finite_loss_guard"]["optimizer_step"] == 17
    assert (
        payload["finite_loss_guard"]["main_loss_value"]
        != payload["finite_loss_guard"]["sub_talker_loss_value"]
    )
    assert payload["finite_loss_guard"]["step_forensics"] is None
    assert payload["phase_history"][-1]["current_optimizer_step"] == 17
    assert payload["phase_history"][-1]["current_train_iteration"] == 68
