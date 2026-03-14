"""Integration tests for train_with_args stop, heartbeat, and loss-guard behaviour.

Purpose:
    Validate that the train_with_args entry point produces a final durable
    checkpoint on stop request, follows the configured heartbeat cadence, and
    fails closed when persistent non-finite loss is detected.

Relationships:
    - Exercises `train_with_args` in
      `scripts/devops/qwen_finetuning_patches/sft_12hz.py`.
    - Uses fakes and factory helpers from `test_support`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import TrainingProgressHeartbeat
from tests.sir_convert_a_lot.ml.qwen.training.test_support import (
    NonFiniteLossError,
    _FakeAccelerator,
    _FakeDataset,
    _FakeNaNQwenModel,
    _FakeOptimizer,
    _FakeQwenModel,
    _FakeQwenWrapper,
    base_training_args,
    fake_save_checkpoint,
    fake_training_batch,
    mark_stop_requested,
    train_with_args,
)

_TRAIN_ROW = {
    "text": "hej världen",
    "audio_codes": [[1, 2], [3, 4]],
    "ref_audio": "refs/speaker-a/ref.wav",
    "precomputed_ref_input_path": "precomputed/ref_mel/swedish_pilot_train/speaker-a/ref_mel.pt",
    "precomputed_ref_input_kind": "ref_mel",
    "precomputed_ref_input_version": "task101_ref_mel_v1",
    "precomputed_ref_input_source_audio": "refs/speaker-a/ref.wav",
    "speaker_id": "speaker-a",
}


def _write_train_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_TRAIN_ROW) + "\n", encoding="utf-8")


def _patch_setup(monkeypatch: pytest.MonkeyPatch, *, accelerator: object, model: object) -> None:
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.Accelerator",
        lambda **kwargs: accelerator,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.Qwen3TTSModel.from_pretrained",
        lambda *args, **kwargs: model,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.AutoConfig.from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.TTSDataset",
        _FakeDataset,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.AdamW",
        _FakeOptimizer,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.save_checkpoint",
        fake_save_checkpoint,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.torch.cuda.is_available",
        lambda: False,
    )


def test_train_with_args_writes_final_durable_checkpoint_on_stop_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stop request should produce one final durable checkpoint before exit."""
    train_manifest = tmp_path / "manifests" / "swedish_pilot_train.prepared.jsonl"
    _write_train_manifest(train_manifest)
    output_model_path = tmp_path / "run" / "checkpoints"
    _FakeAccelerator()
    model = _FakeQwenWrapper(processor=object(), model=_FakeQwenModel(4))

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.Accelerator",
        _FakeAccelerator,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.Qwen3TTSModel.from_pretrained",
        lambda *args, **kwargs: model,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.AutoConfig.from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.TTSDataset",
        _FakeDataset,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.DataLoader",
        lambda *args, **kwargs: [fake_training_batch()],
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.AdamW",
        _FakeOptimizer,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.save_checkpoint",
        fake_save_checkpoint,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.install_training_stop_handlers",
        lambda stop_state: mark_stop_requested(stop_state, 15),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.torch.cuda.is_available",
        lambda: False,
    )

    summary = train_with_args(
        base_training_args(output_model_path=output_model_path, train_manifest=train_manifest)
    )

    latest_checkpoint = json.loads(
        (output_model_path.parent / "latest_checkpoint.json").read_text(encoding="utf-8")
    )
    assert summary.stop_requested is True
    assert summary.stop_signal == "SIGTERM"
    assert summary.stopped_early is True
    assert summary.smoothed_loss is not None
    assert summary.latest_durable_checkpoint_step == 1
    assert summary.durable_checkpoint_retention == 2
    assert summary.durable_checkpoint_min_free_bytes == 16 * 1024**3
    assert summary.gradient_accumulation_steps == 4
    assert summary.train_iterations_completed == 1
    assert summary.dataloader_tuning["num_workers"] == 4
    assert summary.dataloader_tuning["pin_memory"] is True
    assert summary.dataloader_tuning["persistent_workers"] is True
    assert summary.dataloader_tuning["prefetch_factor"] == 4
    assert summary.dataloader_tuning["non_blocking_transfer"] is True
    assert summary.heartbeat_policy == {"interval_optimizer_steps": 20}
    assert summary.finite_loss_guard["triggered"] is False
    assert summary.acceptance_measurement_valid is True
    assert summary.ref_mel_cache["enabled"] is True
    assert summary.ref_mel_cache["max_items"] == 2048
    assert summary.durable_checkpoint_paths == [summary.latest_durable_checkpoint_path]
    assert summary.tracking is not None
    assert summary.tracking.project_name == "task101-qwen-pilot"
    assert summary.tracking.run_name == output_model_path.parent.name
    assert summary.tracking.mlflow_run_id == "fake-mlflow-run-id"
    assert latest_checkpoint["reason"] == "signal-stop"


