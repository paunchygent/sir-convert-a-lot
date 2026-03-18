"""Bounded talker-core stabilization policies for Story 31 exploration.

Purpose:
    Provide small, explicit forward-path interventions around the late-middle
    talker-core seams so Story 31 can test stabilization ideas quickly without
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
LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5 = "layer16_gated_fp32_rescale_1e3_layer15_out_0p5"
LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25 = "layer16_gated_fp32_rescale_1e2_layer15_out_0p25"
LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5"
)
LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p25_layer15_out_0p5"
)
LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_pre_input_ln_rescale_1e3"
)
LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_pre_input_ln_rescale_1e2"
)
TALKER_CORE_STABILIZATION_CHOICES = (
    TALKER_CORE_STABILIZATION_OFF,
    LAYER16_GATED_FP32,
    LAYER16_GATED_FP32_CLAMP_1E4,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2,
)


@dataclass(frozen=True)
class LayerOutputAttenuation:
    """Resolved output attenuation contract for one decoder-layer boundary."""

    layer_index: int
    scale: float


@dataclass(frozen=True)
class LayerInputLayernormEntryRescale:
    """Resolved rescale contract for one decoder-layer input-layernorm entry."""

    layer_index: int
    absmax_cap: float


@dataclass(frozen=True)
class TalkerCoreStabilizationSpec:
    """Resolved bounded stabilization contract for one exploration variant."""

    variant: str
    target_layers: tuple[int, ...]
    force_fp32_gated_product: bool
    gated_product_clamp_abs: float | None
    gated_product_rescale_absmax: float | None
    layer_output_attenuations: tuple[LayerOutputAttenuation, ...]
    input_layernorm_entry_rescales: tuple[LayerInputLayernormEntryRescale, ...]


def resolve_talker_core_stabilization_spec(variant: str) -> TalkerCoreStabilizationSpec:
    """Resolve one bounded stabilization variant into its concrete contract."""
    if variant == TALKER_CORE_STABILIZATION_OFF:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(),
            force_fp32_gated_product=False,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=None,
            layer_output_attenuations=(),
            input_layernorm_entry_rescales=(),
        )
    if variant == LAYER16_GATED_FP32:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=None,
            layer_output_attenuations=(),
            input_layernorm_entry_rescales=(),
        )
    if variant == LAYER16_GATED_FP32_CLAMP_1E4:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=1.0e4,
            gated_product_rescale_absmax=None,
            layer_output_attenuations=(),
            input_layernorm_entry_rescales=(),
        )
    if variant == LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=1.0e3,
            layer_output_attenuations=(LayerOutputAttenuation(layer_index=15, scale=0.5),),
            input_layernorm_entry_rescales=(),
        )
    if variant == LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=1.0e2,
            layer_output_attenuations=(LayerOutputAttenuation(layer_index=15, scale=0.25),),
            input_layernorm_entry_rescales=(),
        )
    if variant == LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=1.0e3,
            layer_output_attenuations=(
                LayerOutputAttenuation(layer_index=16, scale=0.5),
                LayerOutputAttenuation(layer_index=15, scale=0.5),
            ),
            input_layernorm_entry_rescales=(),
        )
    if variant == LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5:
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=1.0e3,
            layer_output_attenuations=(
                LayerOutputAttenuation(layer_index=16, scale=0.25),
                LayerOutputAttenuation(layer_index=15, scale=0.5),
            ),
            input_layernorm_entry_rescales=(),
        )
    if variant == (
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3
    ):
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=1.0e3,
            layer_output_attenuations=(
                LayerOutputAttenuation(layer_index=16, scale=0.5),
                LayerOutputAttenuation(layer_index=15, scale=0.5),
            ),
            input_layernorm_entry_rescales=(
                LayerInputLayernormEntryRescale(layer_index=16, absmax_cap=1.0e3),
            ),
        )
    if variant == (
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2
    ):
        return TalkerCoreStabilizationSpec(
            variant=variant,
            target_layers=(16,),
            force_fp32_gated_product=True,
            gated_product_clamp_abs=None,
            gated_product_rescale_absmax=1.0e3,
            layer_output_attenuations=(
                LayerOutputAttenuation(layer_index=16, scale=0.5),
                LayerOutputAttenuation(layer_index=15, scale=0.5),
            ),
            input_layernorm_entry_rescales=(
                LayerInputLayernormEntryRescale(layer_index=16, absmax_cap=1.0e2),
            ),
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
            original_forwards.append((mlp, mlp.forward, "forward" in mlp.__dict__))
            mlp.forward = MethodType(_patched_mlp_forward_factory(spec), mlp)
        for attenuation in spec.layer_output_attenuations:
            layer = resolve_talker_decoder_layer(model, attenuation.layer_index)
            original_layer_forwards.append((layer, layer.forward, "forward" in layer.__dict__))
            layer.forward = MethodType(
                _patched_layer_forward_factory(
                    original_forward=layer.forward,
                    output_scale=attenuation.scale,
                    layer_index=attenuation.layer_index,
                ),
                layer,
            )
        for rescale in spec.input_layernorm_entry_rescales:
            layer = resolve_talker_decoder_layer(model, rescale.layer_index)
            input_layernorm = getattr(layer, "input_layernorm", None)
            if not isinstance(input_layernorm, torch.nn.Module):
                raise SystemExit(
                    "Talker-core stabilization could not resolve "
                    f"`layer_{rescale.layer_index}.input_layernorm` as a torch module."
                )
            original_input_layernorm_forwards.append(
                (
                    input_layernorm,
                    input_layernorm.forward,
                    "forward" in input_layernorm.__dict__,
                )
            )
            input_layernorm.forward = MethodType(
                _patched_input_layernorm_forward_factory(
                    original_forward=input_layernorm.forward,
                    absmax_cap=rescale.absmax_cap,
                    layer_index=rescale.layer_index,
                ),
                input_layernorm,
            )
        yield
    finally:
        for module, original_forward, had_instance_forward in reversed(
            original_input_layernorm_forwards
        ):
            if had_instance_forward:
                module.forward = original_forward
                continue
            delattr(module, "forward")
        for module, original_forward, had_instance_forward in reversed(original_layer_forwards):
            if had_instance_forward:
                module.forward = original_forward
                continue
            delattr(module, "forward")
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
        return (hidden_states * output_scale, *outputs[1:])

    return patched_forward


def _patched_input_layernorm_forward_factory(
    *,
    original_forward: Callable[..., object],
    absmax_cap: float,
    layer_index: int,
) -> Callable[[torch.nn.Module, object], object]:
    """Build one wrapper that rescales the residual stream before input layernorm."""

    def patched_forward(self: torch.nn.Module, *args: object, **kwargs: object) -> object:
        if len(args) == 0 or not isinstance(args[0], torch.Tensor):
            raise SystemExit(
                "Talker-core stabilization expected input_layernorm "
                f"{layer_index} to receive a tensor as its first argument."
            )
        rescaled_hidden_states = _rescale_tensor_absmax(args[0], absmax_cap=absmax_cap)
        return original_forward(rescaled_hidden_states, *args[1:], **kwargs)

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


def _required_tensor_module(parent: torch.nn.Module, attribute_name: str) -> torch.nn.Module:
    candidate = getattr(parent, attribute_name, None)
    if not isinstance(candidate, torch.nn.Module):
        raise SystemExit(
            "Talker-core stabilization could not resolve "
            f"`{type(parent).__name__}.{attribute_name}` as a torch module."
        )
    return candidate
