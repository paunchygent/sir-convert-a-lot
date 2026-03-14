"""Batch-occupancy helpers for the patched Qwen trainer.

Purpose:
    Summarize the actual Task 101 batch plan into machine-readable occupancy
    evidence so throughput claims can rely on concrete row/token/frame totals
    instead of only the configured profile label.

Relationships:
    - Consumes row metrics from `sft_12hz_batching.py`.
    - Used by `sft_12hz_setup.py` to attach occupancy evidence to the resolved
      throughput-profile payload before training starts.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import TrainingRowBatchMetrics


@dataclass(frozen=True)
class BatchOccupancyRecord:
    """Concrete occupancy totals for one planned training batch."""

    batch_index: int
    row_count: int
    text_token_count: int
    codec_frame_count: int

    def payload(self) -> dict[str, int]:
        """Return a JSON-safe payload for one batch occupancy record."""
        return {
            "batch_index": self.batch_index,
            "row_count": self.row_count,
            "text_token_count": self.text_token_count,
            "codec_frame_count": self.codec_frame_count,
        }


@dataclass(frozen=True)
class BatchOccupancySummary:
    """Aggregate occupancy evidence for one resolved batch plan."""

    total_batches: int
    total_rows: int
    batch_size_histogram: dict[int, int]
    realized_max_batch_size: int
    realized_min_batch_size: int
    mean_batch_size: float
    peak_text_tokens_per_batch: int
    peak_codec_frames_per_batch: int
    batches: tuple[BatchOccupancyRecord, ...]

    def payload(self) -> dict[str, object]:
        """Return a JSON-safe payload for one aggregate occupancy summary."""
        return {
            "total_batches": self.total_batches,
            "total_rows": self.total_rows,
            "batch_size_histogram": {
                str(batch_size): count
                for batch_size, count in sorted(self.batch_size_histogram.items())
            },
            "realized_max_batch_size": self.realized_max_batch_size,
            "realized_min_batch_size": self.realized_min_batch_size,
            "mean_batch_size": self.mean_batch_size,
            "peak_text_tokens_per_batch": self.peak_text_tokens_per_batch,
            "peak_codec_frames_per_batch": self.peak_codec_frames_per_batch,
            "batches": [record.payload() for record in self.batches],
        }


def summarize_batch_occupancy(
    *,
    row_metrics: list[TrainingRowBatchMetrics],
    planned_batches: list[list[int]],
) -> BatchOccupancySummary:
    """Summarize one resolved batch plan into occupancy evidence."""
    if len(planned_batches) == 0:
        raise ValueError("Batch occupancy summary requires at least one planned batch.")

    records: list[BatchOccupancyRecord] = []
    histogram: dict[int, int] = {}
    peak_text_tokens_per_batch = 0
    peak_codec_frames_per_batch = 0
    total_rows = 0

    for batch_index, batch in enumerate(planned_batches):
        row_count = len(batch)
        text_token_count = 0
        codec_frame_count = 0
        for row_index in batch:
            metrics = row_metrics[row_index]
            text_token_count += metrics.text_token_count
            codec_frame_count += metrics.codec_frame_count
        histogram[row_count] = histogram.get(row_count, 0) + 1
        peak_text_tokens_per_batch = max(peak_text_tokens_per_batch, text_token_count)
        peak_codec_frames_per_batch = max(peak_codec_frames_per_batch, codec_frame_count)
        total_rows += row_count
        records.append(
            BatchOccupancyRecord(
                batch_index=batch_index,
                row_count=row_count,
                text_token_count=text_token_count,
                codec_frame_count=codec_frame_count,
            )
        )

    batch_sizes = [record.row_count for record in records]
    return BatchOccupancySummary(
        total_batches=len(records),
        total_rows=total_rows,
        batch_size_histogram=histogram,
        realized_max_batch_size=max(batch_sizes),
        realized_min_batch_size=min(batch_sizes),
        mean_batch_size=(float(total_rows) / float(len(records))),
        peak_text_tokens_per_batch=peak_text_tokens_per_batch,
        peak_codec_frames_per_batch=peak_codec_frames_per_batch,
        batches=tuple(records),
    )
