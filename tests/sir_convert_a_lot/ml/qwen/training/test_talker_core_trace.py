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
    iter_talker_core_trace_targets,
    talker_core_trace_prefix,
)


class _FakeDecoderLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.input_layernorm = torch.nn.LayerNorm(4)
        self.self_attn = torch.nn.Linear(4, 4)
        self.post_attention_layernorm = torch.nn.LayerNorm(4)
        self.mlp = torch.nn.Linear(4, 4)


class _FakeTalkerModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList([_FakeDecoderLayer(), _FakeDecoderLayer()])
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

    assert [target.name for target in targets] == [
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
        "talker_core.final_norm",
    ]
    assert all(target.name.startswith(talker_core_trace_prefix()) for target in targets)
