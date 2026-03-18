"""Focused tests for Story 30 talker-core trace target resolution.

Purpose:
    Lock the deterministic talker-core module target order so T213 can deepen
    the backward trace without drifting away from the intended first-layer and
    per-layer hook families.

Relationships:
    - Exercises `sft_12hz_talker_core_trace.py`.
    - Complements the higher-level lineage probe tests with the smallest local
      signal for talker-core target selection.
"""

from __future__ import annotations

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    iter_talker_core_boundary_trace_targets,
    iter_talker_core_handoff_sub_boundary_trace_targets,
    iter_talker_core_trace_targets,
    talker_core_input_layernorm_internal_trace_names,
    talker_core_trace_prefix,
)


class _FakeTalkerMlp(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gate_proj = torch.nn.Linear(4, 8)
        self.up_proj = torch.nn.Linear(4, 8)
        self.down_proj = torch.nn.Linear(8, 4)


class _FakeDecoderLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.input_layernorm = torch.nn.LayerNorm(4)
        self.self_attn = torch.nn.Linear(4, 4)
        self.post_attention_layernorm = torch.nn.LayerNorm(4)
        self.mlp = _FakeTalkerMlp()


class _FakeTalkerModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList([_FakeDecoderLayer() for _ in range(28)])
        self.norm = torch.nn.LayerNorm(4)


class _FakeTalker(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.model = _FakeTalkerModel()


class _FakeRootModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.talker = _FakeTalker()


def test_iter_talker_core_trace_targets_returns_ordered_layer_and_norm_targets() -> None:
    """The talker-core trace should cover each decoder layer plus the final norm."""
    targets = iter_talker_core_trace_targets(_FakeRootModel())

    assert [target.name for target in targets[:10]] == [
        "talker_core.layer_0.input_layernorm",
        "talker_core.layer_0.self_attn",
        "talker_core.layer_0.post_attention_layernorm",
        "talker_core.layer_0.mlp",
        "talker_core.layer_0.output",
        "talker_core.layer_1.input_layernorm",
        "talker_core.layer_1.self_attn",
        "talker_core.layer_1.post_attention_layernorm",
        "talker_core.layer_1.mlp",
        "talker_core.layer_1.output",
    ]
    assert targets[-1].name == "talker_core.final_norm"
    assert all(target.name.startswith(talker_core_trace_prefix()) for target in targets)


def test_iter_talker_core_boundary_trace_targets_focuses_layer_16_and_15_mlp_boundary() -> None:
    """The T214 boundary trace should target the layer 16/15 seam in fixed order."""
    targets = iter_talker_core_boundary_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_16.input",
        "talker_core.layer_16.input_layernorm",
        "talker_core.layer_16.self_attn",
        "talker_core.layer_16.attention_residual_output",
        "talker_core.layer_16.post_attention_layernorm",
        "talker_core.layer_16.mlp.gate_proj",
        "talker_core.layer_16.mlp.up_proj",
        "talker_core.layer_16.mlp.gated_product",
        "talker_core.layer_16.mlp.down_proj",
        "talker_core.layer_16.output",
        "talker_core.layer_15.input",
        "talker_core.layer_15.input_layernorm",
        "talker_core.layer_15.self_attn",
        "talker_core.layer_15.attention_residual_output",
        "talker_core.layer_15.post_attention_layernorm",
        "talker_core.layer_15.mlp.gate_proj",
        "talker_core.layer_15.mlp.up_proj",
        "talker_core.layer_15.mlp.gated_product",
        "talker_core.layer_15.mlp.down_proj",
        "talker_core.layer_15.output",
    ]


def test_iter_talker_core_handoff_sub_boundary_trace_targets_focuses_t229_chain() -> None:
    """The T229 trace should isolate the narrowed post-T219 layer-16 handoff seam."""
    targets = iter_talker_core_handoff_sub_boundary_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_16.mlp.down_proj",
        "talker_core.layer_16.output",
        "talker_core.layer_16.residual_handoff",
        "talker_core.layer_16.input_layernorm",
    ]


def test_talker_core_input_layernorm_internal_trace_names_lock_t233_chain_order() -> None:
    """The T233 trace should expose the fixed internal RMSNorm arithmetic chain."""
    assert talker_core_input_layernorm_internal_trace_names() == (
        "talker_core.layer_16.input_layernorm.residual_input",
        "talker_core.layer_16.input_layernorm.fp32_input",
        "talker_core.layer_16.input_layernorm.variance",
        "talker_core.layer_16.input_layernorm.normalized_hidden_states",
        "talker_core.layer_16.input_layernorm.output",
    )
