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


def patched_input_layernorm_forward_factory(
    *,
    original_forward: Callable[..., object],
    layer_index: int,
    absmax_cap: float | None,
    output_scale: float | None,
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


def _rescale_tensor_absmax(tensor: torch.Tensor, *, absmax_cap: float) -> torch.Tensor:
    """Rescale one tensor only when its current abs-max exceeds the requested cap."""
    current_absmax = torch.amax(tensor.abs())
    if not bool(torch.isfinite(current_absmax).item()):
        return tensor
    current_value = float(current_absmax.detach().item())
    if current_value == 0.0 or current_value <= absmax_cap:
        return tensor
    return tensor * (absmax_cap / current_value)
