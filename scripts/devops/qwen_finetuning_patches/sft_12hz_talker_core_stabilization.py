"""Bounded talker-core stabilization policies for Story 31 exploration.

Purpose:
    Provide small, explicit forward-path interventions around the late-middle
    talker-core MLP seam so Story 31 can test stability ideas quickly without
    rebuilding the entire training/runtime stack for each hypothesis.

Relationships:
    - Used by `sft_12hz_forward_surfaces.py` to apply an optional bounded
      stabilization policy during the shared talker forward pass.
    - Reuses `sft_12hz_talker_core_trace.py` to resolve live decoder layers
      from the patched Qwen runtime instead of restating layer paths.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import MethodType
from typing import Callable, Iterator

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    resolve_talker_decoder_layer,
)

TALKER_CORE_STABILIZATION_OFF = "off"
LAYER16_GATED_FP32 = "layer16_gated_fp32"
LAYER16_GATED_FP32_CLAMP_1E4 = "layer16_gated_fp32_clamp_1e4"
TALKER_CORE_STABILIZATION_CHOICES = (
    TALKER_CORE_STABILIZATION_OFF,
    LAYER16_GATED_FP32,
    LAYER16_GATED_FP32_CLAMP_1E4,
)


@dataclass(frozen=True)
class TalkerCoreStabilizationSpec:
    """Resolved bounded stabilization contract for one exploration variant."""

    variant: str
    target_layers: tuple[int, ...]
    force_fp32_gated_product: bool
    gated_product_clamp_abs: float | None


def resolve_talker_core_stabilization_spec(variant: str) -> TalkerCoreStabilizationSpec:
    """Resolve one bounded stabilization variant into its concrete contract."""
    if variant == TALKER_CORE_STABILIZATION_OFF:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(),
            force_fp32_gated_product=False,
            gated_product_clamp_abs=None,
        )
    if variant == LAYER16_GATED_FP32:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
        )
    if variant == LAYER16_GATED_FP32_CLAMP_1E4:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=1.0e4,
        )
    raise SystemExit(f"Unsupported talker-core stabilization variant `{variant}`.")


@contextmanager
def apply_talker_core_stabilization(model: object, *, variant: str) -> Iterator[None]:
    """Apply one bounded talker-core stabilization patch for the current forward pass."""
    spec = resolve_talker_core_stabilization_spec(variant)
    if spec.variant == TALKER_CORE_STABILIZATION_OFF:
        yield
        return
    original_forwards: list[tuple[torch.nn.Module, Callable[..., torch.Tensor], bool]] = []
    try:
        for layer_index in spec.target_layers:
            layer = resolve_talker_decoder_layer(model, layer_index)
            mlp = getattr(layer, "mlp", None)
            if not isinstance(mlp, torch.nn.Module):
                raise SystemExit(
                    "Talker-core stabilization could not resolve "
                    f"`layer_{layer_index}.mlp` as a torch module."
                )
            original_forwards.append((mlp, mlp.forward, "forward" in mlp.__dict__))
            mlp.forward = MethodType(_patched_mlp_forward_factory(spec), mlp)
        yield
    finally:
        for module, original_forward, had_instance_forward in reversed(original_forwards):
            if had_instance_forward:
                module.forward = original_forward
                continue
            delattr(module, "forward")


def _patched_mlp_forward_factory(
    spec: TalkerCoreStabilizationSpec,
) -> Callable[[torch.nn.Module, torch.Tensor], torch.Tensor]:
    """Build one patched MLP forward method for the current stabilization spec."""

    def patched_forward(self: torch.nn.Module, x: torch.Tensor) -> torch.Tensor:
        act_fn = _required_tensor_module(self, "act_fn")
        gate_proj = _required_tensor_module(self, "gate_proj")
        up_proj = _required_tensor_module(self, "up_proj")
        down_proj = _required_tensor_module(self, "down_proj")
        gate = act_fn(gate_proj(x))
        up = up_proj(x)
        gated_product = gate.float() * up.float() if spec.force_fp32_gated_product else gate * up
        if spec.gated_product_clamp_abs is not None:
            gated_product = gated_product.clamp(
                min=-spec.gated_product_clamp_abs,
                max=spec.gated_product_clamp_abs,
            )
        output = down_proj(gated_product.to(dtype=up.dtype))
        if not isinstance(output, torch.Tensor):
            raise SystemExit("Talker-core stabilization down projection did not return a tensor.")
        return output

    return patched_forward


def _required_tensor_module(parent: torch.nn.Module, attribute_name: str) -> torch.nn.Module:
    candidate = getattr(parent, attribute_name, None)
    if not isinstance(candidate, torch.nn.Module):
        raise SystemExit(
            "Talker-core stabilization could not resolve "
            f"`{type(parent).__name__}.{attribute_name}` as a torch module."
        )
    return candidate
