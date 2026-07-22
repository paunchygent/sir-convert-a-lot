"""Focused tests for the Qwen eval runtime.

Purpose:
    Verify that the held-out eval helper reuses the no-projection fine-tuning
    graph even when talker-level projection exists for runtime fingerprinting.

Relationships:
    - Exercises `sft_12hz_eval.py`.
    - Complements `test_train_step_runtime.py` so train/eval stay aligned.
"""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest
import torch
from scripts.devops.qwen_finetuning_patches.sft_12hz_eval import run_eval_pass


class _FakeTalkerModel:
    """Minimal talker-model surface used by the eval runtime test."""

    def __init__(self) -> None:
        self.last_text_embedding_input_ids: torch.Tensor | None = None

    def text_embedding(self, input_ids: torch.Tensor) -> torch.Tensor:
        self.last_text_embedding_input_ids = input_ids.detach().clone()
        return torch.zeros((*input_ids.shape, 4), dtype=torch.float32)

    def codec_embedding(self, input_ids: torch.Tensor) -> torch.Tensor:
        return torch.zeros((*input_ids.shape, 4), dtype=torch.float32)


class _FakeTalker:
    """Minimal talker surface used by the eval runtime test."""

    def __init__(self) -> None:
        self.model = _FakeTalkerModel()
        self.text_projection: object | None = None
        self.code_predictor = SimpleNamespace(
            get_input_embeddings=lambda: torch.zeros(1, 1, 4, dtype=torch.float32)
        )

    def get_input_embeddings(self) -> object:
        return self.model.codec_embedding

    def get_text_embeddings(self) -> object:
        return self.model.text_embedding

    def __call__(self, *, inputs_embeds, attention_mask, labels, output_hidden_states):
        del attention_mask, labels, output_hidden_states
        hidden = torch.zeros_like(inputs_embeds)
        return SimpleNamespace(loss=torch.tensor(1.0), hidden_states=[[hidden]])

    def forward_sub_talker_finetune(self, talker_codec_ids, talker_hidden_states):
        del talker_codec_ids, talker_hidden_states
        return None, torch.tensor(1.0)


class _FakeModel:
    """Minimal model double that matches the eval-step surface."""

    device = torch.device("cpu")
    dtype = torch.float32

    def __init__(self) -> None:
        self.talker = _FakeTalker()
        self._training = True

    @property
    def training(self) -> bool:
        return self._training

    def eval(self) -> None:
        self._training = False

    def train(self) -> None:
        self._training = True

    def speaker_encoder(self, ref_mels: torch.Tensor) -> torch.Tensor:
        batch_size = ref_mels.shape[0]
        return torch.zeros((batch_size, 4), dtype=torch.float32)


class _ProjectionRecorder:
    """Record whether the talker-level text projection was applied."""

    def __init__(self) -> None:
        self.called = False

    def __call__(self, values: torch.Tensor) -> torch.Tensor:
        self.called = True
        return values + 1.0


