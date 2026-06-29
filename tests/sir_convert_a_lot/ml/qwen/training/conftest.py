"""Shared pytest fixtures for Qwen training tests.

Purpose:
    Keep local durable-checkpoint tests independent of host filesystem free
    space while preserving explicit low-space override tests.

Relationships:
    - Patches only the Qwen durable checkpoint module's `shutil.disk_usage`
      boundary.
    - Reuses typed checkpoint-space helpers for deterministic capacity tests.
"""

from __future__ import annotations

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES,
)
from tests.sir_convert_a_lot.ml.qwen.training.checkpoint_space_test_support import (
    fake_disk_usage,
)


@pytest.fixture(autouse=True)
def fake_high_checkpoint_free_space(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep successful checkpoint lifecycle tests independent of host free space."""
    required_free_bytes = DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES + (16 * 1024**3)
    monkeypatch.setattr(
        "scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing.shutil.disk_usage",
        lambda _path: fake_disk_usage(free=required_free_bytes + 1),
    )
