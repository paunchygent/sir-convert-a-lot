"""Focused tests for Qwen backward-lineage and fresh-start proof lane talker-core trace target
resolution.

Purpose:
    Lock the deterministic talker-core module target order so per-layer talker-core trace can deepen
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
    iter_talker_core_downstream_convergence_trace_targets,
    iter_talker_core_handoff_sub_boundary_trace_targets,
    iter_talker_core_layer15_output_return_trace_targets,
    iter_talker_core_layer15_output_split_trace_targets,
    iter_talker_core_layer15_residual_output_trace_targets,
    iter_talker_core_post_layer15_output_multiply_fp32_scaled_output_trace_targets,
    iter_talker_core_row_local_outlier_trace_targets,
    iter_talker_core_sub_talker_disagreement_trace_targets,
    iter_talker_core_trace_targets,
    talker_core_downstream_convergence_trace_names,
    talker_core_input_layernorm_internal_trace_names,
    talker_core_layer15_output_return_trace_names,
    talker_core_layer15_output_split_trace_names,
    talker_core_layer15_residual_output_trace_names,
    talker_core_post_layer15_output_multiply_fp32_scaled_output_trace_names,
    talker_core_row_local_outlier_trace_names,
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
    """
    The layer-16/layer-15 boundary trace boundary trace should target the layer 16/15 seam in fixed
    order.
    """
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


def test_iter_talker_core_handoff_sub_boundary_trace_targets_focuses_sub_boundary_chain() -> None:
    """
    The sub-boundary trace should isolate the narrowed post-layer-16 handoff layer-16 handoff seam.
    """
    targets = iter_talker_core_handoff_sub_boundary_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_16.mlp.down_proj",
        "talker_core.layer_16.output",
        "talker_core.layer_16.residual_handoff",
        "talker_core.layer_16.input_layernorm",
    ]


def test_input_layernorm_internal_trace_names_lock_chain_order() -> None:
    """The input-layernorm internal trace should expose the fixed RMSNorm arithmetic chain."""
    assert talker_core_input_layernorm_internal_trace_names() == (
        "talker_core.layer_16.input_layernorm.residual_input",
        "talker_core.layer_16.input_layernorm.fp32_input",
        "talker_core.layer_16.input_layernorm.variance",
        "talker_core.layer_16.input_layernorm.normalized_hidden_states",
        "talker_core.layer_16.input_layernorm.output",
    )


def test_sub_talker_disagreement_trace_targets_focus_corridor() -> None:
    """The sub-talker disagreement trace should isolate the mixed post-input-layernorm output
    disagreement corridor.
    """
    targets = iter_talker_core_sub_talker_disagreement_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
        "talker_core.layer_16.input_layernorm",
    ]


def test_talker_core_row_local_outlier_trace_names_lock_row_local_outlier_order() -> None:
    """The row-local outlier trace should expose the fixed row-local outlier corridor."""
    assert talker_core_row_local_outlier_trace_names() == (
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
        "talker_core.layer_16.input_layernorm.output",
    )


def test_iter_talker_core_row_local_outlier_trace_targets_focuses_row_local_outlier_corridor() -> (
    None
):
    """The row-local outlier trace should isolate the narrowed line-4 outlier corridor."""
    targets = iter_talker_core_row_local_outlier_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    ]


def test_talker_core_downstream_convergence_trace_names_lock_downstream_convergence_order() -> None:
    """The downstream convergence trace should expose the fixed downstream convergence corridor."""
    assert talker_core_downstream_convergence_trace_names() == (
        "talker_core.layer_15.mlp.down_proj",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
        "talker_core.layer_16.input_layernorm.output",
    )


def test_downstream_convergence_trace_targets_focus_corridor() -> None:
    """The downstream convergence trace should isolate the split beneath layer 15 output."""
    targets = iter_talker_core_downstream_convergence_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_15.mlp.down_proj",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    ]


def test_talker_core_layer15_output_split_trace_names_lock_layer15_output_split_order() -> None:
    """The layer-15 split trace should expose the fixed layer-15 split corridor."""
    assert talker_core_layer15_output_split_trace_names() == (
        "talker_core.layer_15.mlp.gated_product",
        "talker_core.layer_15.mlp.down_proj",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    )


def test_iter_talker_core_layer15_output_split_targets_focus_layer15_output_split_corridor() -> (
    None
):
    """The layer-15 split trace should isolate the converged layer-15 residual/output seam."""
    targets = iter_talker_core_layer15_output_split_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_15.mlp.gated_product",
        "talker_core.layer_15.mlp.down_proj",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    ]


def test_talker_core_layer15_residual_output_trace_names_lock_layer15_residual_output_order() -> (
    None
):
    """The residual/output trace should expose the fixed upstream residual/output corridor."""
    assert talker_core_layer15_residual_output_trace_names() == (
        "talker_core.layer_15.output.residual_input",
        "talker_core.layer_15.output.residual_sum",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    )


def test_layer15_residual_output_trace_targets_focus_corridor() -> None:
    """The residual/output trace should isolate the residual-path split beneath layer 15 output."""
    targets = iter_talker_core_layer15_residual_output_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_15.output.residual_input",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    ]


def test_talker_core_layer15_output_return_trace_names_lock_layer15_output_return_order() -> None:
    """The output-return trace should expose the fixed pre-scale versus emitted return corridor."""
    assert talker_core_layer15_output_return_trace_names() == (
        "talker_core.layer_15.output.pre_output_scale_return",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    )


def test_iter_talker_core_layer15_output_return_targets_focus_layer15_output_return_corridor() -> (
    None
):
    """
    The output-return trace should isolate the post-sum return-path split beneath layer 15 output.
    """
    targets = iter_talker_core_layer15_output_return_trace_targets(_FakeRootModel())

    assert [target.name for target in targets] == [
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    ]


def test_fp32_scaled_layer15_output_trace_names_lock_order() -> None:
    """The fp32-scaled output trace should expose the fp32-scaled versus emitted output corridor."""
    assert talker_core_post_layer15_output_multiply_fp32_scaled_output_trace_names() == (
        "talker_core.layer_15.output.fp32_scaled_output",
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    )


def test_fp32_scaled_layer15_output_trace_targets_focus_corridor() -> None:
    """The fp32-scaled output trace should isolate the post-multiply fp32-scaled output seam."""
    targets = iter_talker_core_post_layer15_output_multiply_fp32_scaled_output_trace_targets(
        _FakeRootModel()
    )

    assert [target.name for target in targets] == [
        "talker_core.layer_15.output",
        "talker_core.layer_16.input",
    ]
