"""Focused tests for the Qwen train-step runtime.

Purpose:
    Verify that one optimizer-step window fail-closes before `optimizer.step()`
    when the bounded optimizer guard reports pre-step corruption.

Relationships:
    - Exercises `sft_12hz_train_step.py`.
    - Complements optimizer-guard unit tests with one train-step integration.
"""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest
import torch
from scripts.devops.qwen_finetuning_patches.sft_12hz_train_step import (
    execute_train_iteration,
)


class _FakeOptimizer:
    """Minimal optimizer double that records whether step was attempted."""

    def __init__(self) -> None:
        self.step_called = False
        self.zero_grad_called = False

    def step(self) -> None:
        self.step_called = True

    def zero_grad(self) -> None:
        self.zero_grad_called = True


class _FakeAccelerator:
    """Minimal accelerator double for one bounded train-step test."""

    sync_gradients = True

    def accumulate(self, model: object):
        del model
        return nullcontext()

    def backward(self, loss: torch.Tensor) -> None:
        del loss

    def clip_grad_norm_(self, parameters, max_norm: float) -> torch.Tensor:
        del parameters, max_norm
        return torch.tensor(1.0)


class _FakeTalkerModel:
    """Minimal talker-model surface used by the train-step runtime."""

    def __init__(self) -> None:
        self.last_text_embedding_input_ids: torch.Tensor | None = None

    def text_embedding(self, input_ids: torch.Tensor) -> torch.Tensor:
        self.last_text_embedding_input_ids = input_ids.detach().clone()
        return torch.zeros((*input_ids.shape, 4), dtype=torch.float32)

    def codec_embedding(self, input_ids: torch.Tensor) -> torch.Tensor:
        return torch.zeros((*input_ids.shape, 4), dtype=torch.float32)


class _FakeTalker:
    """Minimal talker surface used by the train-step runtime."""

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
    """Minimal model double that matches the train-step surface."""

    device = torch.device("cpu")
    dtype = torch.float32

    def __init__(self) -> None:
        self.talker = _FakeTalker()

    def parameters(self):
        return [torch.nn.Parameter(torch.ones(1, dtype=torch.float32))]

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


