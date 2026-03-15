"""Configuration contracts for Qwen training status reporting.

Purpose:
    Define the immutable reporting configuration required to write truthful
    live and terminal status artifacts for one training run.

Relationships:
    - Consumed by `status_writer`.
    - Shared by trainer entrypoints and reporting tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class StatusReporterConfig:
    """Static run metadata required to write one training status artifact."""

    status_path: Path
    launch_metadata_path: Path | None
    train_jsonl: Path
    eval_jsonl: Path
    output_dir: Path
    train_row_count: int
    eval_row_count: int
    checkpoint_interval_steps: int
    eval_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    resume_from_checkpoint: Path | None
    dataloader_length: int | None = None
    eval_dataloader_length: int | None = None
    tracking_plan: Mapping[str, object] | None = None
    gradient_accumulation_steps: int = 4
    dataloader_tuning: Mapping[str, object] | None = None
    heartbeat_policy: Mapping[str, object] | None = None
    finite_loss_guard_config: Mapping[str, object] | None = None
    ref_mel_cache_config: Mapping[str, object] | None = None
    bundle_precomputed_reference_input: Mapping[str, object] | None = None
    throughput_profile: Mapping[str, object] | None = None
    profiling_plan: Mapping[str, object] | None = None
    diagnostic: Mapping[str, object] | None = None
