"""Unit tests for Qwen trainer-state checkpoint helpers.

Purpose:
    Validate the durable checkpoint metadata and latest-checkpoint pointer
    contract introduced for `T115` without requiring a real GPU training run.

Relationships:
    - Exercises helper functions in `scripts/devops/qwen_finetuning_patches/sft_12hz.py`.
    - Complements the detached Task 101 runner tests by focusing on the inner
      trainer-state persistence semantics.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import torch
import torch.nn.functional as F

SFT_PATCH_ROOT = Path(__file__).resolve().parents[2] / "scripts/devops/qwen_finetuning_patches"
if SFT_PATCH_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SFT_PATCH_ROOT.as_posix())

SFT_12HZ = importlib.import_module("scripts.devops.qwen_finetuning_patches.sft_12hz")
_checkpoint_resume_cursor = SFT_12HZ._checkpoint_resume_cursor
_checkpoint_advanced_since_latest_save = SFT_12HZ._checkpoint_advanced_since_latest_save
_current_durable_checkpoint_paths = SFT_12HZ._current_durable_checkpoint_paths
_durable_checkpoint_staging_dir = SFT_12HZ._durable_checkpoint_staging_dir
DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES = SFT_12HZ.DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES
_load_durable_checkpoint_metadata = SFT_12HZ._load_durable_checkpoint_metadata
_save_durable_checkpoint = SFT_12HZ._save_durable_checkpoint
train_with_args = SFT_12HZ.train_with_args
TrainingStopState = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).TrainingStopState
mark_stop_requested = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).mark_stop_requested
install_training_stop_handlers = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).install_training_stop_handlers


@dataclass
class _FakeMlflowRunInfo:
    """Minimal MLflow run-info payload for tracker-summary unit tests."""

    run_id: str
    experiment_id: str
    artifact_uri: str


@dataclass
class _FakeMlflowRun:
    """Minimal unwrap-able MLflow tracker object."""

    info: _FakeMlflowRunInfo


class _FakeAccelerator:
    """Minimal accelerator stub for durable checkpoint helper tests."""

    def __init__(
        self,
        *,
        gradient_accumulation_steps: int = 1,
        mixed_precision: str = "bf16",
        log_with: str | list[str] = "tensorboard",
        project_dir: str = "",
    ) -> None:
        del gradient_accumulation_steps, mixed_precision, log_with
        self.is_main_process = True
        self.saved_paths: list[str] = []
        self.wait_count = 0
        self.logged_metrics: list[tuple[dict[str, float | int], int]] = []
        self.trackers_initialized = False
        self.training_ended = False
        artifact_root = Path(project_dir) / "mlflow-artifacts"
        self._tracker = _FakeMlflowRun(
            info=_FakeMlflowRunInfo(
                run_id="fake-mlflow-run-id",
                experiment_id="fake-mlflow-experiment-id",
                artifact_uri=artifact_root.as_posix(),
            )
        )

    def wait_for_everyone(self) -> None:
        """Record one barrier call."""
        self.wait_count += 1

    def save_state(self, output_dir: str | None = None, safe_serialization: bool = True) -> None:
        """Materialize a fake trainer-state marker file."""
        del safe_serialization
        if output_dir is None:
            raise AssertionError("Expected a checkpoint output directory.")
        self.saved_paths.append(output_dir)
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / "accelerate_state_marker.txt").write_text("saved\n", encoding="utf-8")

    def prepare(self, *args: object) -> tuple[object, ...]:
        """Return prepared training objects unchanged."""
        return args

    def accumulate(self, _model: object) -> "_FakeAccelerator":
        """Provide one no-op context manager for accumulate semantics."""
        return self

    def __enter__(self) -> "_FakeAccelerator":
        """Enter the no-op accumulate context."""
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Exit the no-op accumulate context."""
        del exc_type, exc, tb

    @property
    def sync_gradients(self) -> bool:
        """Mirror the training loop expectation that gradients are synchronized."""
        return True

    def backward(self, loss: torch.Tensor) -> None:
        """Backpropagate through the fake training graph."""
        loss.backward()

    def clip_grad_norm_(self, parameters: object, _max_norm: float) -> None:
        """Accept gradient clipping requests without altering the test graph."""
        del parameters

    def unwrap_model(self, model: object) -> object:
        """Return the wrapped model unchanged."""
        return model

    def print(self, *args: object, **kwargs: object) -> None:
        """Suppress accelerator prints during unit tests."""
        del args, kwargs

    def load_state(self, input_dir: str) -> None:
        """Accept resume calls without reading real trainer state."""
        del input_dir

    def skip_first_batches(
        self,
        dataloader: list[dict[str, torch.Tensor]],
        skip: int,
    ) -> list[dict[str, torch.Tensor]]:
        """Return the remaining batches after one deterministic skip count."""
        return dataloader[skip:]

    def init_trackers(
        self,
        _project_name: str,
        config: dict[str, object] | None = None,
        init_kwargs: dict[str, dict[str, object]] | None = None,
    ) -> None:
        """Accept tracker initialization without hitting real backends."""
        del config, init_kwargs
        self.trackers_initialized = True

    def get_tracker(self, name: str, unwrap: bool = False) -> _FakeMlflowRun:
        """Return the fake MLflow tracker expected by the summary helper."""
        del unwrap
        if name != "mlflow":
            raise AssertionError(f"Unexpected tracker lookup: {name}")
        return self._tracker

    def end_training(self) -> None:
        """Record that tracker shutdown happened."""
        self.training_ended = True

    def log(self, values: dict[str, float | int], *, step: int) -> None:
        """Record one flat tracking payload."""
        self.logged_metrics.append((values, step))


