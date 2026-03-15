"""Throughput-profile contracts for Task 101 Qwen training.

Purpose:
    Define the bounded, explicit throughput profiles used to raise useful GPU
    work per launch without hiding the active batching policy.

Relationships:
    - Imported by the control-plane defaults and launch use case for launch defaults.
    - Imported by the patched in-container trainer setup to resolve the active
      bucketed batching policy.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BATCH_POLICY_KIND = "bucketed-frame-token-budget-v1"
DEFAULT_THROUGHPUT_PROFILE_LABEL = "hemma-throughput-aggressive-v1"
DEFAULT_BUCKET_SIGNAL_KIND = "combined-sequence-cost-v1"


@dataclass(frozen=True)
class ThroughputProfileDefaults:
    """Static defaults for one named throughput profile."""

    max_tokens_per_batch: int
    max_codec_frames_per_batch: int
    length_bucket_boundaries: tuple[int, ...]
    minimum_required_max_batch_size: int
    bucket_signal_kind: str = DEFAULT_BUCKET_SIGNAL_KIND
    long_row_singleton_codec_frame_threshold: int | None = None


@dataclass(frozen=True)
class ThroughputBatchPolicy:
    """Resolved throughput policy for one Qwen training launch."""

    profile_label: str
    policy_kind: str
    max_batch_size: int
    max_tokens_per_batch: int
    max_codec_frames_per_batch: int
    length_bucket_boundaries: tuple[int, ...]
    minimum_required_max_batch_size: int
    bucket_signal_kind: str
    long_row_singleton_codec_frame_threshold: int | None


_PROFILE_DEFAULTS: dict[str, ThroughputProfileDefaults] = {
    "hemma-throughput-balanced-v1": ThroughputProfileDefaults(
        max_tokens_per_batch=3072,
        max_codec_frames_per_batch=640,
        length_bucket_boundaries=(128, 192, 256, 320, 384, 448, 512, 640, 768, 896, 1024),
        minimum_required_max_batch_size=1,
    ),
    "hemma-throughput-balanced-frame-primary-v1": ThroughputProfileDefaults(
        max_tokens_per_batch=3072,
        max_codec_frames_per_batch=640,
        length_bucket_boundaries=(128, 192, 256, 320, 384, 448, 512, 640),
        minimum_required_max_batch_size=1,
        bucket_signal_kind="codec-frame-count-v1",
    ),
    "hemma-throughput-balanced-quarantine-v1": ThroughputProfileDefaults(
        max_tokens_per_batch=3072,
        max_codec_frames_per_batch=640,
        length_bucket_boundaries=(128, 192, 256, 320, 384, 448, 512, 640, 768, 896, 1024),
        minimum_required_max_batch_size=1,
        long_row_singleton_codec_frame_threshold=480,
    ),
    "hemma-throughput-balanced-quarantine-tail-v1": ThroughputProfileDefaults(
        max_tokens_per_batch=3072,
        max_codec_frames_per_batch=640,
        length_bucket_boundaries=(
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
        ),
        minimum_required_max_batch_size=1,
        long_row_singleton_codec_frame_threshold=480,
    ),
    "hemma-throughput-balanced-plus-v1": ThroughputProfileDefaults(
        max_tokens_per_batch=3072,
        max_codec_frames_per_batch=768,
        length_bucket_boundaries=(128, 192, 256, 320, 384, 448, 576, 768, 1024),
        minimum_required_max_batch_size=1,
    ),
    "hemma-throughput-aggressive-v1": ThroughputProfileDefaults(
        max_tokens_per_batch=4096,
        max_codec_frames_per_batch=1024,
        length_bucket_boundaries=(
            128,
            192,
            256,
            320,
            384,
            448,
            512,
            640,
            768,
            896,
            1024,
            1280,
        ),
        minimum_required_max_batch_size=8,
    ),
}


def resolve_throughput_batch_policy(
    *,
    profile_label: str,
    max_batch_size: int,
) -> ThroughputBatchPolicy:
    """Resolve one explicit throughput policy from the named profile and cap."""
    if max_batch_size <= 0:
        raise ValueError("`max_batch_size` must be positive.")
    profile_defaults = _PROFILE_DEFAULTS.get(profile_label)
    if profile_defaults is None:
        supported = ", ".join(sorted(_PROFILE_DEFAULTS))
        raise ValueError(
            "Unsupported throughput profile label "
            f"`{profile_label}`. Supported values: {supported}."
        )
    if max_batch_size < profile_defaults.minimum_required_max_batch_size:
        raise ValueError(
            "Throughput profile requires a larger live `max_batch_size`: "
            f"profile_label={profile_label} "
            f"requested_max_batch_size={max_batch_size} "
            f"minimum_required_max_batch_size={profile_defaults.minimum_required_max_batch_size}"
        )
    return ThroughputBatchPolicy(
        profile_label=profile_label,
        policy_kind=DEFAULT_BATCH_POLICY_KIND,
        max_batch_size=max_batch_size,
        max_tokens_per_batch=profile_defaults.max_tokens_per_batch,
        max_codec_frames_per_batch=profile_defaults.max_codec_frames_per_batch,
        length_bucket_boundaries=profile_defaults.length_bucket_boundaries,
        minimum_required_max_batch_size=profile_defaults.minimum_required_max_batch_size,
        bucket_signal_kind=profile_defaults.bucket_signal_kind,
        long_row_singleton_codec_frame_threshold=(
            profile_defaults.long_row_singleton_codec_frame_threshold
        ),
    )


def throughput_policy_payload(
    policy: ThroughputBatchPolicy,
    *,
    batch_occupancy: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return a JSON-safe payload for one resolved throughput policy."""
    payload: dict[str, object] = {
        "profile_label": policy.profile_label,
        "policy_kind": policy.policy_kind,
        "max_batch_size": policy.max_batch_size,
        "max_tokens_per_batch": policy.max_tokens_per_batch,
        "max_codec_frames_per_batch": policy.max_codec_frames_per_batch,
        "length_bucket_boundaries": list(policy.length_bucket_boundaries),
        "minimum_required_max_batch_size": policy.minimum_required_max_batch_size,
        "bucket_signal_kind": policy.bucket_signal_kind,
        "long_row_singleton_codec_frame_threshold": (
            policy.long_row_singleton_codec_frame_threshold
        ),
    }
    if batch_occupancy is not None:
        payload["batch_occupancy"] = batch_occupancy
    return payload
