"""Probe-capture helpers for Qwen optimizer-boundary diagnostics.

Purpose:
    Own the targeted parameter-surface resolution and compact finiteness probe
    payloads used by the optimizer-boundary guard so the failure-decision
    module stays focused on trigger selection rather than tensor inspection.

Relationships:
    - Imported by `sft_12hz_optimizer_guard.py`.
    - Reuses `sft_12hz_forensics.py` tensor summaries and the shared
      `sft_12hz_talker_runtime.py` resolver contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    build_tensor_finiteness_payload,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    resolve_talker_text_embedding_module,
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
    pre_clip_gradient_probes: dict[str, object]
    optimizer_state_probes: dict[str, object]


def capture_pre_step_optimizer_boundary_probes(
    *,
    model: object,
    optimizer: torch.optim.Optimizer,
) -> OptimizerBoundaryPreStepProbes:
    """Capture the active no-projection training surface before clipping."""
    targeted_surfaces = _targeted_parameter_surfaces(model)
    return OptimizerBoundaryPreStepProbes(
        targeted_parameter_names=[surface.name for surface in targeted_surfaces],
        parameter_probes=_parameter_probe_payload(
            targeted_surfaces,
            include_gradients=False,
        ),
        pre_clip_gradient_probes=_parameter_probe_payload(
            targeted_surfaces,
            include_gradients=True,
        ),
        optimizer_state_probes=_optimizer_state_probe_payload(
            optimizer,
            targeted_surfaces,
        ),
    )


def capture_targeted_gradient_probes(*, model: object) -> dict[str, object]:
    """Capture targeted gradient probes for the active no-projection surface."""
    return _parameter_probe_payload(
        _targeted_parameter_surfaces(model),
        include_gradients=True,
    )


def capture_targeted_parameter_probes(*, model: object) -> dict[str, object]:
    """Capture targeted parameter probes for the active no-projection surface."""
    return _parameter_probe_payload(
        _targeted_parameter_surfaces(model),
        include_gradients=False,
    )


def capture_targeted_optimizer_state_probes(
    *,
    model: object,
    optimizer: torch.optim.Optimizer,
) -> dict[str, object]:
    """Capture targeted optimizer-state probes for the active training surface."""
    return _optimizer_state_probe_payload(
        optimizer,
        _targeted_parameter_surfaces(model),
    )


def first_non_finite_surface(payload: dict[str, object] | None) -> str | None:
    """Return the first non-finite surface string from one probe payload."""
    if not isinstance(payload, Mapping):
        return None
    raw_value = payload.get("first_non_finite_surface")
    return raw_value if isinstance(raw_value, str) else None


def _targeted_parameter_surfaces(model: object) -> list[_TargetedParameterSurface]:
    """Return the targeted no-projection text-embedding parameter surfaces."""
    text_embedding = resolve_talker_text_embedding_module(model)
    if text_embedding is None:
        return []
    return _module_parameter_surfaces("text_embedding", text_embedding)


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
        surfaces.append(
            _TargetedParameterSurface(
                name=f"{prefix}.{name}",
                parameter=parameter,
            )
        )
    return surfaces


def _parameter_probe_payload(
    targeted_surfaces: list[_TargetedParameterSurface],
    *,
    include_gradients: bool,
) -> dict[str, object]:
    """Return parameter or gradient finiteness summaries for targeted params."""
    probes: dict[str, object] = {}
    first_non_finite = None
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
        if first_non_finite is None and tensor_summary.get("is_finite") is False:
            suffix = ".grad" if include_gradients else ""
            first_non_finite = f"{surface.name}{suffix}"
    return {
        "probe_kind": "gradients" if include_gradients else "parameters",
        "first_non_finite_surface": first_non_finite,
        "probes": probes,
    }


def _optimizer_state_probe_payload(
    optimizer: torch.optim.Optimizer,
    targeted_surfaces: list[_TargetedParameterSurface],
) -> dict[str, object]:
    """Return optimizer-state finiteness summaries for targeted params."""
    probes: dict[str, object] = {}
    first_non_finite = None
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
            if first_non_finite is None and tensor_summary.get("is_finite") is False:
                first_non_finite = f"{surface.name}.{state_name}"
        if state_summaries:
            probes[surface.name] = state_summaries
    return {
        "first_non_finite_surface": first_non_finite,
        "probes": probes,
    }


def _optimizer_state_mapping(optimizer: torch.optim.Optimizer) -> Mapping[object, object]:
    """Return one optimizer-state mapping across wrapped and raw optimizers."""
    direct_state = getattr(optimizer, "state", None)
    if isinstance(direct_state, Mapping):
        return direct_state
    wrapped_optimizer = getattr(optimizer, "_optimizer", None)
    wrapped_state = getattr(wrapped_optimizer, "state", None)
    if isinstance(wrapped_state, Mapping):
        return wrapped_state
    return {}
