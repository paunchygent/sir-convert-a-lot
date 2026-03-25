"""Focused tests for Story 30 backward-lineage hook session plumbing.

Purpose:
    Lock the reversible T233 input-layernorm wrapper lifecycle and the exact
    internal gradient-observation chain without depending on the broader
    backward-lineage probe runtime.

Relationships:
    - Exercises `story30_backward_lineage_hooks.py` directly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical T233 trace names.
"""

from __future__ import annotations

from types import MethodType

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER_OUTPUT_FP32_TRACE_CALLBACK_ATTRIBUTE,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    resolve_talker_input_layernorm,
    talker_core_input_layernorm_internal_trace_names,
    talker_core_post_t241_layer15_residual_output_trace_names,
    talker_core_post_t243_layer15_output_return_trace_names,
    talker_core_post_t245_fp32_scaled_output_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE,
    TALKER_CORE_POST_T241_LAYER15_RESIDUAL_OUTPUT_HOOK_PROFILE,
    TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
    TALKER_CORE_POST_T245_FP32_SCALED_OUTPUT_HOOK_PROFILE,
    build_gradient_hook_session,
)


class _FakeRmsNorm(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.ones(4))
        self.variance_epsilon = 1e-6

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        input_dtype = hidden_states.dtype
        hidden_states = hidden_states.to(torch.float32)
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.variance_epsilon)
        return self.weight * hidden_states.to(input_dtype)


class _FakeDecoderLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.input_layernorm = _FakeRmsNorm()


class _FakeTalkerModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList([_FakeDecoderLayer() for _ in range(17)])