def test_execute_train_iteration_skips_optimizer_step_on_pre_step_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Train-step runtime should fail closed before applying a corrupt update."""
    optimizer = _FakeOptimizer()
    accelerator = _FakeAccelerator()
    prepared = SimpleNamespace(
        torch_profiler_session=SimpleNamespace(phase=lambda name: nullcontext()),
        effective_dataloader_tuning=SimpleNamespace(non_blocking_transfer=False),
        loss_observer=SimpleNamespace(submit=lambda **kwargs: None, drain_ready=lambda force: []),
        heartbeat_policy=SimpleNamespace(should_emit_train_update=lambda step: False),
        finite_loss_guard=SimpleNamespace(observe=lambda observation: None),
        ref_mel_cache=SimpleNamespace(payload=lambda: {"enabled": True}),
        dataloader_length=128,
        eval_dataloader_length=8,
    )
    batch = {
        "input_ids": torch.zeros((1, 10, 2), dtype=torch.long),
        "codec_ids": torch.zeros((1, 10), dtype=torch.long),
        "semantic_text_ids": torch.zeros((1, 2), dtype=torch.long),
        "semantic_text_positions": torch.tensor([[8, 9]], dtype=torch.long),
        "semantic_text_mask": torch.ones((1, 2), dtype=torch.bool),
        "ref_mels": torch.zeros((1, 4, 4), dtype=torch.float32),
        "batch_provenance": [{"row_id": "L99"}],
        "text_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
        "codec_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
        "attention_mask": torch.ones((1, 10), dtype=torch.long),
        "codec_0_labels": torch.zeros((1, 10), dtype=torch.long),
        "codec_mask": torch.ones((1, 10), dtype=torch.bool),
    }

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.require_batch_tensors",
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
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_microbatch_forensics",
        lambda **kwargs: {"row_id": "L99"},
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_optimizer_step_forensics_window",
        lambda microbatches: {"microbatches": list(microbatches)},
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.capture_pre_step_optimizer_boundary_probes",
        lambda **kwargs: SimpleNamespace(
            targeted_parameter_names=["text_embedding.embedding.weight"],
            parameter_probes={},
            pre_clip_gradient_probes={},
            optimizer_state_probes={},
        ),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_pre_step_optimizer_boundary_failure",
        lambda **kwargs: RuntimeError("pre-step guard fired"),
    )

    with pytest.raises(RuntimeError, match="pre-step guard fired"):
        execute_train_iteration(
            accelerator=accelerator,
            prepared=prepared,
            model=_FakeModel(),
            optimizer=optimizer,
            epoch=5,
            batch=batch,
            train_iterations_completed=803,
            optimizer_steps_completed=1404,
            last_loss=3.9,
            smoothed_loss=3.7,
            latest_eval_loss=6.57,
            best_eval_loss=6.57,
            best_eval_step=1300,
            eval_runs_completed=1,
            latest_durable_checkpoint=None,
            emitted_train_progress=True,
            optimizer_step_microbatches=[],
            checkpoint_interval_steps=500,
            progress_callback=None,
        )

    assert optimizer.step_called is False


def test_execute_train_iteration_does_not_apply_text_projection_in_finetune_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Train-step runtime should fingerprint projection without injecting it."""
    optimizer = _FakeOptimizer()
    accelerator = _FakeAccelerator()
    prepared = SimpleNamespace(
        torch_profiler_session=SimpleNamespace(phase=lambda name: nullcontext()),
        effective_dataloader_tuning=SimpleNamespace(non_blocking_transfer=False),
        loss_observer=SimpleNamespace(submit=lambda **kwargs: None, drain_ready=lambda force: []),
        heartbeat_policy=SimpleNamespace(should_emit_train_update=lambda step: False),
        finite_loss_guard=SimpleNamespace(observe=lambda observation: None),
        ref_mel_cache=SimpleNamespace(payload=lambda: {"enabled": True}),
        dataloader_length=128,
        eval_dataloader_length=8,
    )
    batch = {
        "input_ids": torch.zeros((1, 10, 2), dtype=torch.long),
        "codec_ids": torch.zeros((1, 10), dtype=torch.long),
        "semantic_text_ids": torch.zeros((1, 2), dtype=torch.long),
        "semantic_text_positions": torch.tensor([[8, 9]], dtype=torch.long),
        "semantic_text_mask": torch.ones((1, 2), dtype=torch.bool),
        "ref_mels": torch.zeros((1, 4, 4), dtype=torch.float32),
        "batch_provenance": [{"row_id": "L99"}],
        "text_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
        "codec_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
        "attention_mask": torch.ones((1, 10), dtype=torch.long),
        "codec_0_labels": torch.zeros((1, 10), dtype=torch.long),
        "codec_mask": torch.ones((1, 10), dtype=torch.bool),
    }
    model = _FakeModel()
    projection = _ProjectionRecorder()
    model.talker.text_projection = projection

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.require_batch_tensors",
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
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_microbatch_forensics",
        lambda **kwargs: {"row_id": "L99"},
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_optimizer_step_forensics_window",
        lambda microbatches: {"microbatches": list(microbatches)},
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.capture_pre_step_optimizer_boundary_probes",
        lambda **kwargs: SimpleNamespace(
            targeted_parameter_names=["text_embedding.embedding.weight"],
            parameter_probes={},
            pre_clip_gradient_probes={},
            optimizer_state_probes={},
        ),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_pre_step_optimizer_boundary_failure",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_clip_boundary_optimizer_failure",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_post_step_optimizer_boundary_failure",
        lambda **kwargs: None,
    )

    result = execute_train_iteration(
        accelerator=accelerator,
        prepared=prepared,
        model=model,
        optimizer=optimizer,
        epoch=5,
        batch=batch,
        train_iterations_completed=803,
        optimizer_steps_completed=1404,
        last_loss=3.9,
        smoothed_loss=3.7,
        latest_eval_loss=6.57,
        best_eval_loss=6.57,
        best_eval_step=1300,
        eval_runs_completed=1,
        latest_durable_checkpoint=None,
        emitted_train_progress=True,
        optimizer_step_microbatches=[],
        checkpoint_interval_steps=500,
        progress_callback=None,
    )

    assert projection.called is False
    assert result.completed_optimizer_step is True
    assert model.talker.model.last_text_embedding_input_ids is not None
    expected_semantic_text_ids = batch["semantic_text_ids"]
    assert isinstance(expected_semantic_text_ids, torch.Tensor)
    assert torch.equal(
        model.talker.model.last_text_embedding_input_ids,
        expected_semantic_text_ids,
    )


