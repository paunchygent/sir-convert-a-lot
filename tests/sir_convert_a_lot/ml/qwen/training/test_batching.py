"""Focused tests for Task 101 throughput batching.

Purpose:
    Validate the aggressive bucketed batch sampler and shared throughput-profile
    resolution without requiring a live training run.

Relationships:
    - Exercises `sft_12hz_batching.py` and `training/throughput_profiles.py`.
"""

from __future__ import annotations

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_batch_occupancy import (
    summarize_batch_occupancy,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import (
    BucketedBatchSampler,
    TrainingRowBatchMetrics,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    ThroughputBatchPolicy,
    resolve_throughput_batch_policy,
)


def test_resolve_throughput_batch_policy_uses_aggressive_default_label() -> None:
    """The training lane should resolve the aggressive Task 101 profile."""
    policy = resolve_throughput_batch_policy(
        profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        max_batch_size=8,
    )

    assert policy.profile_label == DEFAULT_THROUGHPUT_PROFILE_LABEL
    assert policy.policy_kind == "bucketed-frame-token-budget-v1"
    assert policy.max_batch_size == 8
    assert policy.max_tokens_per_batch == 4096
    assert policy.max_codec_frames_per_batch == 1024
    assert policy.minimum_required_max_batch_size == 8


def test_resolve_throughput_batch_policy_rejects_tiny_aggressive_batch_caps() -> None:
    """The aggressive profile should fail closed when paired with tiny caps."""
    with pytest.raises(ValueError, match="minimum_required_max_batch_size=8"):
        resolve_throughput_batch_policy(
            profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
            max_batch_size=1,
        )


def test_resolve_throughput_batch_policy_supports_balanced_plus_profile() -> None:
    """The balanced-plus profile should lift frame budget without forcing aggressiveness."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-balanced-plus-v1",
        max_batch_size=8,
    )

    assert policy.profile_label == "hemma-throughput-balanced-plus-v1"
    assert policy.max_tokens_per_batch == 3072
    assert policy.max_codec_frames_per_batch == 768
    assert policy.length_bucket_boundaries == (128, 192, 256, 320, 384, 448, 576, 768, 1024)
    assert policy.minimum_required_max_batch_size == 1


def test_bucketed_batch_sampler_respects_batch_size_and_budget_caps() -> None:
    """The sampler should cap batches by both max size and codec-frame budget."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-aggressive-v1",
        max_batch_size=8,
    )
    sampler = BucketedBatchSampler(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=120, codec_frame_count=400),
            TrainingRowBatchMetrics(text_token_count=118, codec_frame_count=400),
            TrainingRowBatchMetrics(text_token_count=116, codec_frame_count=400),
            TrainingRowBatchMetrics(text_token_count=114, codec_frame_count=400),
        ],
        policy=policy,
    )

    batches = list(sampler)

    assert len(batches) == 2
    assert all(len(batch) == 2 for batch in batches)


def test_bucketed_batch_sampler_keeps_one_open_batch_per_bucket() -> None:
    """The stable packer should flush greedily instead of reshaping row mixtures."""
    sampler = BucketedBatchSampler(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=1, codec_frame_count=6),
            TrainingRowBatchMetrics(text_token_count=1, codec_frame_count=6),
            TrainingRowBatchMetrics(text_token_count=1, codec_frame_count=4),
            TrainingRowBatchMetrics(text_token_count=1, codec_frame_count=4),
        ],
        policy=ThroughputBatchPolicy(
            profile_label="test-greedy",
            policy_kind="bucketed-frame-token-budget-v1",
            max_batch_size=3,
            max_tokens_per_batch=100,
            max_codec_frames_per_batch=10,
            length_bucket_boundaries=(16,),
            minimum_required_max_batch_size=1,
        ),
    )

    assert sampler.planned_batches() == [[0], [1, 2], [3]]


def test_bucketed_batch_sampler_rejects_rows_that_exceed_single_row_budget() -> None:
    """One oversized row should fail closed before training starts."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-balanced-v1",
        max_batch_size=8,
    )

    with pytest.raises(ValueError, match="codec-frame budget"):
        BucketedBatchSampler(
            row_metrics=[
                TrainingRowBatchMetrics(text_token_count=100, codec_frame_count=800),
            ],
            policy=policy,
        )


def test_bucketed_batch_sampler_exposes_planned_batches_for_occupancy_reporting() -> None:
    """The sampler should expose the resolved batch plan for occupancy reporting."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-balanced-v1",
        max_batch_size=2,
    )
    sampler = BucketedBatchSampler(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=20),
            TrainingRowBatchMetrics(text_token_count=11, codec_frame_count=21),
            TrainingRowBatchMetrics(text_token_count=12, codec_frame_count=22),
        ],
        policy=policy,
    )

    planned_batches = sampler.planned_batches()
    yielded_batches = list(sampler)

    assert sorted(planned_batches) == sorted(yielded_batches)


def test_summarize_batch_occupancy_reports_histogram_and_per_batch_totals() -> None:
    """Occupancy summary should expose concrete row, token, and frame totals."""
    summary = summarize_batch_occupancy(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=20),
            TrainingRowBatchMetrics(text_token_count=11, codec_frame_count=21),
            TrainingRowBatchMetrics(text_token_count=12, codec_frame_count=22),
        ],
        planned_batches=[[0, 1], [2]],
    )

    assert summary.total_batches == 2
    assert summary.total_rows == 3
    assert summary.batch_size_histogram == {1: 1, 2: 1}
    assert summary.realized_max_batch_size == 2
    assert summary.realized_min_batch_size == 1
    assert summary.peak_text_tokens_per_batch == 21
    assert summary.peak_codec_frames_per_batch == 41
    assert summary.payload()["batches"] == [
        {
            "batch_index": 0,
            "row_count": 2,
            "text_token_count": 21,
            "codec_frame_count": 41,
        },
        {
            "batch_index": 1,
            "row_count": 1,
            "text_token_count": 12,
            "codec_frame_count": 22,
        },
    ]
