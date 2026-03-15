"""Tests for the in-container Qwen trainer entrypoint.

Purpose:
    Verify that the canonical trainer entrypoint handles legacy bundles
    gracefully while still building the expected reporting configuration.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.ml.qwen.training.trainer`.
    - Complements detached-launch coverage in `test_orchestrator.py`.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.reporting import StatusReporterConfig
from tests.sir_convert_a_lot.ml.qwen.training.test_support import NonFiniteLossError


class _FakeSft12HzModule(ModuleType):
    """Provide the minimal top-level trainer dependency needed for import."""

    def train_with_args(self, *args: object, **kwargs: object) -> None:
        """Accept train entry calls without running the real training loop."""


_fake_sft_12hz = _FakeSft12HzModule("sft_12hz")
sys.modules.setdefault("sft_12hz", _fake_sft_12hz)
trainer = importlib.import_module("scripts.sir_convert_a_lot.ml.qwen.training.trainer")


class _FakeStatusReporter:
    """Capture trainer reporting configuration without touching the real runtime."""

    def __init__(self, config: StatusReporterConfig) -> None:
        self.config = config
        self.tracking: dict[str, object] | None = None

    def write_startup(self) -> None:
        """Record startup without side effects."""

    def tracking_ready(self, tracking: object) -> None:
        """Accept tracker-ready callbacks without side effects."""
        if isinstance(tracking, dict):
            self.tracking = tracking

    def heartbeat(self, heartbeat: object) -> None:
        """Accept heartbeat callbacks without side effects."""

    def write_completed(self, training_summary: object) -> None:
        """Accept completion writes without side effects."""

    def write_failed(self, exc: BaseException) -> dict[str, object]:
        """Return one minimal failed-status payload for trainer tests."""
        return {
            "status": "failed",
            "current_phase": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


@dataclass(frozen=True)
class _FakeTrainingReport:
    """Minimal dataclass report so trainer tests can exercise `asdict()`."""

    status: str


def test_main_accepts_legacy_bundle_without_training_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trainer startup should tolerate legacy bundles that lack a bundle report."""
    train_jsonl = tmp_path / "manifests/train.jsonl"
    eval_jsonl = tmp_path / "manifests/eval.jsonl"
    output_dir = tmp_path / "run"
    bundle_root = tmp_path / "bundle"
    train_jsonl.parent.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)
    train_jsonl.write_text("{}\n", encoding="utf-8")
    eval_jsonl.write_text("{}\n", encoding="utf-8")

    captured: dict[str, _FakeStatusReporter] = {}

    def fake_status_reporter(config: StatusReporterConfig) -> _FakeStatusReporter:
        reporter = _FakeStatusReporter(config)
        captured["reporter"] = reporter
        return reporter

    monkeypatch.setattr(
        trainer,
        "_parse_args",
        lambda: argparse.Namespace(
            launch_id="legacy-launch",
            launch_metadata_path=None,
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_jsonl=train_jsonl,
            eval_jsonl=eval_jsonl,
            pilot_bundle_root=bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            output_dir=output_dir,
            tracker_project_name="qwen-training",
            mlflow_experiment_name="qwen-training",
            mlflow_tracking_uri=None,
            mlflow_artifact_root=None,
            tensorboard_logging_dir=None,
            tracker_run_name=None,
            batch_size=8,
            throughput_profile_label="hemma-throughput-aggressive-v1",
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
            dataloader_persistent_workers=True,
            dataloader_prefetch_factor=4,
            non_blocking_transfer=True,
            data_path_proof_mode=False,
            heartbeat_interval_optimizer_steps=20,
            finite_loss_max_consecutive_steps=3,
            ref_mel_cache_enabled=True,
            ref_mel_cache_max_items=2048,
            torch_profiler_enabled=False,
            torch_profiler_wait_steps=1,
            torch_profiler_warmup_steps=1,
            torch_profiler_active_steps=4,
            torch_profiler_repeat=1,
            torch_profiler_record_shapes=True,
            torch_profiler_profile_memory=True,
            torch_profiler_with_stack=False,
            torch_profiler_trace_dir=None,
            resume_from_checkpoint=None,
        ),
    )
    monkeypatch.setattr(trainer, "StatusReporter", fake_status_reporter)
    monkeypatch.setattr(trainer.torch.cuda, "is_available", lambda: False)

    with pytest.raises(SystemExit, match="Trainer expected GPU-visible torch"):
        trainer.main()

    reporter = captured["reporter"]
    assert reporter.config.bundle_precomputed_reference_input is None


