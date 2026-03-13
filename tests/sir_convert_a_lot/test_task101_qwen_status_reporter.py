"""Focused tests for Task 101 live status reporting.

Purpose:
    Validate the Task 101 live heartbeat reporter and markdown rendering added
    for `T157` without requiring a real detached Docker launch or GPU run.

Relationships:
    - Exercises `task101_qwen_pilot_status_reporter.py`.
    - Exercises `task101_qwen_pilot_metadata.py` for extracted live-status
      markdown fields.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_metadata import _status_markdown
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime_contract import (
    Task101DetachedStatus,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_status_reporter import (
    Task101PilotStatusReporter,
    Task101PilotStatusReporterConfig,
)

SFT_PATCH_ROOT = Path(__file__).resolve().parents[2] / "scripts/devops/qwen_finetuning_patches"
if SFT_PATCH_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SFT_PATCH_ROOT.as_posix())

TrainingProgressHeartbeat = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.sft_12hz_progress"
).TrainingProgressHeartbeat


def test_status_reporter_persists_live_phase_history_and_tracking(tmp_path: Path) -> None:
    """The reporter should preserve live progress, phase history, and tracker ids."""
    output_dir = tmp_path / "run"
    status_path = output_dir / "status.json"
    launch_metadata_path = tmp_path / "launch.json"
    launch_metadata_path.write_text(
        json.dumps({"launch_id": "task101-run"}) + "\n", encoding="utf-8"
    )
    reporter = Task101PilotStatusReporter(
        Task101PilotStatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=launch_metadata_path,
            train_jsonl=tmp_path / "train.jsonl",
            eval_jsonl=tmp_path / "eval.jsonl",
            output_dir=output_dir,
            train_row_count=10,
            eval_row_count=2,
            checkpoint_interval_steps=100,
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            resume_from_checkpoint=None,
            tracking_plan={
                "project_name": "task101-qwen-pilot",
                "run_name": "task101-run",
            },
        )
    )

    reporter.write_startup()
    reporter.tracking_ready(
        {
            "project_name": "task101-qwen-pilot",
            "run_name": "task101-run",
            "mlflow_run_id": "mlflow-run-id",
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
            phase="checkpoint-save",
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

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    launch_payload = json.loads(launch_metadata_path.read_text(encoding="utf-8"))

    assert payload["status"] == "running"
    assert payload["current_phase"] == "checkpoint-save"
    assert payload["current_epoch"] == 0
    assert payload["current_step"] == 2
    assert payload["current_optimizer_step"] == 2
    assert payload["current_train_iteration"] == 2
    assert payload["gradient_accumulation_steps"] == 4
    assert payload["step_semantics"]["gradient_accumulation_steps"] == 4
    assert payload["smoothed_loss"] == 1.47
    assert payload["tracking"]["mlflow_run_id"] == "mlflow-run-id"
    assert [event["phase"] for event in payload["phase_history"]] == [
        "startup",
        "train",
        "checkpoint-save",
    ]
    assert launch_payload["tracking"]["mlflow_run_id"] == "mlflow-run-id"


def test_status_markdown_surfaces_live_pilot_fields() -> None:
    """The markdown renderer should surface live phase and tracker summary fields."""
    markdown = _status_markdown(
        Task101DetachedStatus(
            checked_at="2026-03-13T12:00:10Z",
            launch_id="task101-run",
            container_name="task101-run-container",
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
                "latest_durable_checkpoint_step": 2,
                "latest_durable_checkpoint_saved_at": "2026-03-13T12:00:03Z",
                "tracking": {"mlflow_run_id": "mlflow-run-id"},
            },
            pilot_report_found=False,
            pilot_report=None,
            latest_checkpoint_found=False,
            latest_checkpoint=None,
            logs_tail="still running",
        )
    )

    assert "- pilot_current_phase: `train`" in markdown
    assert "- pilot_current_step: `3`" in markdown
    assert "- pilot_smoothed_loss: `1.3`" in markdown
    assert "- pilot_mlflow_run_id: `mlflow-run-id`" in markdown