class _FakeTalker(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.model = _FakeTalkerModel()


class _FakeRootModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.talker = _FakeTalker()


class _FakeTalkerMlp(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(4, 4, bias=False)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return torch.nn.functional.linear(hidden_states, self.linear.weight)


class _FakeTalkerAttention(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(4, 4, bias=False)

    def forward(
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
    ) -> tuple[torch.Tensor, None]:
        del (
            attention_mask,
            position_ids,
            past_key_values,
            output_attentions,
            use_cache,
            cache_position,
            position_embeddings,
            kwargs,
        )
        return torch.nn.functional.linear(hidden_states, self.linear.weight), None


class _FakeTalkerDecoderLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.input_layernorm = _FakeRmsNorm()
        self.self_attn = _FakeTalkerAttention()
        self.post_attention_layernorm = _FakeRmsNorm()
        self.mlp = _FakeTalkerMlp()

    def forward(self, hidden_states: torch.Tensor) -> tuple[torch.Tensor]:
        residual = hidden_states
        hidden_states = self.input_layernorm(hidden_states)
        hidden_states, _ = self.self_attn(hidden_states=hidden_states)
        hidden_states = residual + hidden_states
        residual = hidden_states
        hidden_states = self.post_attention_layernorm(hidden_states)
        hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states
        return (hidden_states,)


class _FakeResidualTalkerModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList([_FakeTalkerDecoderLayer() for _ in range(17)])


class _FakeResidualTalker(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.model = _FakeResidualTalkerModel()


class _FakeResidualRootModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.talker = _FakeResidualTalker()


def test_t233_hook_session_wraps_input_layernorm_and_restores_forward() -> None:
    """The T233 session should capture the full internal chain and restore the module."""
    model = _FakeRootModel()
    input_layernorm = resolve_talker_input_layernorm(model, layer_index=16)
    session = build_gradient_hook_session(
        hook_profile=TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE
    )

    session.install_pre_forward_hooks(model=model)
    assert "forward" in input_layernorm.__dict__

    hidden_states = torch.randn(2, 4, requires_grad=True)
    output = input_layernorm(hidden_states)
    output.sum().backward()

    assert {item.tensor_name for item in session.ordered_observations()} == set(
        talker_core_input_layernorm_internal_trace_names()
    )
    assert session.first_non_finite_observation().tensor_name is None

    session.close()
    assert "forward" not in input_layernorm.__dict__


def test_t243_hook_session_wraps_layer15_mlp_and_captures_residual_path() -> None:
    """The T243 session should capture residual input, sum, output, and layer-16 handoff."""
    model = _FakeResidualRootModel()
    layer_15 = model.talker.model.layers[15]
    layer_16 = model.talker.model.layers[16]
    session = build_gradient_hook_session(
        hook_profile=TALKER_CORE_POST_T241_LAYER15_RESIDUAL_OUTPUT_HOOK_PROFILE
    )

    session.install_pre_forward_hooks(model=model)
    assert "forward" in layer_15.__dict__

    hidden_states = torch.randn(2, 4, requires_grad=True)
    layer_15_output = layer_15(hidden_states)[0]
    layer_16_output = layer_16(layer_15_output)[0]
    layer_16_output.sum().backward()

    assert {item.tensor_name for item in session.ordered_observations()} == set(
        talker_core_post_t241_layer15_residual_output_trace_names()
    )
    assert session.first_non_finite_observation().tensor_name is None

    session.close()
    assert "forward" not in layer_15.__dict__


def test_t244_hook_session_captures_pre_scale_and_emitted_output() -> None:
    """The T244 session should isolate the winner-specific layer-15 return split."""
    model = _FakeResidualRootModel()
    layer_15 = model.talker.model.layers[15]
    layer_16 = model.talker.model.layers[16]
    session = build_gradient_hook_session(
        hook_profile=TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE
    )

    session.install_pre_forward_hooks(model=model)
    original_forward = layer_15.forward

    def scaled_forward(
        self: torch.nn.Module,
        hidden_states: torch.Tensor,
    ) -> tuple[torch.Tensor]:
        del self
        outputs = original_forward(hidden_states)
        return (outputs[0] * 0.5,)

    layer_15.forward = MethodType(scaled_forward, layer_15)

    hidden_states = torch.randn(2, 4, requires_grad=True)
    layer_15_output = layer_15(hidden_states)[0]
    layer_16_output = layer_16(layer_15_output)[0]
    layer_16_output.sum().backward()

    assert {item.tensor_name for item in session.ordered_observations()} == set(
        talker_core_post_t243_layer15_output_return_trace_names()
    )
    assert session.first_non_finite_observation().tensor_name is None

    session.close()
    assert "forward" not in layer_15.__dict__


def test_t246_hook_session_captures_fp32_scaled_and_emitted_output() -> None:
    """The T246 session should isolate the fp32-scaled versus emitted output seam."""
    model = _FakeResidualRootModel()
    layer_15 = model.talker.model.layers[15]
    layer_16 = model.talker.model.layers[16]
    session = build_gradient_hook_session(
        hook_profile=TALKER_CORE_POST_T245_FP32_SCALED_OUTPUT_HOOK_PROFILE
    )

    session.install_pre_forward_hooks(model=model)
    original_forward = layer_15.forward

    def fp32_scaled_forward(
        self: torch.nn.Module,
        hidden_states: torch.Tensor,
    ) -> tuple[torch.Tensor]:
        del self
        outputs = original_forward(hidden_states)
        scaled_output = outputs[0].to(torch.float32) * 0.5
        callback = getattr(
            layer_15,
            LAYER_OUTPUT_FP32_TRACE_CALLBACK_ATTRIBUTE,
            None,
        )
        if callable(callback):
            callback(scaled_output)
        return (scaled_output.to(dtype=outputs[0].dtype),)

    layer_15.forward = MethodType(fp32_scaled_forward, layer_15)

    hidden_states = torch.randn(2, 4, requires_grad=True)
    layer_15_output = layer_15(hidden_states)[0]
    layer_16_output = layer_16(layer_15_output)[0]
    layer_16_output.sum().backward()

    assert {item.tensor_name for item in session.ordered_observations()} == set(
        talker_core_post_t245_fp32_scaled_output_trace_names()
    )
    assert session.first_non_finite_observation().tensor_name is None

    session.close()
    assert not hasattr(layer_15, LAYER_OUTPUT_FP32_TRACE_CALLBACK_ATTRIBUTE)
