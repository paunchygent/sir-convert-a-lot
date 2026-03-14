"""Throughput-profile contracts for Task 101 Qwen training.

Purpose:
    Define the bounded, explicit throughput profiles used to raise useful GPU
    work per launch without hiding the active batching policy.

Relationships:
    - Imported by the detached training CLI/orchestrator for launch defaults.
    - Imported by the patched in-container trainer setup to resolve the active
      bucketed batching policy.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BATCH_POLICY_KIND = "bucketed-frame-token-budget-v1"
DEFAULT_THROUGHPUT_PROFILE_LABEL = "hemma-throughput-aggressive-v1"


@dataclass(frozen=True)
class ThroughputBatchPolicy:
    """Resolved throughput policy for one Qwen training launch."""

    profile_label: str
    policy_kind: str
    max_batch_size: int
    max_tokens_per_batch: int
    max_codec_frames_per_batch: int
    length_bucket_boundaries: tuple[int, ...]


_PROFILE_DEFAULTS: dict[str, tuple[int, int, tuple[int, ...]]] = {
    "hemma-throughput-balanced-v1": (
        3072,
        640,
        (128, 192, 256, 320, 384, 448, 512, 640, 768, 896, 1024),
    ),
    "hemma-throughput-aggressive-v1": (
        4096,
        1024,
        (128, 192, 256, 320, 384, 448, 512, 640, 768, 896, 1024, 1280),
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
    max_tokens_per_batch, max_codec_frames_per_batch, length_bucket_boundaries = profile_defaults
    return ThroughputBatchPolicy(
        profile_label=profile_label,
        policy_kind=DEFAULT_BATCH_POLICY_KIND,
        max_batch_size=max_batch_size,
        max_tokens_per_batch=max_tokens_per_batch,
        max_codec_frames_per_batch=max_codec_frames_per_batch,
        length_bucket_boundaries=length_bucket_boundaries,
    )


def throughput_policy_payload(policy: ThroughputBatchPolicy) -> dict[str, object]:
    """Return a JSON-safe payload for one resolved throughput policy."""
    return {
        "profile_label": policy.profile_label,
        "policy_kind": policy.policy_kind,
        "max_batch_size": policy.max_batch_size,
        "max_tokens_per_batch": policy.max_tokens_per_batch,
        "max_codec_frames_per_batch": policy.max_codec_frames_per_batch,
        "length_bucket_boundaries": list(policy.length_bucket_boundaries),
    }