def test_train_with_args_only_logs_on_configured_heartbeat_interval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Train-phase tracker/status emission should follow optimizer-step cadence."""
    train_manifest = tmp_path / "manifests" / "swedish_pilot_train.prepared.jsonl"
    _write_train_manifest(train_manifest)
    output_model_path = tmp_path / "run" / "checkpoints"
    accelerator = _FakeAccelerator(
        gradient_accumulation_steps=4,
        respect_gradient_accumulation=True,
    )
    heartbeats: list[TrainingProgressHeartbeat] = []

    _patch_setup(
        monkeypatch,
        accelerator=accelerator,
        model=_FakeQwenWrapper(processor=object(), model=_FakeQwenModel(4)),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.DataLoader",
        lambda *args, **kwargs: [
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
        ],
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.install_training_stop_handlers",
        lambda stop_state: None,
    )

    args = base_training_args(
        output_model_path=output_model_path,
        train_manifest=train_manifest,
        max_steps=3,
        heartbeat_interval_optimizer_steps=2,
    )
    args.checkpoint_interval_steps = 2

    summary = train_with_args(args, progress_callback=heartbeats.append)

    phases = [phase.phase for phase in heartbeats]
    assert phases[:5] == ["startup", "train", "train", "checkpoint-save", "train"]
    assert phases.count("checkpoint-save") >= 3
    assert heartbeats[1].current_optimizer_step == 1
    assert heartbeats[2].current_optimizer_step == 2
    assert heartbeats[2].current_train_iteration == 8
    assert summary.throughput_profile["profile_label"] == "hemma-throughput-aggressive-v1"
    assert summary.throughput_profile["max_batch_size"] == 8
    assert summary.throughput_profile["minimum_required_max_batch_size"] == 8
    assert summary.batch_occupancy["total_batches"] == 1
    assert summary.batch_occupancy["realized_max_batch_size"] == 1
    assert summary.data_path_attribution is None
    assert accelerator.logged_metrics == [
        (
            {
                "train/loss": summary.last_loss,
                "train/loss_ema": summary.smoothed_loss,
                "train/current_step": 2,
                "train/current_optimizer_step": 2,
                "train/current_train_iteration": 8,
                "train/current_epoch": 0,
                "train/checkpoint_interval_steps": 2,
                "train/ref_mel_cache_enabled": True,
                "train/ref_mel_cache_max_items": 2048,
                "train/ref_mel_cache_hits": 0,
                "train/ref_mel_cache_misses": 0,
                "train/ref_mel_cache_size": 0,
                "train/ref_mel_cache_hit_rate": None,
            },
            2,
        )
    ]
    assert summary.optimizer_steps_completed == 3
    assert summary.heartbeat_policy == {"interval_optimizer_steps": 2}
    assert accelerator.sync_gradients_history[:8] == [
        False,
        False,
        False,
        True,
        False,
        False,
        False,
        True,
    ]
    assert accelerator.prepared_optimizer is not None
    assert accelerator.prepared_optimizer.effective_step_calls == 3
    assert accelerator.prepared_optimizer.raw_step_attempts == 12


def test_train_with_args_fails_after_configured_non_finite_loss_streak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persistent non-finite loss should fail closed before acceptance evidence is used."""
    train_manifest = tmp_path / "manifests" / "swedish_pilot_train.prepared.jsonl"
    _write_train_manifest(train_manifest)
    output_model_path = tmp_path / "run" / "checkpoints"
    accelerator = _FakeAccelerator(
        gradient_accumulation_steps=4,
        respect_gradient_accumulation=True,
    )

    _patch_setup(
        monkeypatch,
        accelerator=accelerator,
        model=_FakeQwenWrapper(processor=object(), model=_FakeNaNQwenModel(4)),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_setup.DataLoader",
        lambda *args, **kwargs: [
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
            fake_training_batch(),
        ],
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_loop.install_training_stop_handlers",
        lambda stop_state: None,
    )
    heartbeats: list[TrainingProgressHeartbeat] = []

    with pytest.raises(NonFiniteLossError, match="Non-finite loss guard triggered"):
        train_with_args(
            base_training_args(
                output_model_path=output_model_path,
                train_manifest=train_manifest,
                finite_loss_max_consecutive_steps=2,
            ),
            progress_callback=heartbeats.append,
        )

    assert [phase.phase for phase in heartbeats] == ["startup", "train"]
    assert heartbeats[-1].latest_loss is not None
    assert math.isnan(heartbeats[-1].latest_loss)
    assert accelerator.logged_metrics == []
    assert heartbeats[-1].current_optimizer_step == 1
    assert heartbeats[-1].current_train_iteration == 4
    assert accelerator.prepared_optimizer is not None
    assert accelerator.prepared_optimizer.effective_step_calls == 2
    assert accelerator.prepared_optimizer.raw_step_attempts == 8