class _FakeOptimizer:
    """Minimal optimizer stub used by the train-loop stop test."""

    def __init__(self, _parameters: object, *, lr: float, weight_decay: float) -> None:
        del _parameters, lr, weight_decay

    def step(self) -> None:
        """Accept one optimizer step without mutating real parameters."""

    def zero_grad(self) -> None:
        """Accept zero-grad requests from the training loop."""


class _FakeEmbedding(torch.nn.Module):
    """Simple embedding-like layer for deterministic fake Qwen components."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.embedding = torch.nn.Embedding(64, embedding_dim)

    def forward(self, indices: torch.Tensor) -> torch.Tensor:
        """Return embeddings for one integer tensor."""
        return F.embedding(indices, self.embedding.weight)


class _FakeCodePredictor:
    """Expose the list-of-embeddings contract used by the patched trainer."""

    def __init__(self, embedding_dim: int) -> None:
        self._embeddings = [_FakeEmbedding(embedding_dim) for _ in range(15)]

    def get_input_embeddings(self) -> list[_FakeEmbedding]:
        """Return codec input embeddings for sub-codec conditioning."""
        return self._embeddings


class _FakeTalkerModel(torch.nn.Module):
    """Minimal talker model exposing text and codec embeddings."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.text_embedding = _FakeEmbedding(embedding_dim)
        self.codec_embedding = _FakeEmbedding(embedding_dim)
        self.text_projection = torch.nn.Linear(embedding_dim, embedding_dim)


@dataclass
class _FakeTalkerOutputs:
    """Training output structure matching the patched Qwen loop expectations."""

    loss: torch.Tensor
    hidden_states: list[list[torch.Tensor]]


