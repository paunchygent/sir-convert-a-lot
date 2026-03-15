"""Optimizer-boundary diagnostics and fail-closed guards for Qwen training.

Purpose:
    Keep targeted parameter, gradient, and optimizer-state finiteness checks
    out of `sft_12hz_loop.py` so the training loop stays focused on control
    flow while this module owns corruption detection at optimizer boundaries.

Relationships:
    - Imported by `sft_12hz_loop.py` on sync boundaries before and after one
      optimizer update.
    - Reuses `sft_12hz_forensics.py` tensor summaries so status/report payloads
      share one compact, JSON-safe finiteness contract.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    build_tensor_finiteness_payload,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    resolve_talker_text_embedding_module,
    resolve_talker_text_projection_module,
)


@dataclass(frozen=True)
class _TargetedParameterSurface:
    """One named parameter surface captured by the optimizer-boundary guard."""

    name: str
    parameter: torch.nn.Parameter


@dataclass(frozen=True)
class OptimizerBoundaryPreStepProbes:
    """Captured pre-step probes for one optimizer-boundary inspection window."""

    targeted_parameter_names: list[str]
    parameter_probes: dict[str, object]
    gradient_probes: dict[str, object]
    optimizer_state_probes: dict[str, object]


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
        first_non_finite_surface: str | None,
        pre_step_parameter_probes: dict[str, object] | None,
        pre_step_gradient_probes: dict[str, object] | None,
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
        self.optimizer_step_attempted = optimizer_step_attempted
        self.optimizer_step_completed = optimizer_step_completed
        self.targeted_parameter_names = targeted_parameter_names
        self.first_non_finite_surface = first_non_finite_surface
        self.pre_step_parameter_probes = pre_step_parameter_probes
        self.pre_step_gradient_probes = pre_step_gradient_probes
        self.pre_step_optimizer_state_probes = pre_step_optimizer_state_probes
        self.post_step_parameter_probes = post_step_parameter_probes
        self.post_step_optimizer_state_probes = post_step_optimizer_state_probes
        self.step_forensics = step_forensics
        message = (
            "Optimizer boundary guard triggered "
            f"(trigger_reason={trigger_reason}, optimizer_step={optimizer_step}, "
            f"first_non_finite_surface={first_non_finite_surface})."
        )
        super().__init__(message)

    def payload(self) -> dict[str, object]:
        """Return one JSON-safe optimizer-boundary failure payload."""
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
            "loss_is_finite": (None if self.loss_value is None else math.isfinite(self.loss_value)),
            "main_loss_is_finite": (
                None if self.main_loss_value is None else math.isfinite(self.main_loss_value)
            ),
            "sub_talker_loss_is_finite": (
                None
                if self.sub_talker_loss_value is None
                else math.isfinite(self.sub_talker_loss_value)
            ),
            "grad_norm_is_finite": (
                None if self.grad_norm_value is None else math.isfinite(self.grad_norm_value)
            ),
            "optimizer_step_attempted": self.optimizer_step_attempted,
            "optimizer_step_completed": self.optimizer_step_completed,
            "targeted_parameter_names": list(self.targeted_parameter_names),
            "first_non_finite_surface": self.first_non_finite_surface,
            "pre_step_parameter_probes": self.pre_step_parameter_probes,
            "pre_step_gradient_probes": self.pre_step_gradient_probes,
            "pre_step_optimizer_state_probes": self.pre_step_optimizer_state_probes,
            "post_step_parameter_probes": self.post_step_parameter_probes,
            "post_step_optimizer_state_probes": self.post_step_optimizer_state_probes,
            "step_forensics": self.step_forensics,
        }


def capture_pre_step_optimizer_boundary_probes(
    *,
    model: object,
    optimizer: torch.optim.Optimizer,
) -> OptimizerBoundaryPreStepProbes:
    """Capture one reusable pre-step probe bundle for the targeted surfaces."""
    targeted_surfaces = _targeted_parameter_surfaces(model)
    return OptimizerBoundaryPreStepProbes(
        targeted_parameter_names=[surface.name for surface in targeted_surfaces],
        parameter_probes=_parameter_probe_payload(
            targeted_surfaces,
            include_gradients=False,
        ),
        gradient_probes=_parameter_probe_payload(
            targeted_surfaces,
            include_gradients=True,
        ),
        optimizer_state_probes=_optimizer_state_probe_payload(
            optimizer,
            targeted_surfaces,
        ),
    )


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
    grad_norm: torch.Tensor | float | None,
    step_forensics: dict[str, object] | None,
    pre_step_probes: OptimizerBoundaryPreStepProbes | None = None,
) -> OptimizerBoundaryCorruptionError | None:
    """Return one pre-step failure when targeted gradients are already non-finite."""
    resolved_pre_step_probes = (
        capture_pre_step_optimizer_boundary_probes(model=model, optimizer=optimizer)
        if pre_step_probes is None
        else pre_step_probes
    )
    targeted_parameter_names = list(resolved_pre_step_probes.targeted_parameter_names)
    pre_step_parameter_probes = resolved_pre_step_probes.parameter_probes
    pre_step_gradient_probes = resolved_pre_step_probes.gradient_probes
    pre_step_optimizer_state_probes = resolved_pre_step_probes.optimizer_state_probes
    grad_norm_value = _optional_scalar_value(grad_norm)
    if grad_norm_value is not None and not math.isfinite(grad_norm_value):
        return OptimizerBoundaryCorruptionError(
            trigger_reason="pre_step_non_finite_grad_norm",
            optimizer_step=optimizer_step,
            current_epoch=current_epoch,
            current_train_iteration=current_train_iteration,
            loss_value=_optional_scalar_value(loss),
            main_loss_value=_optional_scalar_value(main_loss),
            sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
            grad_norm_value=grad_norm_value,
            optimizer_step_attempted=False,
            optimizer_step_completed=False,
            targeted_parameter_names=targeted_parameter_names,
            first_non_finite_surface="grad_norm",
            pre_step_parameter_probes=pre_step_parameter_probes,
            pre_step_gradient_probes=pre_step_gradient_probes,
            pre_step_optimizer_state_probes=pre_step_optimizer_state_probes,
            post_step_parameter_probes=None,
            post_step_optimizer_state_probes=None,
            step_forensics=step_forensics,
        )
    first_non_finite_gradient_surface = _first_non_finite_gradient_surface(pre_step_gradient_probes)
    if first_non_finite_gradient_surface is None:
        return None
    return OptimizerBoundaryCorruptionError(
        trigger_reason="pre_step_non_finite_gradients",
        optimizer_step=optimizer_step,
        current_epoch=current_epoch,
        current_train_iteration=current_train_iteration,
        loss_value=_optional_scalar_value(loss),
        main_loss_value=_optional_scalar_value(main_loss),
        sub_talker_loss_value=_optional_scalar_value(sub_talker_loss),
        grad_norm_value=grad_norm_value,
        optimizer_step_attempted=False,
        optimizer_step_completed=False,
        targeted_parameter_names=targeted_parameter_names,
        first_non_finite_surface=first_non_finite_gradient_surface,
        pre_step_parameter_probes=pre_step_parameter_probes,
        pre_step_gradient_probes=pre_step_gradient_probes,
        pre_step_optimizer_state_probes=pre_step_optimizer_state_probes,
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
    pre_step_gradient_probes: dict[str, object] | None,
    pre_step_optimizer_state_probes: dict[str, object] | None,
) -> OptimizerBoundaryCorruptionError | None:
    """Return one post-step failure when parameters or optimizer state are corrupted."""
    targeted_surfaces = _targeted_parameter_surfaces(model)
    targeted_parameter_names = [surface.name for surface in targeted_surfaces]
    post_step_parameter_probes = _parameter_probe_payload(
        targeted_surfaces,
        include_gradients=False,
    )
    post_step_optimizer_state_probes = _optimizer_state_probe_payload(optimizer, targeted_surfaces)
    first_non_finite_parameter_surface = _first_non_finite_parameter_surface(
        post_step_parameter_probes
    )
    if first_non_finite_parameter_surface is not None:
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
            first_non_finite_surface=first_non_finite_parameter_surface,
            pre_step_parameter_probes=pre_step_parameter_probes,
            pre_step_gradient_probes=pre_step_gradient_probes,
            pre_step_optimizer_state_probes=pre_step_optimizer_state_probes,
            post_step_parameter_probes=post_step_parameter_probes,
            post_step_optimizer_state_probes=post_step_optimizer_state_probes,
            step_forensics=step_forensics,
        )
    first_non_finite_optimizer_state_surface = _first_non_finite_optimizer_state_surface(
        post_step_optimizer_state_probes
    )
    if first_non_finite_optimizer_state_surface is None:
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
        first_non_finite_surface=first_non_finite_optimizer_state_surface,
        pre_step_parameter_probes=pre_step_parameter_probes,
        pre_step_gradient_probes=pre_step_gradient_probes,
        pre_step_optimizer_state_probes=pre_step_optimizer_state_probes,
        post_step_parameter_probes=post_step_parameter_probes,
        post_step_optimizer_state_probes=post_step_optimizer_state_probes,
        step_forensics=step_forensics,
    )


def _targeted_parameter_surfaces(model: object) -> list[_TargetedParameterSurface]:
    """Return the targeted text-embedding / text-projection parameter surfaces."""
    text_embedding = resolve_talker_text_embedding_module(model)
    if text_embedding is None:
        return []
    surfaces: list[_TargetedParameterSurface] = []
    surfaces.extend(_module_parameter_surfaces("text_embedding", text_embedding))
    text_projection = resolve_talker_text_projection_module(model)
    surfaces.extend(_module_parameter_surfaces("text_projection", text_projection))
    return surfaces


def _module_parameter_surfaces(
    prefix: str,
    module: object,
) -> list[_TargetedParameterSurface]:
    """Return one deterministic parameter list for one targeted module."""
    if not isinstance(module, torch.nn.Module):
        return []
    surfaces: list[_TargetedParameterSurface] = []
    for name, parameter in module.named_parameters(recurse=True):
        if not isinstance(parameter, torch.nn.Parameter):
            continue
        surface_name = f"{prefix}.{name}"
        surfaces.append(_TargetedParameterSurface(name=surface_name, parameter=parameter))
    return surfaces


def _parameter_probe_payload(
    targeted_surfaces: list[_TargetedParameterSurface],
    *,
    include_gradients: bool,
) -> dict[str, object]:
    """Return parameter or gradient finiteness summaries for targeted params."""
    probes: dict[str, object] = {}
    first_non_finite_surface = None
    for surface in targeted_surfaces:
        tensor = surface.parameter.grad if include_gradients else surface.parameter
        if tensor is None:
            continue
        payload = build_tensor_finiteness_payload(probes=[(surface.name, tensor)])
        tensors_payload = payload.get("tensors")
        if not isinstance(tensors_payload, Mapping):
            continue
        tensor_summary = tensors_payload.get(surface.name)
        if not isinstance(tensor_summary, Mapping):
            continue
        probes[surface.name] = dict(tensor_summary)
        if first_non_finite_surface is None and tensor_summary.get("is_finite") is False:
            suffix = ".grad" if include_gradients else ""
            first_non_finite_surface = f"{surface.name}{suffix}"
    return {
        "probe_kind": "gradients" if include_gradients else "parameters",
        "first_non_finite_surface": first_non_finite_surface,
        "probes": probes,
    }


def _optimizer_state_probe_payload(
    optimizer: torch.optim.Optimizer,
    targeted_surfaces: list[_TargetedParameterSurface],
) -> dict[str, object]:
    """Return optimizer-state finiteness summaries for targeted params."""
    probes: dict[str, object] = {}
    first_non_finite_surface = None
    optimizer_state = _optimizer_state_mapping(optimizer)
    for surface in targeted_surfaces:
        state_payload = optimizer_state.get(surface.parameter)
        if not isinstance(state_payload, Mapping):
            continue
        state_summaries: dict[str, object] = {}
        for state_name, state_value in state_payload.items():
            if not isinstance(state_name, str) or not isinstance(state_value, torch.Tensor):
                continue
            payload = build_tensor_finiteness_payload(
                probes=[(f"{surface.name}.{state_name}", state_value)]
            )
            tensors_payload = payload.get("tensors")
            if not isinstance(tensors_payload, Mapping):
                continue
            tensor_summary = tensors_payload.get(f"{surface.name}.{state_name}")
            if not isinstance(tensor_summary, Mapping):
                continue
            state_summaries[state_name] = dict(tensor_summary)
            if first_non_finite_surface is None and tensor_summary.get("is_finite") is False:
                first_non_finite_surface = f"{surface.name}.{state_name}"
        if state_summaries:
            probes[surface.name] = state_summaries
    return {
        "first_non_finite_surface": first_non_finite_surface,
        "probes": probes,
    }


def _optimizer_state_mapping(optimizer: torch.optim.Optimizer) -> Mapping[object, object]:
    """Return one optimizer-state mapping across wrapped and raw optimizer surfaces."""
    direct_state = getattr(optimizer, "state", None)
    if isinstance(direct_state, Mapping):
        return direct_state
    wrapped_optimizer = getattr(optimizer, "_optimizer", None)
    wrapped_state = getattr(wrapped_optimizer, "state", None)
    if isinstance(wrapped_state, Mapping):
        return wrapped_state
    return {}


def _first_non_finite_gradient_surface(payload: dict[str, object] | None) -> str | None:
    """Return the first non-finite targeted gradient surface from one payload."""
    if not isinstance(payload, Mapping):
        return None
    raw_value = payload.get("first_non_finite_surface")
    return raw_value if isinstance(raw_value, str) else None


def _first_non_finite_parameter_surface(payload: dict[str, object] | None) -> str | None:
    """Return the first non-finite targeted parameter surface from one payload."""
    if not isinstance(payload, Mapping):
        return None
    raw_value = payload.get("first_non_finite_surface")
    return raw_value if isinstance(raw_value, str) else None


def _first_non_finite_optimizer_state_surface(
    payload: dict[str, object] | None,
) -> str | None:
    """Return the first non-finite optimizer-state surface from one payload."""
    if not isinstance(payload, Mapping):
        return None
    raw_value = payload.get("first_non_finite_surface")
    return raw_value if isinstance(raw_value, str) else None


def _optional_scalar_value(value: torch.Tensor | float | None) -> float | None:
    """Return one detached scalar float when possible."""
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().to(device="cpu", dtype=torch.float32).item())
    return float(value)
