"""Optimizer-boundary diagnostics and fail-closed guards for Qwen training.

Purpose:
    Keep optimizer-boundary failure decisions out of `sft_12hz_loop.py` so the
    training loop stays focused on control flow while this module owns
    corruption detection around clipping and optimizer updates.

Relationships:
    - Imported by `sft_12hz_train_step.py` on sync boundaries before and after
      one optimizer update.
    - Consumes probe payloads from
      `sft_12hz_optimizer_guard_probes.py`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard_probes import (
    OptimizerBoundaryPreStepProbes,
    capture_pre_step_optimizer_boundary_probes,
    capture_targeted_optimizer_state_probes,
    capture_targeted_parameter_probes,
    first_non_finite_surface,
)


class OptimizerBoundaryCorruptionError(RuntimeError):
    """Raised when one optimizer-boundary check detects non-finite corruption."""

    def __init__(
        self,
        *,
        trigger_reason: str,
        optimizer_step: int,
        current_epoch: int,
        current_train_iteration: int,
        loss_value: float | None,
        main_loss_value: float | None,
        sub_talker_loss_value: float | None,
        grad_norm_value: float | None,
        optimizer_step_attempted: bool,
        optimizer_step_completed: bool,
        targeted_parameter_names: list[str],
        first_non_finite_stage: str | None,
        first_non_finite_surface: str | None,
        pre_step_parameter_probes: dict[str, object] | None,
        pre_clip_gradient_probes: dict[str, object] | None,
        post_clip_gradient_probes: dict[str, object] | None,
        pre_step_optimizer_state_probes: dict[str, object] | None,
        post_step_parameter_probes: dict[str, object] | None,
        post_step_optimizer_state_probes: dict[str, object] | None,
        step_forensics: dict[str, object] | None,
    ) -> None:
        self.trigger_reason = trigger_reason
        self.optimizer_step = optimizer_step
        self.current_epoch = current_epoch
        self.current_train_iteration = current_train_iteration
        self.loss_value = loss_value
        self.main_loss_value = main_loss_value
        self.sub_talker_loss_value = sub_talker_loss_value
        self.grad_norm_value = grad_norm_value
        self.clip_grad_norm_value = grad_norm_value
        self.optimizer_step_attempted = optimizer_step_attempted
        self.optimizer_step_completed = optimizer_step_completed
        self.targeted_parameter_names = targeted_parameter_names
        self.first_non_finite_stage = first_non_finite_stage
        self.first_non_finite_surface = first_non_finite_surface
        self.pre_step_parameter_probes = pre_step_parameter_probes
        self.pre_clip_gradient_probes = pre_clip_gradient_probes
        self.post_clip_gradient_probes = post_clip_gradient_probes
        self.pre_step_optimizer_state_probes = pre_step_optimizer_state_probes
        self.post_step_parameter_probes = post_step_parameter_probes
        self.post_step_optimizer_state_probes = post_step_optimizer_state_probes
        self.step_forensics = step_forensics
        message = (
            "Optimizer boundary guard triggered "
            f"(trigger_reason={trigger_reason}, optimizer_step={optimizer_step}, "
            f"first_non_finite_stage={first_non_finite_stage}, "
            f"first_non_finite_surface={first_non_finite_surface})."
        )
        super().__init__(message)

    def payload(self) -> dict[str, object]:
        """Return one JSON-safe optimizer-boundary failure payload."""
        grad_norm_is_finite = (
            None if self.grad_norm_value is None else math.isfinite(self.grad_norm_value)
        )
        return {
            "triggered": True,
            "trigger_reason": self.trigger_reason,
            "optimizer_step": self.optimizer_step,
            "current_epoch": self.current_epoch,
            "current_train_iteration": self.current_train_iteration,
            "loss_value": self.loss_value,
            "main_loss_value": self.main_loss_value,
            "sub_talker_loss_value": self.sub_talker_loss_value,
            "grad_norm_value": self.grad_norm_value,
            "clip_grad_norm_value": self.clip_grad_norm_value,
            "loss_is_finite": (None if self.loss_value is None else math.isfinite(self.loss_value)),
            "main_loss_is_finite": (
                None if self.main_loss_value is None else math.isfinite(self.main_loss_value)
            ),
            "sub_talker_loss_is_finite": (
                None
                if self.sub_talker_loss_value is None
                else math.isfinite(self.sub_talker_loss_value)
            ),
            "grad_norm_is_finite": grad_norm_is_finite,
            "clip_grad_norm_is_finite": grad_norm_is_finite,
            "optimizer_step_attempted": self.optimizer_step_attempted,
            "optimizer_step_completed": self.optimizer_step_completed,
            "targeted_parameter_names": list(self.targeted_parameter_names),
            "first_non_finite_stage": self.first_non_finite_stage,
            "first_non_finite_surface": self.first_non_finite_surface,
            "pre_step_parameter_probes": self.pre_step_parameter_probes,
            "pre_clip_gradient_probes": self.pre_clip_gradient_probes,
            "post_clip_gradient_probes": self.post_clip_gradient_probes,
            "pre_step_optimizer_state_probes": self.pre_step_optimizer_state_probes,
            "post_step_parameter_probes": self.post_step_parameter_probes,
            "post_step_optimizer_state_probes": self.post_step_optimizer_state_probes,
            "step_forensics": self.step_forensics,
        }


def build_pre_step_optimizer_boundary_failure(
    *,
    model: object,
    optimizer: torch.optim.Optimizer,
    optimizer_step: int,
    current_epoch: int,
    current_train_iteration: int,
    loss: torch.Tensor,
    main_loss: torch.Tensor,
    sub_talker_loss: torch.Tensor,
    step_forensics: dict[str, object] | None,
    pre_step_probes: OptimizerBoundaryPreStepProbes | None = None,
) -> OptimizerBoundaryCorruptionError | None:
    """Return one failure when targeted gradients are already bad pre-clip."""
    resolved_pre_step_probes = (
        capture_pre_step_optimizer_boundary_probes(model=model, optimizer=optimizer)
        if pre_step_probes is None
        else pre_step_probes
    )
    first_non_finite_gradient = first_non_finite_surface(
        resolved_pre_step_probes.pre_clip_gradient_probes
    )
    if first_non_finite_gradient is None:
        return None
    return OptimizerBoundaryCorruptionError(
        trigger_reason="pre_clip_non_finite_gradients",
        optimizer_step=optimizer_step,
        current_epoch=current_epoch,
        current_train_iteration=current_train_iteration,
        loss_value=_optional_scalar_value(loss),
        main_loss_value=_optional_scalar_value(main_loss),
        sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
        grad_norm_value=None,
        optimizer_step_attempted=False,
        optimizer_step_completed=False,
        targeted_parameter_names=list(resolved_pre_step_probes.targeted_parameter_names),
        first_non_finite_stage="pre_clip",
        first_non_finite_surface=first_non_finite_gradient,
        pre_step_parameter_probes=resolved_pre_step_probes.parameter_probes,
        pre_clip_gradient_probes=resolved_pre_step_probes.pre_clip_gradient_probes,
        post_clip_gradient_probes=None,
        pre_step_optimizer_state_probes=resolved_pre_step_probes.optimizer_state_probes,
        post_step_parameter_probes=None,
        post_step_optimizer_state_probes=None,
        step_forensics=step_forensics,
    )


def build_clip_boundary_optimizer_failure(
    *,
    optimizer_step: int,
    current_epoch: int,
    current_train_iteration: int,
    loss: torch.Tensor,
    main_loss: torch.Tensor,
    sub_talker_loss: torch.Tensor,
    grad_norm: torch.Tensor | float | None,
    step_forensics: dict[str, object] | None,
    pre_step_probes: OptimizerBoundaryPreStepProbes,
    post_clip_gradient_probes: dict[str, object],
) -> OptimizerBoundaryCorruptionError | None:
    """Return one failure when clipping introduces or reveals corruption."""
    grad_norm_value = _optional_scalar_value(grad_norm)
    if grad_norm_value is not None and not math.isfinite(grad_norm_value):
        return OptimizerBoundaryCorruptionError(
            trigger_reason="clip_grad_norm_non_finite",
            optimizer_step=optimizer_step,
            current_epoch=current_epoch,
            current_train_iteration=current_train_iteration,
            loss_value=_optional_scalar_value(loss),
            main_loss_value=_optional_scalar_value(main_loss),
            sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
            grad_norm_value=grad_norm_value,
            optimizer_step_attempted=False,
            optimizer_step_completed=False,
            targeted_parameter_names=list(pre_step_probes.targeted_parameter_names),
            first_non_finite_stage="clip_grad_norm",
            first_non_finite_surface="grad_norm",
            pre_step_parameter_probes=pre_step_probes.parameter_probes,
            pre_clip_gradient_probes=pre_step_probes.pre_clip_gradient_probes,
            post_clip_gradient_probes=post_clip_gradient_probes,
            pre_step_optimizer_state_probes=pre_step_probes.optimizer_state_probes,
            post_step_parameter_probes=None,
            post_step_optimizer_state_probes=None,
            step_forensics=step_forensics,
        )
    first_non_finite_post_clip = first_non_finite_surface(post_clip_gradient_probes)
    if first_non_finite_post_clip is None:
        return None
    return OptimizerBoundaryCorruptionError(
        trigger_reason="post_clip_non_finite_gradients",
        optimizer_step=optimizer_step,
        current_epoch=current_epoch,
        current_train_iteration=current_train_iteration,
        loss_value=_optional_scalar_value(loss),
        main_loss_value=_optional_scalar_value(main_loss),
        sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
        grad_norm_value=grad_norm_value,
        optimizer_step_attempted=False,
        optimizer_step_completed=False,
        targeted_parameter_names=list(pre_step_probes.targeted_parameter_names),
        first_non_finite_stage="post_clip",
        first_non_finite_surface=first_non_finite_post_clip,
        pre_step_parameter_probes=pre_step_probes.parameter_probes,
        pre_clip_gradient_probes=pre_step_probes.pre_clip_gradient_probes,
        post_clip_gradient_probes=post_clip_gradient_probes,
        pre_step_optimizer_state_probes=pre_step_probes.optimizer_state_probes,
        post_step_parameter_probes=None,
        post_step_optimizer_state_probes=None,
        step_forensics=step_forensics,
    )


def build_post_step_optimizer_boundary_failure(
    *,
    model: object,
    optimizer: torch.optim.Optimizer,
    optimizer_step: int,
    current_epoch: int,
    current_train_iteration: int,
    loss: torch.Tensor,
    main_loss: torch.Tensor,
    sub_talker_loss: torch.Tensor,
    grad_norm: torch.Tensor | float | None,
    step_forensics: dict[str, object] | None,
    pre_step_parameter_probes: dict[str, object] | None,
    pre_clip_gradient_probes: dict[str, object] | None,
    post_clip_gradient_probes: dict[str, object] | None,
    pre_step_optimizer_state_probes: dict[str, object] | None,
) -> OptimizerBoundaryCorruptionError | None:
    """Return one post-step failure when params or optimizer state corrupt."""
    post_step_parameter_probes = capture_targeted_parameter_probes(model=model)
    post_step_optimizer_state_probes = capture_targeted_optimizer_state_probes(
        model=model,
        optimizer=optimizer,
    )
    targeted_parameter_names = _targeted_parameter_names(
        pre_step_parameter_probes,
        post_step_parameter_probes,
    )
    first_non_finite_parameter = first_non_finite_surface(post_step_parameter_probes)
    if first_non_finite_parameter is not None:
        return OptimizerBoundaryCorruptionError(
            trigger_reason="post_step_non_finite_parameters",
            optimizer_step=optimizer_step,
            current_epoch=current_epoch,
            current_train_iteration=current_train_iteration,
            loss_value=_optional_scalar_value(loss),
            main_loss_value=_optional_scalar_value(main_loss),
            sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
            grad_norm_value=_optional_scalar_value(grad_norm),
            optimizer_step_attempted=True,
            optimizer_step_completed=True,
            targeted_parameter_names=targeted_parameter_names,
            first_non_finite_stage="post_step",
            first_non_finite_surface=first_non_finite_parameter,
            pre_step_parameter_probes=pre_step_parameter_probes,
            pre_clip_gradient_probes=pre_clip_gradient_probes,
            post_clip_gradient_probes=post_clip_gradient_probes,
            pre_step_optimizer_state_probes=pre_step_optimizer_state_probes,
            post_step_parameter_probes=post_step_parameter_probes,
            post_step_optimizer_state_probes=post_step_optimizer_state_probes,
            step_forensics=step_forensics,
        )
    first_non_finite_optimizer_state = first_non_finite_surface(post_step_optimizer_state_probes)
    if first_non_finite_optimizer_state is None:
        return None
    return OptimizerBoundaryCorruptionError(
        trigger_reason="post_step_non_finite_optimizer_state",
        optimizer_step=optimizer_step,
        current_epoch=current_epoch,
        current_train_iteration=current_train_iteration,
        loss_value=_optional_scalar_value(loss),
        main_loss_value=_optional_scalar_value(main_loss),
        sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
        grad_norm_value=_optional_scalar_value(grad_norm),
        optimizer_step_attempted=True,
        optimizer_step_completed=True,
        targeted_parameter_names=targeted_parameter_names,
        first_non_finite_stage="post_step",
        first_non_finite_surface=first_non_finite_optimizer_state,
        pre_step_parameter_probes=pre_step_parameter_probes,
        pre_clip_gradient_probes=pre_clip_gradient_probes,
        post_clip_gradient_probes=post_clip_gradient_probes,
        pre_step_optimizer_state_probes=pre_step_optimizer_state_probes,
        post_step_parameter_probes=post_step_parameter_probes,
        post_step_optimizer_state_probes=post_step_optimizer_state_probes,
        step_forensics=step_forensics,
    )


def _targeted_parameter_names(*payloads: dict[str, object] | None) -> list[str]:
    """Return the targeted parameter names preserved in probe payload order."""
    for payload in payloads:
        if not isinstance(payload, Mapping):
            continue
        raw_probes = payload.get("probes")
        if not isinstance(raw_probes, Mapping):
            continue
        return [str(name) for name in raw_probes.keys()]
    return []


def _optional_scalar_value(value: torch.Tensor | float | None) -> float | None:
    """Return one detached scalar float when possible."""
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().to(device="cpu", dtype=torch.float32).item())
    return float(value)
