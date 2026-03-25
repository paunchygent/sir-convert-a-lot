"""Hook helpers for the T243/T244/T246 layer-15 output-path splits.

Purpose:
    Keep the T243 residual-path capture, the T244 pre-output-scale return
    capture, and the T246 fp32-scaled-output capture out of the central
    hook-session module so the Story 31 backward-lineage plumbing stays under
    the hot-path size cap while still exposing the exact upstream-anchored
    talker-decoder seam.

Relationships:
    - Imported by `story30_backward_lineage_hooks.py`.
    - Reuses the official `Qwen3TTSTalkerDecoderLayer.forward` semantics:
      saved residual addend -> MLP return path -> residual sum -> returned
      layer output.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER_OUTPUT_FP32_TRACE_CALLBACK_ATTRIBUTE,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    iter_talker_core_post_t241_layer15_residual_output_trace_targets,
    iter_talker_core_post_t243_layer15_output_return_trace_targets,
    iter_talker_core_post_t245_fp32_scaled_output_trace_targets,
    resolve_talker_decoder_layer,
    talker_core_post_t241_layer15_residual_output_trace_names,
    talker_core_post_t243_layer15_output_return_trace_names,
    talker_core_post_t245_fp32_scaled_output_trace_names,
)


class _TensorUnaryModule(Protocol):
    """Protocol for talker submodules that consume and return one tensor."""

    def __call__(self, hidden_states: torch.Tensor, /) -> torch.Tensor: ...


class _TalkerSelfAttention(Protocol):
    """Protocol for the upstream-aligned talker self-attention call shape."""

    def __call__(
        self,
        *,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        position_ids: torch.LongTensor | None = None,
        past_key_values: tuple[torch.Tensor, ...] | None = None,
        output_attentions: bool | None = False,
        use_cache: bool | None = False,
        cache_position: torch.LongTensor | None = None,
        position_embeddings: tuple[torch.Tensor, torch.Tensor] | None = None,
        **kwargs: object,
    ) -> tuple[torch.Tensor, object]: ...


class _TalkerDecoderLayer(Protocol):
    """Protocol for the official Qwen talker decoder layer structure."""

    input_layernorm: _TensorUnaryModule
    self_attn: _TalkerSelfAttention
    post_attention_layernorm: _TensorUnaryModule
    mlp: _TensorUnaryModule


def build_post_t241_layer15_forward(
    *,
    attach_tensor: Callable[[str, torch.Tensor], None],
    attached_output_name: str,
) -> Callable[..., object]:
    """Build one reversible layer-15 wrapper that exposes one live output seam."""

    def on_forward(
        self_module: _TalkerDecoderLayer,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        position_ids: torch.LongTensor | None = None,
        past_key_values: tuple[torch.Tensor, ...] | None = None,
        output_attentions: bool | None = False,
        use_cache: bool | None = False,
        cache_position: torch.LongTensor | None = None,
        position_embeddings: tuple[torch.Tensor, torch.Tensor] | None = None,
        **kwargs: object,
    ) -> object:
        residual = hidden_states
        hidden_states = self_module.input_layernorm(hidden_states)
        hidden_states, self_attn_weights = self_module.self_attn(
            hidden_states=hidden_states,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            output_attentions=output_attentions,
            use_cache=use_cache,
            cache_position=cache_position,
            position_embeddings=position_embeddings,
            **kwargs,
        )
        hidden_states = residual + hidden_states
        residual = hidden_states
        hidden_states = self_module.post_attention_layernorm(hidden_states)
        hidden_states = self_module.mlp(hidden_states)
        hidden_states = residual + hidden_states
        attach_tensor(attached_output_name, hidden_states)
        outputs: tuple[object, ...] = (hidden_states,)
        if output_attentions:
            outputs += (self_attn_weights,)
        return outputs

    return on_forward


def install_post_t241_layer15_residual_output_trace(
    *,
    model: object,
    attach_tensor: Callable[[str, torch.Tensor], None],
    build_forward_hook: Callable[
        [str, Callable[[object], torch.Tensor | None]], Callable[..., None]
    ],
    build_forward_pre_hook: Callable[
        [str, Callable[[object], torch.Tensor | None]], Callable[..., None]
    ],
    register_handle: Callable[[torch.utils.hooks.RemovableHandle], None],
    patch_module_forward: Callable[[torch.nn.Module, Callable[..., object]], None],
) -> None:
    """Install the T243 residual-path hooks and raw residual-sum wrapper."""
    _residual_input_name, residual_sum_name, _output_name, _ = (
        talker_core_post_t241_layer15_residual_output_trace_names()
    )
    for target in iter_talker_core_post_t241_layer15_residual_output_trace_targets(model):
        handle = (
            target.module.register_forward_hook(
                build_forward_hook(target.name, target.tensor_selector)
            )
            if target.hook_kind == "forward"
            else target.module.register_forward_pre_hook(
                build_forward_pre_hook(target.name, target.tensor_selector)
            )
        )
        register_handle(handle)
    layer_15 = resolve_talker_decoder_layer(model, 15)
    patch_module_forward(
        layer_15,
        build_post_t241_layer15_forward(
            attach_tensor=attach_tensor,
            attached_output_name=residual_sum_name,
        ),
    )


def install_post_t243_layer15_output_return_trace(
    *,
    model: object,
    attach_tensor: Callable[[str, torch.Tensor], None],
    build_forward_hook: Callable[
        [str, Callable[[object], torch.Tensor | None]], Callable[..., None]
    ],
    build_forward_pre_hook: Callable[
        [str, Callable[[object], torch.Tensor | None]], Callable[..., None]
    ],
    register_handle: Callable[[torch.utils.hooks.RemovableHandle], None],
    patch_module_forward: Callable[[torch.nn.Module, Callable[..., object]], None],
) -> None:
    """Install the T244 return-path hooks and raw pre-scale output capture."""
    pre_output_scale_return_name, _output_name, _ = (
        talker_core_post_t243_layer15_output_return_trace_names()
    )
    for target in iter_talker_core_post_t243_layer15_output_return_trace_targets(model):
        handle = (
            target.module.register_forward_hook(
                build_forward_hook(target.name, target.tensor_selector)
            )
            if target.hook_kind == "forward"
            else target.module.register_forward_pre_hook(
                build_forward_pre_hook(target.name, target.tensor_selector)
            )
        )
        register_handle(handle)
    layer_15 = resolve_talker_decoder_layer(model, 15)
    patch_module_forward(
        layer_15,
        build_post_t241_layer15_forward(
            attach_tensor=attach_tensor,
            attached_output_name=pre_output_scale_return_name,
        ),
    )


def install_post_t245_fp32_scaled_output_trace(
    *,
    model: object,
    attach_tensor: Callable[[str, torch.Tensor], None],
    build_forward_hook: Callable[
        [str, Callable[[object], torch.Tensor | None]], Callable[..., None]
    ],
    build_forward_pre_hook: Callable[
        [str, Callable[[object], torch.Tensor | None]], Callable[..., None]
    ],
    register_handle: Callable[[torch.utils.hooks.RemovableHandle], None],
    patch_module_attribute: Callable[[torch.nn.Module, str, object], None],
) -> None:
    """Install the T246 fp32-scaled-output hooks beneath the fixed T245 seam."""
    fp32_scaled_output_name, _output_name, _ = (
        talker_core_post_t245_fp32_scaled_output_trace_names()
    )
    for target in iter_talker_core_post_t245_fp32_scaled_output_trace_targets(model):
        handle = (
            target.module.register_forward_hook(
                build_forward_hook(target.name, target.tensor_selector)
            )
            if target.hook_kind == "forward"
            else target.module.register_forward_pre_hook(
                build_forward_pre_hook(target.name, target.tensor_selector)
            )
        )
        register_handle(handle)
    layer_15 = resolve_talker_decoder_layer(model, 15)
    patch_module_attribute(
        layer_15,
        LAYER_OUTPUT_FP32_TRACE_CALLBACK_ATTRIBUTE,
        lambda tensor: attach_tensor(
            fp32_scaled_output_name,
            tensor,
        ),
    )
