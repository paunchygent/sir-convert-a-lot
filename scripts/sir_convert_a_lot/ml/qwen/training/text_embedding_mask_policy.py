"""Text-embedding mask policy contracts for Qwen fine-tuning.

Purpose:
    Define the canonical Task 101 text-embedding mask policies, keep launch
    defaults and backward-compatible legacy defaults explicit, and provide the
    small helpers needed to compute the active text-embedding span during batch
    collation.

Relationships:
    - Imported by the detached Qwen control plane when constructing settings.
    - Imported by the patched Qwen dataset and runtime fingerprint helpers.
    - Consumed by metadata loading so older launch artifacts stay compatible.
"""

from __future__ import annotations

from typing import Literal, get_args

TextEmbeddingMaskPolicy = Literal["legacy_codec_span", "text_span_only"]

LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY: TextEmbeddingMaskPolicy = "legacy_codec_span"
TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY: TextEmbeddingMaskPolicy = "text_span_only"
DEFAULT_TEXT_EMBEDDING_MASK_POLICY: TextEmbeddingMaskPolicy = (
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY
)
LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT: TextEmbeddingMaskPolicy = (
    LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY
)
TEXT_EMBEDDING_MASK_POLICY_CHOICES: tuple[str, ...] = get_args(TextEmbeddingMaskPolicy)


def resolve_text_embedding_mask_policy(
    value: str | None,
    *,
    default: TextEmbeddingMaskPolicy,
) -> TextEmbeddingMaskPolicy:
    """Return one validated mask policy, falling back to the provided default."""
    if value is None:
        return default
    if value == LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY:
        return LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY
    if value == TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY:
        return TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY
    supported_values = ", ".join(TEXT_EMBEDDING_MASK_POLICY_CHOICES)
    raise ValueError(
        f"Unsupported text-embedding mask policy `{value}`. Expected one of: {supported_values}."
    )


def active_text_embedding_length(
    *,
    policy: TextEmbeddingMaskPolicy,
    text_ids_len: int,
    codec_ids_len: int,
) -> int:
    """Return the active text-embedding span length for one collated row."""
    if text_ids_len <= 0:
        raise ValueError("`text_ids_len` must be positive to build the Qwen batch prefix.")
    if codec_ids_len < 0:
        raise ValueError("`codec_ids_len` must be non-negative.")
    if policy == LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY:
        return 8 + text_ids_len + codec_ids_len
    if policy == TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY:
        return 8 + text_ids_len - 2
    raise AssertionError(f"Unhandled text-embedding mask policy: {policy}")
