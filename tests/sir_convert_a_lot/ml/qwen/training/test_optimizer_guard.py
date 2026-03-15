"""Focused tests for Qwen optimizer-boundary corruption guards.

Purpose:
    Verify that the dedicated optimizer-boundary module fails closed before a
    corrupt update and reports both pre-step and post-step evidence for the
    targeted text embedding and text projection parameter family.

Relationships:
    - Exercises `sft_12hz_optimizer_guard.py` directly.
    - Keeps optimizer-boundary scenarios out of the broader train-loop tests.
"""

from __future__ import annotations

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    build_post_step_optimizer_boundary_failure,
    build_pre_step_optimizer_boundary_failure,
    capture_pre_step_optimizer_boundary_probes,
)
from tests.sir_convert_a_lot.ml.qwen.training.test_support import _FakeQwenModel


def _loss_tensors() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return one stable scalar loss triplet for optimizer-boundary tests."""
    return (
        torch.tensor(1.0, dtype=torch.float32),
        torch.tensor(0.8, dtype=torch.float32),
        torch.tensor(0.2, dtype=torch.float32),
    )


def _assign_finite_gradients(model: torch.nn.Module) -> None:
    """Populate deterministic finite gradients on all model parameters."""
    for parameter in model.parameters():
        parameter.grad = torch.ones_like(parameter, dtype=torch.float32)


def test_pre_step_guard_blocks_non_finite_grad_norm() -> None:
    """A non-finite grad norm must fail before `optimizer.step()` is attempted."""
    model = _FakeQwenModel(embedding_dim=4)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    _assign_finite_gradients(model)
    loss, main_loss, sub_talker_loss = _loss_tensors()

    error = build_pre_step_optimizer_boundary_failure(
        model=model,
        optimizer=optimizer,
        optimizer_step=1405,
        current_epoch=5,
        current_train_iteration=804,
        loss=loss,
        main_loss=main_loss,
        sub_talker_loss=sub_talker_loss,
        grad_norm=float("nan"),
        step_forensics={"optimizer_step": 1405},
    )

    assert error is not None
    assert error.trigger_reason == "pre_step_non_finite_grad_norm"
    assert error.optimizer_step_attempted is False
    assert error.optimizer_step_completed is False
    assert error.first_non_finite_surface == "grad_norm"
    payload = error.payload()
    assert payload["pre_step_gradient_probes"] is not None
    assert payload["pre_step_parameter_probes"] is not None
    assert "text_projection.weight" in error.targeted_parameter_names


def test_pre_step_guard_blocks_non_finite_targeted_gradient() -> None:
    """A targeted non-finite gradient must fail closed before the update."""
    model = _FakeQwenModel(embedding_dim=4)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    _assign_finite_gradients(model)
    text_projection_grad = model.talker.text_projection.weight.grad
    assert text_projection_grad is not None
    text_projection_grad.fill_(float("nan"))
    loss, main_loss, sub_talker_loss = _loss_tensors()

    error = build_pre_step_optimizer_boundary_failure(
        model=model,
        optimizer=optimizer,
        optimizer_step=1405,
        current_epoch=5,
        current_train_iteration=804,
        loss=loss,
        main_loss=main_loss,
        sub_talker_loss=sub_talker_loss,
        grad_norm=1.0,
        step_forensics={"optimizer_step": 1405},
    )

    assert error is not None
    assert error.trigger_reason == "pre_step_non_finite_gradients"
    assert error.optimizer_step_attempted is False
    assert error.first_non_finite_surface == "text_projection.weight.grad"


def test_post_step_guard_reports_non_finite_parameter_with_pre_step_probes() -> None:
    """Post-step corruption should preserve the captured pre-step evidence."""
    model = _FakeQwenModel(embedding_dim=4)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    _assign_finite_gradients(model)
    loss, main_loss, sub_talker_loss = _loss_tensors()
    pre_step_probes = capture_pre_step_optimizer_boundary_probes(
        model=model,
        optimizer=optimizer,
    )
    model.talker.model.text_embedding.embedding.weight.data.fill_(float("nan"))

    error = build_post_step_optimizer_boundary_failure(
        model=model,
        optimizer=optimizer,
        optimizer_step=1406,
        current_epoch=5,
        current_train_iteration=808,
        loss=loss,
        main_loss=main_loss,
        sub_talker_loss=sub_talker_loss,
        grad_norm=1.0,
        step_forensics={"optimizer_step": 1406},
        pre_step_parameter_probes=pre_step_probes.parameter_probes,
        pre_step_gradient_probes=pre_step_probes.gradient_probes,
        pre_step_optimizer_state_probes=pre_step_probes.optimizer_state_probes,
    )

    assert error is not None
    assert error.trigger_reason == "post_step_non_finite_parameters"
    assert error.optimizer_step_attempted is True
    assert error.optimizer_step_completed is True
    assert error.first_non_finite_surface == "text_embedding.embedding.weight"
    payload = error.payload()
    assert payload["pre_step_parameter_probes"] == pre_step_probes.parameter_probes
    assert payload["pre_step_gradient_probes"] == pre_step_probes.gradient_probes


def test_post_step_guard_reports_non_finite_optimizer_state() -> None:
    """Corrupted optimizer state must fail immediately after the update."""
    model = _FakeQwenModel(embedding_dim=4)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    _assign_finite_gradients(model)
    loss, main_loss, sub_talker_loss = _loss_tensors()
    pre_step_probes = capture_pre_step_optimizer_boundary_probes(
        model=model,
        optimizer=optimizer,
    )
    text_embedding_weight = model.talker.model.text_embedding.embedding.weight
    optimizer.state[text_embedding_weight]["exp_avg"] = torch.full_like(
        text_embedding_weight,
        float("nan"),
    )
    optimizer.state[text_embedding_weight]["exp_avg_sq"] = torch.ones_like(
        text_embedding_weight,
    )

    error = build_post_step_optimizer_boundary_failure(
        model=model,
        optimizer=optimizer,
        optimizer_step=1406,
        current_epoch=5,
        current_train_iteration=808,
        loss=loss,
        main_loss=main_loss,
        sub_talker_loss=sub_talker_loss,
        grad_norm=1.0,
        step_forensics={"optimizer_step": 1406},
        pre_step_parameter_probes=pre_step_probes.parameter_probes,
        pre_step_gradient_probes=pre_step_probes.gradient_probes,
        pre_step_optimizer_state_probes=pre_step_probes.optimizer_state_probes,
    )

    assert error is not None
    assert error.trigger_reason == "post_step_non_finite_optimizer_state"
    assert error.first_non_finite_surface == "text_embedding.embedding.weight.exp_avg"
