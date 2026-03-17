"""Tests for bounded Story 31 talker-core stabilization policies.

Purpose:
    Prove the first bounded stabilization surface patches only the intended
    talker-core seam and restores the original runtime afterward so the Story
    31 exploration lane can iterate quickly without leaving global mutations
    behind.

Relationships:
    - Exercises `sft_12hz_talker_core_stabilization.py`.
    - Reuses the live talker-layer resolver contract from
      `sft_12hz_talker_core_trace.py`.
"""

from __future__ import annotations

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_GATED_FP32,
    LAYER16_GATED_FP32_CLAMP_1E4,
    LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5,
    TALKER_CORE_STABILIZATION_OFF,
    LayerOutputAttenuation,
    apply_talker_core_stabilization,
    resolve_talker_core_stabilization_spec,
)


def test_resolve_talker_core_stabilization_spec_supports_first_story31_variants() -> None:
    """The Story 31 bounded variants should resolve to a stable concrete contract."""
    off_spec = resolve_talker_core_stabilization_spec(TALKER_CORE_STABILIZATION_OFF)
    fp32_spec = resolve_talker_core_stabilization_spec(LAYER16_GATED_FP32)
    clamp_spec = resolve_talker_core_stabilization_spec(LAYER16_GATED_FP32_CLAMP_1E4)
    attenuate_spec = resolve_talker_core_stabilization_spec(
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5
    )
    stronger_attenuate_spec = resolve_talker_core_stabilization_spec(
        LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25
    )
    handoff_spec = resolve_talker_core_stabilization_spec(
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5
    )
    stronger_handoff_spec = resolve_talker_core_stabilization_spec(
        LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5
    )

    assert off_spec.target_layers == ()
    assert off_spec.force_fp32_gated_product is False
    assert fp32_spec.target_layers == (16,)
    assert fp32_spec.force_fp32_gated_product is True
    assert fp32_spec.gated_product_clamp_abs is None
    assert fp32_spec.gated_product_rescale_absmax is None
    assert clamp_spec.gated_product_clamp_abs == 1.0e4
    assert attenuate_spec.gated_product_rescale_absmax == 1.0e3
    assert attenuate_spec.layer_output_attenuations[0].layer_index == 15
    assert attenuate_spec.layer_output_attenuations[0].scale == 0.5
    assert stronger_attenuate_spec.gated_product_rescale_absmax == 1.0e2
    assert stronger_attenuate_spec.layer_output_attenuations[0].scale == 0.25
    assert handoff_spec.layer_output_attenuations == (
        LayerOutputAttenuation(layer_index=16, scale=0.5),
        LayerOutputAttenuation(layer_index=15, scale=0.5),
    )
    assert stronger_handoff_spec.layer_output_attenuations == (
        LayerOutputAttenuation(layer_index=16, scale=0.25),
        LayerOutputAttenuation(layer_index=15, scale=0.5),
    )


def test_apply_talker_core_stabilization_patches_only_layer_16_and_restores_forward() -> None:
    """The bounded stabilization surface should patch only the targeted late-middle MLP."""
    model = _fake_model(layer_count=18)
    assert "forward" not in _layer_mlp(model, 16).__dict__
    assert "forward" not in _layer_mlp(model, 15).__dict__

    with apply_talker_core_stabilization(model, variant=LAYER16_GATED_FP32):
        assert "forward" in _layer_mlp(model, 16).__dict__
        assert "forward" not in _layer_mlp(model, 15).__dict__

    assert "forward" not in _layer_mlp(model, 16).__dict__
    assert "forward" not in _layer_mlp(model, 15).__dict__


def test_apply_talker_core_stabilization_patches_layer15_output_and_restores_forward() -> None:
    """The late-middle attenuation family should patch only the targeted layer output seam."""
    model = _fake_model(layer_count=18)
    assert "forward" not in _layer(model, 15).__dict__
    assert "forward" not in _layer(model, 16).__dict__

    with apply_talker_core_stabilization(
        model,
        variant=LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5,
    ):
        assert "forward" in _layer(model, 15).__dict__
        assert "forward" not in _layer(model, 16).__dict__

    assert "forward" not in _layer(model, 15).__dict__
    assert "forward" not in _layer(model, 16).__dict__


def test_apply_talker_core_stabilization_patches_layer16_and_layer15_output_for_handoff_family() -> (
    None
):
    """The third family should patch both sides of the shifted layer-16 handoff seam."""
    model = _fake_model(layer_count=18)
    assert "forward" not in _layer(model, 15).__dict__
    assert "forward" not in _layer(model, 16).__dict__

    with apply_talker_core_stabilization(
        model,
        variant=LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5,
    ):
        assert "forward" in _layer(model, 15).__dict__
        assert "forward" in _layer(model, 16).__dict__

    assert "forward" not in _layer(model, 15).__dict__
    assert "forward" not in _layer(model, 16).__dict__


