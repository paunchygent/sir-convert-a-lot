"""Gradient-hook profiles for Story 30 lineage probes.

Purpose:
    Centralize hook-profile choices and the actual tensor/module hook plumbing
    so the in-container probe can switch from baseline surface tracing to the
    deeper talker-core trace without becoming a single oversized module.

Relationships:
    - Imported by `backward_lineage_probe.py`.
    - Reuses `sft_12hz_talker_core_trace.py` to resolve talker-core module
      boundaries from the live patched Qwen runtime.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from types import MethodType
from typing import Callable

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    summarize_tensor_finiteness,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces import (
    TalkerForwardSurfaces,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    iter_talker_core_boundary_trace_targets,
    iter_talker_core_handoff_sub_boundary_trace_targets,
    iter_talker_core_trace_targets,
    resolve_talker_input_layernorm,
    talker_core_input_layernorm_internal_trace_names,
    talker_core_trace_prefix,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_contracts import (
    FirstNonFiniteHookObservation,
    TensorGradientObservation,
)

BASELINE_HOOK_PROFILE = "baseline"
TALKER_CORE_HOOK_PROFILE = "talker_core"
TALKER_CORE_BOUNDARY_HOOK_PROFILE = "talker_core_boundary"
TALKER_CORE_HANDOFF_SUB_BOUNDARY_HOOK_PROFILE = "talker_core_handoff_sub_boundary"
TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE = "talker_core_input_layernorm_internal"
HOOK_PROFILE_CHOICES = (
    BASELINE_HOOK_PROFILE,
    TALKER_CORE_HOOK_PROFILE,
    TALKER_CORE_BOUNDARY_HOOK_PROFILE,
    TALKER_CORE_HANDOFF_SUB_BOUNDARY_HOOK_PROFILE,
    TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE,
)
_BASELINE_FORWARD_SURFACE_NAMES = (
    "semantic_text_embeddings",
    "input_text_embedding",
    "input_codec_embedding",
    "fused_auxiliary_embedding",
    "input_embeddings",
    "hidden_states",
    "talker_hidden_states",
)


@dataclass
class _FirstNonFiniteHookState:
    """Mutable state holder for the earliest matching non-finite hook."""

    tensor_name: str | None = None
    hook_order: int | None = None


@dataclass(frozen=True)
class _PatchedModuleForward:
    """One reversible module-forward override owned by a hook session."""

    module: torch.nn.Module
    original_forward: Callable[..., object]
    had_instance_forward: bool


class GradientHookSession:
    """One lifecycle-scoped hook session for a lineage probe backward pass."""

    def __init__(self, *, hook_profile: str) -> None:
        self._hook_profile = _validate_hook_profile(hook_profile)
        self._handles: list[torch.utils.hooks.RemovableHandle] = []
        self._observations: dict[str, TensorGradientObservation] = {}
        self._patched_module_forwards: list[_PatchedModuleForward] = []
        self._first_non_finite = _FirstNonFiniteHookState()
        self._hook_counter = 0

    def install_pre_forward_hooks(self, *, model: object) -> None:
        """Install any module forward hooks required before the shared forward pass."""
        if self._hook_profile == BASELINE_HOOK_PROFILE:
            return
        if self._hook_profile == TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE:
            self._install_input_layernorm_internal_trace(model=model)
            return
        if self._hook_profile == TALKER_CORE_HOOK_PROFILE:
            trace_targets = iter_talker_core_trace_targets(model)
        elif self._hook_profile == TALKER_CORE_BOUNDARY_HOOK_PROFILE:
            trace_targets = iter_talker_core_boundary_trace_targets(model)
        else:
            trace_targets = iter_talker_core_handoff_sub_boundary_trace_targets(model)
        for target in trace_targets:
            handle = (
                target.module.register_forward_hook(
                    self._build_forward_hook(target.name, target.tensor_selector)
                )
                if target.hook_kind == "forward"
                else target.module.register_forward_pre_hook(
                    self._build_forward_pre_hook(target.name, target.tensor_selector)
                )
            )
            self._handles.append(handle)

    def attach_forward_surfaces(self, forward_surfaces: TalkerForwardSurfaces) -> None:
        """Attach baseline post-forward tensor hooks from the shared surfaces."""
        for surface_name in _BASELINE_FORWARD_SURFACE_NAMES:
            self._attach_tensor(surface_name, getattr(forward_surfaces, surface_name))

    def ordered_observations(self) -> tuple[TensorGradientObservation, ...]:
        """Return instrumented tensor observations in actual backward hook order."""
        return tuple(
            sorted(self._observations.values(), key=lambda observation: observation.hook_order)
        )

    def first_non_finite_observation(self) -> FirstNonFiniteHookObservation:
        """Return the earliest non-finite hook across the full instrumented session."""
        return FirstNonFiniteHookObservation(
            tensor_name=self._first_non_finite.tensor_name,
            hook_order=self._first_non_finite.hook_order,
        )

    def first_non_finite_matching_prefix(self, prefix: str) -> FirstNonFiniteHookObservation:
        """Return the earliest non-finite hook whose tensor name starts with one prefix."""
        for observation in self.ordered_observations():
            if observation.tensor_name.startswith(prefix) and not observation.is_finite:
                return FirstNonFiniteHookObservation(
                    tensor_name=observation.tensor_name,
                    hook_order=observation.hook_order,
                )
        return FirstNonFiniteHookObservation(tensor_name=None, hook_order=None)

    def close(self) -> None:
        """Remove all forward and gradient hooks owned by this session."""
        for patched_forward in reversed(self._patched_module_forwards):
            if patched_forward.had_instance_forward:
                patched_forward.module.forward = patched_forward.original_forward
                continue
            delattr(patched_forward.module, "forward")
        self._patched_module_forwards.clear()
        for handle in self._handles:
            with suppress(RuntimeError):
                handle.remove()
        self._handles.clear()

    def _build_forward_hook(
        self,
        name: str,
        tensor_selector,
    ) -> Callable[[torch.nn.Module, tuple[object, ...], object], None]:
        """Return one module forward hook that retains the selected output gradient."""

        def on_forward(
            _module: torch.nn.Module, _inputs: tuple[object, ...], output: object
        ) -> None:
            tensor = tensor_selector(output)
            if tensor is None:
                return
            self._attach_tensor(name, tensor)

        return on_forward

    def _build_forward_pre_hook(
        self,
        name: str,
        tensor_selector,
    ) -> Callable[[torch.nn.Module, tuple[object, ...]], None]:
        """Return one module forward-pre-hook that retains the selected input gradient."""

        def on_forward_pre(_module: torch.nn.Module, inputs: tuple[object, ...]) -> None:
            tensor = tensor_selector(inputs)
            if tensor is None:
                return
            self._attach_tensor(name, tensor)

        return on_forward_pre

    def _attach_tensor(self, name: str, tensor: torch.Tensor) -> None:
        if name in self._observations or not tensor.requires_grad:
            return
        tensor.retain_grad()

        def on_grad(gradient: torch.Tensor) -> torch.Tensor:
            self._hook_counter += 1
            summary = summarize_tensor_finiteness(gradient)
            observation = TensorGradientObservation(
                tensor_name=name,
                hook_order=self._hook_counter,
                is_finite=_required_summary_bool(summary, "is_finite"),
                nan_count=_required_summary_int(summary, "nan_count"),
                inf_count=_required_summary_int(summary, "inf_count"),
                max_abs=_optional_summary_float(summary, "max_abs"),
            )
            self._observations[name] = observation
            if (not observation.is_finite) and self._first_non_finite.tensor_name is None:
                self._first_non_finite.tensor_name = name
                self._first_non_finite.hook_order = self._hook_counter
            return gradient

        self._handles.append(tensor.register_hook(on_grad))

    def _install_input_layernorm_internal_trace(self, *, model: object) -> None:
        """Patch the T233 layer-16 input-layernorm forward for internal tracing."""
        input_layernorm = resolve_talker_input_layernorm(model, layer_index=16)
        self._patched_module_forwards.append(
            _PatchedModuleForward(
                module=input_layernorm,
                original_forward=input_layernorm.forward,
                had_instance_forward="forward" in input_layernorm.__dict__,
            )
        )
        input_layernorm.forward = MethodType(
            self._build_input_layernorm_internal_forward(),
            input_layernorm,
        )

    def _build_input_layernorm_internal_forward(
        self,
    ) -> Callable[[torch.nn.Module, object], torch.Tensor]:
        """Build one reversible RMSNorm wrapper for the T233 internal chain."""
        (
            residual_input_name,
            fp32_input_name,
            variance_name,
            normalized_hidden_states_name,
            output_name,
        ) = talker_core_input_layernorm_internal_trace_names()

        def on_forward(
            self_module: torch.nn.Module, *args: object, **kwargs: object
        ) -> torch.Tensor:
            if kwargs:
                raise SystemExit(
                    "Backward-lineage probe expected `layer_16.input_layernorm` "
                    "to receive no keyword arguments under the T233 profile."
                )
            if len(args) != 1 or not isinstance(args[0], torch.Tensor):
                raise SystemExit(
                    "Backward-lineage probe expected `layer_16.input_layernorm` "
                    "to receive exactly one tensor input under the T233 profile."
                )
            residual_input = args[0]
            self._attach_tensor(residual_input_name, residual_input)
            input_dtype = residual_input.dtype
            fp32_input = residual_input.to(torch.float32)
            self._attach_tensor(fp32_input_name, fp32_input)
            variance = fp32_input.pow(2).mean(-1, keepdim=True)
            self._attach_tensor(variance_name, variance)
            variance_epsilon = _required_variance_epsilon(self_module)
            normalized_hidden_states = fp32_input * torch.rsqrt(variance + variance_epsilon)
            self._attach_tensor(normalized_hidden_states_name, normalized_hidden_states)
            weight = _required_layernorm_weight(self_module)
            output = weight * normalized_hidden_states.to(input_dtype)
            self._attach_tensor(output_name, output)
            return output

        return on_forward


def build_gradient_hook_session(*, hook_profile: str) -> GradientHookSession:
    """Build one lifecycle-scoped gradient hook session for a probe case."""
    return GradientHookSession(hook_profile=hook_profile)


def talker_core_prefix() -> str:
    """Return the canonical talker-core trace prefix for hook filtering."""
    return talker_core_trace_prefix()


def _validate_hook_profile(hook_profile: str) -> str:
    if hook_profile not in HOOK_PROFILE_CHOICES:
        raise SystemExit(
            f"Backward-lineage probe received unsupported hook profile `{hook_profile}`."
        )
    return hook_profile


def _required_summary_bool(summary: dict[str, object], key: str) -> bool:
    value = summary.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Backward-lineage tensor summary returned malformed `{key}`.")
    return value


def _required_summary_int(summary: dict[str, object], key: str) -> int:
    value = summary.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Backward-lineage tensor summary returned malformed `{key}`.")
    return value


def _optional_summary_float(summary: dict[str, object], key: str) -> float | None:
    value = summary.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise SystemExit(f"Backward-lineage tensor summary returned malformed `{key}`.")
    return float(value)


def _required_layernorm_weight(module: torch.nn.Module) -> torch.Tensor:
    weight = getattr(module, "weight", None)
    if not isinstance(weight, torch.Tensor):
        raise SystemExit(
            "Backward-lineage probe could not resolve `layer_16.input_layernorm.weight` "
            "as a tensor under the T233 profile."
        )
    return weight


def _required_variance_epsilon(module: torch.nn.Module) -> float:
    value = getattr(module, "variance_epsilon", None)
    if not isinstance(value, (int, float)):
        raise SystemExit(
            "Backward-lineage probe could not resolve "
            "`layer_16.input_layernorm.variance_epsilon` as a scalar under the T233 profile."
        )
    return float(value)
