"""Shared test support for Qwen training tests.

Purpose:
    Provide reusable fakes, stubs, and factory helpers for testing the
    sft_12hz training patches without requiring a real GPU training run.

Relationships:
    - Consumed by test_checkpoint_cursor, test_checkpoint_persistence,
      test_stop_signals, and test_train_loop modules.
    - Exercises helper functions in
      `scripts/devops/qwen_finetuning_patches/sft_12hz*.py`.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F

from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import TrainingRowBatchMetrics

SFT_PATCH_ROOT = Path(__file__).resolve().parents[2] / "scripts/devops/qwen_finetuning_patches"
if SFT_PATCH_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SFT_PATCH_ROOT.as_posix())

SFT_12HZ = importlib.import_module("scripts.devops.qwen_finetuning_patches.sft_12hz")
SFT_12HZ_CHECKPOINTING = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing"
)
_checkpoint_resume_cursor = SFT_12HZ_CHECKPOINTING._checkpoint_resume_cursor
_checkpoint_advanced_since_latest_save = (
    SFT_12HZ_CHECKPOINTING._checkpoint_advanced_since_latest_save
)
_current_durable_checkpoint_paths = SFT_12HZ_CHECKPOINTING._current_durable_checkpoint_paths
_durable_checkpoint_staging_dir = SFT_12HZ_CHECKPOINTING._durable_checkpoint_staging_dir
DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES = (
    SFT_12HZ_CHECKPOINTING.DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES
)
_load_durable_checkpoint_metadata = SFT_12HZ_CHECKPOINTING._load_durable_checkpoint_metadata
_save_durable_checkpoint = SFT_12HZ_CHECKPOINTING._save_durable_checkpoint
train_with_args = SFT_12HZ.train_with_args
TrainingStopState = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.training_stop"
).TrainingStopState
NonFiniteLossError = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls"
).NonFiniteLossError
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
        respect_gradient_accumulation: bool = False,
        mixed_precision: str = "bf16",
        log_with: str | list[str] = "tensorboard",
        project_dir: str = "",
    ) -> None:
        del mixed_precision, log_with
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.respect_gradient_accumulation = respect_gradient_accumulation
        self.is_main_process = True
        self.saved_paths: list[str] = []
        self.wait_count = 0
        self.logged_metrics: list[tuple[dict[str, float | int], int]] = []
        self.trackers_initialized = False
        self.training_ended = False
        self.accumulate_calls = 0
        self.sync_gradients_history: list[bool] = []
        self.prepared_optimizer: _FakePreparedOptimizer | None = None
        self._sync_gradients = True
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
        prepared_args = list(args)
        if len(prepared_args) >= 2 and isinstance(prepared_args[1], _FakeOptimizer):
            wrapped_optimizer = _FakePreparedOptimizer(
                optimizer=prepared_args[1],
                accelerator=self,
            )
            self.prepared_optimizer = wrapped_optimizer
            prepared_args[1] = wrapped_optimizer
        return tuple(prepared_args)

    def accumulate(self, _model: object) -> "_FakeAccelerator":
        """Provide one no-op context manager for accumulate semantics."""
        self.accumulate_calls += 1
        if not self.respect_gradient_accumulation:
            self._sync_gradients = True
        else:
            self._sync_gradients = self.accumulate_calls % self.gradient_accumulation_steps == 0
        self.sync_gradients_history.append(self._sync_gradients)
        return self

    def __enter__(self) -> "_FakeAccelerator":
        """Enter the no-op accumulate context."""
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Exit the no-op accumulate context."""
        del exc_type, exc, tb

    @property
    def sync_gradients(self) -> bool:
        """Mirror Accelerate accumulation semantics for sync boundaries."""
        return self._sync_gradients

    def backward(self, loss: torch.Tensor) -> None:
        """Backpropagate through the fake training graph."""
        loss.backward()

    def clip_grad_norm_(self, parameters: Iterable[object], _max_norm: float) -> torch.Tensor:
        """Return one deterministic gradient norm from the fake parameter set."""
        total_squared_norm = torch.tensor(0.0, dtype=torch.float32)
        saw_gradient = False
        for parameter in parameters:
            gradient = getattr(parameter, "grad", None)
            if gradient is None:
                continue
            saw_gradient = True
            gradient_norm = gradient.detach().to(dtype=torch.float32).norm()
            total_squared_norm = total_squared_norm + (gradient_norm * gradient_norm)
        if not saw_gradient:
            return torch.tensor(0.0, dtype=torch.float32)
        return total_squared_norm.sqrt()

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
        dataloader: list[dict[str, object]],
        skip: int,
    ) -> list[dict[str, object]]:
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
        self.step_calls = 0
        self.zero_grad_calls = 0

    def step(self) -> None:
        """Accept one optimizer step without mutating real parameters."""
        self.step_calls += 1

    def zero_grad(self) -> None:
        """Accept zero-grad requests from the training loop."""
        self.zero_grad_calls += 1


