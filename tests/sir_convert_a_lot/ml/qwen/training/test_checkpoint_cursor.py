"""Tests for checkpoint-resume cursor epoch-boundary semantics.

Purpose:
    Validate that the resume cursor correctly advances to the next epoch
    when the last batch of an epoch completes.

Relationships:
    - Exercises `_checkpoint_resume_cursor` in
      `scripts/devops/qwen_finetuning_patches/sft_12hz_checkpointing.py`.
"""

from __future__ import annotations

from tests.sir_convert_a_lot.ml.qwen.training.test_support import (
    _checkpoint_resume_cursor,
)


def test_checkpoint_resume_cursor_rolls_to_next_epoch_at_epoch_boundary() -> None:
    """A completed last batch should advance the resume cursor to the next epoch."""
    next_epoch, next_step = _checkpoint_resume_cursor(
        epoch=2,
        step_in_epoch=4,
        dataloader_length=5,
    )

    assert next_epoch == 3
    assert next_step == 0
