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
import sys
from pathlib import Path
from types import ModuleType

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.reporting import StatusReporterConfig


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

    def write_startup(self) -> None:
        """Record startup without side effects."""

    def tracking_ready(self, tracking: object) -> None:
        """Accept tracker-ready callbacks without side effects."""

    def heartbeat(self, heartbeat: object) -> None:
        """Accept heartbeat callbacks without side effects."""

    def write_completed(self, training_summary: object) -> None:
        """Accept completion writes without side effects."""

    def write_failed(self, exc: Exception) -> None:
        """Accept failure writes without side effects."""


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
            checkpoint_interval_steps=100,
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
            dataloader_persistent_workers=True,
            dataloader_prefetch_factor=4,
            non_blocking_transfer=True,
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