class _FakeTalker(torch.nn.Module):
    """Minimal talker wrapper implementing the two trainer call surfaces."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.model = _FakeTalkerModel(embedding_dim)
        self.code_predictor = _FakeCodePredictor(embedding_dim)

    def forward(
        self,
        *,
        inputs_embeds: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
        output_hidden_states: bool,
    ) -> _FakeTalkerOutputs:
        """Return one lightweight differentiable loss and hidden-state payload."""
        del attention_mask, labels, output_hidden_states
        return _FakeTalkerOutputs(
            loss=inputs_embeds.mean(),
            hidden_states=[[inputs_embeds]],
        )

    def forward_sub_talker_finetune(
        self,
        talker_codec_ids: torch.Tensor,
        talker_hidden_states: torch.Tensor,
    ) -> tuple[None, torch.Tensor]:
        """Return one small differentiable auxiliary loss."""
        del talker_codec_ids
        return None, talker_hidden_states.mean() * 0.0 + torch.tensor(
            0.1,
            dtype=talker_hidden_states.dtype,
            device=talker_hidden_states.device,
        )


class _FakeQwenModel(torch.nn.Module):
    """Minimal multi-speaker model satisfying the patched trainer contract."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.device = torch.device("cpu")
        self.dtype = torch.float32
        self.talker = _FakeTalker(embedding_dim)
        self._speaker_projection = torch.nn.Linear(embedding_dim, embedding_dim)

    def speaker_encoder(self, ref_mels: torch.Tensor) -> torch.Tensor:
        """Project one fake reference mel tensor into speaker embeddings."""
        pooled = ref_mels.mean(dim=1)
        return F.linear(
            pooled,
            self._speaker_projection.weight,
            self._speaker_projection.bias,
        )


@dataclass
class _FakeQwenWrapper:
    """Wrapper matching the upstream Qwen object shape used by the trainer."""

    processor: object
    model: _FakeQwenModel


class _FakeDataset:
    """Minimal dataset shell for DataLoader construction in tests."""

    def __init__(
        self,
        rows: list[object],
        _processor: object,
        _config: object,
        ref_mel_cache: object | None = None,
    ) -> None:
        del ref_mel_cache
        self.rows = rows
        self.collate_fn = lambda batch: batch

    def __len__(self) -> int:
        """Return the deterministic fake row count."""
        return len(self.rows)


