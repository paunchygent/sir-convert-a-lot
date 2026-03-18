"""Talker-core trace targets for Story 30 backward-lineage probes.

Purpose:
    Expose deterministic talker-core hook targets for both the broad
    per-layer trace used by `T213` and the narrower layer `16` / layer `15`
    boundary split used by `T214`, without duplicating upstream Qwen talker
    path assumptions in probe code.

Relationships:
    - Imported by `story30_backward_lineage_hooks.py` to install module hooks
      before the shared Qwen talker forward pass executes.
    - Reuses the live patched talker runtime layout from the actual model
      object rather than restating architecture paths in the probe layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import torch

TalkerTraceHookKind = Literal["forward", "forward_pre"]

_TALKER_CORE_PREFIX = "talker_core."
_BOUNDARY_TARGET_LAYER_INDICES = (16, 15)
_HANDOFF_SUB_BOUNDARY_LAYER_INDEX = 16
_INPUT_LAYERNORM_INTERNAL_LAYER_INDEX = 16
_POST_T234_DISAGREEMENT_LAYER_INDICES = (16, 15)
_POST_T235_ROW_LOCAL_OUTLIER_LAYER_INDICES = (16, 15)


@dataclass(frozen=True)
class TalkerCoreTraceTarget:
    """One named talker-core module target for backward tracing."""

    name: str
    module: torch.nn.Module
    hook_kind: TalkerTraceHookKind
    tensor_selector: Callable[[object], torch.Tensor | None]


def talker_core_trace_prefix() -> str:
    """Return the canonical prefix used for talker-core trace targets."""
    return _TALKER_CORE_PREFIX


def resolve_talker_decoder_layers(model: object) -> tuple[torch.nn.Module, ...]:
    """Return the live talker decoder layers from one patched Qwen model."""
    return _resolve_decoder_layers(_resolve_talker_model(model))


def resolve_talker_decoder_layer(model: object, layer_index: int) -> torch.nn.Module:
    """Return one indexed live talker decoder layer from one patched Qwen model."""
    return _required_layer(resolve_talker_decoder_layers(model), layer_index)


def resolve_talker_input_layernorm(model: object, layer_index: int) -> torch.nn.Module:
    """Return one indexed live decoder-layer input layernorm from one patched model."""
    return _required_module(resolve_talker_decoder_layer(model, layer_index), "input_layernorm")


def talker_core_input_layernorm_internal_trace_names() -> tuple[str, ...]:
    """Return the fixed T233 internal trace chain for `layer_16.input_layernorm`."""
    layer_prefix = (
        f"{_TALKER_CORE_PREFIX}layer_{_INPUT_LAYERNORM_INTERNAL_LAYER_INDEX}.input_layernorm"
    )
    return (
        f"{layer_prefix}.residual_input",
        f"{layer_prefix}.fp32_input",
        f"{layer_prefix}.variance",
        f"{layer_prefix}.normalized_hidden_states",
        f"{layer_prefix}.output",
    )


def talker_core_post_t235_row_local_outlier_trace_names() -> tuple[str, ...]:
    """Return the fixed T236 row-local outlier corridor for `sub_talker_loss`."""
    return (
        f"{_TALKER_CORE_PREFIX}layer_15.output",
        f"{_TALKER_CORE_PREFIX}layer_16.input",
        f"{_TALKER_CORE_PREFIX}layer_16.input_layernorm.output",
    )


def iter_talker_core_trace_targets(model: object) -> tuple[TalkerCoreTraceTarget, ...]:
    """Return the broad per-layer talker-core targets used by `T213`."""
    talker_model = _resolve_talker_model(model)
    layers = resolve_talker_decoder_layers(model)
    targets: list[TalkerCoreTraceTarget] = []
    for layer_index, layer in enumerate(layers):
        layer_prefix = f"{_TALKER_CORE_PREFIX}layer_{layer_index}"
        targets.extend(
            (
                _forward_target(
                    name=f"{layer_prefix}.input_layernorm",
                    module=_required_module(layer, "input_layernorm"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.self_attn",
                    module=_required_module(layer, "self_attn"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.post_attention_layernorm",
                    module=_required_module(layer, "post_attention_layernorm"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.mlp",
                    module=_required_module(layer, "mlp"),
                ),
                _forward_target(name=f"{layer_prefix}.output", module=layer),
            )
        )
    targets.append(
        _forward_target(
            name=f"{_TALKER_CORE_PREFIX}final_norm",
            module=_required_module(talker_model, "norm"),
        )
    )
    return tuple(targets)


def iter_talker_core_boundary_trace_targets(
    model: object,
) -> tuple[TalkerCoreTraceTarget, ...]:
    """Return the finer layer `16` / layer `15` boundary targets used by `T214`."""
    layers = resolve_talker_decoder_layers(model)
    targets: list[TalkerCoreTraceTarget] = []
    for layer_index in _BOUNDARY_TARGET_LAYER_INDICES:
        layer = _required_layer(layers, layer_index)
        layer_prefix = f"{_TALKER_CORE_PREFIX}layer_{layer_index}"
        mlp = _required_module(layer, "mlp")
        targets.extend(
            (
                _forward_pre_target(name=f"{layer_prefix}.input", module=layer),
                _forward_target(
                    name=f"{layer_prefix}.input_layernorm",
                    module=_required_module(layer, "input_layernorm"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.self_attn",
                    module=_required_module(layer, "self_attn"),
                ),
                _forward_pre_target(
                    name=f"{layer_prefix}.attention_residual_output",
                    module=_required_module(layer, "post_attention_layernorm"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.post_attention_layernorm",
                    module=_required_module(layer, "post_attention_layernorm"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.mlp.gate_proj",
                    module=_required_module(mlp, "gate_proj"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.mlp.up_proj",
                    module=_required_module(mlp, "up_proj"),
                ),
                _forward_pre_target(
                    name=f"{layer_prefix}.mlp.gated_product",
                    module=_required_module(mlp, "down_proj"),
                ),
                _forward_target(
                    name=f"{layer_prefix}.mlp.down_proj",
                    module=_required_module(mlp, "down_proj"),
                ),
                _forward_target(name=f"{layer_prefix}.output", module=layer),
            )
        )
    return tuple(targets)


def iter_talker_core_handoff_sub_boundary_trace_targets(
    model: object,
) -> tuple[TalkerCoreTraceTarget, ...]:
    """Return the narrowed post-T219 layer-16 handoff targets used by `T229`."""
    layer = resolve_talker_decoder_layer(model, _HANDOFF_SUB_BOUNDARY_LAYER_INDEX)
    mlp = _required_module(layer, "mlp")
    input_layernorm = _required_module(layer, "input_layernorm")
    layer_prefix = f"{_TALKER_CORE_PREFIX}layer_{_HANDOFF_SUB_BOUNDARY_LAYER_INDEX}"
    return (
        _forward_target(
            name=f"{layer_prefix}.mlp.down_proj",
            module=_required_module(mlp, "down_proj"),
        ),
        _forward_target(name=f"{layer_prefix}.output", module=layer),
        _forward_pre_target(
            name=f"{layer_prefix}.residual_handoff",
            module=input_layernorm,
        ),
        _forward_target(
            name=f"{layer_prefix}.input_layernorm",
            module=input_layernorm,
        ),
    )


def iter_talker_core_post_t234_disagreement_trace_targets(
    model: object,
) -> tuple[TalkerCoreTraceTarget, ...]:
    """Return the narrowed T235 corridor between the T234 disagreement seams."""
    layer_16, layer_15 = (
        resolve_talker_decoder_layer(model, layer_index)
        for layer_index in _POST_T234_DISAGREEMENT_LAYER_INDICES
    )
    return (
        _forward_target(name=f"{_TALKER_CORE_PREFIX}layer_15.output", module=layer_15),
        _forward_pre_target(name=f"{_TALKER_CORE_PREFIX}layer_16.input", module=layer_16),
        _forward_target(
            name=f"{_TALKER_CORE_PREFIX}layer_16.input_layernorm",
            module=_required_module(layer_16, "input_layernorm"),
        ),
    )


def iter_talker_core_post_t235_row_local_outlier_trace_targets(
    model: object,
) -> tuple[TalkerCoreTraceTarget, ...]:
    """Return the narrowed T236 row-local corridor around the line-4 outlier."""
    layer_16, layer_15 = (
        resolve_talker_decoder_layer(model, layer_index)
        for layer_index in _POST_T235_ROW_LOCAL_OUTLIER_LAYER_INDICES
    )
    return (
        _forward_target(name=f"{_TALKER_CORE_PREFIX}layer_15.output", module=layer_15),
        _forward_pre_target(name=f"{_TALKER_CORE_PREFIX}layer_16.input", module=layer_16),
    )


def _forward_target(name: str, module: torch.nn.Module) -> TalkerCoreTraceTarget:
    """Build one forward-output trace target."""
    return TalkerCoreTraceTarget(
        name=name,
        module=module,
        hook_kind="forward",
        tensor_selector=_select_primary_tensor,
    )


def _forward_pre_target(name: str, module: torch.nn.Module) -> TalkerCoreTraceTarget:
    """Build one forward-pre-hook trace target that selects the first tensor input."""
    return TalkerCoreTraceTarget(
        name=name,
        module=module,
        hook_kind="forward_pre",
        tensor_selector=_select_first_input_tensor,
    )


def _resolve_talker_model(model: object) -> torch.nn.Module:
    talker = getattr(model, "talker", None)
    if talker is None:
        raise SystemExit("Backward-lineage probe could not resolve `model.talker`.")
    talker_model = getattr(talker, "model", None)
    if not isinstance(talker_model, torch.nn.Module):
        raise SystemExit("Backward-lineage probe could not resolve `model.talker.model`.")
    return talker_model


def _resolve_decoder_layers(talker_model: torch.nn.Module) -> tuple[torch.nn.Module, ...]:
    layers = getattr(talker_model, "layers", None)
    if not isinstance(layers, torch.nn.ModuleList):
        raise SystemExit("Backward-lineage probe could not resolve `model.talker.model.layers`.")
    return tuple(layer for layer in layers)


def _required_layer(layers: tuple[torch.nn.Module, ...], layer_index: int) -> torch.nn.Module:
    if layer_index < 0 or layer_index >= len(layers):
        raise SystemExit(
            f"Backward-lineage probe could not resolve `model.talker.model.layers[{layer_index}]`."
        )
    return layers[layer_index]


def _required_module(parent: object, attribute_name: str) -> torch.nn.Module:
    candidate = getattr(parent, attribute_name, None)
    if not isinstance(candidate, torch.nn.Module):
        raise SystemExit(
            "Backward-lineage probe could not resolve "
            f"`{type(parent).__name__}.{attribute_name}` as a torch module."
        )
    return candidate


def _select_primary_tensor(value: object) -> torch.Tensor | None:
    if isinstance(value, torch.Tensor):
        return value
    if isinstance(value, tuple) and len(value) > 0:
        first_value = value[0]
        if isinstance(first_value, torch.Tensor):
            return first_value
    if isinstance(value, list) and len(value) > 0:
        first_value = value[0]
        if isinstance(first_value, torch.Tensor):
            return first_value
    return None


def _select_first_input_tensor(value: object) -> torch.Tensor | None:
    if isinstance(value, tuple) and len(value) > 0:
        first_value = value[0]
        if isinstance(first_value, torch.Tensor):
            return first_value
    return None
