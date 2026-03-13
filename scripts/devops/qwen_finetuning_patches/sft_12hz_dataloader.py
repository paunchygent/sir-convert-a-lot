"""DataLoader tuning helpers for the patched Qwen trainer.

Purpose:
    Hold Task 101 dataloader and transfer-path tuning contracts so `sft_12hz.py`
    stays focused on model/training orchestration while still exposing
    evidence-backed loader controls.

Relationships:
    - Imported by `sft_12hz.py` for dataloader argument validation and
      effective-configuration resolution.
    - Its payloads are persisted in training summary/status artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import torch

DEFAULT_DATALOADER_NUM_WORKERS = 4
DEFAULT_DATALOADER_PIN_MEMORY = True
DEFAULT_DATALOADER_PERSISTENT_WORKERS = True
DEFAULT_DATALOADER_PREFETCH_FACTOR = 4
DEFAULT_NON_BLOCKING_TRANSFER = True


@dataclass(frozen=True)
class DataloaderTuning:
    """Effective Task 101 dataloader and transfer controls."""

    num_workers: int
    pin_memory: bool
    persistent_workers: bool
    prefetch_factor: int | None
    non_blocking_transfer: bool


def resolve_dataloader_tuning(
    *,
    num_workers: int,
    pin_memory: bool,
    persistent_workers: bool,
    prefetch_factor: int,
    non_blocking_transfer: bool,
) -> DataloaderTuning:
    """Validate and normalize dataloader tuning for one training run."""
    if num_workers < 0:
        raise ValueError("`--dataloader-num-workers` must be >= 0.")
    if prefetch_factor <= 0:
        raise ValueError("`--dataloader-prefetch-factor` must be positive.")
    if num_workers == 0:
        return DataloaderTuning(
            num_workers=0,
            pin_memory=pin_memory,
            persistent_workers=False,
            prefetch_factor=None,
            non_blocking_transfer=non_blocking_transfer,
        )
    return DataloaderTuning(
        num_workers=num_workers,
        pin_memory=pin_memory,
        persistent_workers=persistent_workers,
        prefetch_factor=prefetch_factor,
        non_blocking_transfer=non_blocking_transfer,
    )


def dataloader_kwargs(
    *,
    tuning: DataloaderTuning,
    batch_size: int,
    collate_fn: Callable[..., object],
) -> dict[str, object]:
    """Build DataLoader kwargs from one normalized tuning payload."""
    kwargs: dict[str, object] = {
        "batch_size": batch_size,
        "shuffle": True,
        "collate_fn": collate_fn,
        "num_workers": tuning.num_workers,
        "pin_memory": tuning.pin_memory,
    }
    if tuning.num_workers > 0:
        kwargs["persistent_workers"] = tuning.persistent_workers
        if tuning.prefetch_factor is None:
            raise ValueError("Resolved dataloader tuning requires `prefetch_factor`.")
        kwargs["prefetch_factor"] = tuning.prefetch_factor
    return kwargs


def to_device_with_optional_non_blocking(
    tensor: torch.Tensor,
    *,
    device: torch.device | str,
    dtype: torch.dtype,
    non_blocking_transfer: bool,
) -> torch.Tensor:
    """Move one tensor to device with optional non-blocking transfer."""
    return tensor.to(
        device=device,
        dtype=dtype,
        non_blocking=non_blocking_transfer,
    )


def dataloader_tuning_payload(tuning: DataloaderTuning) -> dict[str, object]:
    """Return a JSON-safe tuning payload for status and tracker artifacts."""
    return asdict(tuning)
