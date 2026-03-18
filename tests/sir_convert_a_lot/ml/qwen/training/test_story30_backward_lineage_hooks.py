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

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    resolve_talker_input_layernorm,
    talker_core_input_layernorm_internal_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE,
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
