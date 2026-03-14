"""Bucketed batching helpers for the patched Qwen trainer.

Purpose:
    Build aggressive but bounded Task 101 training batches using token/frame
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


@dataclass
class _OpenBatch:
    """Mutable planned batch used by the within-bucket packer."""

    indices: list[int]
    text_token_count: int
    codec_frame_count: int

    @property
    def row_count(self) -> int:
        """Return the current number of rows in the open batch."""
        return len(self.indices)

    def add(self, index: int, metrics: TrainingRowBatchMetrics) -> None:
        """Append one row and update cumulative budget usage."""
        self.indices.append(index)
        self.text_token_count += metrics.text_token_count
        self.codec_frame_count += metrics.codec_frame_count


class BucketedBatchSampler(Sampler[list[int]]):
    """Yield bounded training batches grouped by approximate sequence length."""

    def __init__(
        self,
        *,
        row_metrics: list[TrainingRowBatchMetrics],
        policy: ThroughputBatchPolicy,
    ) -> None:
        if not row_metrics:
            raise ValueError("Bucketed batch sampler requires at least one training row.")
        self._row_metrics = row_metrics
        self._policy = policy
        self._planned_batches = self._build_batches()

    def __iter__(self) -> Iterator[list[int]]:
        shuffled_batches = [list(batch) for batch in self._planned_batches]
        random.shuffle(shuffled_batches)
        yield from shuffled_batches

    def __len__(self) -> int:
        return len(self._planned_batches)

    def planned_batches(self) -> list[list[int]]:
        """Return a copy of the resolved batch plan for occupancy reporting."""
        return [list(batch) for batch in self._planned_batches]

    def _build_batches(self) -> list[list[int]]:
        buckets: dict[int, list[int]] = defaultdict(list)
        for index, metrics in enumerate(self._row_metrics):
            self._validate_single_row_budget(index, metrics)
            buckets[self._bucket_boundary(metrics.total_sequence_cost)].append(index)

        planned_batches: list[list[int]] = []
        for boundary in sorted(buckets):
            ordered_indices = sorted(
                buckets[boundary],
                key=lambda index: (
                    self._row_metrics[index].codec_frame_count,
                    self._row_metrics[index].text_token_count,
                ),
                reverse=True,
            )
            open_batches: list[_OpenBatch] = []
            for index in ordered_indices:
                metrics = self._row_metrics[index]
                best_fit_batch = self._select_best_fit_batch(open_batches, metrics)
                if best_fit_batch is None:
                    open_batches.append(
                        _OpenBatch(
                            indices=[index],
                            text_token_count=metrics.text_token_count,
                            codec_frame_count=metrics.codec_frame_count,
                        )
                    )
                    continue
                best_fit_batch.add(index, metrics)
            planned_batches.extend(list(open_batch.indices) for open_batch in open_batches)
        return planned_batches

    def _select_best_fit_batch(
        self,
        open_batches: list[_OpenBatch],
        metrics: TrainingRowBatchMetrics,
    ) -> _OpenBatch | None:
        """Return the tightest-fitting open batch for one row when possible."""
        best_batch: _OpenBatch | None = None
        best_score: tuple[int, int, int, int] | None = None
        for open_batch in open_batches:
            if open_batch.row_count >= self._policy.max_batch_size:
                continue
            next_token_count = open_batch.text_token_count + metrics.text_token_count
            if next_token_count > self._policy.max_tokens_per_batch:
                continue
            next_codec_frame_count = open_batch.codec_frame_count + metrics.codec_frame_count
            if next_codec_frame_count > self._policy.max_codec_frames_per_batch:
                continue
            remaining_codec_budget = (
                self._policy.max_codec_frames_per_batch - next_codec_frame_count
            )
            remaining_token_budget = self._policy.max_tokens_per_batch - next_token_count
            remaining_batch_capacity = self._policy.max_batch_size - (open_batch.row_count + 1)
            score = (
                remaining_codec_budget,
                remaining_token_budget,
                remaining_batch_capacity,
                open_batch.indices[0],
            )
            if best_score is None or score < best_score:
                best_batch = open_batch
                best_score = score
        return best_batch

    def _bucket_boundary(self, total_sequence_cost: int) -> int:
        for boundary in self._policy.length_bucket_boundaries:
            if total_sequence_cost <= boundary:
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
