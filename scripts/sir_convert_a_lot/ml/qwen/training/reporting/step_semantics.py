"""Step-semantics payload helpers for Qwen training artifacts.

Purpose:
    Own the machine-readable step and epoch semantics shared across live status
    and terminal training reports.

Relationships:
    - Used by status payload builders and failure projection.
    - Shared by tests that assert operator-facing counter truthfulness.
"""

from __future__ import annotations


def step_semantics_payload(gradient_accumulation_steps: int | None) -> dict[str, object] | None:
    """Return a machine-readable step-semantics payload for status artifacts."""
    if gradient_accumulation_steps is None:
        return None
    return {
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "optimizer_step_definition": (
            "increments only on iterations where accelerate.sync_gradients is true"
        ),
        "train_iteration_definition": "increments on every dataloader iteration",
        "epoch_index_base": 0,
        "epoch_definition": (
            "zero-based dataloader pass index restored from the durable checkpoint cursor on resume"
        ),
    }
