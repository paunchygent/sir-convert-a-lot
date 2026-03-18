"""Input-layernorm stabilization helpers for bounded Story 31 experiments.

Purpose:
    Keep the layer-16 input-layernorm entry/output wrapper contracts small and
    reusable so the main talker-core stabilization surface can add bounded
    families without exceeding the hot-path module cap.

Relationships:
    - Imported by `sft_12hz_talker_core_stabilization.py`.
    - Reuses the same reversible MethodType patching pattern as the broader
      Story 31 stabilization lane.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import torch


@dataclass(frozen=True)
class LayerInputLayernormEntryRescale:
    """Resolved rescale contract for one decoder-layer input-layernorm entry."""

    layer_index: int
    absmax_cap: float


@dataclass(frozen=True)
class LayerInputLayernormOutputAttenuation:
    """Resolved attenuation contract for one decoder-layer input-layernorm output."""

    layer_index: int
    scale: float


@dataclass(frozen=True)
class LayerInputLayernormFp32OutputCap:
    """Resolved fp32 output-cap contract for one decoder-layer input-layernorm."""

    layer_index: int
    absmax_cap: float


def patched_input_layernorm_forward_factory(
    *,
    original_forward: Callable[..., object],
    layer_index: int,
    absmax_cap: float | None,
    output_scale: float | None,
    fp32_output_absmax_cap: float | None,
) -> Callable[[torch.nn.Module, object], object]:
    """Build one wrapper that optionally rescales the entry and output seams."""

    def patched_forward(self: torch.nn.Module, *args: object, **kwargs: object) -> object:
        if len(args) == 0 or not isinstance(args[0], torch.Tensor):
            raise SystemExit(
                "Talker-core stabilization expected input_layernorm "
                f"{layer_index} to receive a tensor as its first argument."
            )
        hidden_states = args[0]
        if absmax_cap is not None:
            hidden_states = _rescale_tensor_absmax(hidden_states, absmax_cap=absmax_cap)
        if fp32_output_absmax_cap is not None:
            return _patched_input_layernorm_fp32_output_forward(
                module=self,
                hidden_states=hidden_states,
                kwargs=kwargs,
                output_scale=output_scale,
                absmax_cap=fp32_output_absmax_cap,
                layer_index=layer_index,
            )
        outputs = original_forward(hidden_states, *args[1:], **kwargs)
        if output_scale is None:
            return outputs
        if not isinstance(outputs, torch.Tensor):
            raise SystemExit(
                "Talker-core stabilization expected input_layernorm "
                f"{layer_index} to return a tensor before output attenuation."
            )
        return outputs * output_scale

    return patched_forward


def _patched_input_layernorm_fp32_output_forward(
    *,
    module: torch.nn.Module,
    hidden_states: torch.Tensor,
    kwargs: dict[str, object],
    output_scale: float | None,
    absmax_cap: float,
    layer_index: int,
) -> torch.Tensor:
    """Rebuild one RMSNorm output path and cap its weighted fp32 seam."""
    if kwargs:
        raise SystemExit(
            "Talker-core stabilization expected input_layernorm "
            f"{layer_index} to receive no keyword arguments for fp32 output capping."
        )
    input_dtype = hidden_states.dtype
    fp32_input = hidden_states.to(torch.float32)
    variance = fp32_input.pow(2).mean(-1, keepdim=True)
    variance_epsilon = _required_variance_epsilon(module, layer_index=layer_index)
    normalized_hidden_states = fp32_input * torch.rsqrt(variance + variance_epsilon)
    weight = _required_layernorm_weight(module, layer_index=layer_index).to(torch.float32)
    weighted_fp32_output = weight * normalized_hidden_states
    weighted_fp32_output = _rescale_tensor_absmax(weighted_fp32_output, absmax_cap=absmax_cap)
    output = weighted_fp32_output.to(input_dtype)
    if output_scale is None:
        return output
    return output * output_scale


def _rescale_tensor_absmax(tensor: torch.Tensor, *, absmax_cap: float) -> torch.Tensor:
    """Rescale one tensor only when its current abs-max exceeds the requested cap."""
    current_absmax = torch.amax(tensor.abs())
    if not bool(torch.isfinite(current_absmax).item()):
        return tensor
    current_value = float(current_absmax.detach().item())
    if current_value == 0.0 or current_value <= absmax_cap:
        return tensor
    return tensor * (absmax_cap / current_value)


def _required_layernorm_weight(module: torch.nn.Module, *, layer_index: int) -> torch.Tensor:
    weight = getattr(module, "weight", None)
    if not isinstance(weight, torch.Tensor):
        raise SystemExit(
            "Talker-core stabilization could not resolve "
            f"`layer_{layer_index}.input_layernorm.weight` as a tensor."
        )
    return weight


def _required_variance_epsilon(module: torch.nn.Module, *, layer_index: int) -> float:
    variance_epsilon = getattr(module, "variance_epsilon", None)
    if not isinstance(variance_epsilon, (float, int)):
        raise SystemExit(
            "Talker-core stabilization expected "
            f"`layer_{layer_index}.input_layernorm.variance_epsilon` as a scalar."
        )
    return float(variance_epsilon)
