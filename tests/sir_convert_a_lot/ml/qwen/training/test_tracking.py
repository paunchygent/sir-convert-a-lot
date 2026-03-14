"""Focused tests for canonical Qwen training tracking helpers."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.reporting import merge_launch_tracking_metadata

TRACKING = importlib.import_module("scripts.devops.qwen_finetuning_patches.sft_12hz_tracking")

TrainingTrackerConfig = TRACKING.TrainingTrackerConfig
build_training_tracker_config = TRACKING.build_training_tracker_config
refresh_training_tracker_summary = TRACKING.refresh_training_tracker_summary


@dataclass
class FakeMlflowRunInfo:
    """Minimal MLflow run-info payload for tracking-summary tests."""

    run_id: str
    experiment_id: str
    artifact_uri: str


@dataclass
class FakeMlflowRun:
    """Minimal unwrap-able MLflow tracker object."""

    info: FakeMlflowRunInfo


class FakeAccelerator:
    """Provide the tracker lookup surface used by the summary helper."""

    def __init__(self, tracker: FakeMlflowRun) -> None:
        self.is_main_process = True
        self._tracker = tracker

    def get_tracker(self, name: str, unwrap: bool = False) -> FakeMlflowRun:
        """Return the fake MLflow tracker for the requested name."""
        del unwrap
        if name != "mlflow":
            raise AssertionError(f"Unexpected tracker lookup: {name}")
        return self._tracker


def test_build_training_tracker_config_defaults_to_run_scoped_paths(tmp_path: Path) -> None:
    """Tracker defaults should stay scoped under the launch-specific run root."""
    output_model_path = tmp_path / "qwen-20260313t120000z" / "checkpoints"

    config = build_training_tracker_config(
        output_model_path=output_model_path,
        tracker_run_name=None,
        tracker_project_name=None,
        mlflow_experiment_name=None,
        mlflow_tracking_uri=None,
        mlflow_artifact_root=None,
        tensorboard_logging_dir=None,
    )

    assert config.project_name == "task101-qwen-pilot"
    assert config.run_name == "qwen-20260313t120000z"
    assert config.mlflow_experiment_name == "task101-qwen-pilot"
    assert config.mlflow_tracking_uri.endswith("/trackers/mlflow/mlflow.db")
    assert config.mlflow_artifact_root.endswith("/trackers/mlflow/artifacts")
    assert config.tensorboard_logging_dir.endswith("/trackers/tensorboard")


def test_refresh_training_tracker_summary_uses_project_named_tensorboard_run_dir(
    tmp_path: Path,
) -> None:
    """Tracker summaries should mirror the TensorBoard directory shape Accelerate uses."""
    logging_dir = tmp_path / "trackers" / "tensorboard"
    mlflow_db_path = tmp_path / "trackers" / "mlflow" / "mlflow.db"
    run_dir = logging_dir / "task101-qwen-pilot"
    run_dir.mkdir(parents=True, exist_ok=True)
    event_file = run_dir / "events.out.tfevents.123"
    event_file.write_text("", encoding="utf-8")
    tracker = FakeMlflowRun(
        info=FakeMlflowRunInfo(
            run_id="mlflow-run-id",
            experiment_id="mlflow-experiment-id",
            artifact_uri=(tmp_path / "trackers" / "mlflow" / "artifacts").as_posix(),
        )
    )

    summary = refresh_training_tracker_summary(
        FakeAccelerator(tracker),
        tracker_config=TrainingTrackerConfig(
            project_name="task101-qwen-pilot",
            run_name="qwen-20260313t120000z",
            tracker_backends=("mlflow", "tensorboard"),
            mlflow_experiment_name="task101-qwen-pilot",
            mlflow_tracking_uri=f"sqlite:///{mlflow_db_path.as_posix()}",
            mlflow_artifact_root=(tmp_path / "trackers" / "mlflow" / "artifacts").as_posix(),
            mlflow_system_metrics_interval_seconds=10,
            tensorboard_logging_dir=logging_dir.as_posix(),
        ),
        system_metrics_enabled=True,
    )

    assert summary.project_name == "task101-qwen-pilot"
    assert summary.run_name == "qwen-20260313t120000z"
    assert summary.mlflow_run_id == "mlflow-run-id"
    assert summary.tensorboard_run_dir == run_dir.as_posix()
    assert summary.tensorboard_event_files == [event_file.as_posix()]


def test_merge_launch_tracking_metadata_updates_existing_launch_artifact(tmp_path: Path) -> None:
    """The reporter should merge live tracker metadata back into launch.json."""
    launch_metadata_path = tmp_path / "launch.json"
    launch_metadata_path.write_text(
        json.dumps(
            {
                "launch_id": "qwen-20260313t120000z",
                "tracking": {
                    "project_name": "qwen-training",
                    "run_name": "planned-run-name",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    merge_launch_tracking_metadata(
        launch_metadata_path,
        tracking={
            "project_name": "qwen-training",
            "run_name": "qwen-20260313t120000z",
            "mlflow_run_id": "mlflow-run-id",
        },
    )

    payload = json.loads(launch_metadata_path.read_text(encoding="utf-8"))
    assert payload["tracking"] == {
        "project_name": "qwen-training",
        "run_name": "qwen-20260313t120000z",
        "mlflow_run_id": "mlflow-run-id",
    }
