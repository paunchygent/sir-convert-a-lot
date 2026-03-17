"""Talker-core tracing targets for Story 30 backward-lineage probes.

Purpose:
    Expose a deterministic, architecture-grounded list of talker-core modules
    whose forward outputs should be retained for backward finiteness tracing
    between final hidden states and input embeddings.

Relationships:
    - Imported by `story30_backward_lineage_hooks.py` to install module output
      hooks before the shared Qwen talker forward pass executes.
    - Reuses the live patched talker runtime layout instead of duplicating
      model-path assumptions in probe code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import torch

_TALKER_CORE_PREFIX = "talker_core."


@dataclass(frozen=True)
class TalkerCoreTraceTarget:
    """One named talker-core module output target for backward tracing."""

    name: str
    module: torch.nn.Module
    output_selector: Callable[[object], torch.Tensor | None]


def talker_core_trace_prefix() -> str:
    """Return the canonical prefix used for talker-core trace targets."""
    return _TALKER_CORE_PREFIX


def iter_talker_core_trace_targets(model: object) -> tuple[TalkerCoreTraceTarget, ...]:
    """Return the deterministic talker-core targets for one Qwen talker model."""
    talker_model = _resolve_talker_model(model)
    layers = _resolve_decoder_layers(talker_model)
    targets: list[TalkerCoreTraceTarget] = []
    for layer_index, layer in enumerate(layers):
        layer_prefix = f"{_TALKER_CORE_PREFIX}layer_{layer_index}"
        targets.extend(
            (
                TalkerCoreTraceTarget(
                    name=f"{layer_prefix}.input_layernorm",
                    module=_required_module(layer, "input_layernorm"),
                    output_selector=_select_primary_tensor,
                ),
                TalkerCoreTraceTarget(
                    name=f"{layer_prefix}.self_attn",
                    module=_required_module(layer, "self_attn"),
                    output_selector=_select_primary_tensor,
                ),
                TalkerCoreTraceTarget(
                    name=f"{layer_prefix}.post_attention_layernorm",
                    module=_required_module(layer, "post_attention_layernorm"),
                    output_selector=_select_primary_tensor,
                ),
                TalkerCoreTraceTarget(
                    name=f"{layer_prefix}.mlp",
                    module=_required_module(layer, "mlp"),
                    output_selector=_select_primary_tensor,
                ),
                TalkerCoreTraceTarget(
                    name=f"{layer_prefix}.output",
                    module=layer,
                    output_selector=_select_primary_tensor,
                ),
            )
        )
    targets.append(
        TalkerCoreTraceTarget(
            name=f"{_TALKER_CORE_PREFIX}final_norm",
            module=_required_module(talker_model, "norm"),
            output_selector=_select_primary_tensor,
        )
    )
    return tuple(targets)


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