def test_main_forwards_eval_jsonl_into_inner_training_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trainer should pass the held-out eval manifest into the inner patched trainer."""
    train_jsonl = tmp_path / "manifests/train.jsonl"
    eval_jsonl = tmp_path / "manifests/eval.jsonl"
    output_dir = tmp_path / "run"
    train_jsonl.parent.mkdir(parents=True, exist_ok=True)
    train_jsonl.write_text("{}\n", encoding="utf-8")
    eval_jsonl.write_text("{}\n", encoding="utf-8")
    captured_training_args: dict[str, argparse.Namespace] = {}

    monkeypatch.setattr(
        trainer,
        "_parse_args",
        lambda: argparse.Namespace(
            launch_id="eval-launch",
            launch_metadata_path=None,
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_jsonl=train_jsonl,
            eval_jsonl=eval_jsonl,
            pilot_bundle_root=None,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            output_dir=output_dir,
            tracker_project_name="qwen-training",
            mlflow_experiment_name="qwen-training",
            mlflow_tracking_uri=None,
            mlflow_artifact_root=None,
            tensorboard_logging_dir=None,
            tracker_run_name=None,
            batch_size=8,
            throughput_profile_label="hemma-throughput-aggressive-v1",
            lr=2e-5,
            num_epochs=1,
            max_steps=1,
            checkpoint_interval_steps=500,
            eval_interval_steps=50,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
            dataloader_persistent_workers=True,
            dataloader_prefetch_factor=4,
            non_blocking_transfer=True,
            data_path_proof_mode=False,
            heartbeat_interval_optimizer_steps=20,
            finite_loss_max_consecutive_steps=3,
            ref_mel_cache_enabled=True,
            ref_mel_cache_max_items=2048,
            torch_profiler_enabled=False,
            torch_profiler_wait_steps=1,
            torch_profiler_warmup_steps=1,
            torch_profiler_active_steps=4,
            torch_profiler_repeat=1,
            torch_profiler_record_shapes=True,
            torch_profiler_profile_memory=True,
            torch_profiler_with_stack=False,
            torch_profiler_trace_dir=None,
            resume_from_checkpoint=None,
        ),
    )
    monkeypatch.setattr(trainer.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(trainer.torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(trainer.torch.version, "hip", "6.4.0")
    monkeypatch.setattr(trainer, "StatusReporter", _FakeStatusReporter)

    def fake_train_with_args(
        training_args: argparse.Namespace,
        *,
        progress_callback: object,
        tracker_ready_callback: object,
    ) -> object:
        captured_training_args["value"] = training_args
        return argparse.Namespace(
            tracking=None,
            latest_eval_loss=0.8,
            best_eval_loss=0.8,
            best_eval_step=1,
            eval_runs_completed=1,
        )

    monkeypatch.setattr(trainer.sft_12hz, "train_with_args", fake_train_with_args)
    monkeypatch.setattr(
        trainer,
        "build_training_report",
        lambda **kwargs: _FakeTrainingReport(status="completed"),
    )
    monkeypatch.setattr(
        trainer,
        "write_json",
        lambda path, payload: path.parent.mkdir(parents=True, exist_ok=True),
    )

    assert trainer.main() == 0
    assert captured_training_args["value"].eval_jsonl == eval_jsonl.as_posix()


def test_main_writes_failed_report_artifacts_for_non_finite_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trainer failures should persist `failure.txt`, `status.json`, and `report.json`."""
    train_jsonl = tmp_path / "manifests/train.jsonl"
    eval_jsonl = tmp_path / "manifests/eval.jsonl"
    output_dir = tmp_path / "run"
    train_jsonl.parent.mkdir(parents=True, exist_ok=True)
    train_jsonl.write_text("{}\n", encoding="utf-8")
    eval_jsonl.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        trainer,
        "_parse_args",
        lambda: argparse.Namespace(
            launch_id="failed-launch",
            launch_metadata_path=None,
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_jsonl=train_jsonl,
            eval_jsonl=eval_jsonl,
            pilot_bundle_root=None,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            output_dir=output_dir,
            tracker_project_name="qwen-training",
            mlflow_experiment_name="qwen-training",
            mlflow_tracking_uri=None,
            mlflow_artifact_root=None,
            tensorboard_logging_dir=None,
            tracker_run_name=None,
            batch_size=8,
            throughput_profile_label="hemma-throughput-aggressive-v1",
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
            dataloader_persistent_workers=True,
            dataloader_prefetch_factor=4,
            non_blocking_transfer=True,
            data_path_proof_mode=False,
            heartbeat_interval_optimizer_steps=20,
            finite_loss_max_consecutive_steps=3,
            ref_mel_cache_enabled=True,
            ref_mel_cache_max_items=2048,
            torch_profiler_enabled=False,
            torch_profiler_wait_steps=1,
            torch_profiler_warmup_steps=1,
            torch_profiler_active_steps=4,
            torch_profiler_repeat=1,
            torch_profiler_record_shapes=True,
            torch_profiler_profile_memory=True,
            torch_profiler_with_stack=False,
            torch_profiler_trace_dir=None,
            resume_from_checkpoint=None,
        ),
    )
    monkeypatch.setattr(trainer.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(trainer.torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(trainer.torch.version, "hip", "6.4.0")
    monkeypatch.setattr(
        trainer.sft_12hz,
        "train_with_args",
        lambda *args, **kwargs: (_ for _ in ()).throw(
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
        ),
    )

    with pytest.raises(NonFiniteLossError):
        trainer.main()

    status_payload = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
    report_payload = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    failure_text = (output_dir / "failure.txt").read_text(encoding="utf-8")

    assert "NonFiniteLossError" in failure_text
    assert status_payload["current_optimizer_step"] == 17
    assert status_payload["finite_loss_guard"]["optimizer_step"] == 17
    assert report_payload["status"] == "failed"
    assert report_payload["training_summary"] is None
    assert report_payload["failure"]["current_optimizer_step"] == 17
    assert report_payload["failure"]["current_train_iteration"] == 68
    assert report_payload["failure"]["step_semantics"]["epoch_index_base"] == 0
    assert report_payload["failure"]["finite_loss_guard"]["optimizer_step"] == 17
    assert report_payload["failure"]["finite_loss_guard"]["sub_talker_loss_value"] == 0.1


def test_main_writes_failure_artifacts_for_startup_system_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup `SystemExit` failures should still produce canonical failure artifacts."""
    train_jsonl = tmp_path / "manifests/train.jsonl"
    eval_jsonl = tmp_path / "manifests/eval.jsonl"
    output_dir = tmp_path / "run"
    train_jsonl.parent.mkdir(parents=True, exist_ok=True)
    train_jsonl.write_text("{}\n", encoding="utf-8")
    eval_jsonl.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        trainer,
        "_parse_args",
        lambda: argparse.Namespace(
            launch_id="startup-failure-launch",
            launch_metadata_path=None,
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_jsonl=train_jsonl,
            eval_jsonl=eval_jsonl,
            pilot_bundle_root=None,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            output_dir=output_dir,
            tracker_project_name="qwen-training",
            mlflow_experiment_name="qwen-training",
            mlflow_tracking_uri=None,
            mlflow_artifact_root=None,
            tensorboard_logging_dir=None,
            tracker_run_name=None,
            batch_size=8,
            throughput_profile_label="hemma-throughput-aggressive-v1",
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
            dataloader_persistent_workers=True,
            dataloader_prefetch_factor=4,
            non_blocking_transfer=True,
            data_path_proof_mode=False,
            heartbeat_interval_optimizer_steps=20,
            finite_loss_max_consecutive_steps=3,
            ref_mel_cache_enabled=True,
            ref_mel_cache_max_items=2048,
            torch_profiler_enabled=False,
            torch_profiler_wait_steps=1,
            torch_profiler_warmup_steps=1,
            torch_profiler_active_steps=4,
            torch_profiler_repeat=1,
            torch_profiler_record_shapes=True,
            torch_profiler_profile_memory=True,
            torch_profiler_with_stack=False,
            torch_profiler_trace_dir=None,
            resume_from_checkpoint=None,
        ),
    )
    monkeypatch.setattr(trainer.torch.cuda, "is_available", lambda: False)

    with pytest.raises(SystemExit, match="Trainer expected GPU-visible torch"):
        trainer.main()

    status_payload = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
    report_payload = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    failure_text = (output_dir / "failure.txt").read_text(encoding="utf-8")

    assert "Trainer expected GPU-visible torch" in failure_text
    assert status_payload["status"] == "failed"
    assert report_payload["status"] == "failed"
    assert report_payload["failure"]["error"] == (
        "SystemExit: Trainer expected GPU-visible torch inside the container."
    )
