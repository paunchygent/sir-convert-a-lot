"""Gradient-accumulation contracts for bounded Qwen proof runs.

Purpose:
    Centralize the Qwen pilot training gradient-accumulation defaults, supported proof
    overrides, and validation logic so control-plane, detached-runtime, and
    patched trainer modules can share one truthful contract.

Relationships:
    - Imported by the detached Qwen control-plane parsers and settings models.
    - Imported by patched `sft_12hz_*` runtime helpers when building
      accumulation-aware status, progress, and scheduling semantics.
    - Consumed by reporting and eval surfaces so bounded proof artifacts remain
      self-describing.
"""

from __future__ import annotations

from typing import Literal, get_args

GradientAccumulationSteps = Literal[1, 2, 4]

DEFAULT_GRADIENT_ACCUMULATION_STEPS: GradientAccumulationSteps = 4
GRADIENT_ACCUMULATION_STEP_CHOICES: tuple[int, ...] = get_args(GradientAccumulationSteps)


def resolve_gradient_accumulation_steps(
    value: int | None,
    *,
    default: GradientAccumulationSteps,
) -> GradientAccumulationSteps:
    """Return one validated accumulation value for the Qwen pilot training lane."""
    if value is None:
        return default
    if value == 1:
        return 1
    if value == 2:
        return 2
    if value == 4:
        return 4
    supported_values = ", ".join(str(choice) for choice in GRADIENT_ACCUMULATION_STEP_CHOICES)
    raise ValueError(
        f"Unsupported `gradient_accumulation_steps` `{value}`. Expected one of: {supported_values}."
    )
