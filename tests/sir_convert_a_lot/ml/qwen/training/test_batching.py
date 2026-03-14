"""Focused tests for Task 101 throughput batching.

Purpose:
    Validate the aggressive bucketed batch sampler and shared throughput-profile
    resolution without requiring a live training run.

Relationships:
    - Exercises `sft_12hz_batching.py` and `training/throughput_profiles.py`.
"""

from __future__ import annotations

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import (
    BucketedBatchSampler,
    TrainingRowBatchMetrics,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
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
