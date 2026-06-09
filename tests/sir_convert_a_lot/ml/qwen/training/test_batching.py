"""Focused tests for Qwen pilot training throughput batching.

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
from scripts.sir_convert_a_lot.ml.qwen.training.batch_plan_analysis import (
    build_singleton_fit_audit,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    ThroughputBatchPolicy,
    resolve_throughput_batch_policy,
)


def test_resolve_throughput_batch_policy_uses_aggressive_default_label() -> None:
    """The training lane should resolve the aggressive Qwen pilot training profile."""
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


def test_resolve_throughput_batch_policy_supports_frame_primary_profile() -> None:
    """The frame-primary profile should switch bucket grouping to codec-frame counts."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-balanced-frame-primary-v1",
        max_batch_size=8,
    )

    assert policy.profile_label == "hemma-throughput-balanced-frame-primary-v1"
    assert policy.max_tokens_per_batch == 3072
    assert policy.max_codec_frames_per_batch == 640
    assert policy.length_bucket_boundaries == (128, 192, 256, 320, 384, 448, 512, 640)
    assert policy.bucket_signal_kind == "codec-frame-count-v1"


def test_resolve_throughput_batch_policy_supports_quarantine_profile() -> None:
    """The quarantine profile should keep the stable cap while forcing long-row singletons."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-balanced-quarantine-v1",
        max_batch_size=8,
    )

    assert policy.profile_label == "hemma-throughput-balanced-quarantine-v1"
    assert policy.max_tokens_per_batch == 3072
    assert policy.max_codec_frames_per_batch == 640
    assert policy.long_row_singleton_codec_frame_threshold == 480


def test_resolve_throughput_batch_policy_supports_quarantine_tail_profile() -> None:
    """The quarantine-tail profile should expose narrower upper-tail boundaries."""
    policy = resolve_throughput_batch_policy(
        profile_label="hemma-throughput-balanced-quarantine-tail-v1",
        max_batch_size=8,
    )

    assert policy.profile_label == "hemma-throughput-balanced-quarantine-tail-v1"
    assert policy.long_row_singleton_codec_frame_threshold == 480
    assert policy.length_bucket_boundaries == (
        128,
        192,
        256,
        320,
        384,
        448,
        512,
        576,
        640,
        704,
        768,
        896,
        1024,
    )


def test_bucketed_batch_sampler_replays_deterministic_epoch_shuffle() -> None:
    """Train-batch shuffling should be explicit and reproducible per epoch."""
    sampler = BucketedBatchSampler(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=80),
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=70),
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=60),
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=50),
        ],
        policy=ThroughputBatchPolicy(
            profile_label="test-profile",
            policy_kind="bucketed-frame-token-budget-v1",
            max_batch_size=1,
            max_tokens_per_batch=512,
            max_codec_frames_per_batch=512,
            length_bucket_boundaries=(64, 96, 128),
            minimum_required_max_batch_size=1,
            bucket_signal_kind="combined-sequence-cost-v1",
            long_row_singleton_codec_frame_threshold=None,
        ),
        shuffle=True,
        shuffle_seed=23,
    )

    sampler.set_epoch(1)
    epoch_one_first = list(iter(sampler))
    epoch_one_second = list(iter(sampler))
    sampler.set_epoch(2)
    epoch_two = list(iter(sampler))

    assert epoch_one_first == epoch_one_second
    assert epoch_one_first != epoch_two


def test_bucketed_batch_sampler_can_disable_shuffle_for_eval_truth() -> None:
    """Held-out eval batching should preserve the planned deterministic order."""
    sampler = BucketedBatchSampler(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=80),
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=70),
            TrainingRowBatchMetrics(text_token_count=16, codec_frame_count=60),
        ],
        policy=ThroughputBatchPolicy(
            profile_label="test-profile",
            policy_kind="bucketed-frame-token-budget-v1",
            max_batch_size=1,
            max_tokens_per_batch=512,
            max_codec_frames_per_batch=512,
            length_bucket_boundaries=(64, 96, 128),
            minimum_required_max_batch_size=1,
            bucket_signal_kind="combined-sequence-cost-v1",
            long_row_singleton_codec_frame_threshold=None,
        ),
        shuffle=False,
        shuffle_seed=23,
    )

    assert list(iter(sampler)) == sampler.planned_batches()


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
            bucket_signal_kind="combined-sequence-cost-v1",
            long_row_singleton_codec_frame_threshold=None,
        ),
    )

    assert sampler.planned_batches() == [[0], [1, 2], [3]]


def test_bucketed_batch_sampler_quarantines_long_rows_into_singletons() -> None:
    """Long-row quarantine should remove near-budget rows from normal packing."""
    sampler = BucketedBatchSampler(
        row_metrics=[
            TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=500),
            TrainingRowBatchMetrics(text_token_count=9, codec_frame_count=480),
            TrainingRowBatchMetrics(text_token_count=8, codec_frame_count=120),
            TrainingRowBatchMetrics(text_token_count=7, codec_frame_count=110),
        ],
        policy=ThroughputBatchPolicy(
            profile_label="test-quarantine",
            policy_kind="bucketed-frame-token-budget-v1",
            max_batch_size=4,
            max_tokens_per_batch=1000,
            max_codec_frames_per_batch=640,
            length_bucket_boundaries=(1024,),
            minimum_required_max_batch_size=1,
            bucket_signal_kind="combined-sequence-cost-v1",
            long_row_singleton_codec_frame_threshold=480,
        ),
    )

    assert sampler.planned_batches() == [[0], [1], [2, 3]]


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


def test_bucketed_batch_sampler_can_use_codec_frame_primary_bucket_signal() -> None:
    """Frame-primary bucketing should group rows by codec frames rather than combined cost."""
    row_metrics = [
        TrainingRowBatchMetrics(text_token_count=140, codec_frame_count=300),
        TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=300),
        TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=280),
    ]
    combined_cost_sampler = BucketedBatchSampler(
        row_metrics=row_metrics,
        policy=ThroughputBatchPolicy(
            profile_label="test-combined-cost",
            policy_kind="bucketed-frame-token-budget-v1",
            max_batch_size=8,
            max_tokens_per_batch=1000,
            max_codec_frames_per_batch=640,
            length_bucket_boundaries=(400, 800),
            minimum_required_max_batch_size=1,
            bucket_signal_kind="combined-sequence-cost-v1",
            long_row_singleton_codec_frame_threshold=None,
        ),
    )
    frame_primary_sampler = BucketedBatchSampler(
        row_metrics=row_metrics,
        policy=ThroughputBatchPolicy(
            profile_label="test-frame-primary",
            policy_kind="bucketed-frame-token-budget-v1",
            max_batch_size=8,
            max_tokens_per_batch=1000,
            max_codec_frames_per_batch=640,
            length_bucket_boundaries=(280, 320),
            minimum_required_max_batch_size=1,
            bucket_signal_kind="codec-frame-count-v1",
            long_row_singleton_codec_frame_threshold=None,
        ),
    )

    assert combined_cost_sampler.planned_batches() == [[1, 2], [0]]
    assert frame_primary_sampler.planned_batches() == [[2], [0, 1]]


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


def test_singleton_fit_audit_detects_later_same_bucket_partner() -> None:
    """The audit should flag singleton rows that have a later fit in the same bucket."""
    policy = ThroughputBatchPolicy(
        profile_label="test-fit-audit-same-bucket",
        policy_kind="bucketed-frame-token-budget-v1",
        max_batch_size=8,
        max_tokens_per_batch=1000,
        max_codec_frames_per_batch=640,
        length_bucket_boundaries=(400, 800),
        minimum_required_max_batch_size=1,
        bucket_signal_kind="combined-sequence-cost-v1",
        long_row_singleton_codec_frame_threshold=None,
    )
    row_metrics = [
        TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=350),
        TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=300),
        TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=290),
    ]
    sampler = BucketedBatchSampler(row_metrics=row_metrics, policy=policy)

    summary = build_singleton_fit_audit(
        row_metrics=row_metrics,
        policy=policy,
        planned_batches=sampler.planned_batches(),
        codec_frame_band_min=320,
        codec_frame_band_max=375,
    )

    assert summary is not None
    assert summary.audited_singleton_count == 1
    assert summary.same_bucket_fit_count == 1
    assert summary.adjacent_lower_bucket_fit_count == 0
    assert summary.same_bucket_only_count == 1


def test_singleton_fit_audit_detects_adjacent_lower_bucket_partner() -> None:
    """The audit should flag singleton rows whose fit only exists in the adjacent lower bucket."""
    policy = ThroughputBatchPolicy(
        profile_label="test-fit-audit-lower-bucket",
        policy_kind="bucketed-frame-token-budget-v1",
        max_batch_size=8,
        max_tokens_per_batch=1000,
        max_codec_frames_per_batch=640,
        length_bucket_boundaries=(300, 500, 800),
        minimum_required_max_batch_size=1,
        bucket_signal_kind="combined-sequence-cost-v1",
        long_row_singleton_codec_frame_threshold=None,
    )
    row_metrics = [
        TrainingRowBatchMetrics(text_token_count=50, codec_frame_count=350),
        TrainingRowBatchMetrics(text_token_count=40, codec_frame_count=300),
        TrainingRowBatchMetrics(text_token_count=10, codec_frame_count=280),
    ]
    sampler = BucketedBatchSampler(row_metrics=row_metrics, policy=policy)

    summary = build_singleton_fit_audit(
        row_metrics=row_metrics,
        policy=policy,
        planned_batches=sampler.planned_batches(),
        codec_frame_band_min=320,
        codec_frame_band_max=375,
    )

    assert summary is not None
    assert summary.audited_singleton_count == 1
    assert summary.same_bucket_fit_count == 0
    assert summary.adjacent_lower_bucket_fit_count == 1
    assert summary.adjacent_lower_only_count == 1