def test_execute_train_iteration_can_use_the_masked_full_channel_lookup_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Train-step runtime should support the exact masked full-channel control path."""
    optimizer = _FakeOptimizer()
    accelerator = _FakeAccelerator()
    prepared = SimpleNamespace(
        torch_profiler_session=SimpleNamespace(phase=lambda name: nullcontext()),
        effective_dataloader_tuning=SimpleNamespace(non_blocking_transfer=False),
        loss_observer=SimpleNamespace(submit=lambda **kwargs: None, drain_ready=lambda force: []),
        heartbeat_policy=SimpleNamespace(should_emit_train_update=lambda step: False),
        finite_loss_guard=SimpleNamespace(observe=lambda observation: None),
        ref_mel_cache=SimpleNamespace(payload=lambda: {"enabled": True}),
        dataloader_length=128,
        eval_dataloader_length=8,
        text_embedding_assembly_mode="full_channel_masked",
    )
    full_text_ids = torch.tensor([[41, 42, 43, 44, 45, 46, 47, 48, 49, 50]], dtype=torch.long)
    batch = {
        "input_ids": torch.stack(
            (full_text_ids, torch.zeros_like(full_text_ids)),
            dim=-1,
        ),
        "codec_ids": torch.zeros((1, 10), dtype=torch.long),
        "semantic_text_ids": torch.tensor([[49, 50]], dtype=torch.long),
        "semantic_text_positions": torch.tensor([[8, 9]], dtype=torch.long),
        "semantic_text_mask": torch.ones((1, 2), dtype=torch.bool),
        "ref_mels": torch.zeros((1, 4, 4), dtype=torch.float32),
        "batch_provenance": [{"row_id": "L99"}],
        "text_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
        "codec_embedding_mask": torch.ones((1, 10, 1), dtype=torch.float32),
        "attention_mask": torch.ones((1, 10), dtype=torch.long),
        "codec_0_labels": torch.zeros((1, 10), dtype=torch.long),
        "codec_mask": torch.ones((1, 10), dtype=torch.bool),
    }

    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.require_batch_tensors",
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
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_microbatch_forensics",
        lambda **kwargs: {"row_id": "L99"},
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_optimizer_step_forensics_window",
        lambda microbatches: {"microbatches": list(microbatches)},
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.capture_pre_step_optimizer_boundary_probes",
        lambda **kwargs: SimpleNamespace(
            targeted_parameter_names=["text_embedding.embedding.weight"],
            parameter_probes={},
            pre_clip_gradient_probes={},
            optimizer_state_probes={},
        ),
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_pre_step_optimizer_boundary_failure",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_clip_boundary_optimizer_failure",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_train_step.build_post_step_optimizer_boundary_failure",
        lambda **kwargs: None,
    )

    model = _FakeModel()
    result = execute_train_iteration(
        accelerator=accelerator,
        prepared=prepared,
        model=model,
        optimizer=optimizer,
        epoch=5,
        batch=batch,
        train_iterations_completed=803,
        optimizer_steps_completed=1404,
        last_loss=3.9,
        smoothed_loss=3.7,
        latest_eval_loss=6.57,
        best_eval_loss=6.57,
        best_eval_step=1300,
        eval_runs_completed=1,
        latest_durable_checkpoint=None,
        emitted_train_progress=True,
        optimizer_step_microbatches=[],
        checkpoint_interval_steps=500,
        progress_callback=None,
    )

    assert result.completed_optimizer_step is True
    assert model.talker.model.last_text_embedding_input_ids is not None
    assert torch.equal(
        model.talker.model.last_text_embedding_input_ids,
        full_text_ids,
    )
