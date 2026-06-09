"""Resolved Qwen stability lab talker-core stabilization specs and variant constants.

Purpose:
    Keep the bounded variant taxonomy and concrete spec resolution separate
    from the patch-application logic so the hot-path runtime module stays
    within the stricter architecture cap.

Relationships:
    - Imported by `sft_12hz_talker_core_stabilization.py`.
    - Reuses the input-layernorm helper contracts for the input-layernorm family and input-layernorm
      output
      families.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.devops.qwen_finetuning_patches import (
    sft_12hz_talker_core_stabilization_input_layernorm as input_layernorm_patch,
)

LayerInputLayernormEntryRescale = input_layernorm_patch.LayerInputLayernormEntryRescale
LayerInputLayernormFp32OutputCap = input_layernorm_patch.LayerInputLayernormFp32OutputCap
LayerInputLayernormOutputAttenuation = input_layernorm_patch.LayerInputLayernormOutputAttenuation

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
LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P75 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75"
)
LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5"
)
LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3"
)
LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e2"
)
LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32 = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3_"
    "layer15_output_scale_fp32"
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
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P75,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32,
)


@dataclass(frozen=True)
class LayerOutputAttenuation:
    """Resolved output attenuation contract for one decoder-layer boundary."""

    layer_index: int
    scale: float
    use_fp32_multiply: bool = False


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
    input_layernorm_output_attenuations: tuple[LayerInputLayernormOutputAttenuation, ...]
    input_layernorm_fp32_output_caps: tuple[LayerInputLayernormFp32OutputCap, ...]


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
            input_layernorm_output_attenuations=(),
            input_layernorm_fp32_output_caps=(),
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
            input_layernorm_output_attenuations=(),
            input_layernorm_fp32_output_caps=(),
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
            input_layernorm_output_attenuations=(),
            input_layernorm_fp32_output_caps=(),
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
            input_layernorm_output_attenuations=(),
            input_layernorm_fp32_output_caps=(),
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
            input_layernorm_output_attenuations=(),
            input_layernorm_fp32_output_caps=(),
        )
    if variant == LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5:
        return _layer16_handoff_spec(variant=variant)
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
            input_layernorm_output_attenuations=(),
            input_layernorm_fp32_output_caps=(),
        )
    if variant == (
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3
    ):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_entry_rescales=(
                LayerInputLayernormEntryRescale(layer_index=16, absmax_cap=1.0e3),
            ),
        )
    if variant == (
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2
    ):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_entry_rescales=(
                LayerInputLayernormEntryRescale(layer_index=16, absmax_cap=1.0e2),
            ),
        )
    if variant == (
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P75
    ):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_output_attenuations=(
                LayerInputLayernormOutputAttenuation(layer_index=16, scale=0.75),
            ),
        )
    if variant == (
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5
    ):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_output_attenuations=(
                LayerInputLayernormOutputAttenuation(layer_index=16, scale=0.5),
            ),
        )
    if variant == (LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_output_attenuations=(
                LayerInputLayernormOutputAttenuation(layer_index=16, scale=0.5),
            ),
            input_layernorm_fp32_output_caps=(
                LayerInputLayernormFp32OutputCap(layer_index=16, absmax_cap=1.0e3),
            ),
        )
    if variant == (LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_output_attenuations=(
                LayerInputLayernormOutputAttenuation(layer_index=16, scale=0.5),
            ),
            input_layernorm_fp32_output_caps=(
                LayerInputLayernormFp32OutputCap(layer_index=16, absmax_cap=1.0e2),
            ),
        )
    if variant == (LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32):
        return _layer16_handoff_spec(
            variant=variant,
            input_layernorm_output_attenuations=(
                LayerInputLayernormOutputAttenuation(layer_index=16, scale=0.5),
            ),
            input_layernorm_fp32_output_caps=(
                LayerInputLayernormFp32OutputCap(layer_index=16, absmax_cap=1.0e3),
            ),
            layer15_output_use_fp32_multiply=True,
        )
    raise SystemExit(f"Unsupported talker-core stabilization variant `{variant}`.")


def _layer16_handoff_spec(
    *,
    variant: str,
    input_layernorm_entry_rescales: tuple[LayerInputLayernormEntryRescale, ...] = (),
    input_layernorm_output_attenuations: tuple[LayerInputLayernormOutputAttenuation, ...] = (),
    input_layernorm_fp32_output_caps: tuple[LayerInputLayernormFp32OutputCap, ...] = (),
    layer15_output_use_fp32_multiply: bool = False,
) -> TalkerCoreStabilizationSpec:
    return TalkerCoreStabilizationSpec(
        variant=variant,
        target_layers=(16,),
        force_fp32_gated_product=True,
        gated_product_clamp_abs=None,
        gated_product_rescale_absmax=1.0e3,
        layer_output_attenuations=(
            LayerOutputAttenuation(layer_index=16, scale=0.5),
            LayerOutputAttenuation(
                layer_index=15,
                scale=0.5,
                use_fp32_multiply=layer15_output_use_fp32_multiply,
            ),
        ),
        input_layernorm_entry_rescales=input_layernorm_entry_rescales,
        input_layernorm_output_attenuations=input_layernorm_output_attenuations,
        input_layernorm_fp32_output_caps=input_layernorm_fp32_output_caps,
    )
