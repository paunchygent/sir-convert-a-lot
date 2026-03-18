"""Bounded talker-core stabilization policy application for Story 31.

Purpose:
    Apply one resolved Story 31 stabilization spec to the live patched Qwen
    talker runtime for a single forward pass, while restoring every patched
    module afterward so experiments remain reversible and composable.

Relationships:
    - Used by `sft_12hz_forward_surfaces.py` to apply an optional bounded
      stabilization policy during the shared talker forward pass.
    - Reuses `sft_12hz_talker_core_stabilization_specs.py` for the variant
      taxonomy and concrete spec resolution.
    - Reuses `sft_12hz_talker_core_stabilization_input_layernorm.py` for the
      reversible layer-16 input-layernorm entry/output wrapper families.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import MethodType
from typing import Callable, Iterator, Sequence

import torch

from scripts.devops.qwen_finetuning_patches import (
    sft_12hz_talker_core_stabilization_input_layernorm as input_layernorm_patch,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization_specs import (
    LAYER16_GATED_FP32,
    LAYER16_GATED_FP32_CLAMP_1E4,
    LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P75,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32,
    TALKER_CORE_STABILIZATION_CHOICES,
    TALKER_CORE_STABILIZATION_OFF,
    LayerOutputAttenuation,
    TalkerCoreStabilizationSpec,
    resolve_talker_core_stabilization_spec,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    resolve_talker_decoder_layer,
)

__all__ = [
    "LAYER16_GATED_FP32",
    "LAYER16_GATED_FP32_CLAMP_1E4",
    "LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5",
    "LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2",
    "LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3",
    "LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P75",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2",
    "LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3",
    "TALKER_CORE_STABILIZATION_CHOICES",
    "TALKER_CORE_STABILIZATION_OFF",
    "LayerInputLayernormEntryRescale",
    "LayerInputLayernormFp32OutputCap",
    "LayerInputLayernormOutputAttenuation",
    "LayerOutputAttenuation",
    "TalkerCoreStabilizationSpec",
    "apply_talker_core_stabilization",
    "resolve_talker_core_stabilization_spec",
]

LayerInputLayernormEntryRescale = input_layernorm_patch.LayerInputLayernormEntryRescale
LayerInputLayernormFp32OutputCap = input_layernorm_patch.LayerInputLayernormFp32OutputCap
LayerInputLayernormOutputAttenuation = input_layernorm_patch.LayerInputLayernormOutputAttenuation


@contextmanager
def apply_talker_core_stabilization(model: object, *, variant: str) -> Iterator[None]:
    """Apply one bounded talker-core stabilization patch for the current forward pass."""
    spec = resolve_talker_core_stabilization_spec(variant)
    if spec.variant == TALKER_CORE_STABILIZATION_OFF:
        yield
        return
    original_mlp_forwards: list[tuple[torch.nn.Module, Callable[..., torch.Tensor], bool]] = []
    original_layer_forwards: list[tuple[torch.nn.Module, Callable[..., object], bool]] = []
    original_input_layernorm_forwards: list[
        tuple[torch.nn.Module, Callable[..., object], bool]
    ] = []
    try:
        for layer_index in spec.target_layers:
            layer = resolve_talker_decoder_layer(model, layer_index)
            mlp = getattr(layer, "mlp", None)
            if not isinstance(mlp, torch.nn.Module):
                raise SystemExit(
                    "Talker-core stabilization could not resolve "
                    f"`layer_{layer_index}.mlp` as a torch module."
                )
            original_mlp_forwards.append((mlp, mlp.forward, "forward" in mlp.__dict__))
            mlp.forward = MethodType(_patched_mlp_forward_factory(spec), mlp)
        for attenuation in spec.layer_output_attenuations:
            layer = resolve_talker_decoder_layer(model, attenuation.layer_index)
            original_layer_forwards.append((layer, layer.forward, "forward" in layer.__dict__))
            layer.forward = MethodType(
                _patched_layer_forward_factory(
                    original_forward=layer.forward,
                    output_scale=attenuation.scale,
                    layer_index=attenuation.layer_index,
                    use_fp32_multiply=attenuation.use_fp32_multiply,
                ),
                layer,
            )
        for patch in _input_layernorm_patch_specs(spec):
            layer = resolve_talker_decoder_layer(model, patch.layer_index)
            input_layernorm = getattr(layer, "input_layernorm", None)
            if not isinstance(input_layernorm, torch.nn.Module):
                raise SystemExit(
                    "Talker-core stabilization could not resolve "
                    f"`layer_{patch.layer_index}.input_layernorm` as a torch module."
                )
            original_input_layernorm_forwards.append(
                (
                    input_layernorm,
                    input_layernorm.forward,
                    "forward" in input_layernorm.__dict__,
                )
            )
            input_layernorm.forward = MethodType(
                input_layernorm_patch.patched_input_layernorm_forward_factory(
                    original_forward=input_layernorm.forward,
                    absmax_cap=patch.absmax_cap,
                    output_scale=patch.output_scale,
                    fp32_output_absmax_cap=patch.fp32_output_absmax_cap,
                    layer_index=patch.layer_index,
                ),
                input_layernorm,
            )
        yield
    finally:
        _restore_instance_forwards(original_input_layernorm_forwards)
        _restore_instance_forwards(original_layer_forwards)
        _restore_instance_forwards(original_mlp_forwards)


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
        output_dtype = up.dtype
        gated_product = gate.float() * up.float() if spec.force_fp32_gated_product else gate * up
        if spec.gated_product_clamp_abs is not None:
            gated_product = gated_product.clamp(
                min=-spec.gated_product_clamp_abs,
                max=spec.gated_product_clamp_abs,
            )
        if spec.gated_product_rescale_absmax is not None:
            gated_product = _rescale_tensor_absmax(
                gated_product,
                absmax_cap=spec.gated_product_rescale_absmax,
            )
        output = down_proj(gated_product.to(dtype=output_dtype))
        if not isinstance(output, torch.Tensor):
            raise SystemExit("Talker-core stabilization down projection did not return a tensor.")
        return output

    return patched_forward


def _patched_layer_forward_factory(
    *,
    original_forward: Callable[..., object],
    output_scale: float,
    layer_index: int,
    use_fp32_multiply: bool,
) -> Callable[[torch.nn.Module, object], object]:
    """Build one wrapper that attenuates the decoder-layer output seam."""

    def patched_forward(self: torch.nn.Module, *args: object, **kwargs: object) -> object:
        outputs = original_forward(*args, **kwargs)
        if not isinstance(outputs, tuple) or len(outputs) == 0:
            raise SystemExit(
                "Talker-core stabilization expected decoder layer "
                f"{layer_index} to return a non-empty tuple."
            )
        hidden_states = outputs[0]
        if not isinstance(hidden_states, torch.Tensor):
            raise SystemExit(
                "Talker-core stabilization expected decoder layer "
                f"{layer_index} output[0] to be a tensor."
            )
        if use_fp32_multiply:
            output_dtype = hidden_states.dtype
            scaled_hidden_states = hidden_states.to(torch.float32) * output_scale
            return (scaled_hidden_states.to(dtype=output_dtype), *outputs[1:])
        return (hidden_states * output_scale, *outputs[1:])

    return patched_forward


def _required_tensor_module(parent: torch.nn.Module, attribute_name: str) -> torch.nn.Module:
    candidate = getattr(parent, attribute_name, None)
    if not isinstance(candidate, torch.nn.Module):
        raise SystemExit(
            "Talker-core stabilization could not resolve "
            f"`{type(parent).__name__}.{attribute_name}` as a torch module."
        )
    return candidate


def _rescale_tensor_absmax(tensor: torch.Tensor, *, absmax_cap: float) -> torch.Tensor:
    current_absmax = torch.amax(tensor.abs())
    if not bool(torch.isfinite(current_absmax).item()):
        return tensor
    current_value = float(current_absmax.detach().item())
    if current_value == 0.0 or current_value <= absmax_cap:
        return tensor
    return tensor * (absmax_cap / current_value)


def _restore_instance_forwards(
    original_forwards: Sequence[tuple[torch.nn.Module, Callable[..., object], bool]],
) -> None:
    for module, original_forward, had_instance_forward in reversed(original_forwards):
        if had_instance_forward:
            module.forward = original_forward
            continue
        delattr(module, "forward")


class _InputLayernormPatchSpec:
    def __init__(
        self,
        *,
        layer_index: int,
        absmax_cap: float | None,
        output_scale: float | None,
        fp32_output_absmax_cap: float | None,
    ) -> None:
        self.layer_index = layer_index
        self.absmax_cap = absmax_cap
        self.output_scale = output_scale
        self.fp32_output_absmax_cap = fp32_output_absmax_cap


def _input_layernorm_patch_specs(
    spec: TalkerCoreStabilizationSpec,
) -> tuple[_InputLayernormPatchSpec, ...]:
    output_scales: dict[int, float | None] = {
        attenuation.layer_index: attenuation.scale
        for attenuation in spec.input_layernorm_output_attenuations
    }
    entry_rescales = {
        rescale.layer_index: rescale.absmax_cap for rescale in spec.input_layernorm_entry_rescales
    }
    fp32_output_caps = {
        cap.layer_index: cap.absmax_cap for cap in spec.input_layernorm_fp32_output_caps
    }
    layer_indices = sorted(set(output_scales) | set(entry_rescales) | set(fp32_output_caps))
    return tuple(
        _InputLayernormPatchSpec(
            layer_index=layer_index,
            absmax_cap=entry_rescales.get(layer_index),
            output_scale=output_scales.get(layer_index),
            fp32_output_absmax_cap=fp32_output_caps.get(layer_index),
        )
        for layer_index in layer_indices
    )