def test_apply_talker_core_stabilization_clamps_gated_product_and_preserves_dtype() -> None:
    """The first bounded clamp variant should bound the gated product cleanly."""
    model = _fake_model(layer_count=18)
    sample = torch.full((1, 2, 3), 20_000.0, dtype=torch.bfloat16)

    with apply_talker_core_stabilization(model, variant=LAYER16_GATED_FP32_CLAMP_1E4):
        output = _layer_mlp(model, 16)(sample)

    assert output.dtype == torch.bfloat16
    assert float(output.abs().max().item()) <= 10_048.0


def test_apply_talker_core_stabilization_rescales_gated_product_and_attenuates_layer15_output() -> (
    None
):
    """The second candidate should bound the gated product and scale the layer-15 seam."""
    model = _fake_model(layer_count=18)
    sample = torch.full((1, 2, 3), 20_000.0, dtype=torch.bfloat16)
    baseline_layer15_output = _layer(model, 15)(sample)[0]

    with apply_talker_core_stabilization(
        model,
        variant=LAYER16_GATED_FP32_RESCALE_1E2_LAYER15_OUT_0P25,
    ):
        layer16_output = _layer_mlp(model, 16)(sample)
        layer15_output = _layer(model, 15)(sample)[0]

    assert layer16_output.dtype == torch.bfloat16
    assert float(layer16_output.abs().max().item()) <= 128.0
    assert torch.equal(layer15_output, baseline_layer15_output * 0.25)


def test_apply_talker_core_stabilization_attenuates_layer16_handoff_and_layer15_output() -> None:
    """The third candidate family should scale both layer-16 and layer-15 seams."""
    base_model = _fake_model(layer_count=18)
    handoff_model = _fake_model(layer_count=18)
    sample = torch.full((1, 2, 3), 20_000.0, dtype=torch.bfloat16)
    with apply_talker_core_stabilization(
        base_model,
        variant=LAYER16_GATED_FP32_RESCALE_1E3_LAYER15_OUT_0P5,
    ):
        base_layer16_output = _layer(base_model, 16)(sample)[0]
        base_layer15_output = _layer(base_model, 15)(sample)[0]

    with apply_talker_core_stabilization(
        handoff_model,
        variant=LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P25_LAYER15_OUT_0P5,
    ):
        layer16_output = _layer(handoff_model, 16)(sample)[0]
        layer15_output = _layer(handoff_model, 15)(sample)[0]

    assert torch.equal(layer16_output, base_layer16_output * 0.25)
    assert torch.equal(layer15_output, base_layer15_output)


class _FakeIdentityModule(torch.nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


class _FakeTalkerMlp(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.act_fn = _FakeIdentityModule()
        self.gate_proj = _FakeIdentityModule()
        self.up_proj = _FakeIdentityModule()
        self.down_proj = _FakeIdentityModule()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self.down_proj(self.act_fn(self.gate_proj(x)) * self.up_proj(x))
        if not isinstance(output, torch.Tensor):
            raise SystemExit("Fake talker MLP did not return a tensor.")
        return output


class _FakeTalkerLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.mlp = _FakeTalkerMlp()

    def forward(self, hidden_states: torch.Tensor) -> tuple[torch.Tensor]:
        return (self.mlp(hidden_states),)


class _FakeTalkerModel(torch.nn.Module):
    def __init__(self, *, layer_count: int) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList(_FakeTalkerLayer() for _ in range(layer_count))


class _FakeTalkerWrapper:
    def __init__(self, *, layer_count: int) -> None:
        self.model = _FakeTalkerModel(layer_count=layer_count)


class _FakeTrainingModel:
    def __init__(self, *, layer_count: int) -> None:
        self.talker = _FakeTalkerWrapper(layer_count=layer_count)


def _fake_model(*, layer_count: int) -> _FakeTrainingModel:
    return _FakeTrainingModel(layer_count=layer_count)


def _layer_mlp(model: _FakeTrainingModel, layer_index: int) -> _FakeTalkerMlp:
    return _layer(model, layer_index).mlp


def _layer(model: _FakeTrainingModel, layer_index: int) -> _FakeTalkerLayer:
    layer = model.talker.model.layers[layer_index]
    if not isinstance(layer, _FakeTalkerLayer):
        raise SystemExit(f"Fake talker layer {layer_index} resolved to an unexpected module.")
    return layer
