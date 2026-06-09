"""Bucketed batching helpers for the patched Qwen trainer.

Purpose:
    Build aggressive but bounded Qwen pilot training training batches using token/frame
    budgets and length bucketing instead of fixed-size random batching.

Relationships:
    - Imported by `sft_12hz_setup.py` to construct the DataLoader batch sampler.
    - Reuses the shared throughput-profile contract from the domain training
      package.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterator

from torch.utils.data import Sampler

from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import ThroughputBatchPolicy


@dataclass(frozen=True)
class TrainingRowBatchMetrics:
    """Length signals for one training row used by the bucketed batcher."""

    text_token_count: int
    codec_frame_count: int

    @property
    def total_sequence_cost(self) -> int:
        """Return one combined sequence-length proxy for bucketing."""
        return self.text_token_count + self.codec_frame_count


def bucket_signal_value(
    *,
    metrics: TrainingRowBatchMetrics,
    policy: ThroughputBatchPolicy,
) -> int:
    """Return the active bucket-signal value for one row under one policy."""
    if policy.bucket_signal_kind == "combined-sequence-cost-v1":
        return metrics.total_sequence_cost
    if policy.bucket_signal_kind == "codec-frame-count-v1":
        return metrics.codec_frame_count
    raise ValueError(
        "Unsupported throughput bucket signal kind "
        f"`{policy.bucket_signal_kind}` for profile `{policy.profile_label}`."
    )


class BucketedBatchSampler(Sampler[list[int]]):
    """Yield bounded training batches grouped by approximate sequence length."""

    def __init__(
        self,
        *,
        row_metrics: list[TrainingRowBatchMetrics],
        policy: ThroughputBatchPolicy,
        shuffle: bool = True,
        shuffle_seed: int = 0,
    ) -> None:
        if not row_metrics:
            raise ValueError("Bucketed batch sampler requires at least one training row.")
        self._row_metrics = row_metrics
        self._policy = policy
        self._shuffle = shuffle
        self._shuffle_seed = shuffle_seed
        self._current_epoch = 0
        self._planned_batches = self._build_batches()

    def __iter__(self) -> Iterator[list[int]]:
        resolved_batches = [list(batch) for batch in self._planned_batches]
        if not self._shuffle:
            yield from resolved_batches
            return
        random.Random(self._shuffle_seed + self._current_epoch).shuffle(resolved_batches)
        yield from resolved_batches

    def __len__(self) -> int:
        return len(self._planned_batches)

    def planned_batches(self) -> list[list[int]]:
        """Return a copy of the resolved batch plan for occupancy reporting."""
        return [list(batch) for batch in self._planned_batches]

    def set_epoch(self, epoch: int) -> None:
        """Set the epoch-specific shuffle cursor for deterministic replay."""
        if epoch < 0:
            raise ValueError("Bucketed batch sampler epoch must be non-negative.")
        self._current_epoch = epoch

    def _build_batches(self) -> list[list[int]]:
        buckets: dict[int, list[int]] = defaultdict(list)
        quarantined_indices: list[int] = []
        quarantine_threshold = self._policy.long_row_singleton_codec_frame_threshold
        for index, metrics in enumerate(self._row_metrics):
            self._validate_single_row_budget(index, metrics)
            if (
                quarantine_threshold is not None
                and metrics.codec_frame_count >= quarantine_threshold
            ):
                quarantined_indices.append(index)
                continue
            buckets[self._bucket_boundary(metrics)].append(index)

        planned_batches: list[list[int]] = []
        for index in sorted(
            quarantined_indices,
            key=lambda current_index: (
                self._row_metrics[current_index].codec_frame_count,
                self._row_metrics[current_index].text_token_count,
            ),
            reverse=True,
        ):
            planned_batches.append([index])
        for boundary in sorted(buckets):
            ordered_indices = sorted(
                buckets[boundary],
                key=lambda index: (
                    self._row_metrics[index].codec_frame_count,
                    self._row_metrics[index].text_token_count,
                ),
                reverse=True,
            )
            current_batch: list[int] = []
            current_token_count = 0
            current_codec_frame_count = 0
            for index in ordered_indices:
                metrics = self._row_metrics[index]
                exceeds_batch_size = len(current_batch) >= self._policy.max_batch_size
                exceeds_token_budget = (
                    current_token_count + metrics.text_token_count
                    > self._policy.max_tokens_per_batch
                )
                exceeds_frame_budget = (
                    current_codec_frame_count + metrics.codec_frame_count
                    > self._policy.max_codec_frames_per_batch
                )
                if current_batch and (
                    exceeds_batch_size or exceeds_token_budget or exceeds_frame_budget
                ):
                    planned_batches.append(current_batch)
                    current_batch = []
                    current_token_count = 0
                    current_codec_frame_count = 0
                current_batch.append(index)
                current_token_count += metrics.text_token_count
                current_codec_frame_count += metrics.codec_frame_count
            if current_batch:
                planned_batches.append(current_batch)
        return planned_batches

    def _bucket_boundary(self, metrics: TrainingRowBatchMetrics) -> int:
        bucket_value = bucket_signal_value(metrics=metrics, policy=self._policy)
        for boundary in self._policy.length_bucket_boundaries:
            if bucket_value <= boundary:
                return boundary
        return self._policy.length_bucket_boundaries[-1] + 1

    def _validate_single_row_budget(
        self,
        index: int,
        metrics: TrainingRowBatchMetrics,
    ) -> None:
        if metrics.text_token_count > self._policy.max_tokens_per_batch:
            raise ValueError(
                "Training row exceeded the configured text-token budget for one batch: "
                f"row_index={index} text_token_count={metrics.text_token_count} "
                f"budget={self._policy.max_tokens_per_batch}"
            )
        if metrics.codec_frame_count > self._policy.max_codec_frames_per_batch:
            raise ValueError(
                "Training row exceeded the configured codec-frame budget for one batch: "
                f"row_index={index} codec_frame_count={metrics.codec_frame_count} "
                f"budget={self._policy.max_codec_frames_per_batch}"
            )