def _fake_save_checkpoint(**kwargs: object) -> str:
    """Persist one lightweight fake checkpoint directory for the stop test."""
    output_dir = Path(str(kwargs["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.as_posix()


def _fake_training_batch() -> dict[str, torch.Tensor]:
    """Return one minimal batch compatible with the patched Qwen loop."""
    embedding_dim = 4
    sequence_length = 8
    input_ids = torch.zeros((1, sequence_length, 2), dtype=torch.long)
    codec_ids = torch.zeros((1, sequence_length, 16), dtype=torch.long)
    ref_mels = torch.ones((1, 2, embedding_dim), dtype=torch.float32)
    text_embedding_mask = torch.ones((1, sequence_length, embedding_dim), dtype=torch.float32)
    codec_embedding_mask = torch.ones((1, sequence_length, embedding_dim), dtype=torch.float32)
    attention_mask = torch.ones((1, sequence_length), dtype=torch.long)
    codec_0_labels = torch.zeros((1, sequence_length), dtype=torch.long)
    codec_mask = torch.ones((1, sequence_length), dtype=torch.bool)
    return {
        "input_ids": input_ids,
        "codec_ids": codec_ids,
        "ref_mels": ref_mels,
        "text_embedding_mask": text_embedding_mask,
        "codec_embedding_mask": codec_embedding_mask,
        "attention_mask": attention_mask,
        "codec_0_labels": codec_0_labels,
        "codec_mask": codec_mask,
    }


def test_checkpoint_resume_cursor_rolls_to_next_epoch_at_epoch_boundary() -> None:
    """A completed last batch should advance the resume cursor to the next epoch."""
    next_epoch, next_step = _checkpoint_resume_cursor(
        epoch=2,
        step_in_epoch=4,
        dataloader_length=5,
    )

    assert next_epoch == 3
    assert next_step == 0


def test_save_durable_checkpoint_writes_metadata_and_latest_pointer(tmp_path: Path) -> None:
    """Saving one durable checkpoint should persist metadata plus latest pointer."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"

    metadata = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=8,
        epoch=0,
        step_in_epoch=7,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    checkpoint_dir = output_model_path / "state-step-00000008"
    assert metadata.checkpoint_path == checkpoint_dir.as_posix()
    assert checkpoint_dir.exists() is True
    assert (checkpoint_dir / "accelerate_state_marker.txt").exists() is True
    saved_metadata = json.loads(
        (checkpoint_dir / "training_state.json").read_text(encoding="utf-8")
    )
    latest_pointer = json.loads(
        (output_model_path.parent / "latest_checkpoint.json").read_text(encoding="utf-8")
    )
    assert saved_metadata["optimizer_steps_completed"] == 8
    assert saved_metadata["next_epoch"] == 0
    assert saved_metadata["next_step_in_epoch"] == 8
    assert latest_pointer["checkpoint_path"] == checkpoint_dir.as_posix()
    assert accelerator.saved_paths == [
        _durable_checkpoint_staging_dir(output_model_path, 8).as_posix()
    ]


def test_save_durable_checkpoint_prunes_older_paths_after_validation(tmp_path: Path) -> None:
    """Retention should keep the newest durable checkpoints only after a valid new save."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"
    epoch_checkpoint = output_model_path / "checkpoint-epoch-0"
    final_checkpoint = output_model_path / "checkpoint-final"
    epoch_checkpoint.mkdir(parents=True, exist_ok=True)
    final_checkpoint.mkdir(parents=True, exist_ok=True)
    first_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=2,
        epoch=0,
        step_in_epoch=1,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    second_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    latest_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=6,
        epoch=0,
        step_in_epoch=5,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    retained_paths = _current_durable_checkpoint_paths(output_model_path)
    latest_pointer = json.loads(
        (output_model_path.parent / "latest_checkpoint.json").read_text(encoding="utf-8")
    )
    assert first_checkpoint.checkpoint_path not in retained_paths
    assert retained_paths == [
        second_checkpoint.checkpoint_path,
        latest_checkpoint.checkpoint_path,
    ]
    assert latest_pointer["checkpoint_path"] == latest_checkpoint.checkpoint_path
    assert epoch_checkpoint.exists() is True
    assert final_checkpoint.exists() is True


def test_save_durable_checkpoint_maintains_pointer_and_retained_paths_when_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed validation must not flip the latest pointer or prune older checkpoints."""
    accelerator = _FakeAccelerator()
    output_model_path = tmp_path / "run" / "checkpoints"
    first_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=2,
        epoch=0,
        step_in_epoch=1,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    second_checkpoint = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    latest_pointer_path = output_model_path.parent / "latest_checkpoint.json"
    before_failure_pointer = json.loads(latest_pointer_path.read_text(encoding="utf-8"))
    original_validate = SFT_12HZ._validate_saved_durable_checkpoint

    def _fail_validation(
        checkpoint_dir: Path,
        *,
        expected_metadata: object,
    ) -> None:
        if checkpoint_dir.name == ".state-step-00000006.incomplete":
            raise RuntimeError("simulated validation failure")
        original_validate(checkpoint_dir, expected_metadata=expected_metadata)

    monkeypatch.setattr(
        "sft_12hz_checkpointing._validate_saved_durable_checkpoint",
        _fail_validation,
    )

    with pytest.raises(RuntimeError, match="simulated validation failure"):
        _save_durable_checkpoint(
            accelerator=accelerator,
            output_model_path=output_model_path,
            optimizer_steps_completed=6,
            epoch=0,
            step_in_epoch=5,
            dataloader_length=10,
            reason="interval",
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        )

    assert _current_durable_checkpoint_paths(output_model_path) == [
        first_checkpoint.checkpoint_path,
        second_checkpoint.checkpoint_path,
    ]
    assert json.loads(latest_pointer_path.read_text(encoding="utf-8")) == before_failure_pointer
    assert (output_model_path / "state-step-00000006").exists() is False
    assert _durable_checkpoint_staging_dir(output_model_path, 6).exists() is False


def test_save_durable_checkpoint_cleans_partial_state_and_allows_retry(
    tmp_path: Path,
) -> None:
    """A failed save should clean staging artifacts so the same step can be retried."""
    output_model_path = tmp_path / "run" / "checkpoints"

    class _FailOnceAccelerator(_FakeAccelerator):
        """Fake accelerator that fails once after materializing a partial save."""

        def __init__(self) -> None:
            super().__init__()
            self.fail_next = True

        def save_state(
            self, output_dir: str | None = None, safe_serialization: bool = True
        ) -> None:
            super().save_state(output_dir=output_dir, safe_serialization=safe_serialization)
            if self.fail_next:
                self.fail_next = False
                raise RuntimeError("simulated save failure")

    accelerator = _FailOnceAccelerator()

    with pytest.raises(RuntimeError, match="simulated save failure"):
        _save_durable_checkpoint(
            accelerator=accelerator,
            output_model_path=output_model_path,
            optimizer_steps_completed=4,
            epoch=0,
            step_in_epoch=3,
            dataloader_length=10,
            reason="interval",
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        )

    assert (output_model_path / "state-step-00000004").exists() is False
    assert _durable_checkpoint_staging_dir(output_model_path, 4).exists() is False

    metadata = _save_durable_checkpoint(
        accelerator=accelerator,
        output_model_path=output_model_path,
        optimizer_steps_completed=4,
        epoch=0,
        step_in_epoch=3,
        dataloader_length=10,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    assert metadata.checkpoint_path == (output_model_path / "state-step-00000004").as_posix()


def test_save_durable_checkpoint_fails_closed_for_first_checkpoint_when_free_space_is_low(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first durable checkpoint save should use the conservative fallback estimate."""
    output_model_path = tmp_path / "run" / "checkpoints"
    required_free_bytes = DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES + (16 * 1024**3)

    class _FakeDiskUsage:
        """Minimal disk-usage record for the free-space guard test."""

        def __init__(self, free: int) -> None:
            self.total = free * 2
            self.used = free
            self.free = free

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.shutil.disk_usage",
        lambda _path: _FakeDiskUsage(required_free_bytes - 1),
    )

    with pytest.raises(RuntimeError, match="enough free space"):
        _save_durable_checkpoint(
            accelerator=_FakeAccelerator(),
            output_model_path=output_model_path,
            optimizer_steps_completed=4,
            epoch=0,
            step_in_epoch=3,
            dataloader_length=10,
            reason="interval",
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        )


def test_load_durable_checkpoint_metadata_rehydrates_resume_cursor(tmp_path: Path) -> None:
    """Loading durable checkpoint metadata should preserve resume fields exactly."""
    checkpoint_dir = tmp_path / "checkpoints" / "state-step-00000012"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "training_state.json").write_text(
        json.dumps(
            {
                "checkpoint_path": checkpoint_dir.as_posix(),
                "saved_at": "2026-03-09T12:00:00Z",
                "reason": "final-step",
                "optimizer_steps_completed": 12,
                "epoch": 1,
                "next_epoch": 2,
                "next_step_in_epoch": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    metadata = _load_durable_checkpoint_metadata(checkpoint_dir)

    assert metadata.optimizer_steps_completed == 12
    assert metadata.epoch == 1
    assert metadata.next_epoch == 2
    assert metadata.next_step_in_epoch == 0


def test_checkpoint_advanced_since_latest_save_detects_unsaved_progress(tmp_path: Path) -> None:
    """Unsaved optimizer progress should request one more durable checkpoint."""
    latest_checkpoint = _save_durable_checkpoint(
        accelerator=_FakeAccelerator(),
        output_model_path=tmp_path / "run" / "checkpoints",
        optimizer_steps_completed=12,
        epoch=1,
        step_in_epoch=4,
        dataloader_length=5,
        reason="interval",
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )

    assert (
        _checkpoint_advanced_since_latest_save(
            latest_checkpoint,
            optimizer_steps_completed=13,
        )
        is True
    )
    assert (
        _checkpoint_advanced_since_latest_save(
            latest_checkpoint,
            optimizer_steps_completed=12,
        )
        is False
    )


def test_mark_stop_requested_records_first_signal_only() -> None:
    """The first stop signal should win so the loop reports one stable cause."""
    stop_state = TrainingStopState()

    mark_stop_requested(stop_state, signal_number=15)
    mark_stop_requested(stop_state, signal_number=2)

    assert stop_state.stop_requested is True
    assert stop_state.signal_name == "SIGTERM"


def test_mark_stop_requested_falls_back_for_unknown_signal_number() -> None:
    """Unknown signal values should still be recorded deterministically."""
    stop_state = TrainingStopState()

    mark_stop_requested(stop_state, signal_number=999)

    assert stop_state.stop_requested is True
    assert stop_state.signal_name == "signal-999"


def test_install_training_stop_handlers_requires_main_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signal handler installation should reject worker-thread misuse explicitly."""
    stop_state = TrainingStopState()
    fake_main = object()
    fake_worker = object()

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.training_stop.threading.main_thread",
        lambda: fake_main,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.training_stop.threading.current_thread",
        lambda: fake_worker,
    )

    with pytest.raises(RuntimeError, match="main training thread"):
        install_training_stop_handlers(stop_state)


def test_train_with_args_writes_final_durable_checkpoint_on_stop_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stop request should produce one final durable checkpoint before exit."""
    train_manifest = tmp_path / "manifests" / "swedish_pilot_train.prepared.jsonl"
    train_manifest.parent.mkdir(parents=True, exist_ok=True)
    train_manifest.write_text(
        json.dumps(
            {
                "text": "hej världen",
                "audio_codes": [[1, 2], [3, 4]],
                "ref_audio": "refs/speaker-a/ref.wav",
                "speaker_id": "speaker-a",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output_model_path = tmp_path / "run" / "checkpoints"

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.Accelerator",
        _FakeAccelerator,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.Qwen3TTSModel.from_pretrained",
        lambda *args, **kwargs: _FakeQwenWrapper(processor=object(), model=_FakeQwenModel(4)),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.AutoConfig.from_pretrained",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.TTSDataset",
        _FakeDataset,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.DataLoader",
        lambda *args, **kwargs: [_fake_training_batch()],
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.AdamW",
        _FakeOptimizer,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz._save_checkpoint",
        _fake_save_checkpoint,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.install_training_stop_handlers",
        lambda stop_state: mark_stop_requested(stop_state, 15),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz.torch.cuda.is_available",
        lambda: False,
    )

    summary = train_with_args(
        argparse.Namespace(
            init_model_path="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            output_model_path=output_model_path.as_posix(),
            train_jsonl=train_manifest.as_posix(),
            batch_size=1,
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=100,
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
            resume_from_checkpoint=None,
            metrics_output_json=None,
            speaker_name="pilot_multi_speaker",
        )
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
    assert summary.ref_mel_cache["enabled"] is True
    assert summary.ref_mel_cache["max_items"] == 2048
    assert summary.durable_checkpoint_paths == [summary.latest_durable_checkpoint_path]
    assert summary.tracking is not None
    assert summary.tracking.project_name == "task101-qwen-pilot"
    assert summary.tracking.run_name == output_model_path.parent.name
    assert summary.tracking.mlflow_run_id == "fake-mlflow-run-id"
    assert latest_checkpoint["reason"] == "signal-stop"
