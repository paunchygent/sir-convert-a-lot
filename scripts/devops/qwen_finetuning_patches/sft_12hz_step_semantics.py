"""Step-semantics helpers for the patched Qwen trainer.

Purpose:
    Keep gradient-accumulation and step-counter semantics centralized so
    `sft_12hz.py` can report truthful optimizer-step versus loop-iteration
    progress without inlining policy constants and payload builders.

Relationships:
    - Imported by `sft_12hz.py` for accumulation-aware counter updates.
    - Reused by Task 101 status/report surfaces through trainer summaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
)

GRADIENT_ACCUMULATION_STEPS = DEFAULT_GRADIENT_ACCUMULATION_STEPS


@dataclass(frozen=True)
class TrainingStepSemantics:
    """Machine-readable definitions for Task 101 step counters."""

    gradient_accumulation_steps: int
    optimizer_step_definition: str
    train_iteration_definition: str


def default_training_step_semantics(
    gradient_accumulation_steps: int = GRADIENT_ACCUMULATION_STEPS,
) -> TrainingStepSemantics:
    """Return the canonical Task 101 step-semantics payload."""
    return TrainingStepSemantics(
        gradient_accumulation_steps=gradient_accumulation_steps,
        optimizer_step_definition=(
            "increments only on iterations where accelerate.sync_gradients is true"
        ),
        train_iteration_definition=(
            "increments on every dataloader iteration (micro-batch loop iteration)"
        ),
    )


def step_semantics_payload(
    gradient_accumulation_steps: int = GRADIENT_ACCUMULATION_STEPS,
) -> dict[str, object]:
    """Return a JSON-safe mapping for status/report payload embedding."""
    return asdict(
        default_training_step_semantics(
            gradient_accumulation_steps=gradient_accumulation_steps,
        )
    )