def test_run_eval_pass_does_not_apply_text_projection(
    monkeypatch,
) -> None:
    """Held-out eval should not inject projection into the fine-tune graph."""
    model = _FakeModel()
    projection = _ProjectionRecorder()
    model.talker.text_projection = projection
    prepared = SimpleNamespace(
        model=model,
        accelerator=SimpleNamespace(),
        eval_dataloader=[
            {
                "input_ids": torch.zeros((1, 10, 2), dtype=torch.long),
                "codec_ids": torch.zeros((1, 10), dtype=torch.long),
                "semantic_text_ids": torch.zeros((1, 2), dtype=torch.long),
                "semantic_text_positions": torch.tensor([[8, 9]], dtype=torch.long),
                "semantic_text_mask": torch.ones((1, 2), dtype=torch.bool),
                "ref_mels": torch.zeros((1, 4, 4), dtype=torch.float32),
                "text_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
                "codec_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
                "attention_mask": torch.ones((1, 10), dtype=torch.long),
                "codec_0_labels": torch.zeros((1, 10), dtype=torch.long),
                "codec_mask": torch.ones((1, 10), dtype=torch.bool),
            }
        ],
        eval_dataloader_length=1,
        torch_profiler_session=SimpleNamespace(phase=lambda name: nullcontext()),
        effective_dataloader_tuning=SimpleNamespace(non_blocking_transfer=False),
    )

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_eval.require_batch_tensors",
        lambda payload: payload,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces.to_device_with_optional_non_blocking",
        lambda tensor, **kwargs: tensor,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces.fuse_auxiliary_codebook_embeddings",
        lambda **kwargs: torch.zeros((1, 10, 4), dtype=torch.float32),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_eval.log_eval_metrics",
        lambda *args, **kwargs: None,
    )

    result = run_eval_pass(
        prepared=prepared,
        current_epoch=5,
        current_optimizer_step=1401,
        current_train_iteration=788,
        latest_loss=3.9,
        smoothed_loss=3.7,
        latest_durable_checkpoint=None,
        latest_eval_loss=None,
        best_eval_loss=None,
        best_eval_step=None,
        eval_runs_completed=0,
        eval_batches_completed=0,
        progress_callback=None,
    )

    assert projection.called is False
    assert model.talker.model.last_text_embedding_input_ids is not None
    expected_semantic_text_ids = prepared.eval_dataloader[0]["semantic_text_ids"]
    assert isinstance(expected_semantic_text_ids, torch.Tensor)
    assert torch.equal(
        model.talker.model.last_text_embedding_input_ids,
        expected_semantic_text_ids,
    )
    assert result.latest_eval_loss == pytest.approx(1.3)


def test_run_eval_pass_can_use_the_masked_full_channel_lookup_path(
    monkeypatch,
) -> None:
    """Held-out eval should support the exact masked full-channel control path."""
    model = _FakeModel()
    full_text_ids = torch.tensor([[61, 62, 63, 64, 65, 66, 67, 68, 69, 70]], dtype=torch.long)
    prepared = SimpleNamespace(
        model=model,
        accelerator=SimpleNamespace(),
        eval_dataloader=[
            {
                "input_ids": torch.stack(
                    (full_text_ids, torch.zeros_like(full_text_ids)),
                    dim=-1,
                ),
                "codec_ids": torch.zeros((1, 10), dtype=torch.long),
                "semantic_text_ids": torch.tensor([[69, 70]], dtype=torch.long),
                "semantic_text_positions": torch.tensor([[8, 9]], dtype=torch.long),
                "semantic_text_mask": torch.ones((1, 2), dtype=torch.bool),
                "ref_mels": torch.zeros((1, 4, 4), dtype=torch.float32),
                "text_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
                "codec_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
                "attention_mask": torch.ones((1, 10), dtype=torch.long),
                "codec_0_labels": torch.zeros((1, 10), dtype=torch.long),
                "codec_mask": torch.ones((1, 10), dtype=torch.bool),
            }
        ],
        eval_dataloader_length=1,
        torch_profiler_session=SimpleNamespace(phase=lambda name: nullcontext()),
        effective_dataloader_tuning=SimpleNamespace(non_blocking_transfer=False),
        text_embedding_assembly_mode="full_channel_masked",
    )

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_eval.require_batch_tensors",
        lambda payload: payload,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces.to_device_with_optional_non_blocking",
        lambda tensor, **kwargs: tensor,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces.fuse_auxiliary_codebook_embeddings",
        lambda **kwargs: torch.zeros((1, 10, 4), dtype=torch.float32),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_eval.log_eval_metrics",
        lambda *args, **kwargs: None,
    )

    result = run_eval_pass(
        prepared=prepared,
        current_epoch=5,
        current_optimizer_step=1401,
        current_train_iteration=788,
        latest_loss=3.9,
        smoothed_loss=3.7,
        latest_durable_checkpoint=None,
        latest_eval_loss=None,
        best_eval_loss=None,
        best_eval_step=None,
        eval_runs_completed=0,
        eval_batches_completed=0,
        progress_callback=None,
    )

    assert model.talker.model.last_text_embedding_input_ids is not None
    assert torch.equal(model.talker.model.last_text_embedding_input_ids, full_text_ids)
    assert result.latest_eval_loss == pytest.approx(1.3)
