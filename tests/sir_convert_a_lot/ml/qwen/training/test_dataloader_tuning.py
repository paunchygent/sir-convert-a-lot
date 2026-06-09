"""Focused tests for Qwen dataloader tuning helpers.

Purpose:
    Validate Qwen pilot training dataloader tuning normalization and DataLoader kwargs
    shaping without requiring a real GPU run.

Relationships:
    - Exercises `scripts/devops/qwen_finetuning_patches/sft_12hz_dataloader.py`.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    dataloader_kwargs,
    resolve_dataloader_tuning,
)


def test_resolve_dataloader_tuning_disables_worker_only_options_for_single_process() -> None:
    """Single-process loader mode should disable worker-only tuning options."""
    tuning = resolve_dataloader_tuning(
        num_workers=0,
        pin_memory=True,
        persistent_workers=True,
        prefetch_factor=4,
        non_blocking_transfer=True,
    )

    assert tuning.num_workers == 0
    assert tuning.pin_memory is True
    assert tuning.persistent_workers is False
    assert tuning.prefetch_factor is None
    assert tuning.non_blocking_transfer is True


def test_dataloader_kwargs_include_prefetch_and_persistent_for_multiprocess_mode() -> None:
    """Multiprocess loader mode should keep prefetch and persistent worker settings."""
    tuning = resolve_dataloader_tuning(
        num_workers=4,
        pin_memory=True,
        persistent_workers=True,
        prefetch_factor=8,
        non_blocking_transfer=True,
    )

    kwargs = dataloader_kwargs(
        tuning=tuning,
        batch_size=2,
        collate_fn=lambda batch: batch,
    )

    assert kwargs["batch_size"] == 2
    assert kwargs["shuffle"] is True
    assert kwargs["num_workers"] == 4
    assert kwargs["pin_memory"] is True
    assert kwargs["persistent_workers"] is True
    assert kwargs["prefetch_factor"] == 8
