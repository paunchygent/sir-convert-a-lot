"""Layernorm-specific hook helpers for Qwen backward-lineage and fresh-start proof lane/31
backward-lineage probes.

Purpose:
    Keep the reversible layernorm wrapper logic out of the central hook-session
    module so the hot-path hook dispatcher stays within the repo size cap while
    still exposing the exact internal and seam-localized normalization
    surfaces used by input-layernorm internal and downstream Qwen stability lab diagnosis tasks.

Relationships:
    - Imported by `qwen_backward_lineage_hooks.py`.
    - Reuses `sft_12hz_talker_core_trace.py` to resolve live talker
      input-layernorm modules from the patched Qwen runtime.
"""

from __future__ import annotations

from collections.abc import Callable

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    TalkerCoreTraceTarget,
    resolve_talker_input_layernorm,
)


def install_input_layernorm_internal_trace(
    *,
    model: object,
    attach_tensor: Callable[[str, torch.Tensor], None],
    patch_module_forward: Callable[[torch.nn.Module, Callable[..., object]], None],
    trace_names: tuple[str, ...],
) -> None:
    """Patch the input-layernorm internal layer-16 input-layernorm forward for internal tracing."""
    input_layernorm = resolve_talker_input_layernorm(model, layer_index=16)
    patch_module_forward(
        input_layernorm,
        build_input_layernorm_internal_forward(
            attach_tensor=attach_tensor,
            trace_names=trace_names,
        ),
    )


def build_input_layernorm_internal_forward(
    *,
    attach_tensor: Callable[[str, torch.Tensor], None],
    trace_names: tuple[str, ...],
) -> Callable[[torch.nn.Module, object], torch.Tensor]:
    """Build one reversible RMSNorm wrapper for the input-layernorm internal internal chain."""
    (
        residual_input_name,
        fp32_input_name,
        variance_name,
        normalized_hidden_states_name,
        output_name,
    ) = trace_names

    def on_forward(self_module: torch.nn.Module, *args: object, **kwargs: object) -> torch.Tensor:
        if kwargs:
            raise SystemExit(
                "Backward-lineage probe expected `layer_16.input_layernorm` "
                "to receive no keyword arguments under the INPUT_LAYERNORM_INTERNAL profile."
            )
        if len(args) != 1 or not isinstance(args[0], torch.Tensor):
            raise SystemExit(
                "Backward-lineage probe expected `layer_16.input_layernorm` "
                "to receive exactly one tensor input under the INPUT_LAYERNORM_INTERNAL profile."
            )
        residual_input = args[0]
        attach_tensor(residual_input_name, residual_input)
        input_dtype = residual_input.dtype
        fp32_input = residual_input.to(torch.float32)
        attach_tensor(fp32_input_name, fp32_input)
        variance = fp32_input.pow(2).mean(-1, keepdim=True)
        attach_tensor(variance_name, variance)
        variance_epsilon = _required_variance_epsilon(self_module)
        normalized_hidden_states = fp32_input * torch.rsqrt(variance + variance_epsilon)
        attach_tensor(normalized_hidden_states_name, normalized_hidden_states)
        weight = _required_layernorm_weight(self_module)
        output = weight * normalized_hidden_states.to(input_dtype)
        attach_tensor(output_name, output)
        return output

    return on_forward


def install_layer16_input_layernorm_output_trace(
    *,
    model: object,
    trace_targets: tuple[TalkerCoreTraceTarget, ...],
    output_name: str,
    profile_label: str,
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
    """Install one narrowed corridor plus a reversible layer-16 output wrapper."""
    for target in trace_targets:
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
    input_layernorm = resolve_talker_input_layernorm(model, layer_index=16)
    patch_module_forward(
        input_layernorm,
        build_layer16_input_layernorm_output_forward(
            attach_tensor=attach_tensor,
            output_name=output_name,
            profile_label=profile_label,
        ),
    )


def build_layer16_input_layernorm_output_forward(
    *,
    attach_tensor: Callable[[str, torch.Tensor], None],
    output_name: str,
    profile_label: str,
) -> Callable[[torch.nn.Module, object], torch.Tensor]:
    """Build one reversible wrapper that exposes the layer-16 output seam."""

    def on_forward(self_module: torch.nn.Module, *args: object, **kwargs: object) -> torch.Tensor:
        if kwargs:
            raise SystemExit(
                "Backward-lineage probe expected `layer_16.input_layernorm` "
                f"to receive no keyword arguments under the {profile_label} profile."
            )
        if len(args) != 1 or not isinstance(args[0], torch.Tensor):
            raise SystemExit(
                "Backward-lineage probe expected `layer_16.input_layernorm` "
                f"to receive exactly one tensor input under the {profile_label} profile."
            )
        residual_input = args[0]
        input_dtype = residual_input.dtype
        hidden_states = residual_input.to(torch.float32)
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        variance_epsilon = _required_variance_epsilon(self_module)
        hidden_states = hidden_states * torch.rsqrt(variance + variance_epsilon)
        weight = _required_layernorm_weight(self_module)
        output = weight * hidden_states.to(input_dtype)
        attach_tensor(output_name, output)
        return output

    return on_forward


def _required_layernorm_weight(module: torch.nn.Module) -> torch.Tensor:
    weight = getattr(module, "weight", None)
    if not isinstance(weight, torch.Tensor):
        raise SystemExit(
            "Backward-lineage probe could not resolve `layer_16.input_layernorm.weight` "
            "as a tensor under the requested profile."
        )
    return weight


def _required_variance_epsilon(module: torch.nn.Module) -> float:
    value = getattr(module, "variance_epsilon", None)
    if not isinstance(value, (int, float)):
        raise SystemExit(
            "Backward-lineage probe could not resolve "
            "`layer_16.input_layernorm.variance_epsilon` as a scalar under the "
            "requested profile."
        )
    return float(value)