class _FakePreparedOptimizer:
    """Simulate Accelerate's wrapped optimizer under accumulation mode."""

    def __init__(self, *, optimizer: _FakeOptimizer, accelerator: _FakeAccelerator) -> None:
        self._optimizer = optimizer
        self._accelerator = accelerator
        self.raw_step_attempts = 0
        self.raw_zero_grad_attempts = 0
        self.effective_step_calls = 0
        self.effective_zero_grad_calls = 0

    def step(self) -> None:
        """Apply the optimizer step only on sync boundaries."""
        self.raw_step_attempts += 1
        if not self._accelerator.sync_gradients:
            return
        self.effective_step_calls += 1
        self._optimizer.step()

    def zero_grad(self) -> None:
        """Zero gradients only on sync boundaries."""
        self.raw_zero_grad_attempts += 1
        if not self._accelerator.sync_gradients:
            return
        self.effective_zero_grad_calls += 1
        self._optimizer.zero_grad()


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


class _FakeNaNTalker(_FakeTalker):
    """Minimal talker variant that emits a persistent non-finite main loss."""

    def forward(
        self,
        *,
        inputs_embeds: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
        output_hidden_states: bool,
    ) -> _FakeTalkerOutputs:
        """Return one NaN loss while preserving the hidden-state structure."""
        del attention_mask, labels, output_hidden_states
        nan_loss = (inputs_embeds.sum() * 0.0) + torch.tensor(
            float("nan"),
            dtype=inputs_embeds.dtype,
            device=inputs_embeds.device,
        )
        return _FakeTalkerOutputs(
            loss=nan_loss,
            hidden_states=[[inputs_embeds]],
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


class _FakeNaNQwenModel(_FakeQwenModel):
    """Minimal multi-speaker model that keeps producing non-finite loss."""

    def __init__(self, embedding_dim: int) -> None:
        super().__init__(embedding_dim)
        self.talker = _FakeNaNTalker(embedding_dim)


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
        data_path_attribution: object | None = None,
    ) -> None:
        del ref_mel_cache, data_path_attribution
        self.rows = rows
        self.collate_fn = lambda batch: batch

    def __len__(self) -> int:
        """Return the deterministic fake row count."""
        return len(self.rows)

    def batch_metrics(self) -> list[TrainingRowBatchMetrics]:
        """Return simple fake batching metrics for the patched sampler path."""
        return [TrainingRowBatchMetrics(text_token_count=8, codec_frame_count=8) for _ in self.rows]


def fake_save_checkpoint(**kwargs: object) -> str:
    """Persist one lightweight fake checkpoint directory for the stop test."""
    output_dir = Path(str(kwargs["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.as_posix()


def fake_training_batch() -> dict[str, object]:
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
    speaker_ids = torch.zeros((1,), dtype=torch.long)
    return {
        "input_ids": input_ids,
        "codec_ids": codec_ids,
        "ref_mels": ref_mels,
        "text_embedding_mask": text_embedding_mask,
        "codec_embedding_mask": codec_embedding_mask,
        "attention_mask": attention_mask,
        "codec_0_labels": codec_0_labels,
        "codec_mask": codec_mask,
        "speaker_ids": speaker_ids,
        "batch_provenance": [
            {
                "row_id": "tests/train.jsonl#L1",
                "manifest_path": "tests/train.jsonl",
                "manifest_line_number": 1,
                "dataset_index": 0,
                "speaker_id": "speaker-a",
                "text_preview": "hej världen",
                "codec_frame_count": 8,
                "ref_audio": "refs/speaker-a/ref.wav",
            }
        ],
    }


def base_training_args(
    *,
    output_model_path: Path,
    train_manifest: Path,
    max_steps: int = 8,
    heartbeat_interval_optimizer_steps: int = 20,
    finite_loss_max_consecutive_steps: int = 3,
) -> argparse.Namespace:
    """Return one baseline argparse namespace for focused train-loop tests."""
    return argparse.Namespace(
        init_model_path="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        output_model_path=output_model_path.as_posix(),
        train_jsonl=train_manifest.as_posix(),
        eval_jsonl=train_manifest.as_posix(),
        batch_size=8,
        lr=2e-5,
        num_epochs=1,
        max_steps=max_steps,
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        resume_from_checkpoint=None,
        metrics_output_json=None,
        data_path_proof_mode=False,
        heartbeat_interval_optimizer_steps=heartbeat_interval_optimizer_steps,
        finite_loss_max_consecutive_steps=finite_loss_max_consecutive_steps,
    )
